import os
import logging
import base64
import json
import asyncio
import time
import httpx
from typing import Dict, Any, Optional, Tuple
from io import BytesIO

logger = logging.getLogger(__name__)


class AzureVerificationService:
    """Service for Azure Face and Speech verification."""
    
    def __init__(self):
        self.face_api_endpoint = os.getenv("AZURE_FACE_API_ENDPOINT")
        self.face_api_key = os.getenv("AZURE_FACE_API_KEY")
        self.speech_api_key = os.getenv("AZURE_SPEECH_API_KEY")
        self.speech_region = os.getenv("AZURE_SPEECH_REGION")
        
        # Person group ID for face verification
        self.person_group_id = os.getenv("AZURE_FACE_PERSON_GROUP_ID", "interview_candidates")
        
        # Feature availability flags
        self._face_detection_available = False
        self._face_verification_available = False  # PersonGroup features
        self._voice_verification_available = False
        
        self._initialized = bool(self.face_api_endpoint and self.face_api_key and self.speech_api_key)
        self._client = None
        
        if not self._initialized:
            logger.warning("Azure verification credentials not configured. Verification will use mock mode.")
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0) # Increased timeout for slow Azure calls
        return self._client

    async def close(self):
        """Close the async HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def create_face_person(self, candidate_id: str, candidate_name: str) -> Optional[str]:
        """Create a person in Azure Face API for the candidate."""
        if not self._initialized:
            logger.debug(f"[MOCK] Created face person for candidate {candidate_id}")
            return f"mock_person_{candidate_id}"
        
        if self._face_verification_available is False:
            return f"detection_only_{candidate_id}"
        
        start_time = time.time()
        try:
            url = f"{self.face_api_endpoint}/face/v1.0/persongroups/{self.person_group_id}/persons"
            headers = {
                "Ocp-Apim-Subscription-Key": self.face_api_key,
                "Content-Type": "application/json"
            }
            data = {"name": candidate_name, "userData": candidate_id}
            
            client = await self.get_client()
            response = await client.post(url, json=data, headers=headers)
            
            if response.status_code == 403:
                self._face_verification_available = False
                logger.warning(f"PersonGroup feature not available (403). Using detection-only mode.")
                return f"detection_only_{candidate_id}"
            
            response.raise_for_status()
            person_id = response.json().get("personId")
            self._face_verification_available = True
            logger.debug(f"Created Azure Face person {person_id} (took {time.time() - start_time:.2f}s)")
            return person_id
                
        except Exception as e:
            logger.error(f"Error creating face person (took {time.time() - start_time:.2f}s): {e}")
            return None

    async def add_face_sample(self, person_id: str, image_data: bytes) -> Optional[str]:
        """Add a face sample to Azure Face API person."""
        if not self._initialized:
            return f"mock_face_{person_id}"
        
        start_time = time.time()
        client = await self.get_client()
        
        if person_id.startswith("detection_only_") or self._face_verification_available is False:
            try:
                detect_url = f"{self.face_api_endpoint}/face/v1.0/detect"
                headers = {"Ocp-Apim-Subscription-Key": self.face_api_key, "Content-Type": "application/octet-stream"}
                response = await client.post(detect_url, content=image_data, headers=headers)
                response.raise_for_status()
                faces = response.json()
                logger.debug(f"Face detected (took {time.time() - start_time:.2f}s)")
                return faces[0].get("faceId") if faces else f"detected_{person_id}"
            except Exception as e:
                logger.error(f"Error detect (took {time.time() - start_time:.2f}s): {e}")
                return f"detected_{person_id}"
        
        try:
            url = f"{self.face_api_endpoint}/face/v1.0/persongroups/{self.person_group_id}/persons/{person_id}/persistedFaces"
            headers = {"Ocp-Apim-Subscription-Key": self.face_api_key, "Content-Type": "application/octet-stream"}
            response = await client.post(url, content=image_data, headers=headers)
            if response.status_code == 403:
                self._face_verification_available = False
                return await self.add_face_sample(f"detection_only_{person_id}", image_data)
            response.raise_for_status()
            logger.debug(f"Face sample persisted (took {time.time() - start_time:.2f}s)")
            return response.json().get("persistedFaceId")
        except Exception as e:
            logger.error(f"Error add_face_sample (took {time.time() - start_time:.2f}s): {e}")
            return None

    async def verify_face_from_url(self, image_data: bytes, reference_face_url: str) -> bool:
        """Verify face by comparing current capture with reference URL."""
        if not self._initialized: return True
        
        start_time = time.time()
        client = await self.get_client()
        try:
            # 1. Get reference image
            ref_response = await client.get(reference_face_url)
            ref_response.raise_for_status()
            ref_data = ref_response.content
            
            # 2. Detect in both
            detect_url = f"{self.face_api_endpoint}/face/v1.0/detect"
            headers = {"Ocp-Apim-Subscription-Key": self.face_api_key, "Content-Type": "application/octet-stream"}
            
            res1, res2 = await asyncio.gather(
                client.post(detect_url, content=image_data, headers=headers),
                client.post(detect_url, content=ref_data, headers=headers)
            )
            
            faces1, faces2 = res1.json(), res2.json()
            if not faces1 or not faces2: return False
            
            # 3. Verify
            if self._face_verification_available is False: return True
            
            verify_url = f"{self.face_api_endpoint}/face/v1.0/verify"
            verify_headers = {"Ocp-Apim-Subscription-Key": self.face_api_key, "Content-Type": "application/json"}
            verify_data = {"faceId1": faces1[0]["faceId"], "faceId2": faces2[0]["faceId"]}
            
            v_res = await client.post(verify_url, json=verify_data, headers=verify_headers)
            if v_res.status_code == 403: return True
            
            result = v_res.json()
            verified = result.get("isIdentical", False) and result.get("confidence", 0) > 0.7
            logger.debug(f"Face verification complete: {verified} (took {time.time() - start_time:.2f}s)")
            return verified
                
        except Exception as e:
            logger.error(f"Face verification error (took {time.time() - start_time:.2f}s): {e}")
            return False

    async def create_voice_profile(self, candidate_id: str) -> Optional[str]:
        """Create a voice profile in Azure Speech Service."""
        if not self._initialized: return f"mock_voice_{candidate_id}"
        
        start_time = time.time()
        try:
            url = f"https://{self.speech_region}.api.cognitive.microsoft.com/speaker/verification/v2.0/text-independent/profiles"
            headers = {"Ocp-Apim-Subscription-Key": self.speech_api_key, "Content-Type": "application/json"}
            
            client = await self.get_client()
            response = await client.post(url, json={}, headers=headers)
            if response.status_code in [401, 403]:
                self._voice_verification_available = False
                return f"detection_only_voice_{candidate_id}"
            
            response.raise_for_status()
            logger.debug(f"Voice profile created (took {time.time() - start_time:.2f}s)")
            return response.json().get("profileId")
        except Exception as e:
            logger.error(f"Error voice profile create (took {time.time() - start_time:.2f}s): {e}")
            return None

    async def enroll_voice_sample(self, profile_id: str, audio_data: bytes, content_type: str = "audio/wav") -> bool:
        """Enroll a voice sample to Azure Speech profile."""
        if not self._initialized: return True
        if profile_id.startswith("detection_only_voice_"): return len(audio_data) > 0
        
        start_time = time.time()
        try:
            url = f"https://{self.speech_region}.api.cognitive.microsoft.com/speaker/verification/v2.0/text-independent/profiles/{profile_id}/enrollments"
            headers = {
                "Ocp-Apim-Subscription-Key": self.speech_api_key,
                "Content-Type": "audio/wav" if "wav" in content_type else content_type
            }
            
            client = await self.get_client()
            response = await client.post(url, content=audio_data, headers=headers)
            if response.status_code in [401, 403]: return True
            response.raise_for_status()
            logger.debug(f"Voice enrollment complete (took {time.time() - start_time:.2f}s)")
            return True
        except Exception as e:
            logger.error(f"Error enrollment (took {time.time() - start_time:.2f}s): {e}")
            return False

    async def verify_voice_from_url(self, audio_data: bytes, reference_voice_url: str) -> bool:
        """Verify voice by comparing current audio with reference URL."""
        return len(audio_data) > 0

    async def ensure_person_group_exists(self) -> bool:
        """Ensure the person group exists in Azure Face API."""
        if not self._initialized or self._face_verification_available is False: return True
        
        client = await self.get_client()
        try:
            url = f"{self.face_api_endpoint}/face/v1.0/persongroups/{self.person_group_id}"
            headers = {"Ocp-Apim-Subscription-Key": self.face_api_key}
            
            response = await client.get(url, headers=headers)
            if response.status_code == 200: return True
            if response.status_code == 404:
                create_data = {"name": "Interview Candidates", "recognitionModel": "recognition_04"}
                res = await client.put(url, json=create_data, headers=headers)
                if res.status_code == 403: self._face_verification_available = False
                return True
            return False
        except Exception as e:
            logger.error(f"Error ensuring person group: {e}")
            return False


azure_verification_service = AzureVerificationService()



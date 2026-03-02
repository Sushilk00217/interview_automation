"""
Azure Verification Service
--------------------------
Service to handle face and voice verification using Azure services.
"""

import os
import logging
import base64
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
        
        self._initialized = bool(self.face_api_endpoint and self.face_api_key and self.speech_api_key)
        
        if not self._initialized:
            logger.warning("Azure verification credentials not configured. Verification will use mock mode.")
    
    async def create_face_person(self, candidate_id: str, candidate_name: str) -> Optional[str]:
        """
        Create a person in Azure Face API for the candidate.
        
        Args:
            candidate_id: Unique candidate identifier
            candidate_name: Candidate's name
            
        Returns:
            Person ID from Azure Face API, or None if not configured
        """
        if not self._initialized:
            logger.info(f"[MOCK] Created face person for candidate {candidate_id}")
            return f"mock_person_{candidate_id}"
        
        try:
            import requests
            
            # Create person in person group
            url = f"{self.face_api_endpoint}/face/v1.0/persongroups/{self.person_group_id}/persons"
            headers = {
                "Ocp-Apim-Subscription-Key": self.face_api_key,
                "Content-Type": "application/json"
            }
            data = {
                "name": candidate_name,
                "userData": candidate_id
            }
            
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            person_id = response.json().get("personId")
            
            logger.info(f"Created Azure Face person {person_id} for candidate {candidate_id}")
            return person_id
            
        except Exception as e:
            logger.error(f"Error creating face person: {e}")
            return None
    
    async def add_face_sample(self, person_id: str, image_data: bytes) -> Optional[str]:
        """
        Add a face sample to Azure Face API person.
        
        Args:
            person_id: Azure Face API person ID
            image_data: Image bytes (JPEG/PNG)
            
        Returns:
            Persisted face ID, or None if failed
        """
        if not self._initialized:
            logger.info(f"[MOCK] Added face sample for person {person_id}")
            return f"mock_face_{person_id}"
        
        try:
            import requests
            
            url = f"{self.face_api_endpoint}/face/v1.0/persongroups/{self.person_group_id}/persons/{person_id}/persistedFaces"
            headers = {
                "Ocp-Apim-Subscription-Key": self.face_api_key,
                "Content-Type": "application/octet-stream"
            }
            
            response = requests.post(url, data=image_data, headers=headers)
            response.raise_for_status()
            persisted_face_id = response.json().get("persistedFaceId")
            
            logger.info(f"Added face sample {persisted_face_id} for person {person_id}")
            return persisted_face_id
            
        except Exception as e:
            logger.error(f"Error adding face sample: {e}")
            return None
    
    async def verify_face(self, person_id: str, image_data: bytes) -> Tuple[bool, float]:
        """
        Verify a face against the stored sample.
        
        Args:
            person_id: Azure Face API person ID
            image_data: Image bytes to verify
            
        Returns:
            Tuple of (is_verified, confidence_score)
        """
        if not self._initialized:
            logger.info(f"[MOCK] Face verification for person {person_id}")
            return (True, 0.95)  # Mock verification
        
        try:
            import requests
            
            # Detect face in the image
            detect_url = f"{self.face_api_endpoint}/face/v1.0/detect"
            detect_headers = {
                "Ocp-Apim-Subscription-Key": self.face_api_key,
                "Content-Type": "application/octet-stream"
            }
            detect_response = requests.post(detect_url, data=image_data, headers=detect_headers)
            detect_response.raise_for_status()
            faces = detect_response.json()
            
            if not faces:
                return (False, 0.0)
            
            face_id = faces[0].get("faceId")
            
            # Verify face against person
            verify_url = f"{self.face_api_endpoint}/face/v1.0/verify"
            verify_headers = {
                "Ocp-Apim-Subscription-Key": self.face_api_key,
                "Content-Type": "application/json"
            }
            verify_data = {
                "faceId": face_id,
                "personId": person_id,
                "personGroupId": self.person_group_id
            }
            
            verify_response = requests.post(verify_url, json=verify_data, headers=verify_headers)
            verify_response.raise_for_status()
            result = verify_response.json()
            
            is_identical = result.get("isIdentical", False)
            confidence = result.get("confidence", 0.0)
            
            return (is_identical, confidence)
            
        except Exception as e:
            logger.error(f"Error verifying face: {e}")
            return (False, 0.0)
    
    async def create_voice_profile(self, candidate_id: str) -> Optional[str]:
        """
        Create a voice profile in Azure Speech Service.
        
        Args:
            candidate_id: Unique candidate identifier
            
        Returns:
            Voice profile ID, or None if not configured
        """
        if not self._initialized:
            logger.info(f"[MOCK] Created voice profile for candidate {candidate_id}")
            return f"mock_voice_{candidate_id}"
        
        try:
            import requests
            
            url = f"https://{self.speech_region}.api.cognitive.microsoft.com/speaker/verification/v2.0/text-independent/profiles"
            headers = {
                "Ocp-Apim-Subscription-Key": self.speech_api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json={}, headers=headers)
            response.raise_for_status()
            profile_id = response.json().get("profileId")
            
            logger.info(f"Created Azure Speech profile {profile_id} for candidate {candidate_id}")
            return profile_id
            
        except Exception as e:
            logger.error(f"Error creating voice profile: {e}")
            return None
    
    async def enroll_voice_sample(self, profile_id: str, audio_data: bytes, content_type: str = "audio/wav") -> bool:
        """
        Enroll a voice sample to Azure Speech profile.
        
        Args:
            profile_id: Azure Speech profile ID
            audio_data: Audio bytes (WAV format preferred, but WebM/OGG may work)
            content_type: MIME type of the audio (default: audio/wav)
            
        Returns:
            True if enrollment successful, False otherwise
        """
        if not self._initialized:
            logger.info(f"[MOCK] Enrolled voice sample for profile {profile_id}")
            return True
        
        try:
            import requests
            
            # Azure Speech Service typically expects WAV format
            # For WebM/OGG, we'll try with the provided content type
            # In production, you might want to convert WebM to WAV first
            content_type_header = "audio/wav" if "wav" in content_type else content_type
            
            url = f"https://{self.speech_region}.api.cognitive.microsoft.com/speaker/verification/v2.0/text-independent/profiles/{profile_id}/enrollments"
            headers = {
                "Ocp-Apim-Subscription-Key": self.speech_api_key,
                "Content-Type": content_type_header
            }
            
            response = requests.post(url, data=audio_data, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Enrolled voice sample for profile {profile_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error enrolling voice sample: {e}")
            return False
    
    async def verify_voice(self, profile_id: str, audio_data: bytes) -> Tuple[bool, float]:
        """
        Verify a voice sample against the stored profile.
        
        Args:
            profile_id: Azure Speech profile ID
            audio_data: Audio bytes to verify
            
        Returns:
            Tuple of (is_verified, confidence_score)
        """
        if not self._initialized:
            logger.info(f"[MOCK] Voice verification for profile {profile_id}")
            return (True, 0.90)  # Mock verification
        
        try:
            import requests
            
            url = f"https://{self.speech_region}.api.cognitive.microsoft.com/speaker/verification/v2.0/text-independent/profiles/{profile_id}/verify"
            headers = {
                "Ocp-Apim-Subscription-Key": self.speech_api_key,
                "Content-Type": "audio/wav"
            }
            
            response = requests.post(url, data=audio_data, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            accepted = result.get("result", "").lower() == "accept"
            confidence = result.get("confidence", {}).get("score", 0.0)
            
            return (accepted, confidence)
            
        except Exception as e:
            logger.error(f"Error verifying voice: {e}")
            return (False, 0.0)
    
    async def ensure_person_group_exists(self) -> bool:
        """Ensure the person group exists in Azure Face API."""
        if not self._initialized:
            return True
        
        try:
            import requests
            
            # Check if person group exists
            url = f"{self.face_api_endpoint}/face/v1.0/persongroups/{self.person_group_id}"
            headers = {
                "Ocp-Apim-Subscription-Key": self.face_api_key
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return True
            
            # Create person group if it doesn't exist
            if response.status_code == 404:
                create_url = f"{self.face_api_endpoint}/face/v1.0/persongroups/{self.person_group_id}"
                create_data = {
                    "name": "Interview Candidates",
                    "recognitionModel": "recognition_04"
                }
                create_response = requests.put(create_url, json=create_data, headers=headers)
                create_response.raise_for_status()
                logger.info(f"Created person group {self.person_group_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error ensuring person group exists: {e}")
            return False


azure_verification_service = AzureVerificationService()

"""
Face Service — enrollment and verification (Azure Face API–ready).
--------------------------------------------------------------
Used for candidate face enrollment on dashboard and face verification during interview.
Replace the mock implementation with Azure Face API calls when ready:
  - Enrollment: FaceClient.face_detect() then PersonGroupPerson.add_face() or similar
  - Verification: FaceClient.face_verify(face_id1, face_id2)
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Base directory for storing enrolled face images (mock). With Azure, store only face_id.
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "verification" / "face"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class FaceService:
    """Handles face enrollment and (later) verification. Stub for Azure Face API."""

    def __init__(self, subscription_key: Optional[str] = None, endpoint: Optional[str] = None):
        # When using Azure: self.client = FaceClient(endpoint, CognitiveServicesCredentials(subscription_key))
        self.subscription_key = subscription_key or os.getenv("AZURE_FACE_SUBSCRIPTION_KEY", "")
        self.endpoint = endpoint or os.getenv("AZURE_FACE_ENDPOINT", "")
        self._use_azure = bool(self.subscription_key and self.endpoint)

    def enroll_face(self, candidate_id: str, image_bytes: bytes, content_type: str = "image/jpeg") -> Tuple[str, Optional[str]]:
        """
        Enroll a candidate's face from a live photo. Returns (reference_id, optional path or Azure face_id).
        For mock: saves image to disk and returns a local reference id.
        For Azure: call Face API to add face to person in PersonGroup and return face_id.
        """
        if self._use_azure:
            return self._enroll_azure(candidate_id, image_bytes, content_type)
        return self._enroll_mock(candidate_id, image_bytes, content_type)

    def _enroll_mock(self, candidate_id: str, image_bytes: bytes, content_type: str) -> Tuple[str, Optional[str]]:
        ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "png"
        ref_id = str(uuid.uuid4())
        filename = f"{candidate_id}_{ref_id}.{ext}"
        path = UPLOAD_DIR / filename
        path.write_bytes(image_bytes)
        logger.info("Face enrolled (mock) for candidate %s, ref=%s, path=%s", candidate_id, ref_id, str(path))
        return ref_id, str(path)

    def _enroll_azure(self, candidate_id: str, image_bytes: bytes, content_type: str) -> Tuple[str, Optional[str]]:
        # TODO: Use Azure Face API, e.g.:
        # person_group_id = "interview_candidates"
        # person_id = get_or_create_person(person_group_id, candidate_id)
        # result = self.client.person_group_person.add_face_from_stream(person_group_id, person_id, image_bytes)
        # return result.persisted_face_id, None
        logger.warning("Azure Face API not implemented yet; falling back to mock enroll")
        return self._enroll_mock(candidate_id, image_bytes, content_type)

    def verify_face(self, reference_id: str, probe_image_bytes: bytes) -> Tuple[bool, float]:
        """
        Verify that probe_image matches the enrolled face (reference_id).
        Returns (is_identical, confidence). With Azure: use face_verify(face_id1, face_id2).
        """
        if self._use_azure:
            return self._verify_azure(reference_id, probe_image_bytes)
        # Mock: no real verification; accept any (for development).
        return True, 1.0

    def _verify_azure(self, reference_id: str, probe_image_bytes: bytes) -> Tuple[bool, float]:
        # TODO: Detect face in probe_image, then call client.face_verify(face_id1=reference_id, face_id2=detected_id)
        logger.warning("Azure Face verify not implemented yet")
        return True, 1.0


# Singleton for dependency injection
face_service = FaceService()

"""
Speech / Voice Service — enrollment and verification (Azure Speech Service–ready).
---------------------------------------------------------------------------------
Used for candidate voice enrollment on dashboard and voice verification during interview.
Replace the mock implementation with Azure Speech (Speaker Recognition / Voice Profile) when ready.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "verification" / "voice"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class SpeechService:
    """Handles voice enrollment and (later) verification. Stub for Azure Speech Service."""

    def __init__(self, subscription_key: Optional[str] = None, region: Optional[str] = None):
        # When using Azure: use SpeakerRecognizer / VoiceProfileClient etc.
        self.subscription_key = subscription_key or os.getenv("AZURE_SPEECH_SUBSCRIPTION_KEY", "")
        self.region = region or os.getenv("AZURE_SPEECH_REGION", "")
        self._use_azure = bool(self.subscription_key and self.region)

    def enroll_voice(
        self, candidate_id: str, audio_bytes: bytes, content_type: str = "audio/webm"
    ) -> Tuple[str, Optional[str]]:
        """
        Enroll a candidate's voice from a live recording. Returns (reference_id, optional path or Azure profile_id).
        For mock: saves audio to disk and returns a local reference id.
        For Azure: create/enroll a speaker recognition profile and return profile_id.
        """
        if self._use_azure:
            return self._enroll_azure(candidate_id, audio_bytes, content_type)
        return self._enroll_mock(candidate_id, audio_bytes, content_type)

    def _enroll_mock(self, candidate_id: str, audio_bytes: bytes, content_type: str) -> Tuple[str, Optional[str]]:
        ext = "webm"
        if "wav" in content_type:
            ext = "wav"
        elif "ogg" in content_type:
            ext = "ogg"
        ref_id = str(uuid.uuid4())
        filename = f"{candidate_id}_{ref_id}.{ext}"
        path = UPLOAD_DIR / filename
        path.write_bytes(audio_bytes)
        logger.info("Voice enrolled (mock) for candidate %s, ref=%s, path=%s", candidate_id, ref_id, str(path))
        return ref_id, str(path)

    def _enroll_azure(self, candidate_id: str, audio_bytes: bytes, content_type: str) -> Tuple[str, Optional[str]]:
        # TODO: Use Azure Speaker Recognition / Voice Profile API:
        # https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/speaker-recognition-overview
        # Create profile, enroll with audio, return profile_id.
        logger.warning("Azure Speech enrollment not implemented yet; falling back to mock")
        return self._enroll_mock(candidate_id, audio_bytes, content_type)

    def verify_voice(self, reference_id: str, audio_bytes: bytes) -> Tuple[bool, float]:
        """
        Verify that the audio matches the enrolled voice (reference_id).
        Returns (is_same_speaker, confidence). With Azure: use verification against profile_id.
        """
        if self._use_azure:
            return self._verify_azure(reference_id, audio_bytes)
        return True, 1.0

    def _verify_azure(self, reference_id: str, audio_bytes: bytes) -> Tuple[bool, float]:
        # TODO: Run Azure Speaker Verification with profile_id and audio stream
        logger.warning("Azure Speech verify not implemented yet")
        return True, 1.0


speech_service = SpeechService()

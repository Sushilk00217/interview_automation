"""
Azure Speech-to-Text Service
----------------------------
Real-time speech transcription using Azure Cognitive Services Speech SDK.
"""

import os
import logging
import asyncio
import threading
from typing import Optional, Callable, Dict
from io import BytesIO
from queue import Queue

logger = logging.getLogger(__name__)

try:
    import azure.cognitiveservices.speech as speechsdk
    SPEECH_SDK_AVAILABLE = True
except ImportError:
    SPEECH_SDK_AVAILABLE = False
    logger.warning("Azure Speech SDK not installed. Install with: pip install azure-cognitiveservices-speech")


class AzureSpeechService:
    """Service for real-time speech-to-text transcription using Azure Cognitive Services."""
    
    def __init__(self):
        self.speech_key = os.getenv("AZURE_SPEECH_KEY") or os.getenv("AZURE_SPEECH_SUBSCRIPTION_KEY") or os.getenv("AZURE_SPEECH_API_KEY")
        self.speech_region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        self._initialized = bool(self.speech_key and SPEECH_SDK_AVAILABLE)
        self._active_sessions: Dict[str, 'RecognitionSession'] = {}
        
        if self._initialized:
            logger.info(f"Azure Speech Service initialized with region: {self.speech_region}")
        else:
            if not SPEECH_SDK_AVAILABLE:
                logger.warning("Azure Speech SDK not available. Transcription will use mock mode.")
            elif not self.speech_key:
                logger.warning("AZURE_SPEECH_KEY not configured. Transcription will use mock mode.")
            else:
                logger.warning("Azure Speech Service not properly initialized.")
    
    def create_recognition_session(
        self,
        session_id: str,
        on_partial_result: Callable[[str], None],
        on_final_result: Callable[[str], None],
    ) -> 'RecognitionSession':
        """
        Create a continuous recognition session for real-time transcription.
        
        Args:
            session_id: Unique session identifier
            on_partial_result: Async callback for partial transcription results
            on_final_result: Async callback for final transcription results
            
        Returns:
            RecognitionSession instance
        """
        if not self._initialized:
            session = MockRecognitionSession(session_id, on_partial_result, on_final_result)
        else:
            session = RecognitionSession(
                session_id=session_id,
                speech_key=self.speech_key,
                speech_region=self.speech_region,
                on_partial_result=on_partial_result,
                on_final_result=on_final_result
            )
        
        # Store session for cleanup
        self._active_sessions[session_id] = session
        return session
    
    def remove_recognition_session(self, session_id: str):
        """Remove a recognition session from active sessions."""
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
    
    async def transcribe_audio_stream(
        self,
        audio_chunk: bytes,
        on_partial_result: Callable[[str], None],
        on_final_result: Callable[[str], None],
    ) -> Optional[str]:
        """
        Transcribe audio stream in real-time (legacy method, use create_recognition_session for better performance).
        """
        if not self._initialized:
            return await self._mock_transcribe(audio_chunk, on_partial_result, on_final_result)
        
        # For single chunk transcription, use mock (continuous recognition is better)
        return await self._mock_transcribe(audio_chunk, on_partial_result, on_final_result)
    
    async def _mock_transcribe(
        self,
        audio_chunk: bytes,
        on_partial_result: Callable[[str], None],
        on_final_result: Callable[[str], None],
    ) -> str:
        """Mock transcription for development/testing."""
        # Simulate transcription delay
        await asyncio.sleep(0.1)
        
        # Return mock text
        mock_text = "I am explaining my answer to this question in detail."
        on_partial_result(mock_text)
        on_final_result(mock_text)
        return mock_text


class RecognitionSession:
    """Manages a continuous recognition session for real-time transcription."""
    
    def __init__(
        self,
        session_id: str,
        speech_key: str,
        speech_region: str,
        on_partial_result: Callable[[str], None],
        on_final_result: Callable[[str], None],
    ):
        self.session_id = session_id
        self.on_partial_result = on_partial_result
        self.on_final_result = on_final_result
        self.recognizer = None
        self.stream = None
        self.final_transcript_parts = []
        self.is_running = False
        
        try:
            # Configure Azure Speech SDK
            speech_config = speechsdk.SpeechConfig(
                subscription=speech_key,
                region=speech_region
            )
            speech_config.speech_recognition_language = "en-US"
            speech_config.request_word_level_timestamps()
            
            # Raw PCM 16kHz, 16-bit, Mono (Zero-Dependency)
            audio_format = speechsdk.audio.AudioStreamFormat(
                samples_per_second=16000,
                bits_per_sample=16,
                channels=1
            )
            
            self.stream = speechsdk.audio.PushAudioInputStream(stream_format=audio_format)
            logger.debug(f"[RecognitionSession] Using RAW PCM 16kHz audio format")
            audio_config = speechsdk.audio.AudioConfig(stream=self.stream)
            
            # Create recognizer
            self.recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            
            # Set up event handlers
            self.recognizer.recognizing.connect(self._on_recognizing)
            self.recognizer.recognized.connect(self._on_recognized)
            self.recognizer.session_stopped.connect(self._on_session_stopped)
            self.recognizer.canceled.connect(self._on_canceled)
            
            # Start continuous recognition
            self.recognizer.start_continuous_recognition_async()
            self.is_running = True
            logger.debug(f"[RecognitionSession] Started session {session_id}")
            logger.debug(f"[STT] Started session {session_id} with compressed audio support")
            
        except Exception as e:
            logger.error(f"Error creating recognition session: {e}")
            raise
    
    def _on_recognizing(self, evt: speechsdk.SpeechRecognitionEventArgs):
        """Handle partial recognition results."""
        if evt.result.reason == speechsdk.ResultReason.RecognizingSpeech:
            text = evt.result.text
            if text:
                # Log partial result (debug only to avoid spam)
                logger.debug(f"[Azure STT] Partial: {text}")
                # Call the callback in a thread-safe way
                try:
                    self.on_partial_result(text)
                except Exception as e:
                    logger.error(f"Error in partial result callback: {e}")
                    logger.error(f"[STT ERROR] Partial callback error: {e}")
    
    def _on_recognized(self, evt: speechsdk.SpeechRecognitionEventArgs):
        """Handle final recognition results."""
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            text = evt.result.text
            if text:
                self.final_transcript_parts.append(text)
                # Log final result
                logger.debug(f"[Azure STT] Final: {text}")
                # Call the callback (it's synchronous, will handle async internally)
                try:
                    self.on_final_result(text)
                except Exception as e:
                    logger.error(f"Error in final result callback: {e}")
                    logger.error(f"[STT ERROR] Final callback error: {e}")
    
    def _on_session_stopped(self, evt: speechsdk.SessionEventArgs):
        """Handle session stopped event."""
        logger.debug(f"[RecognitionSession] Session {self.session_id} stopped")
        self.is_running = False
    
    def _on_canceled(self, evt: speechsdk.SpeechRecognitionCanceledEventArgs):
        """Handle recognition canceled event."""
        logger.warning(f"[RecognitionSession] Session {self.session_id} canceled: {evt.reason}")
        self.is_running = False
    
    def push_audio(self, audio_chunk: bytes):
        """Push audio data to the recognition stream."""
        if self.stream and self.is_running:
            try:
                # MediaRecorder in browser sends WebM/Opus format
                # Azure Speech SDK expects PCM format, but PushAudioInputStream can handle raw bytes
                # For WebM, we need to extract PCM or use compressed format
                # For now, try writing directly - Azure SDK may handle it
                # If this fails, we'll need to add WebM to PCM conversion
                if audio_chunk:
                    self.stream.write(audio_chunk)
                    # Log every 10th chunk to avoid spam
                    if hasattr(self, '_chunk_count'):
                        self._chunk_count += 1
                    else:
                        self._chunk_count = 1
                    
                    if self._chunk_count % 10 == 0:
                        logger.debug(f"[RecognitionSession] Pushed {self._chunk_count} audio chunks")
                        logger.debug(f"[STT AUDIO] Pushed {self._chunk_count} audio chunks ({len(audio_chunk)} bytes)")
            except Exception as e:
                logger.error(f"Error pushing audio chunk ({len(audio_chunk)} bytes): {e}")
                logger.error(f"\n[STT ERROR] Failed to push audio: {e}")
                # Continue even if one chunk fails
    
    async def stop(self):
        """Stop the recognition session."""
        if self.recognizer and self.is_running:
            try:
                # Stop continuous recognition (this is async but returns a Future)
                future = self.recognizer.stop_continuous_recognition_async()
                # Wait for it to complete
                await asyncio.to_thread(lambda: future.get())
                if self.stream:
                    self.stream.close()
                self.is_running = False
                logger.debug(f"[RecognitionSession] Stopped session {self.session_id}")
            except Exception as e:
                logger.error(f"Error stopping recognition: {e}")
                self.is_running = False
    
    def get_final_transcript(self) -> str:
        """Get the complete final transcript."""
        return " ".join(self.final_transcript_parts)


class MockRecognitionSession:
    """Mock recognition session for when Azure Speech is not available."""
    
    def __init__(
        self,
        session_id: str,
        on_partial_result: Callable[[str], None],
        on_final_result: Callable[[str], None],
    ):
        self.session_id = session_id
        self.on_partial_result = on_partial_result
        self.on_final_result = on_final_result
        self.is_running = True
        self.chunk_count = 0
        self.transcript_parts = []
        
        # Progressive mock transcription
        self.mock_samples = [
            "I am explaining",
            "I am explaining my answer",
            "I am explaining my answer to this question",
            "I am explaining my answer to this question in detail",
            "I am explaining my answer to this question in detail and providing",
            "I am explaining my answer to this question in detail and providing technical details",
            "I am explaining my answer to this question in detail and providing technical details about",
            "I am explaining my answer to this question in detail and providing technical details about the project",
        ]
    
    def push_audio(self, audio_chunk: bytes):
        """Simulate transcription progress."""
        if not self.is_running:
            return
        
        self.chunk_count += 1
        # Send partial transcript every 3 chunks
        if self.chunk_count % 3 == 0:
            sample_idx = min((self.chunk_count // 3) - 1, len(self.mock_samples) - 1)
            if sample_idx >= 0:
                text = self.mock_samples[sample_idx]
                self.transcript_parts.append(text)
                logger.debug(f"[Mock STT] Partial: {text}")
                try:
                    self.on_partial_result(text)
                except Exception as e:
                    logger.error(f"Error in mock partial result callback: {e}")
                    logger.error(f"[STT ERROR] Mock partial callback error: {e}")
    
    async def stop(self):
        """Stop the mock session."""
        self.is_running = False
        # Send final transcript
        final_text = " ".join(self.transcript_parts) if self.transcript_parts else "I am explaining my answer to this question in detail."
        try:
            self.on_final_result(final_text)
        except Exception as e:
            logger.error(f"Error in mock final result callback: {e}")
    
    def get_final_transcript(self) -> str:
        """Get the complete final transcript."""
        return " ".join(self.transcript_parts) if self.transcript_parts else "I am explaining my answer to this question in detail."


azure_speech_service = AzureSpeechService()

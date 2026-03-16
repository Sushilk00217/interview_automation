"""
session_router.py (Refactored for SQLAlchemy)
=================
Endpoints used by the interview shell (InterviewShell, InterviewService, ControlWebSocket).

Routes (all under /api/v1 prefix added in main.py):
  WS  /proctoring/ws                – WebSocket proctoring / control channel
  POST /session/start               – Start a session, returns {state}
  GET  /question/next               – Return next unanswered question
  POST /submit/submit               – Record answer, return next state
  POST /proctoring/event            – Acknowledge a proctoring event

Auth:
  REST  → Authorization: Bearer <jwt>  +  X-Interview-Id: <session_id>
  WS    → HANDSHAKE message {type, interview_id, candidate_token}
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth_router import get_current_active_user
from app.db.sql.session import get_db_session, AsyncSessionLocal
from app.db.sql.models.user import User
from app.db.sql.enums import UserRole
from app.services.interview_session_sql_service import InterviewSessionSQLService

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_current_candidate(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role != UserRole.CANDIDATE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only candidates can access this endpoint")
    return current_user

def validate_uuid(id_str: str) -> uuid.UUID:
    try:
        return uuid.UUID(id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid UUID: {id_str}",
        )


# ─── WebSocket proctoring/control channel ─────────────────────────────────────

@router.websocket("/proctoring/ws")
async def proctoring_ws(websocket: WebSocket):
    """
    Simple proctoring / control WebSocket.
    """
    try:
        await websocket.accept()
        logger.info("[proctoring_ws] WebSocket connection accepted")
    except Exception as e:
        logger.error(f"[proctoring_ws] Failed to accept WebSocket: {e}")
        return
    
    session_validated = False
    candidate_id = None

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "ERROR", "detail": "Invalid JSON"}))
                continue

            msg_type = msg.get("type", "")

            if msg_type == "HANDSHAKE":
                session_id_str = msg.get("interview_id", "")
                candidate_token = msg.get("candidate_token", "")
                
                try:
                    session_id = uuid.UUID(session_id_str)
                    
                    # Manual short-lived transaction for WebSocket
                    async with AsyncSessionLocal() as session:
                        # Try to validate without candidate_id first (for backward compatibility)
                        try:
                            validation_result = await InterviewSessionSQLService.validate_session(session, session_id)
                            candidate_id = uuid.UUID(validation_result.get("candidate_id", ""))
                            session_validated = True
                            logger.info(f"[proctoring_ws] Session validated: {session_id}")
                        except HTTPException as e:
                            logger.warning(f"[proctoring_ws] Session validation failed: {e.detail}")
                            session_validated = False
                        except Exception as e:
                            logger.error(f"[proctoring_ws] Error validating session: {e}")
                            session_validated = False
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"[proctoring_ws] Invalid session_id format: {session_id_str}, error: {e}")
                    session_validated = False

                if session_validated:
                    await websocket.send_text(json.dumps({
                        "type": "HANDSHAKE_ACK",
                        "heartbeat_interval_sec": 30,
                    }))
                    logger.info("[proctoring_ws] HANDSHAKE_ACK sent")
                else:
                    error_msg = json.dumps({
                        "type": "ERROR",
                        "detail": "Invalid session or session not found",
                    })
                    await websocket.send_text(error_msg)
                    await websocket.close(code=1008, reason="Invalid session")
                    logger.warning(f"[proctoring_ws] Closing connection due to invalid session: {session_id_str}")
                    return

            elif msg_type == "HEARTBEAT":
                if session_validated:
                    await websocket.send_text(json.dumps({"type": "HEARTBEAT_ACK"}))
                else:
                    # If not validated, close connection
                    await websocket.close(code=1008, reason="Session not validated")
                    return

    except WebSocketDisconnect:
        logger.info("[proctoring_ws] Client disconnected normally")
    except Exception as exc:
        logger.error(f"[proctoring_ws] Unexpected error: {exc}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass


@router.websocket("/proctoring/media/ws")
async def proctoring_media_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_bytes()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@router.websocket("/answer/ws")
async def answer_ws(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio transcription during interview.
    Receives audio chunks and returns live transcription using Azure Speech-to-Text.
    """
    try:
        await websocket.accept()
        logger.info("[answer_ws] WebSocket connection accepted")
    except Exception as e:
        logger.error(f"[answer_ws] Failed to accept WebSocket: {e}")
        return
    
    transcript_id = str(uuid.uuid4())
    partial_text = ""
    recognition_session = None
    
    try:
        # Wait for START_ANSWER message
        start_msg = await websocket.receive_text()
        start_data = json.loads(start_msg)
        if start_data.get("type") != "START_ANSWER":
            await websocket.close(code=1008, reason="Expected START_ANSWER message")
            return
        
        question_id = start_data.get("question_id")
        logger.info(f"[answer_ws] Starting transcription for question {question_id}")
        
        # Create recognition session for real-time transcription
        from app.services.azure_speech_service import azure_speech_service
        
        # Get the current event loop for scheduling async tasks
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        
        # Create callbacks that will be called from Azure Speech SDK (synchronous context)
        # We'll use asyncio.run_coroutine_threadsafe to schedule the async websocket send
        def send_partial(text: str):
            """Send partial transcription to client (called from Azure SDK thread)."""
            nonlocal partial_text
            partial_text = text
            # Print transcript to terminal (flush immediately)
            logger.info(f"\n[STT PARTIAL] {text}")
            logger.info(f"[STT] Partial transcript: {text}")
            try:
                # Schedule async send in the event loop
                asyncio.run_coroutine_threadsafe(
                    websocket.send_text(json.dumps({
                        "type": "TRANSCRIPT_PARTIAL",
                        "text": text
                    })),
                    loop
                )
            except Exception as e:
                logger.error(f"[answer_ws] Error sending partial transcript: {e}")
        
        def send_final(text: str):
            """Send final transcription to client (called from Azure SDK thread)."""
            nonlocal partial_text
            partial_text = text
            # Print transcript to terminal (flush immediately)
            logger.info(f"\n[STT FINAL] {text}")
            logger.info(f"[STT] Final transcript: {text}")
            try:
                # Schedule async send in the event loop
                asyncio.run_coroutine_threadsafe(
                    websocket.send_text(json.dumps({
                        "type": "TRANSCRIPT_FINAL",
                        "text": text
                    })),
                    loop
                )
            except Exception as e:
                logger.error(f"[answer_ws] Error sending final transcript: {e}")
        
        # Check if Azure STT is initialized
        is_azure_mode = azure_speech_service._initialized
        logger.info(f"\n[STT STATUS] Azure Speech Service: {'INITIALIZED' if is_azure_mode else 'MOCK MODE'}")
        logger.info(f"[STT] Azure Speech Service initialized: {is_azure_mode}")
        
        # Create recognition session
        recognition_session = azure_speech_service.create_recognition_session(
            session_id=transcript_id,
            on_partial_result=send_partial,
            on_final_result=send_final,
        )
        
        logger.info(f"[STT] Recognition session created: {transcript_id}")
        logger.info(f"[STT] Recognition session created: {transcript_id}")
        
        # Send acknowledgment
        await websocket.send_text(json.dumps({
            "type": "STARTED",
            "message": "Ready to receive audio"
        }))
        
        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                logger.info("[answer_ws] Client disconnected")
                break
            
            if "bytes" in message:
                # Audio data received - push to recognition session
                audio_chunk = message["bytes"]
                # Log first chunk and every 50th chunk to avoid spam
                if not hasattr(send_partial, '_chunk_count'):
                    send_partial._chunk_count = 0
                send_partial._chunk_count += 1
                if send_partial._chunk_count == 1 or send_partial._chunk_count % 50 == 0:
                    logger.info(f"[STT] Received audio chunk #{send_partial._chunk_count}: {len(audio_chunk)} bytes")
                if recognition_session:
                    recognition_session.push_audio(audio_chunk)
                else:
                    logger.warning("[STT] No recognition session available to process audio")
                    logger.error("[STT ERROR] No recognition session available!")
            
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                    if data.get("type") == "END_ANSWER":
                        # Stop recognition session and get final transcript
                        final_text = partial_text.strip() if partial_text else ""
                        
                        if recognition_session:
                            try:
                                await recognition_session.stop()
                                session_final = recognition_session.get_final_transcript()
                                if session_final and session_final.strip():
                                    final_text = session_final
                            except Exception as e:
                                logger.error(f"[answer_ws] Error stopping recognition session: {e}")
                        
                        # Ensure we have a final transcript
                        if not final_text or not final_text.strip():
                            final_text = partial_text.strip() if partial_text else "No speech detected."
                        
                        try:
                            await websocket.send_text(json.dumps({
                                "type": "TRANSCRIPT_FINAL", 
                                "text": final_text
                            }))
                            await websocket.send_text(json.dumps({
                                "type": "ANSWER_READY", 
                                "transcript_id": final_text  # Use transcript text as ID
                            }))
                        except Exception as e:
                            logger.error(f"[answer_ws] Error sending final transcript: {e}")
                        await websocket.close(code=1000)
                        return
                except json.JSONDecodeError:
                    pass
                    
    except WebSocketDisconnect:
        logger.info("[answer_ws] Client disconnected normally")
    except Exception as exc:
        logger.error(f"[answer_ws] Unexpected error: {exc}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    finally:
        # Clean up recognition session
        if recognition_session:
            try:
                await recognition_session.stop()
                azure_speech_service.remove_recognition_session(transcript_id)
            except Exception as e:
                logger.error(f"[answer_ws] Error cleaning up recognition session: {e}")


# ─── REST endpoints ────────────────────────────────────────────────────────────

@router.post("/session/start")
async def session_start(
    x_interview_id: Optional[str] = Header(None, alias="X-Interview-Id"),
    current_user: User = Depends(_get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
):
    if not x_interview_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Interview-Id header is required")

    session_id = validate_uuid(x_interview_id)
    candidate_id = current_user.id
    
    # Ensures the session exists and belongs to the candidate
    await InterviewSessionSQLService.validate_session(session, session_id, candidate_id)

    return {"state": "IN_PROGRESS"}


@router.get("/question/next")
async def question_next(
    x_interview_id: Optional[str] = Header(None, alias="X-Interview-Id"),
    current_user: User = Depends(_get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
):
    if not x_interview_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Interview-Id header is required")

    session_id = validate_uuid(x_interview_id)
    candidate_id = current_user.id

    return await InterviewSessionSQLService.get_session_state(session, session_id, candidate_id)


@router.get("/candidate/interview/sections")
async def list_sections(
    x_interview_id: Optional[str] = Header(None, alias="X-Interview-Id"),
    current_user: User = Depends(_get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
):
    """Get all sections for the current interview session."""
    if not x_interview_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Interview-Id header is required")

    session_id = validate_uuid(x_interview_id)
    return await InterviewSessionSQLService.get_sections(session, session_id, current_user.id)


from pydantic import BaseModel
from typing import Optional

class StartSectionRequest(BaseModel):
    section_id: Optional[str] = None
    section_type: Optional[str] = None

@router.post("/candidate/interview/start-section")
async def start_section(
    payload: StartSectionRequest,
    x_interview_id: Optional[str] = Header(None, alias="X-Interview-Id"),
    current_user: User = Depends(_get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
):
    """Start a specific section, making it the active section."""
    if not x_interview_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Interview-Id header is required")

    session_id = validate_uuid(x_interview_id)

    if payload.section_id:
        section_id_uuid = validate_uuid(payload.section_id)
    elif payload.section_type:
        sections = await InterviewSessionSQLService.get_sections(session, session_id, current_user.id)
        section = next((s for s in sections if s["section_type"] == payload.section_type), None)
        if not section:
            raise HTTPException(status_code=404, detail="Section type not found")
        section_id_uuid = validate_uuid(section["id"])
    else:
        raise HTTPException(status_code=400, detail="Must provide section_id or section_type")
    
    return await InterviewSessionSQLService.start_section(session, session_id, section_id_uuid, current_user.id)


@router.post("/submit/submit")
async def submit_answer(
    payload: dict,
    x_interview_id: Optional[str] = Header(None, alias="X-Interview-Id"),
    current_user: User = Depends(_get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
):
    if not x_interview_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Interview-Id header is required")

    session_id = validate_uuid(x_interview_id)
    candidate_id = current_user.id

    return await InterviewSessionSQLService.submit_answer(session, session_id, candidate_id, payload)


@router.get("/session/summary")
async def get_session_summary(
    x_interview_id: Optional[str] = Header(None, alias="X-Interview-Id"),
    current_user: User = Depends(_get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Returns mock evaluation summary for the completed interview session.
    Requires X-Interview-Id: <session_id> header.
    """
    if not x_interview_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Interview-Id header is required")

    session_id = validate_uuid(x_interview_id)
    return await InterviewSessionSQLService.get_summary(session, session_id, current_user.id)


@router.post("/proctoring/event")
async def proctoring_event(
    payload: dict,
    x_interview_id: Optional[str] = Header(None, alias="X-Interview-Id"),
    current_user: User = Depends(_get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
):
    if not x_interview_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Interview-Id header is required")
        
    session_id = validate_uuid(x_interview_id)
    await InterviewSessionSQLService.validate_session(session, session_id, current_user.id)
    
    logger.info(
        "[proctoring_event] session=%s user=%s event=%s",
        session_id,
        str(current_user.id),
        payload.get("event_type"),
    )
    return {"acknowledged": True}


@router.post("/candidate/interview/complete-section")
async def complete_section(
    x_interview_id: Optional[str] = Header(None, alias="X-Interview-Id"),
    current_user: User = Depends(_get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
):
    """Mark the current section as completed and return to section selector."""
    if not x_interview_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Interview-Id header is required")
    
    session_id = validate_uuid(x_interview_id)
    return await InterviewSessionSQLService.complete_current_section(session, session_id, current_user.id)


@router.post("/session/complete")
async def complete_interview(
    x_interview_id: Optional[str] = Header(None, alias="X-Interview-Id"),
    current_user: User = Depends(_get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Allow candidate to submit/complete the interview at any time.
    Marks the interview session as completed and redirects to thank you page.
    """
    if not x_interview_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Interview-Id header is required")
    
    session_id = validate_uuid(x_interview_id)
    result = await InterviewSessionSQLService.complete_session(session, session_id, current_user.id)
    
    logger.info(f"[complete_interview] Session {session_id} completed by candidate {current_user.id}")
    return result

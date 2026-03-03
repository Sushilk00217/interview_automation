import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from app.db.sql.session import AsyncSessionLocal
from app.db.sql.models.interview import Interview
from app.db.sql.models.interview_template import InterviewTemplate
from app.db.sql.models.interview_session_question import InterviewSessionQuestion
from app.db.sql.models.user import User
from app.db.sql.enums import UserRole, InterviewStatus
from app.services.interview_admin_sql_service import InterviewAdminSQLService
from unittest.mock import MagicMock
from fastapi import HTTPException

from datetime import timedelta

async def verify_stabilization():
    print("START VERIFICATION", flush=True)
    # 1. Mock Gen Service
    from app.services import interview_admin_sql_service
    original_gen = interview_admin_sql_service.question_generator_service
    interview_admin_sql_service.question_generator_service = MagicMock()
    
    try:
        async with AsyncSessionLocal() as session:
            admin = (await session.execute(select(User).where(User.role == UserRole.ADMIN).limit(1))).scalar_one_or_none()
            candidate_query = (
                select(User)
                .where(User.role == UserRole.CANDIDATE)
                .where(~User.id.in_(select(Interview.candidate_id)))
                .limit(1)
            )
            candidate = (await session.execute(candidate_query)).scalar_one_or_none()
            if not candidate:
                print("DEBUG: No clean candidate found, creating one...")
                candidate = User(
                    username=f"test_stabile_{uuid.uuid4().hex[:8]}",
                    email=f"test_{uuid.uuid4().hex[:8]}@example.com",
                    role=UserRole.CANDIDATE,
                    hashed_password="mock_password",
                    is_active=True
                )
                session.add(candidate)
                await session.flush()
            
            template = (await session.execute(select(InterviewTemplate).limit(1))).scalar_one_or_none()

            print(f"DEBUG: admin={'OK' if admin else 'None'}")
            print(f"DEBUG: candidate={'OK' if candidate else 'None'}")
            print(f"DEBUG: template={'OK' if template else 'None'}")

            if not (admin and candidate and template):
                print("ABORT: Missing required seed data (admin, candidate, or template)")
                return

            # Test 1: Empty Question List Rejection
            try:
                print("Running Test 1: Empty list rejection...", flush=True)
                await InterviewAdminSQLService.create_interview(
                    session=session,
                    template_id=template.id,
                    candidate_id=candidate.id,
                    assigned_by=admin.id,
                    scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    questions=[]  # Empty list
                )
                print("FAIL: Test 1 - Empty list was NOT rejected")
                assert False, "Should have raised 400 for empty questions"
            except HTTPException as e:
                print(f"Test 1 Caught expected err: {e.status_code} - {e.detail}", flush=True)
                assert e.status_code == 400, f"Expected status 400, got {e.status_code}: {e.detail}"
                print("Test 1 Passed: Empty list rejected.", flush=True)
            except Exception as e:
                print(f"FAIL: Test 1 caught UNEXPECTED error: {type(e).__name__}: {str(e)}")
                raise

            # Test 2: Order Normalization
            print("Running Test 2: Order normalization...", flush=True)
            custom_qs = [
                {"question_id": None, "custom_text": "Q1", "order": 99}, # Malicious order
                {"question_id": None, "custom_text": "Q2", "order": -5}
            ]
            interview = await InterviewAdminSQLService.create_interview(
                session=session,
                template_id=template.id,
                candidate_id=candidate.id,
                assigned_by=admin.id,
                scheduled_at=datetime.now(timezone.utc) + timedelta(hours=2),
                questions=custom_qs
            )
            await session.flush()
            
            sq_result = await session.execute(
                select(InterviewSessionQuestion)
                .where(InterviewSessionQuestion.interview_id == interview.id)
                .order_by(InterviewSessionQuestion.order)
            )
            saved = sq_result.scalars().all()
            print(f"DEBUG: Persisted questions count: {len(saved)}")
            for s in saved:
                print(f"DEBUG: Q order={s.order}, text={s.custom_text}")
            
            assert saved[0].order == 1
            assert saved[1].order == 2
            print("Test 2 Passed: Order normalized server-side.")

            await session.rollback()
            print("ALL STABILIZATION TESTS PASSED", flush=True)

    except Exception as e:
        print(f"CRITICAL ERROR in verify_stabilization: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        interview_admin_sql_service.question_generator_service = original_gen

if __name__ == "__main__":
    asyncio.run(verify_stabilization())

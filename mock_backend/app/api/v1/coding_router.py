"""
Coding Interview Router
-----------------------
Endpoints for candidates to interact with coding problems during an interview.

GET  /coding/problem   – Fetch a specific or random coding problem
POST /coding/run       – Run code against visible test cases (no submission saved)
POST /coding/submit    – Run code against ALL test cases and persist submission
"""

import uuid
import random
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.sql.session import get_db_session
from app.db.sql.models.coding_problem import CodingProblem, TestCase, CodeSubmission
from app.db.sql.enums import SubmissionStatus
from app.services.code_execution_service import run_test_cases

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coding", tags=["coding"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    """Convert a string to UUID, raising HTTP 422 on failure."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid UUID for '{field_name}': {value}",
        )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class CodeRunRequest(BaseModel):
    problem_id: str
    language: str
    source_code: str
    interview_id: Optional[str] = None
    candidate_id: Optional[str] = None


class TestCaseResult(BaseModel):
    test_case_id: str
    input: str
    expected_output: str
    actual_output: str
    passed: bool
    error: Optional[str] = None


class CodeRunResponse(BaseModel):
    passed: int
    total: int
    results: List[TestCaseResult]


class SubmitResponse(BaseModel):
    submission_id: str
    status: str
    passed: int
    total: int
    results: List[TestCaseResult]


class ProblemResponse(BaseModel):
    id: str
    title: str
    description: str
    difficulty: str
    time_limit_sec: int
    starter_code: dict
    examples: List[dict]


# ---------------------------------------------------------------------------
# Endpoint 1 — GET /coding/problem
# ---------------------------------------------------------------------------

@router.get(
    "/problem",
    response_model=ProblemResponse,
    summary="Fetch a coding problem",
    description=(
        "If problem_id is provided, returns that specific problem. "
        "Otherwise selects a random problem not in exclude_ids. "
        "Only visible (non-hidden) test cases are returned as examples."
    ),
)
async def get_coding_problem(
    problem_id: Optional[str] = None,
    exclude_ids: Optional[str] = None,           # comma-separated UUIDs
    session: AsyncSession = Depends(get_db_session),
) -> ProblemResponse:

    problem: Optional[CodingProblem] = None

    if problem_id:
        # --- fetch by explicit ID -------------------------------------------
        pid = _parse_uuid(problem_id, "problem_id")
        result = await session.execute(
            select(CodingProblem).where(CodingProblem.id == pid)
        )
        problem = result.scalars().first()
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"CodingProblem with id '{problem_id}' not found.",
            )
    else:
        # --- select random problem not in exclude_ids -----------------------
        excluded_uuids: List[uuid.UUID] = []
        if exclude_ids:
            for raw in exclude_ids.split(","):
                raw = raw.strip()
                if raw:
                    excluded_uuids.append(_parse_uuid(raw, "exclude_ids"))

        query = select(CodingProblem)
        if excluded_uuids:
            query = query.where(CodingProblem.id.notin_(excluded_uuids))

        result = await session.execute(query)
        all_problems = result.scalars().all()

        if not all_problems:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No coding problems available.",
            )
        problem = random.choice(all_problems)

    # --- fetch visible test cases as examples --------------------------------
    tc_result = await session.execute(
        select(TestCase)
        .where(TestCase.problem_id == problem.id, TestCase.is_hidden == False)  # noqa: E712
        .order_by(TestCase.order)
    )
    visible_test_cases = tc_result.scalars().all()

    examples = [
        {
            "input": tc.input,
            "expected_output": tc.expected_output,
            "order": tc.order,
        }
        for tc in visible_test_cases
    ]

    return ProblemResponse(
        id=str(problem.id),
        title=problem.title,
        description=problem.description,
        difficulty=problem.difficulty,
        time_limit_sec=problem.time_limit_sec,
        starter_code=problem.starter_code or {},
        examples=examples,
    )


# ---------------------------------------------------------------------------
# Endpoint 2 — POST /coding/run
# ---------------------------------------------------------------------------

@router.post(
    "/run",
    response_model=CodeRunResponse,
    summary="Run code against visible test cases",
    description=(
        "Executes candidate's source code against the visible (non-hidden) test cases "
        "for the given problem. Results are NOT persisted."
    ),
)
async def run_code(
    request: CodeRunRequest,
    session: AsyncSession = Depends(get_db_session),
) -> CodeRunResponse:

    pid = _parse_uuid(request.problem_id, "problem_id")

    # Verify the problem exists
    prob_result = await session.execute(
        select(CodingProblem).where(CodingProblem.id == pid)
    )
    problem = prob_result.scalars().first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CodingProblem with id '{request.problem_id}' not found.",
        )

    # Fetch visible test cases only
    tc_result = await session.execute(
        select(TestCase)
        .where(TestCase.problem_id == pid, TestCase.is_hidden == False)  # noqa: E712
        .order_by(TestCase.order)
    )
    visible_tcs = tc_result.scalars().all()

    if not visible_tcs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No visible test cases found for this problem.",
        )

    # Build input for execution service
    tc_dicts = [
        {
            "id": str(tc.id),
            "input": tc.input,
            "expected_output": tc.expected_output,
        }
        for tc in visible_tcs
    ]

    # Execute (synchronous — wraps subprocess)
    raw_results = run_test_cases(
        language=request.language,
        source_code=request.source_code,
        test_cases=tc_dicts,
    )

    results = [
        TestCaseResult(
            test_case_id=str(r["test_case_id"]),
            input=r["input"],
            expected_output=r["expected_output"],
            actual_output=r["actual_output"],
            passed=r["passed"],
            error=r.get("error"),
        )
        for r in raw_results
    ]

    passed_count = sum(1 for r in results if r.passed)

    return CodeRunResponse(
        passed=passed_count,
        total=len(results),
        results=results,
    )


# ---------------------------------------------------------------------------
# Endpoint 3 — POST /coding/submit
# ---------------------------------------------------------------------------

@router.post(
    "/submit",
    response_model=SubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit code solution and persist result",
    description=(
        "Executes candidate's source code against ALL test cases (including hidden) "
        "and records the submission in the database."
    ),
)
async def submit_code(
    request: CodeRunRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SubmitResponse:

    pid = _parse_uuid(request.problem_id, "problem_id")

    # Validate optional FK fields
    interview_uuid: Optional[uuid.UUID] = None
    candidate_uuid: Optional[uuid.UUID] = None

    if request.interview_id:
        interview_uuid = _parse_uuid(request.interview_id, "interview_id")
    if request.candidate_id:
        candidate_uuid = _parse_uuid(request.candidate_id, "candidate_id")

    # Verify problem exists
    prob_result = await session.execute(
        select(CodingProblem).where(CodingProblem.id == pid)
    )
    problem = prob_result.scalars().first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CodingProblem with id '{request.problem_id}' not found.",
        )

    # Fetch ALL test cases (visible + hidden)
    tc_result = await session.execute(
        select(TestCase)
        .where(TestCase.problem_id == pid)
        .order_by(TestCase.order)
    )
    all_tcs = tc_result.scalars().all()

    if not all_tcs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No test cases found for this problem.",
        )

    tc_dicts = [
        {
            "id": str(tc.id),
            "input": tc.input,
            "expected_output": tc.expected_output,
        }
        for tc in all_tcs
    ]

    # Execute against all test cases
    raw_results = run_test_cases(
        language=request.language,
        source_code=request.source_code,
        test_cases=tc_dicts,
    )

    results = [
        TestCaseResult(
            test_case_id=str(r["test_case_id"]),
            input=r["input"],
            expected_output=r["expected_output"],
            actual_output=r["actual_output"],
            passed=r["passed"],
            error=r.get("error"),
        )
        for r in raw_results
    ]

    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    sub_status = SubmissionStatus.PASSED if passed_count == total_count else SubmissionStatus.FAILED

    # Persist the submission
    submission = CodeSubmission(
        id=uuid.uuid4(),
        problem_id=pid,
        interview_id=interview_uuid,
        candidate_id=candidate_uuid,
        language=request.language,
        source_code=request.source_code,
        status=sub_status.value,
        results=[r.model_dump() for r in results],
        passed_count=passed_count,
        total_count=total_count,
    )
    session.add(submission)
    await session.commit()
    await session.refresh(submission)

    logger.info(
        "Code submission saved: id=%s problem=%s status=%s passed=%d/%d",
        submission.id,
        pid,
        sub_status.value,
        passed_count,
        total_count,
    )

    return SubmitResponse(
        submission_id=str(submission.id),
        status=sub_status.value,
        passed=passed_count,
        total=total_count,
        results=results,
    )

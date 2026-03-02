from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth_router, dashboard_router
from app.api.v1 import interview_router, template_router, question_router
from app.api.v1 import candidate_interview_router
from app.api.v1 import candidate_profile_router
from app.api.v1 import session_router
from app.api.v1 import verification_router

from contextlib import asynccontextmanager
from app.db.sql.session import AsyncSessionLocal, test_database_connection
import logging
 
# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Step 1: Verify database connectivity ──────────────────────────────────
    logger.info("Initializing application and checking database connection...")
    await test_database_connection()

    yield
    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Application shutting down.")

app = FastAPI(title="AI Interview Automation Mock Backend", lifespan=lifespan)

# CORS Middleware - Allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Router inclusions
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(dashboard_router.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(template_router.router, prefix="/api/v1/admin/templates", tags=["Interview Template Engine"])
app.include_router(question_router.router, prefix="/api/v1/admin/questions", tags=["Question Bank"])
app.include_router(interview_router.router, prefix="/api/v1/admin/interviews", tags=["Interviews"])
app.include_router(candidate_interview_router.router, prefix="/api/v1/candidate/interviews", tags=["Candidate Interviews"])
app.include_router(candidate_profile_router.router, prefix="/api/v1/candidate", tags=["Candidate Profile (Face/Voice)"])
app.include_router(session_router.router, prefix="/api/v1", tags=["Session"])
app.include_router(verification_router.router, prefix="/api/v1/verification", tags=["Verification"])

@app.get("/")
async def root():
    return {"message": "Mock Backend is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint to verify backend is running"""
    return {"status": "ok", "message": "Backend is healthy"}

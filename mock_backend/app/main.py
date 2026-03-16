from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth_router, dashboard_router
from app.api.v1 import interview_router
from app.api.v1 import candidate_interview_router
from app.api.v1 import candidate_profile_router
from app.api.v1 import session_router
from app.api.v1 import verification_router
from app.api.v1 import template_router
from app.api.v1 import coding_router

from contextlib import asynccontextmanager
from app.db.sql.session import AsyncSessionLocal, test_database_connection
import logging
from pathlib import Path

# Load .env file explicitly before importing services
try:
    from dotenv import load_dotenv
    # Try to load .env from mock_backend directory
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logging.getLogger(__name__).info(f"Loaded .env file from: {env_path}")
    else:
        # Try parent directory (project root)
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logging.getLogger(__name__).info(f"Loaded .env file from: {env_path}")
        else:
            logging.getLogger(__name__).warning(f".env file not found. Tried: {Path(__file__).resolve().parent / '.env'} and {Path(__file__).resolve().parent.parent / '.env'}")
except ImportError:
    logging.getLogger(__name__).warning("python-dotenv not installed. Install with: pip install python-dotenv")
except Exception as e:
    logging.getLogger(__name__).warning(f"Error loading .env file: {e}")
 
from app.core.config import settings

# Configure logging
LOG_LEVEL_STR = settings.LOG_LEVEL.upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

logging.basicConfig(
    level=LOG_LEVEL,
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
app.include_router(interview_router.router, prefix="/api/v1/admin/interviews", tags=["Interviews"])
app.include_router(candidate_interview_router.router, prefix="/api/v1/candidate/interviews", tags=["Candidate Interviews"])
app.include_router(candidate_profile_router.router, prefix="/api/v1/candidate", tags=["Candidate Profile (Face/Voice)"])
app.include_router(session_router.router, prefix="/api/v1", tags=["Session"])
app.include_router(verification_router.router, prefix="/api/v1/verification", tags=["Verification"])
app.include_router(template_router.router, tags=["Admin Templates"])
app.include_router(coding_router.router, prefix="/api/v1/candidate", tags=["Coding"])

@app.get("/")
async def root():
    return {"message": "Mock Backend is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint to verify backend is running"""
    return {"status": "ok", "message": "Backend is healthy"}

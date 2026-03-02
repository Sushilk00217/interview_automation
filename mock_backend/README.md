# AI Interview Automation - Mock Backend

Standalone backend for the AI Interview Automation platform, powered by FastAPI, PostgreSQL, and Azure AI Services.

---

## 🚀 Features

### 1. Advanced Question Generation
- **Azure OpenAI Integration**: Uses GPT-4o to generate personalized conversational questions.
- **Context-Aware**: Analyses candidate resumes (PDF) and Job Descriptions to tailor questions.
- **Difficulty Scaling**: Automatically progresses from Medium (overview/tech) to Hard (architecture/problem-solving).
- **Project Focus**: Specifically targets projects listed in the candidate's profile.

### 2. Multi-Modal Identity Verification
- **Face Verification**: Azure Face API integration for photo-based identity checks.
- **Voice Enrollment**: Azure Speech Service for speaker verification.
- **Interview Gatekeeper**: Prevents starting interviews until verification is complete.
- **Mock Mode**: Falls back to automatic verification if Azure credentials are not configured.

### 3. Interview Lifecycle Management
- **72-Hour Expiration**: Interviews automatically expire 72 hours after the scheduled time.
- **Real-time Status**: Tracks candidate progress and verification status.

---

## 🛠️ Setup & Installation

### 1️⃣ Prerequisites
- Python 3.10+
- PostgreSQL 15+
- Git

### 2️⃣ Clone & Workspace Setup
```bash
git clone <your-repo-url>
cd mock_backend

# Windows
python -m venv venv
.\venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Database Configuration (PostgreSQL)

**1. Create the Database**
```sql
CREATE DATABASE interview_test_db;
```

**2. Configure Environment Variables**
Create a `.env` file in the project root:
```env
DATABASE_URL=postgresql+asyncpg://postgres:YourPassword@localhost:5432/interview_test_db
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Azure Verification
AZURE_FACE_ENDPOINT=...
AZURE_FACE_API_KEY=...
AZURE_SPEECH_API_KEY=...
AZURE_SPEECH_REGION=eastus
```
> [!IMPORTANT]
> If your password contains `@`, encode it as `%40` (e.g., `pass%40123`).

**3. Initialize Database**
```bash
# Run migrations
alembic upgrade head

# Seed initial data (Admin, Templates, Question Bank)
python -m seeds.run_seeds
```

---

## ⚡ Running the App

Start the development server:
```bash
uvicorn app.main:app --reload
```
- **API Server**: `http://127.0.0.1:8000`
- **Swagger Docs**: `http://127.0.0.1:8000/docs`

---

## 🏗️ Project Structure

- `app/`: Application core
  - `api/`: Route definitions (Auth, Interviews, Verification)
  - `services/`: Business logic (OpenAI, Resume Parsing, ID Verification)
  - `db/sql/`: Models and repositories
- `seeds/`: Idempotent data seeding logic
- `alembic/`: Database migrations
- `uploads/`: Local storage for Resumes and Media samples
- `tests/`: Integration and diagnostic tests

---

## 🧪 Troubleshooting

**Error: 500 on Interview Scheduling**
- Verify `curated_questions` exists in response.
- Ensure all migrations are applied (`alembic upgrade head`).
- Confirm seeding was performed (`python -m seeds.run_seeds`).

**Error: Database Connection Failed**
- Check if PostgreSQL is running locally.
- Verify the connection string in `.env`.
- Ensure the database name matches what you created in psql.

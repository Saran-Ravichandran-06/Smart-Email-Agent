# Smart Email & Communication Agent

AI-assisted Gmail inbox for detecting actionable emails, extracting tasks, tracking follow-ups, and drafting/sending replies.

## Features

- Google OAuth login and Gmail inbox sync
- Clean Gmail parsing with plain-text preference and HTML fallback
- Priority classification: urgent, important, low, noise
- Noise filtering for newsletters, promotions, no-reply senders, and automated notifications
- Task extraction with due dates from real email content
- Follow-up detection for emails requiring a response
- Reply draft generation using local Ollama / Phi-3
- Gmail reply sending through the connected account
- Thread resolution state to avoid recreating completed tasks

## Tech Stack

- Frontend: React, Vite, TypeScript, Tailwind CSS, Zustand
- Backend: FastAPI, SQLAlchemy, Alembic
- Database: PostgreSQL
- AI: Ollama with Phi-3
- Integration: Google OAuth 2.0 and Gmail API

## Project Structure

```text
Email_Agent/
  backend/     FastAPI API, Gmail sync, AI services, database models
  frontend/    React app for inbox, tasks, follow-ups, settings
  test.md      Short local testing guide
```

## Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL 14+
- Ollama with Phi-3 installed
- Google Cloud project with Gmail API enabled

Pull Phi-3:

```bash
ollama pull phi3
```

## Google Cloud Setup

1. Enable Gmail API in Google Cloud Console.
2. Configure OAuth consent screen.
3. Create an OAuth 2.0 Web Client.
4. Add this redirect URI:

```text
http://localhost:8000/api/auth/google/callback
```

Required Gmail/OAuth scopes are configured in the backend:

- `openid`
- `userinfo.email`
- `userinfo.profile`
- `gmail.readonly`
- `gmail.compose`
- `gmail.send`

## Environment Setup

Backend:

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Update `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/email_agent
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
SESSION_SECRET_KEY=replace-with-a-long-random-secret
ENABLE_MOCK_MODE=false
ENABLE_DEV_ENDPOINTS=false
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=phi3
```

Frontend:

```bash
cd frontend
npm install
copy .env.example .env
```

`frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Database

Create the database:

```sql
CREATE DATABASE email_agent;
```

Apply migrations:

```bash
cd backend
alembic upgrade head
```

## Run Locally

Start backend:

```bash
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Start frontend:

```bash
cd frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

## Typical Workflow

1. Open the app.
2. Connect Gmail from Settings.
3. Sync Gmail.
4. Review inbox priorities, tasks, and follow-ups.
5. Generate a reply draft when needed.
6. Edit and send the reply through Gmail.
7. Mark tasks complete as work is finished.

## Useful Commands

Backend checks:

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend checks:

```bash
cd frontend
npm run build
```

## Notes

- This project is optimized for local small-model inference, especially Phi-3.
- Thread summaries and complex memory systems are intentionally not included.
- Existing OAuth tokens may need re-authentication when Gmail scopes change.
- Mock mode is available only when explicitly enabled with `ENABLE_MOCK_MODE=true`.

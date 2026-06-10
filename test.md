# Real Gmail Setup and Testing

Short guide to run the project with real Gmail instead of mock data.

## 1. Google Cloud Setup

1. Open Google Cloud Console.
2. Create or select a project.
3. Enable **Gmail API**.
4. Configure **OAuth consent screen**.
5. Create OAuth credentials:
   - Type: **Web application**
   - Authorized redirect URI:

```text
http://localhost:8000/api/auth/google/callback
```

6. Copy the generated:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`

## 2. Backend Environment

Create or update `backend/.env`:

```env
APP_ENV=development
DEBUG=true
HOST=0.0.0.0
PORT=8000

ENABLE_MOCK_MODE=false
ENABLE_DEV_ENDPOINTS=false

FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
SESSION_SECRET_KEY=change-this-to-a-long-random-secret

DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/email_agent

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

GMAIL_SYNC_MAX_RESULTS=50

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=phi3
OLLAMA_TIMEOUT_SECONDS=120
```

## 3. Frontend Environment

Create or update `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 4. Start Database

Make sure PostgreSQL is running and has this database:

```text
email_agent
```

Use the same username/password as `DATABASE_URL`.

## 5. Start Backend

From `backend`:

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Check backend health:

```text
http://localhost:8000/api/health
```

## 6. Start Frontend

From `frontend`:

```bash
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## 7. Login With Gmail

1. Open the app.
2. Click **Connect Gmail**.
3. Sign in with Google.
4. Accept Gmail permissions.
5. After redirect, confirm the app shows the Gmail user.

Quick API check:

```text
GET http://localhost:8000/api/auth/me
```

Expected result: authenticated user with `gmail_connected: true`.

## 8. Sync Real Emails

In the app, trigger Gmail sync from the inbox.

Expected result:

- emails load from the real Gmail inbox
- sender, recipient, subject, date, labels, and cleaned body are stored
- duplicate messages are skipped on repeated sync
- emails belong only to the logged-in user

## 9. Test Agent Features

After sync, test these from the UI:

1. Open inbox.
2. Verify synced email list.
3. Open an email detail page.
4. Run or verify:
   - priority classification
   - task extraction
   - follow-up detection
   - thread summary
   - reply draft generation

For reply drafts, keep Ollama running locally:

```bash
ollama serve
ollama pull phi3
```

## 10. Expected Working Flow

```text
Frontend
-> Connect Gmail
-> Google OAuth
-> Backend callback
-> User and token saved
-> Inbox sync
-> Real Gmail emails stored
-> AI processing runs on cleaned email body
-> Reply draft generated with Phi-3
```

## 11. Common Issues

- OAuth error: redirect URI must exactly match Google Cloud and `GOOGLE_REDIRECT_URI`.
- Mock data appears: set `ENABLE_MOCK_MODE=false`.
- Login fails: check `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and backend logs.
- Sync fails: reconnect Gmail and verify Gmail API is enabled.
- AI timeout: keep `OLLAMA_TIMEOUT_SECONDS=120` and use `phi3`.

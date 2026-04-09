# VidyaAI

VidyaAI is a FastAPI + React tutoring app for chapter-based study, quiz practice, and AI-assisted explanations over NCERT-style content.

## What is in this repo

- `backend/` - FastAPI API, auth, tutor endpoints, quiz tracking, PDF ingestion
- `frontend/` - Vite + React + TypeScript student UI
- `chroma_db/` - local Chroma persistence
- `data/` - local content/data assets
- `run_backend.ps1` - starts the backend on port `8000`
- `run_frontend.ps1` - starts the frontend on port `3000`
- `start_vidya_ai.ps1` - opens backend and frontend together

## Stack

- Backend: FastAPI, SQLModel, ChromaDB, httpx
- Frontend: React 18, TypeScript, Vite, Axios, Zustand
- LLM runtime: Ollama
- Default DB: SQLite

## Runtime URLs

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Ollama: `http://localhost:11434`

## Environment Variables

### Frontend

Frontend backend URL is controlled by:

```env
VITE_API_URL=http://localhost:8000
```

The active local file is:

- `frontend/.env`

Important: this frontend uses `VITE_API_URL`, not `REACT_APP_API_URL`.

### Backend

Common backend variables:

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gpt-oss:120b-cloud
SECRET_KEY=your-secret-key
ADMIN_TOKEN=admin-secret
DATABASE_URL=sqlite:///./vidya_ai.db
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

The backend env file is:

- `backend/.env`

## Quick Start

### Option 1: repo scripts on Windows

From the repo root:

```powershell
./start_vidya_ai.ps1
```

Or run them separately:

```powershell
./run_backend.ps1
./run_frontend.ps1
```

### Option 2: manual startup

#### Backend

From the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Create or update `backend/.env`, then start:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

#### Frontend

From the repo root:

```powershell
cd frontend
npm install
```

Set `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

Then start:

```powershell
npm run dev
```

## Ollama Setup

VidyaAI expects Ollama to be running locally.

```powershell
ollama serve
ollama pull gpt-oss:120b-cloud
ollama pull nomic-embed-text
```

If Ollama embeddings are unavailable, the backend falls back to a local hash embedding function for retrieval.

## API Route File

Most application routes used by the frontend are defined in:

- `backend/main.py`

## API Endpoints Used by the Frontend

### Auth

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `PATCH /auth/profile`

### Library

- `GET /library/books/{class_grade}`
- `GET /library/chapter/{book_id}`

### Dashboard

- `GET /dashboard/stats`
- `GET /dashboard/progress`

### Tutor

- `POST /tutor/chat`
- `POST /tutor/quiz`
- `POST /tutor/quiz/submit`
- `POST /tutor/summarize`
- `POST /tutor/explain`
- `POST /tutor/sources`

## Backend Routes Present but Not Currently Used by the UI

- `POST /auth/google`
- `GET /library/classes`
- `GET /library/overview`
- `POST /tutor/essay`
- `POST /admin/enrich-book/{book_id}`
- `POST /admin/upload-pdf`
- `POST /upload-pdf`
- `GET /health`

## Where the Frontend Makes Backend Calls

### Shared base URL

- `frontend/src/api/client.ts`
- `frontend/src/pages/Chat.tsx`
- `frontend/src/pages/Chapter.tsx`

### Auth calls

- `frontend/src/store/auth.ts` -> `/auth/register`, `/auth/login`, `/auth/me`, `/auth/profile`

### Page-level calls

- `frontend/src/pages/Dashboard.tsx` -> `/library/books/{class_grade}`, `/dashboard/stats`, `/dashboard/progress`
- `frontend/src/pages/Library.tsx` -> `/library/books/{class_grade}`
- `frontend/src/pages/Subject.tsx` -> `/library/books/{class_grade}`
- `frontend/src/pages/Quiz.tsx` -> `/library/books/{class_grade}`, `/tutor/quiz`, `/tutor/quiz/submit`
- `frontend/src/pages/Chat.tsx` -> `/library/books/{class_grade}`, `/library/chapter/{book_id}`, `/tutor/sources`, `/tutor/chat`, `/tutor/summarize`, `/tutor/explain`
- `frontend/src/pages/Chapter.tsx` -> `/library/chapter/{book_id}`, `/tutor/sources`, `/tutor/summarize`, `/tutor/explain`, `/tutor/quiz`, `/tutor/quiz/submit`

## Request Style Used in the Frontend

- Axios is used for standard JSON API calls through `frontend/src/api/client.ts`
- Raw `fetch` is used in `Chat.tsx` and `Chapter.tsx` for streaming tutor responses
- Auth token injection is handled in `frontend/src/api/client.ts`

## Changing the Backend URL

If you want the frontend to call a different backend:

1. Update `frontend/.env`
2. Set `VITE_API_URL` to the new backend origin
3. Restart the frontend dev server

Example:

```env
VITE_API_URL=https://your-backend-domain.com
```

## Ingestion Notes

The repo also contains ingestion utilities that talk to the backend directly:

- `backend/ingest.py`
- `backend/ingest_all.py`

`backend/ingest.py` currently contains its own backend URL constant, so changing only `frontend/.env` does not affect ingestion scripts.

## Useful Files

- `frontend/.env`
- `frontend/src/api/client.ts`
- `frontend/src/pages/Chat.tsx`
- `frontend/src/pages/Chapter.tsx`
- `frontend/src/store/auth.ts`
- `backend/main.py`
- `backend/.env`
- `run_backend.ps1`
- `run_frontend.ps1`
- `start_vidya_ai.ps1`

## Notes

- The frontend is a Vite app, so `VITE_*` env vars are the ones that matter in the browser build.
- If documentation elsewhere still mentions `REACT_APP_API_URL`, treat that as outdated for the current frontend.

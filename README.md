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

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `GET /auth/me` - Get current user info

### Library
- `GET /library/classes` - Available classes for user
- `GET /library/books/{class_grade}` - Get books by class

### Tutoring
- `POST /tutor/chat` - Chat with AI tutor (streaming)
- `POST /tutor/quiz` - Generate quiz questions
- `POST /tutor/summarize` - Generate chapter summary
- `POST /tutor/explain` - Explain a concept
- `POST /tutor/essay` - Generate an essay

### Admin
- `POST /admin/upload-pdf` - Upload PDF (requires ADMIN_TOKEN)

## 📊 Database Schema

**Users**
- id, email, full_name, hashed_password
- google_id (for Google OAuth)
- plan_type (free/premium/enterprise)
- subscription status and expiry

**Books**
- id, class_grade, subject, chapter
- chunks_count, is_ingested status

**User Access Logs**
- Tracks user interactions (chat, quiz, etc.)

**Quiz Attempts**
- Stores quiz scores and user answers

## 🔐 Security Features

- ✅ Passwords hashed with bcrypt
- ✅ JWT tokens for session management
- ✅ CORS protection
- ✅ Access control based on subscription tier
- ✅ Environment variables for secrets

## 🎯 Usage Examples

### Register & Login
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"student@example.com","full_name":"John Doe","password":"secure123"}'
```

### Chat with Tutor
```bash
curl -X POST "http://localhost:8000/tutor/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "message":"What is photosynthesis?",
    "class_grade":"10",
    "subject":"science"
  }'
```

### Generate Quiz
```bash
curl -X POST "http://localhost:8000/tutor/quiz" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "topic":"Quadratic Equations",
    "class_grade":"10",
    "subject":"math",
    "num_questions":5
  }'
```

## 📈 Scaling & Deployment

### MongoDB for Chats (Future)
Replace SQLite with MongoDB for distributed access logs.

### PostgreSQL for Production
```bash
# Update DATABASE_URL
DATABASE_URL=postgresql://user:password@localhost/vidya_ai
```

### Docker Deployment
See `Dockerfile` (to be created) for containerized deployment.

### Kubernetes
Helm charts available for K8s deployment.

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Submit a pull request

## 📝 License

MIT License - see LICENSE file

## 💬 Support

For issues or questions:
- GitHub Issues: [create new issue]
- Email: support@vidyaai.com

---

**Made with ❤️ for Indian Students**

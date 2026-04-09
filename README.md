# VidyaAI - Smart NCERT AI Tutor Platform

A production-ready AI tutoring application for Indian students (Classes 10-12) built with **FastAPI + Ollama + ChromaDB + React**.

## 🎯 Features

✅ **Smart AI Tutoring**
- Interactive chat with GPT-OSS 120B model
- Concept explanations with Indian examples
- Essay generation for any topic
- Quiz generation with automated grading

✅ **User Management**
- Email/password registration & login
- JWT-based authentication
- User access logs & quiz history

✅ **Content Organization**
- NCERT books organized by class, subject, chapter
- RAG-powered retrieval for accurate answers
- Support for Class 10-12 curriculum

✅ **Subscription Tiers**
- **Free**: Class 10 only, 5 daily queries
- **Premium**: Classes 10-12, 100 daily queries, 50+ chat history
- **Enterprise**: Unlimited access

✅ **Clean, Modern UI**
- Responsive design with Tailwind CSS
- Seamless streaming responses
- Real-time loading states

## 🛠️ Tech Stack

- **Backend**: FastAPI, SQLModel, ChromaDB, Ollama
- **Database**: SQLite (expandable to PostgreSQL)
- **Frontend**: React 18, TypeScript, Tailwind CSS
- **LLM**: Ollama with gpt-oss:120b-cloud
- **Embeddings**: nomic-embed-text
- **Authentication**: JWT + passlib

## 📋 Prerequisites

- **Python 3.10+**
- **Node.js 16+** (for frontend)
- **Ollama** with models installed:
  - `ollama pull gpt-oss:120b-cloud`
  - `ollama pull nomic-embed-text`
- **Ollama running** on `http://localhost:11434`

## 🚀 Quick Start

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r ../requirements.txt

# Create .env file
cp ../.env.example .env

# Initialize database
python -c "from database import create_db_and_tables; create_db_and_tables()"

# Start backend server
uvicorn main:app --reload --port 8000
```

Backend runs on: `http://localhost:8000`

### 2. Ingest NCERT PDFs

```bash
# For single file
python ingest.py --file "path/to/Math_Ch1.pdf" --class 10 --subject math

# For entire folder
python ingest.py --folder "path/to/ncert_pdfs" --class 10 --subject math

# List ingested books
python ingest.py --list --class 10
```

### 3. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env file
echo "REACT_APP_API_URL=http://localhost:8000" > .env

# Start development server
npm start
```

Frontend runs on: `http://localhost:3000`

## 📚 API Endpoints

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

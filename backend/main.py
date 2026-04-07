"""
VidyaAI Backend - Smart NCERT AI Tutor with Authentication
FastAPI + Ollama + ChromaDB + SQLModel + JWT
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select
from datetime import datetime, timedelta
import httpx
import chromadb
from chromadb.utils import embedding_functions
import PyPDF2
import os
import json
import re
import uuid
import asyncio
import hashlib
from typing import Optional, List
import io

from .database import (
    engine, create_db_and_tables, get_session,
    User, Book, UserAccessLog, QuizAttempt,
    CATALOG,
    get_user_by_email, get_user_by_google_id, get_user_by_id, get_books_by_class, get_book_by_id, get_book_by_chapter, build_chapter_payload, parse_json_list
)
from .auth import (
    hash_password, verify_password, create_access_token, verify_token,
    get_current_user, get_plan_limits, check_plan_access, verify_google_token
)


class LocalHashEmbeddingFunction:
    name = "local-hash-embedding"

    def __call__(self, input: List[str]) -> List[List[float]]:
        vectors = []
        dimensions = 128
        for document in input:
            vector = [0.0] * dimensions
            for token in re.findall(r"\w+", document.lower()):
                digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
                index = int(digest[:8], 16) % dimensions
                sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
                vector[index] += sign
            norm = sum(value * value for value in vector) ** 0.5 or 1.0
            vectors.append([value / norm for value in vector])
        return vectors

# Initialize database
create_db_and_tables()

app = FastAPI(title="VidyaAI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ChromaDB setup ──────────────────────────────────────────────────────────
CHROMA_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

# Use Ollama embeddings via nomic-embed-text, fallback to local hash embeddings.
try:
    ef = embedding_functions.OllamaEmbeddingFunction(
        url="http://localhost:11434/api/embeddings",
        model_name="nomic-embed-text",
    )
    print("Using Ollama nomic-embed-text embeddings")
except Exception as exc:
    ef = LocalHashEmbeddingFunction()
    print(f"Falling back to local hash embeddings: {exc}")

# ── Ollama config ────────────────────────────────────────────────────────────
OLLAMA_BASE = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")  # Updated model

# ── Pydantic models ──────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    class_grade: str = "10"
    roll_number: Optional[str] = None
    school_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleAuthRequest(BaseModel):
    token: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    class_grade: Optional[str] = None
    roll_number: Optional[str] = None
    school_name: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    class_grade: Optional[str] = None
    subject: Optional[str] = None
    chapter: Optional[str] = None
    history: list = []

class QuizRequest(BaseModel):
    topic: str
    class_grade: Optional[str] = None
    subject: Optional[str] = None
    num_questions: int = 5

class SummaryRequest(BaseModel):
    chapter: str
    class_grade: Optional[str] = None
    subject: Optional[str] = None
    chapter_scope: Optional[str] = None

class ExplainRequest(BaseModel):
    concept: str
    class_grade: Optional[str] = None
    subject: Optional[str] = None
    simple_mode: bool = True
    chapter: Optional[str] = None

class SourceRequest(BaseModel):
    query: str
    class_grade: Optional[str] = None
    subject: Optional[str] = None
    chapter: Optional[str] = None

class QuizSubmitRequest(BaseModel):
    topic: str
    class_grade: Optional[str] = None
    subject: Optional[str] = None
    score: float
    total_questions: int
    correct_answers: int
    quiz_data: str
    time_taken_seconds: int = 0

class EssayRequest(BaseModel):
    topic: str
    class_grade: Optional[str] = None
    subject: Optional[str] = None
    length: str = "medium"  # short, medium, long

# ── Helper: Get ChromaDB collection for a class/subject ─────────────────────
def get_collection(class_grade: str, subject: str):
    """Get or create collection for a specific class and subject"""
    collection_name = f"ncert_class{class_grade}_{subject.lower()}"
    try:
        return chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"class": class_grade, "subject": subject}
        )
    except Exception as e:
        print(f"Collection creation error: {e}")
        return None


def build_embeddings(texts: List[str]) -> List[List[float]]:
    return ef(texts)


def _extract_json_object(raw_text: str) -> Optional[dict]:
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def _split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+", text)
    return [piece.strip() for piece in pieces if len(piece.strip()) > 30]


def _safe_extract_pdf_text(page) -> str:
    try:
        return page.extract_text() or ""
    except Exception as exc:
        print(f"PDF page extraction warning: {exc}")
        return ""


def _heuristic_chapter_assets(chapter: str, text: str) -> dict:
    cleaned = re.sub(r"\s+", " ", text).strip()
    sentences = _split_sentences(cleaned)
    summary = " ".join(sentences[:3]) if sentences else f"{chapter} is available for study in VidyaAI."

    topic_candidates = []
    for line in re.split(r"[\n\r]+", text):
        line = line.strip(" :-\t")
        if 4 < len(line) < 70 and re.match(r"^[A-Za-z0-9 ,()'-]+$", line):
            lower_line = line.lower()
            if lower_line != chapter.lower() and lower_line not in {item.lower() for item in topic_candidates}:
                topic_candidates.append(line)
        if len(topic_candidates) >= 6:
            break

    if not topic_candidates:
        topic_candidates = [sentence[:70].rstrip(".") for sentence in sentences[:5]]

    key_points = [sentence for sentence in sentences[:4]]
    excerpt = " ".join(sentences[:2]) if sentences else cleaned[:280]

    return {
        "summary_text": summary[:1200],
        "topics_covered": topic_candidates[:6],
        "key_points": key_points[:5],
        "content_excerpt": excerpt[:500],
    }


async def generate_chapter_assets(chapter: str, class_grade: str, subject: str, text: str) -> dict:
    prompt = f"""Create compact chapter metadata for VidyaAI.

Chapter: {chapter}
Class: {class_grade}
Subject: {subject}

Text:
{text[:3500]}

Return only valid JSON:
{{
  "summary_text": "2-4 sentence chapter summary",
  "topics_covered": ["topic 1", "topic 2", "topic 3"],
  "key_points": ["point 1", "point 2", "point 3"],
  "content_excerpt": "short excerpt capturing the chapter focus"
}}
"""

    messages = [
        {"role": "system", "content": "You create concise chapter metadata for NCERT content. Return valid JSON only."},
        {"role": "user", "content": prompt},
    ]

    try:
        raw = ""
        async for chunk in ollama_chat(messages, stream=False):
            raw += chunk
        parsed = _extract_json_object(raw)
        if parsed:
            return {
                "summary_text": str(parsed.get("summary_text", "")).strip(),
                "topics_covered": [str(item).strip() for item in parsed.get("topics_covered", []) if str(item).strip()][:8],
                "key_points": [str(item).strip() for item in parsed.get("key_points", []) if str(item).strip()][:6],
                "content_excerpt": str(parsed.get("content_excerpt", "")).strip(),
            }
    except Exception as exc:
        print(f"Chapter asset generation fallback for {chapter}: {exc}")

    return _heuristic_chapter_assets(chapter, text)

# ── Helper: call Ollama ──────────────────────────────────────────────────────
async def ollama_chat(messages: list, stream: bool = False):
    async with httpx.AsyncClient(timeout=120) as client:
        payload = {
            "model": MODEL,
            "messages": messages,
            "stream": stream,
        }
        if stream:
            async with client.stream("POST", f"{OLLAMA_BASE}/api/chat", json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data:
                                yield data["message"].get("content", "")
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            pass
        else:
            resp = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            yield data["message"]["content"]

# ── Helper: RAG retrieval ────────────────────────────────────────────────────
def retrieve_context(query: str, class_grade: str = None, subject: str = None, chapter: str = None, n_results: int = 5):
    if not class_grade:
        return ""

    subjects = [subject.lower()] if subject else list(CATALOG.get(class_grade, {}).keys())
    if not subjects:
        return ""

    query_embedding = build_embeddings([query])
    context_parts = []

    try:
        for current_subject in subjects:
            collection = get_collection(class_grade, current_subject)
            if not collection:
                continue

            query_kwargs = {
                "query_embeddings": query_embedding,
                "n_results": max(1, min(n_results, 4)),
            }
            if chapter:
                query_kwargs["where"] = {"chapter": chapter}

            results = collection.query(**query_kwargs)
            docs = results["documents"][0] if results["documents"] else []
            metas = results["metadatas"][0] if results["metadatas"] else []
            for doc, meta in zip(docs, metas):
                src = f"[{meta.get('subject', current_subject).upper()} Class {meta.get('class', class_grade)} - {meta.get('chapter', '')}]"
                context_parts.append(f"{src}\n{doc}")

        if context_parts:
            return "\n\n---\n\n".join(context_parts[:n_results])
    except Exception as e:
        print(f"Retrieval error: {e}")

    query_terms = {term.lower() for term in re.findall(r"[A-Za-z0-9]+", query) if len(term) > 2}
    with Session(engine) as session:
        statement = select(Book).where(Book.class_grade == class_grade)
        if subject:
            statement = statement.where(Book.subject == subject.lower())
        if chapter:
            statement = statement.where(Book.chapter == chapter)
        books = session.exec(statement).all()

    def score_book(book: Book) -> int:
        searchable = " ".join(
            [
                book.chapter,
                book.summary_text or "",
                " ".join(parse_json_list(book.topics_json)),
                book.content_excerpt or "",
            ]
        ).lower()
        return sum(1 for term in query_terms if term in searchable)

    ranked_books = sorted(books, key=lambda book: (score_book(book), book.is_ingested, book.chapter_num), reverse=True)
    fallback_parts = []
    for book in ranked_books[: max(1, min(n_results, 4))]:
        topics = ", ".join(parse_json_list(book.topics_json)[:4])
        fallback_parts.append(
            f"[{book.subject.upper()} Class {book.class_grade} - {book.chapter}]\n"
            f"{book.summary_text or book.content_excerpt or ''}\n"
            f"Topics: {topics}"
        )
    return "\n\n---\n\n".join(part for part in fallback_parts if part.strip())


def retrieve_source_cards(query: str, class_grade: str = None, subject: str = None, chapter: str = None, n_results: int = 3):
    if not class_grade or not query:
        return []

    subjects = [subject.lower()] if subject else list(CATALOG.get(class_grade, {}).keys())
    if not subjects:
        return []

    cards = []
    seen = set()
    query_embedding = build_embeddings([query])

    def add_card(subject_name: str, chapter: str, snippet: str, page: Optional[int] = None, source_type: str = "ncert_text"):
        cleaned_snippet = re.sub(r"\s+", " ", snippet).strip()
        if not cleaned_snippet:
            return
        key = (subject_name, chapter, page, cleaned_snippet[:120])
        if key in seen:
            return
        seen.add(key)
        cards.append({
            "subject": subject_name,
            "class_grade": class_grade,
            "chapter": chapter,
            "page": page,
            "snippet": cleaned_snippet[:360],
            "source_type": source_type,
        })

    try:
        for current_subject in subjects:
            collection = get_collection(class_grade, current_subject)
            if not collection:
                continue

            query_kwargs = {
                "query_embeddings": query_embedding,
                "n_results": max(1, min(n_results, 3)),
            }
            if chapter:
                query_kwargs["where"] = {"chapter": chapter}
            results = collection.query(**query_kwargs)
            docs = results["documents"][0] if results["documents"] else []
            metas = results["metadatas"][0] if results["metadatas"] else []
            for doc, meta in zip(docs, metas):
                add_card(
                    meta.get("subject", current_subject),
                    meta.get("chapter", ""),
                    doc,
                    meta.get("page"),
                    "official_pdf",
                )
                if len(cards) >= n_results:
                    return cards[:n_results]
    except Exception as exc:
        print(f"Source card retrieval error: {exc}")

    query_terms = {term.lower() for term in re.findall(r"[A-Za-z0-9]+", query) if len(term) > 2}
    with Session(engine) as local_session:
        statement = select(Book).where(Book.class_grade == class_grade)
        if subject:
            statement = statement.where(Book.subject == subject.lower())
        if chapter:
            statement = statement.where(Book.chapter == chapter)
        books = local_session.exec(statement).all()

    def score_book(book: Book) -> int:
        searchable = " ".join(
            [
                book.chapter,
                book.summary_text or "",
                " ".join(parse_json_list(book.topics_json)),
                book.content_excerpt or "",
            ]
        ).lower()
        return sum(1 for term in query_terms if term in searchable)

    ranked_books = sorted(books, key=lambda book: (score_book(book), book.is_ingested, book.chapter_num), reverse=True)
    for book in ranked_books[: max(1, min(n_results, 4))]:
        add_card(
            book.subject,
            book.chapter,
            book.content_excerpt or book.summary_text or "",
            None,
            book.source_type,
        )
        if len(cards) >= n_results:
            break
    return cards[:n_results]


def find_relevant_book(session: Session, class_grade: str, subject: Optional[str], chapter_hint: Optional[str]) -> Optional[Book]:
    if not class_grade:
        return None

    statement = select(Book).where(Book.class_grade == class_grade)
    if subject:
        statement = statement.where(Book.subject == subject.lower())
    books = session.exec(statement).all()
    if not books:
        return None

    if chapter_hint:
        hint = chapter_hint.strip().lower()
        exact = next((book for book in books if book.chapter.lower() == hint), None)
        if exact:
            return exact
        contains = next((book for book in books if book.chapter.lower() in hint or hint in book.chapter.lower()), None)
        if contains:
            return contains

    if subject:
        return books[0]
    return None


def log_learning_action(session: Session, user_id: int, action: str, class_grade: str, subject: Optional[str], chapter_hint: Optional[str]) -> None:
    book = find_relevant_book(session, class_grade, subject, chapter_hint)
    if not book:
        return
    log = UserAccessLog(
        user_id=user_id,
        book_id=book.id,
        action=action,
    )
    session.add(log)
    session.commit()


def _compute_streak(activity_dates: list[datetime]) -> int:
    if not activity_dates:
        return 0
    unique_days = sorted({item.date() for item in activity_dates}, reverse=True)
    today = datetime.utcnow().date()
    if unique_days[0] not in {today, today - timedelta(days=1)}:
        return 0
    streak = 0
    expected = unique_days[0]
    for day in unique_days:
        if day == expected:
            streak += 1
            expected = expected - timedelta(days=1)
        else:
            break
    return streak

def get_accessible_classes_for_user(user: User) -> list[str]:
    limits = get_plan_limits(user.plan_type)
    classes = set(limits["classes_available"])
    if user.class_grade:
        classes.add(str(user.class_grade))
    return sorted(classes, key=lambda value: int(value))

# ── Endpoints ────────────────────────────────────────────────────────────────

# ── AUTH ENDPOINTS ────────────────────────────────────────────────────────────

@app.post("/auth/register")
async def register(req: RegisterRequest, session: Session = Depends(get_session)):
    """Register a new user"""
    # Check if user already exists
    existing_user = get_user_by_email(session, req.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user = User(
        email=req.email,
        full_name=req.full_name,
        hashed_password=hash_password(req.password),
        class_grade=req.class_grade,
        roll_number=req.roll_number,
        school_name=req.school_name,
        plan_type="free",
        subscription_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Generate token
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    
    return AuthResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "class_grade": user.class_grade,
            "plan_type": user.plan_type,
            "roll_number": user.roll_number,
            "school_name": user.school_name,
        }
    )

@app.post("/auth/login")
async def login(req: LoginRequest, session: Session = Depends(get_session)):
    """Login user with email and password"""
    user = get_user_by_email(session, req.email)
    if not user or not verify_password(req.password, user.hashed_password or ""):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Update last login
    user.last_login = datetime.utcnow()
    session.add(user)
    session.commit()
    
    # Generate token
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    
    return AuthResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "class_grade": user.class_grade,
            "plan_type": user.plan_type,
            "roll_number": user.roll_number,
            "school_name": user.school_name,
        }
    )

@app.post("/auth/google")
async def google_auth(req: GoogleAuthRequest, session: Session = Depends(get_session)):
    """Sign in or register using a Google ID token."""
    google_user = await verify_google_token(req.token)
    if not google_user or not google_user.get("email") or not google_user.get("google_id"):
        raise HTTPException(status_code=401, detail="Invalid Google token")

    user = get_user_by_google_id(session, google_user["google_id"])
    if not user:
        user = get_user_by_email(session, google_user["email"])
        if user:
            user.google_id = google_user["google_id"]
        else:
            user = User(
                email=google_user["email"],
                full_name=google_user.get("name") or google_user["email"].split("@")[0],
                google_id=google_user["google_id"],
                class_grade="10",
                plan_type="free",
                subscription_active=True,
            )
            session.add(user)

    user.last_login = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)

    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    return AuthResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "class_grade": user.class_grade,
            "plan_type": user.plan_type,
            "roll_number": user.roll_number,
            "school_name": user.school_name,
        }
    )

@app.get("/auth/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get current user information"""
    user = get_user_by_id(session, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "class_grade": user.class_grade,
        "roll_number": user.roll_number,
        "school_name": user.school_name,
        "plan_type": user.plan_type,
        "subscription_active": user.subscription_active,
        "created_at": user.created_at
    }


@app.patch("/auth/profile")
async def update_profile(
    req: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user = get_user_by_id(session, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.full_name is not None and req.full_name.strip():
        user.full_name = req.full_name.strip()
    if req.class_grade is not None and req.class_grade.strip():
        user.class_grade = req.class_grade.strip()
    if req.roll_number is not None:
        user.roll_number = req.roll_number.strip() or None
    if req.school_name is not None:
        user.school_name = req.school_name.strip() or None

    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "class_grade": user.class_grade,
        "roll_number": user.roll_number,
        "school_name": user.school_name,
        "plan_type": user.plan_type,
        "subscription_active": user.subscription_active,
        "created_at": user.created_at,
    }

# ── LIBRARY & BOOK ENDPOINTS ──────────────────────────────────────────────────

@app.get("/library/classes")
async def get_available_classes(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get available classes for current user based on plan"""
    user = get_user_by_id(session, current_user["user_id"])
    accessible_classes = get_accessible_classes_for_user(user)
    
    return {
        "available_classes": accessible_classes,
        "plan_type": user.plan_type
    }

@app.get("/library/books/{class_grade}")
async def get_books_by_class_endpoint(
    class_grade: str,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all books for a class"""
    # Check access
    user = get_user_by_id(session, current_user["user_id"])
    accessible_classes = get_accessible_classes_for_user(user)
    
    if class_grade not in accessible_classes:
        raise HTTPException(status_code=403, detail="Access denied for this class")
    
    # Get books
    books = get_books_by_class(session, class_grade)
    
    # Group by subject
    grouped = {}
    for book in books:
        if book.subject not in grouped:
            grouped[book.subject] = []
        grouped[book.subject].append({
            "id": book.id,
            "chapter_num": book.chapter_num,
            "chapter": book.chapter,
            "is_ingested": book.is_ingested,
            "chunks_count": book.chunks_count
        })
    
    return {
        "class": class_grade,
        "subjects": grouped
    }


@app.get("/library/chapter/{book_id}")
async def get_chapter_detail(
    book_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user = get_user_by_id(session, current_user["user_id"])
    book = get_book_by_id(session, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Chapter not found")

    accessible_classes = get_accessible_classes_for_user(user)
    if book.class_grade not in accessible_classes:
        raise HTTPException(status_code=403, detail="Access denied for this class")

    return build_chapter_payload(book)


@app.post("/admin/enrich-book/{book_id}")
async def enrich_book_content(
    book_id: int,
    token: str = Form(os.getenv("ADMIN_TOKEN", "admin-secret")),
    session: Session = Depends(get_session),
):
    if token != os.getenv("ADMIN_TOKEN", "admin-secret"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    book = get_book_by_id(session, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Chapter not found")

    context = retrieve_context(book.chapter, book.class_grade, book.subject, n_results=10)
    if not context:
        raise HTTPException(status_code=400, detail="No ingested context found for this chapter")

    assets = await generate_chapter_assets(book.chapter, book.class_grade, book.subject, context)
    book.summary_text = assets.get("summary_text")
    book.topics_json = json.dumps(assets.get("topics_covered", []))
    book.key_points_json = json.dumps(assets.get("key_points", []))
    book.content_excerpt = assets.get("content_excerpt")
    book.updated_at = datetime.utcnow()
    session.add(book)
    session.commit()

    return {"message": "Chapter content enriched", "book_id": book.id, "topics_saved": len(assets.get("topics_covered", []))}


@app.get("/library/overview")
async def get_library_overview(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user = get_user_by_id(session, current_user["user_id"])
    accessible_classes = get_accessible_classes_for_user(user)
    classes = []
    for class_grade in accessible_classes:
        books = get_books_by_class(session, class_grade)
        classes.append({
            "class_grade": class_grade,
            "total_chapters": len(books),
            "ingested_chapters": sum(1 for book in books if book.is_ingested),
            "subjects": sorted({book.subject for book in books}),
        })
    return {"classes": classes}


@app.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user_id = current_user["user_id"]
    access_logs = session.exec(select(UserAccessLog).where(UserAccessLog.user_id == user_id)).all()
    quiz_attempts = session.exec(select(QuizAttempt).where(QuizAttempt.user_id == user_id)).all()
    book_ids = {log.book_id for log in access_logs}
    return {
        "totalChats": sum(1 for log in access_logs if log.action == "chat"),
        "totalQuizzes": len(quiz_attempts),
        "totalSummaries": sum(1 for log in access_logs if log.action == "summary"),
        "booksAccessed": len(book_ids),
    }


@app.get("/dashboard/progress")
async def get_dashboard_progress(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user_id = current_user["user_id"]
    access_logs = session.exec(select(UserAccessLog).where(UserAccessLog.user_id == user_id)).all()
    quiz_attempts = session.exec(select(QuizAttempt).where(QuizAttempt.user_id == user_id)).all()

    all_dates = [log.accessed_at for log in access_logs] + [attempt.attempted_at for attempt in quiz_attempts]
    streak_days = _compute_streak(all_dates)

    book_map = {}
    for log in access_logs:
        if log.book_id not in book_map:
            book_map[log.book_id] = session.get(Book, log.book_id)
    for attempt in quiz_attempts:
        if attempt.book_id not in book_map:
            book_map[attempt.book_id] = session.get(Book, attempt.book_id)

    recent_events = []
    for log in access_logs:
        book = book_map.get(log.book_id)
        if not book:
            continue
        recent_events.append({
            "type": log.action,
            "chapter": book.chapter,
            "subject": book.subject,
            "timestamp": log.accessed_at.isoformat(),
        })
    for attempt in quiz_attempts:
        book = book_map.get(attempt.book_id)
        if not book:
            continue
        recent_events.append({
            "type": "quiz_attempt",
            "chapter": book.chapter,
            "subject": book.subject,
            "timestamp": attempt.attempted_at.isoformat(),
            "score_percent": round((attempt.correct_answers / max(1, attempt.total_questions)) * 100),
        })
    recent_events.sort(key=lambda item: item["timestamp"], reverse=True)

    topic_scores = {}
    for attempt in quiz_attempts:
        book = book_map.get(attempt.book_id)
        if not book:
            continue
        key = (book.subject, book.chapter)
        entry = topic_scores.setdefault(key, {"scores": [], "subject": book.subject, "chapter": book.chapter})
        entry["scores"].append(attempt.correct_answers / max(1, attempt.total_questions))

    weak_topics = []
    for entry in topic_scores.values():
        average = sum(entry["scores"]) / len(entry["scores"])
        if average < 0.7:
            weak_topics.append({
                "subject": entry["subject"],
                "chapter": entry["chapter"],
                "score_percent": round(average * 100),
            })
    weak_topics.sort(key=lambda item: item["score_percent"])

    recent_books = []
    seen_books = set()
    for log in sorted(access_logs, key=lambda item: item.accessed_at, reverse=True):
        book = book_map.get(log.book_id)
        if not book or book.id in seen_books:
            continue
        seen_books.add(book.id)
        score_entry = topic_scores.get((book.subject, book.chapter))
        recent_books.append({
            "subject": book.subject,
            "chapter": book.chapter,
            "reason": "Quiz again to strengthen this chapter" if score_entry and (sum(score_entry["scores"]) / len(score_entry["scores"])) < 0.75 else "Quick revision recommended",
        })
        if len(recent_books) >= 4:
            break

    return {
        "streak_days": streak_days,
        "recent_activity": recent_events[:6],
        "weak_topics": weak_topics[:4],
        "revision_queue": recent_books,
    }

# ── TUTOR ENDPOINTS ──────────────────────────────────────────────────────────

@app.post("/tutor/chat")
async def chat(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Chat with AI tutor"""
    # Check access and limits
    user = get_user_by_id(session, current_user["user_id"])
    accessible_classes = get_accessible_classes_for_user(user)

    if req.class_grade and req.class_grade not in accessible_classes:
        raise HTTPException(status_code=403, detail="Access denied for this class")

    class_grade = req.class_grade or user.class_grade or "10"
    subject = req.subject or "general"
    
    active_chapter = req.chapter.strip() if req.chapter and req.chapter.strip() else None
    context = retrieve_context(req.message, class_grade, subject, chapter=active_chapter)

    sys_prompt = f"""You are VidyaAI, a warm and brilliant NCERT tutor for Indian students.
Your job is to teach like a great personal tutor, not like a dictionary or generic chatbot.

Student profile:
- Class: {class_grade}
- Subject: {subject}
{f"- Chapter: {active_chapter}" if active_chapter else "- Chapter scope: all chapters in this subject"}

{f"NCERT TEXTBOOK CONTEXT (use this first and stay grounded in it):\n{context}" if context else "Use NCERT-aligned knowledge and stay within the textbook syllabus."}

Teaching rules:
- Answer the student's actual chapter doubt directly in the first 1-2 lines
- Stay tied to the current chapter/topic, never drift into generic definitions
- If the student asks for the main idea, core idea, or explanation, explain the chapter concept itself
- Use short paragraphs, not one giant wall of text
- Use one clear Indian classroom or everyday example when it helps
- Break steps cleanly for maths/science problem solving
- End with one short memory line or exam tip when useful
- Do not use markdown bullets, hashes, or tables
- Do not mention that you are an AI unless asked"""

    messages = [{"role": "system", "content": sys_prompt}]
    for h in req.history[-6:]:  # keep last 6 turns
        messages.append(h)
    messages.append({"role": "user", "content": req.message})

    log_learning_action(session, current_user["user_id"], "chat", class_grade, req.subject, active_chapter or req.message)

    async def stream_response():
        async for chunk in ollama_chat(messages, stream=True):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


@app.post("/tutor/quiz")
async def generate_quiz(
    req: QuizRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Generate quiz questions"""
    user = get_user_by_id(session, current_user["user_id"])
    accessible_classes = get_accessible_classes_for_user(user)

    class_grade = req.class_grade or user.class_grade or "10"

    if class_grade not in accessible_classes:
        raise HTTPException(status_code=403, detail="Access denied for this class")
    
    context = retrieve_context(req.topic, class_grade, req.subject, n_results=8)

    prompt = f"""Generate exactly {req.num_questions} multiple-choice questions about: "{req.topic}"
{"For Class " + class_grade if class_grade else ""}
{"Subject: " + req.subject if req.subject else ""}

{f"Based on this NCERT content:\n{context[:2000]}" if context else "Based on NCERT curriculum."}

Question quality rules:
- Keep questions at the correct NCERT level for the class
- Test understanding, not random trivia
- Use plausible distractors
- Keep explanations short, clear, and textbook-grounded

Return ONLY a JSON array. No extra text. Format:
[
  {{
    "question": "...",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "correct": "A",
    "explanation": "Brief explanation why this is correct"
  }}
]"""

    messages = [
        {"role": "system", "content": "You are a quiz generator. Return only valid JSON arrays, no markdown, no extra text."},
        {"role": "user", "content": prompt}
    ]

    full_response = ""
    async for chunk in ollama_chat(messages, stream=False):
        full_response += chunk

    # Extract JSON
    json_match = re.search(r'\[.*\]', full_response, re.DOTALL)
    if json_match:
        try:
            questions = json.loads(json_match.group())
            return {"questions": questions, "topic": req.topic}
        except:
            pass

    raise HTTPException(status_code=500, detail="Failed to parse quiz JSON. Try again.")


@app.post("/tutor/quiz/submit")
async def submit_quiz_attempt(
    req: QuizSubmitRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user = get_user_by_id(session, current_user["user_id"])
    class_grade = req.class_grade or user.class_grade or "10"
    book = find_relevant_book(session, class_grade, req.subject, req.topic)
    if not book:
        raise HTTPException(status_code=404, detail="Could not match this quiz to a chapter")

    attempt = QuizAttempt(
        user_id=current_user["user_id"],
        book_id=book.id,
        topic=req.topic,
        score=req.score,
        total_questions=req.total_questions,
        correct_answers=req.correct_answers,
        time_taken_seconds=req.time_taken_seconds,
        quiz_data=req.quiz_data,
    )
    session.add(attempt)
    session.commit()

    log_learning_action(session, current_user["user_id"], "quiz", class_grade, req.subject, book.chapter)

    return {"message": "Quiz attempt saved"}


@app.post("/tutor/summarize")
async def summarize_chapter(
    req: SummaryRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Generate chapter summary"""
    user = get_user_by_id(session, current_user["user_id"])
    accessible_classes = get_accessible_classes_for_user(user)

    class_grade = req.class_grade or user.class_grade or "10"

    if class_grade not in accessible_classes:
        raise HTTPException(status_code=403, detail="Access denied for this class")
    
    active_chapter = req.chapter_scope.strip() if req.chapter_scope and req.chapter_scope.strip() else req.chapter
    context = retrieve_context(req.chapter, class_grade, req.subject, chapter=active_chapter, n_results=10)

    prompt = f"""Create a student-ready revision sheet for: "{req.chapter}"
{"Class " + class_grade if class_grade else ""}
{"Subject: " + req.subject if req.subject else ""}

{f"NCERT Content:\n{context[:3000]}" if context else "Use NCERT curriculum knowledge."}

Write it like something a student would actually revise from the night before an exam.
Use exactly these section labels in this order:

Chapter Snapshot: [2-3 short sentences on what the chapter is about]

Must Know Ideas: [4-6 short, chapter-specific points]

Important Terms: [important words, formulas, rules, dates, or definitions from this chapter only]

How to Answer Questions: [3-4 practical exam tips or solving steps]

Common Mistakes: [2-3 mistakes students often make]

Check Yourself: [3 likely exam questions or self-test prompts]

Rules:
- Be concrete and chapter-specific
- No generic study advice unless it directly fits the chapter
- Use plain text only
- Keep each section concise and easy to scan
- Do not use markdown symbols"""

    messages = [
        {"role": "system", "content": "You create crisp, chapter-specific NCERT revision sheets for students. Keep them concrete, exam-friendly, and easy to scan."},
        {"role": "user", "content": prompt}
    ]

    log_learning_action(session, current_user["user_id"], "summary", class_grade, req.subject, active_chapter or req.chapter)

    async def stream_summary():
        async for chunk in ollama_chat(messages, stream=True):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_summary(), media_type="text/event-stream")


@app.post("/tutor/explain")
async def explain_concept(
    req: ExplainRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Explain a concept"""
    user = get_user_by_id(session, current_user["user_id"])

    class_grade = req.class_grade or user.class_grade or "10"
    active_chapter = req.chapter.strip() if req.chapter and req.chapter.strip() else None
    context = retrieve_context(req.concept, class_grade, req.subject, chapter=active_chapter, n_results=6)

    if req.simple_mode:
        style = """Explain for a school student in simple language.
Use this exact section order and labels:
Big Idea:
In This Chapter:
Simple Explanation:
Worked Example:
Common Mistake:
Remember:

Rules:
- Stay tied to the actual chapter/topic from the NCERT context
- Do not give a generic dictionary definition disconnected from the chapter
- Keep each section short and readable
- Use one clear example a student will understand"""
    else:
        style = """Use this exact section order and labels:
Concept:
How It Works:
Key Details:
Worked Example:
Exam Tip:

Keep it detailed but still student-friendly and chapter-grounded."""

    prompt = f"""Explain this concept: "{req.concept}"
{"For Class " + class_grade if class_grade else ""}
{"Subject: " + req.subject if req.subject else ""}
{f"Chapter: {active_chapter}" if active_chapter else ""}

{f"NCERT Reference:\n{context[:2000]}" if context else ""}

{style}

If the prompt mentions something like main idea, core idea, key idea, or explain simply, explain the actual chapter concept from the NCERT reference, not the phrase itself.
Do not use markdown. Keep the response in plain text with short labeled sections."""

    messages = [
        {"role": "system", "content": "You are VidyaAI, a student-first NCERT explainer. You turn textbook concepts into short, clear lesson cards that stay grounded in the chapter."},
        {"role": "user", "content": prompt}
    ]

    log_learning_action(session, current_user["user_id"], "explain", class_grade, req.subject, active_chapter or req.concept)

    async def stream_explain():
        async for chunk in ollama_chat(messages, stream=True):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_explain(), media_type="text/event-stream")


@app.post("/tutor/sources")
async def get_tutor_sources(
    req: SourceRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user = get_user_by_id(session, current_user["user_id"])
    class_grade = req.class_grade or user.class_grade or "10"
    accessible_classes = get_accessible_classes_for_user(user)
    if class_grade not in accessible_classes:
        raise HTTPException(status_code=403, detail="Access denied for this class")

    return {
        "sources": retrieve_source_cards(req.query, class_grade, req.subject, chapter=req.chapter, n_results=3)
    }


@app.post("/tutor/essay")
async def generate_essay(
    req: EssayRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Generate an essay on a topic"""
    user = get_user_by_id(session, current_user["user_id"])

    class_grade = req.class_grade or user.class_grade or "10"
    context = retrieve_context(req.topic, class_grade, req.subject, n_results=12)
    
    length_map = {
        "short": "500-700 words",
        "medium": "800-1200 words",
        "long": "1500-2000 words"
    }
    
    prompt = f"""Write an essay ({length_map.get(req.length, '800-1200 words')}) on: "{req.topic}"
{"For Class " + class_grade if class_grade else ""}
{"Subject: " + req.subject if req.subject else ""}

{f"Use this reference:\n{context[:3000]}" if context else "Use NCERT knowledge."}

Structure:
1. **Introduction** - Hook and thesis statement
2. **Body** - 3-4 well-developed paragraphs with examples
3. **Conclusion** - Summary and final thoughts

Write in clear, academic English suitable for a {class_grade}th grader.
Do not use markdown formatting."""

    messages = [
        {"role": "system", "content": "You are VidyaAI, an expert essay writer for NCERT students."},
        {"role": "user", "content": prompt}
    ]

    async def stream_essay():
        async for chunk in ollama_chat(messages, stream=True):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_essay(), media_type="text/event-stream")

# ── PDF INGESTION ────────────────────────────────────────────────────────────

@app.post("/admin/upload-pdf")
@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    subject: str = Form("general"),
    class_grade: str = Form("unknown"),
    chapter: str = Form(""),
    book_id: Optional[int] = Form(None),
    token: str = Form(os.getenv("ADMIN_TOKEN", "admin-secret")),
    session: Session = Depends(get_session)
):
    """Upload and ingest a PDF (admin endpoint)"""
    # Simple token check (upgrade to JWT in production)
    if token != os.getenv("ADMIN_TOKEN", "admin-secret"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")

    content = await file.read()
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(content), strict=False)

    chunks = []
    chapter_name = chapter or file.filename.replace(".pdf", "")
    subject_name = subject.lower()
    chapter_counts = {}
    chapter_text_map = {}
    chapter_books = []

    if class_grade and subject_name:
        chapter_books = [
            book for book in get_books_by_class(session, class_grade)
            if book.subject == subject_name
        ]
        chapter_books.sort(key=lambda book: len(book.chapter), reverse=True)

    current_chapter = chapter_name

    for page_num, page in enumerate(pdf_reader.pages):
        text = _safe_extract_pdf_text(page)
        if not text or len(text.strip()) < 50:
            continue

        if not chapter and chapter_books:
            lowered_text = text.lower()
            for candidate in chapter_books:
                if candidate.chapter.lower() in lowered_text:
                    current_chapter = candidate.chapter
                    break

        # Split into ~500 char chunks with overlap
        words = text.split()
        chunk_size = 150  # words
        overlap = 30
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if len(chunk.strip()) > 100:
                chapter_counts[current_chapter] = chapter_counts.get(current_chapter, 0) + 1
                chapter_text_map.setdefault(current_chapter, []).append(chunk)
                chunks.append({
                    "text": chunk,
                    "page": page_num + 1,
                    "chapter": current_chapter,
                    "subject": subject_name,
                    "class": class_grade,
                    "source": file.filename,
                })

    if not chunks:
        raise HTTPException(status_code=400, detail="No text extracted from PDF")

    # Get collection and add to ChromaDB
    collection = get_collection(class_grade, subject_name)
    if not collection:
        raise HTTPException(status_code=500, detail="Failed to create collection")
    
    ids = [str(uuid.uuid4()) for _ in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [{k: v for k, v in c.items() if k != "text"} for c in chunks]

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=build_embeddings(documents),
    )

    if book_id:
        book = session.get(Book, book_id)
        if book:
            book.chunks_count = len(chunks)
            book.is_ingested = True
            book.total_pages = len(pdf_reader.pages)
            book.source_type = "official_pdf"
            book.file_name = file.filename
            if chapter_text_map.get(current_chapter):
                assets = await generate_chapter_assets(book.chapter, book.class_grade, book.subject, " ".join(chapter_text_map[current_chapter]))
                book.summary_text = assets.get("summary_text")
                book.topics_json = json.dumps(assets.get("topics_covered", []))
                book.key_points_json = json.dumps(assets.get("key_points", []))
                book.content_excerpt = assets.get("content_excerpt")
            book.updated_at = datetime.utcnow()
            session.add(book)
    elif chapter_counts:
        for book in chapter_books:
            if book.chapter in chapter_counts:
                book.chunks_count = chapter_counts[book.chapter]
                book.is_ingested = True
                book.total_pages = len(pdf_reader.pages)
                book.source_type = "official_pdf"
                book.file_name = file.filename
                chapter_text = " ".join(chapter_text_map.get(book.chapter, []))
                if chapter_text:
                    assets = await generate_chapter_assets(book.chapter, book.class_grade, book.subject, chapter_text)
                    book.summary_text = assets.get("summary_text")
                    book.topics_json = json.dumps(assets.get("topics_covered", []))
                    book.key_points_json = json.dumps(assets.get("key_points", []))
                    book.content_excerpt = assets.get("content_excerpt")
                book.updated_at = datetime.utcnow()
                session.add(book)
    session.commit()

    return {
        "message": f"Ingested '{file.filename}' successfully",
        "chunks_added": len(chunks),
        "subject": subject_name,
        "class": class_grade,
        "chapter": current_chapter,
        "chapters_detected": sorted(chapter_counts.keys()),
    }


@app.get("/health")
async def health(session: Session = Depends(get_session)):
    """Health check endpoint"""
    book_count = len(session.exec(select(Book)).all())
    ingested_count = len([book for book in session.exec(select(Book)).all() if book.is_ingested])
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
        return {
            "status": "ok",
            "ollama": "connected",
            "model": MODEL,
            "available_models": models,
            "book_count": book_count,
            "ingested_books": ingested_count,
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "book_count": book_count,
            "ingested_books": ingested_count,
        }

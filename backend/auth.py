"""
VidyaAI Authentication & Security
JWT, password hashing, and OAuth setup
"""

from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, Depends, status, Header
import os
import httpx

SECRET_KEY = os.getenv("SECRET_KEY", "vidya-ai-dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


async def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")

    payload = verify_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {"user_id": int(user_id), "email": payload.get("email")}


async def optional_user(authorization: str = Header(None)) -> Optional[dict]:
    if not authorization:
        return None
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None


async def verify_google_token(token: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://www.googleapis.com/oauth2/v1/tokeninfo?id_token={token}")
            if response.status_code == 200:
                data = response.json()
                return {
                    "google_id": data.get("user_id"),
                    "email": data.get("email"),
                    "name": data.get("name"),
                    "picture": data.get("picture"),
                }
    except Exception as exc:
        print(f"Google token verification error: {exc}")
    return None


ALL_CLASSES = [str(grade) for grade in range(4, 13)]


def check_plan_access(user_plan: str, required_plan: str = "free") -> bool:
    plan_levels = {"free": 0, "premium": 1, "enterprise": 2}
    return plan_levels.get(user_plan, 0) >= plan_levels.get(required_plan, 0)


def get_plan_limits(plan_type: str) -> dict:
    limits = {
        "free": {
            "max_daily_queries": 5,
            "max_pdf_uploads": 1,
            "max_quiz_per_day": 2,
            "access_all_classes": True,
            "classes_available": ALL_CLASSES,
            "max_chat_history": 3,
        },
        "premium": {
            "max_daily_queries": 100,
            "max_pdf_uploads": 20,
            "max_quiz_per_day": 20,
            "access_all_classes": True,
            "classes_available": ALL_CLASSES,
            "max_chat_history": 50,
        },
        "enterprise": {
            "max_daily_queries": float("inf"),
            "max_pdf_uploads": float("inf"),
            "max_quiz_per_day": float("inf"),
            "access_all_classes": True,
            "classes_available": ALL_CLASSES,
            "max_chat_history": float("inf"),
        },
    }
    return limits.get(plan_type, limits["free"])

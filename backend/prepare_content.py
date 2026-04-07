#!/usr/bin/env python3
"""Prepare stored curriculum content for all chapters and enrich ingested PDFs."""

import argparse

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from .database import Book, create_db_and_tables, engine
from .main import app
from .seed_curriculum_content import seed_curriculum_content


def enrich_ingested_books(class_grade: str | None = None, subject: str | None = None, token: str = "admin-secret") -> tuple[int, int]:
    client = TestClient(app)
    with Session(engine) as session:
        books = session.exec(select(Book).where(Book.is_ingested == True)).all()  # noqa: E712

    filtered = [
        book
        for book in books
        if (not class_grade or book.class_grade == class_grade) and (not subject or book.subject == subject.lower())
    ]

    success = 0
    for book in filtered:
        response = client.post(f"/admin/enrich-book/{book.id}", data={"token": token})
        if response.status_code == 200:
            success += 1
        else:
            print(f"Enrichment failed for book {book.id} ({book.chapter}): {response.status_code} {response.text}")
    return success, len(filtered)


def prepare_content(class_grade: str | None = None, subject: str | None = None, force: bool = False) -> None:
    create_db_and_tables()
    seed_curriculum_content(class_grade=class_grade, subject=subject, force=force)
    success, total = enrich_ingested_books(class_grade=class_grade, subject=subject)
    print(f"Enriched {success} ingested chapters out of {total} matched ingested records.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare VidyaAI content for curriculum and ingested books")
    parser.add_argument("--class", dest="class_grade", help="Filter by class grade")
    parser.add_argument("--subject", help="Filter by subject")
    parser.add_argument("--force", action="store_true", help="Regenerate stored curriculum content")
    args = parser.parse_args()

    prepare_content(class_grade=args.class_grade, subject=args.subject, force=args.force)

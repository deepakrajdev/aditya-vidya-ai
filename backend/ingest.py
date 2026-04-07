#!/usr/bin/env python3
"""VidyaAI NCERT ingestion tool."""

import argparse
import httpx
import re
import sys
from pathlib import Path
from sqlmodel import Session, select

from .database import Book, CATALOG, create_db_and_tables, engine

API_URL = "http://localhost:8000"


def get_chapter_name(class_grade: str, subject: str, filename: str) -> tuple[int, str]:
    subject_catalog = CATALOG.get(class_grade, {}).get(subject.lower(), [])

    explicit_match = re.search(r"(?:ch|chapter)[_\s-]?(\d+)", filename.lower())
    if explicit_match:
        chapter_num = int(explicit_match.group(1))
        if 1 <= chapter_num <= len(subject_catalog):
            return chapter_num, subject_catalog[chapter_num - 1]

    suffix_match = re.search(r"(\d{2})\.pdf$", filename.lower())
    if suffix_match:
        chapter_num = int(suffix_match.group(1))
        if 1 <= chapter_num <= len(subject_catalog):
            return chapter_num, subject_catalog[chapter_num - 1]

    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    return 0, stem


def register_book_in_db(class_grade: str, subject: str, chapter_num: int, chapter_name: str, filename: str) -> int:
    create_db_and_tables()
    with Session(engine) as session:
        if chapter_num > 0:
            statement = select(Book).where(
                Book.class_grade == class_grade,
                Book.subject == subject.lower(),
                Book.chapter_num == chapter_num,
            )
            existing = session.exec(statement).first()
            if existing:
                return existing.id

        statement = select(Book).where(
            Book.class_grade == class_grade,
            Book.subject == subject.lower(),
            Book.chapter == chapter_name,
        )
        existing = session.exec(statement).first()
        if existing:
            return existing.id

        book = Book(
            class_grade=class_grade,
            subject=subject.lower(),
            chapter=chapter_name,
            chapter_num=max(chapter_num, 1),
            file_name=filename,
            is_ingested=False,
            source_type="catalog",
        )
        session.add(book)
        session.commit()
        session.refresh(book)
        return book.id


def ingest_file(filepath: str, subject: str | None = None, class_grade: str | None = None, chapter: str | None = None) -> None:
    filename = Path(filepath).name
    subject = (subject or "general").lower()
    class_grade = class_grade or "10"

    chapter_num, chapter_name = get_chapter_name(class_grade, subject, filename)
    final_chapter = chapter or chapter_name
    book_id = register_book_in_db(class_grade, subject, chapter_num, final_chapter, filename)

    print(f"Ingesting: {filename}")
    print(f"  Class: {class_grade} | Subject: {subject} | Chapter: {final_chapter}")

    try:
        with open(filepath, "rb") as file_handle:
            response = httpx.post(
                f"{API_URL}/upload-pdf",
                files={"file": (filename, file_handle, "application/pdf")},
                data={
                    "subject": subject,
                    "class_grade": class_grade,
                    "chapter": final_chapter,
                    "book_id": str(book_id),
                },
                timeout=300,
            )

        if response.status_code == 200:
            data = response.json()
            print(f"  OK: {data.get('chunks_added', 0)} chunks added")
            if data.get("chapters_detected"):
                print(f"  Detected chapters: {', '.join(data['chapters_detected'])}")
        else:
            print(f"  API error ({response.status_code}): {response.text}")
    except Exception as exc:
        print(f"  Error: {exc}")


def ingest_folder(folder: str, class_grade: str = "10", subject: str | None = None) -> None:
    pdfs = sorted(Path(folder).glob("**/*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {folder}")
        return

    print(f"Found {len(pdfs)} PDFs to ingest for Class {class_grade}.")
    for index, pdf in enumerate(pdfs, start=1):
        print(f"[{index}/{len(pdfs)}]")
        ingest_file(str(pdf), subject=subject, class_grade=class_grade)
        print()


def list_ingested_books(class_grade: str = "10") -> None:
    create_db_and_tables()
    with Session(engine) as session:
        statement = select(Book).where(Book.class_grade == class_grade).order_by(Book.subject, Book.chapter_num)
        books = session.exec(statement).all()

    print(f"Books in database for Class {class_grade}:")
    for book in books:
        status = "INGESTED" if book.is_ingested else "PENDING"
        print(f"{status} | {book.subject.upper()} | Ch {book.chapter_num}: {book.chapter}")
        print(f"  Summary saved: {'yes' if book.summary_text else 'no'} | Topics saved: {'yes' if book.topics_json else 'no'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VidyaAI NCERT ingestion tool")
    parser.add_argument("--folder", help="Folder containing NCERT PDFs")
    parser.add_argument("--file", help="Single PDF file to ingest")
    parser.add_argument("--subject", help="Subject name")
    parser.add_argument("--class", dest="class_grade", default="10", help="Class grade")
    parser.add_argument("--chapter", help="Chapter name")
    parser.add_argument("--list", action="store_true", help="List stored books")
    parser.add_argument("--api", default=API_URL, help=f"API URL (default: {API_URL})")

    args = parser.parse_args()
    API_URL = args.api

    if args.list:
        list_ingested_books(args.class_grade)
    elif args.folder:
        ingest_folder(args.folder, args.class_grade, args.subject)
    elif args.file:
        ingest_file(args.file, args.subject, args.class_grade, args.chapter)
    else:
        parser.print_help()
        sys.exit(1)

#!/usr/bin/env python3
"""
VidyaAI - Fix Duplicate Book Entries
======================================
Run this ONCE from the project root to remove all duplicate chapter rows.
After running this, duplicates will never appear again because ingest_all.py
and the startup seed_catalog() both use the same deduplication key.

Usage:
    cd "C:\\Users\\aditya\\Downloads\\canara hsbc\\vidya AI"
    python fix_duplicates.py

    # Dry run first (see what would be deleted without actually deleting):
    python fix_duplicates.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from collections import defaultdict

# ── Fix import path ───────────────────────────────────────────────────────────
SCRIPT_PATH  = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent
if PROJECT_ROOT.name == "backend":
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BACKEND_DIR = PROJECT_ROOT / "backend"
if not BACKEND_DIR.exists():
    print(f"[FATAL] Cannot find backend/ at {PROJECT_ROOT}")
    sys.exit(1)


def fix_duplicates(dry_run: bool = False) -> None:
    from backend.database import Book, create_db_and_tables, engine
    from sqlmodel import Session, select

    create_db_and_tables()

    with Session(engine) as session:
        all_books = session.exec(select(Book).order_by(Book.id)).all()

        print(f"\nTotal book rows in DB: {len(all_books)}")

        # Group by the natural unique key: (class_grade, subject, chapter_num)
        # and also by (class_grade, subject, chapter) name as a secondary key
        groups: dict[tuple, list[Book]] = defaultdict(list)

        for book in all_books:
            # Normalise: use chapter_num as primary key if > 0, else chapter name
            key = (book.class_grade, book.subject.lower(), book.chapter_num, book.chapter.strip().lower())
            groups[key].append(book)

        to_delete: list[Book] = []

        for key, books in groups.items():
            if len(books) == 1:
                continue

            # Sort: prefer ingested rows, then highest chunk count, then lowest id
            books_sorted = sorted(
                books,
                key=lambda b: (
                    not b.is_ingested,            # ingested first
                    -(b.chunks_count or 0),       # more chunks first
                    b.id,                         # lowest id first (oldest)
                ),
            )

            keeper   = books_sorted[0]
            dupes    = books_sorted[1:]

            print(
                f"\n  Duplicate: Class {keeper.class_grade} | {keeper.subject} | "
                f"Ch {keeper.chapter_num} | {keeper.chapter}"
            )
            print(f"    KEEP   id={keeper.id}  ingested={keeper.is_ingested}  chunks={keeper.chunks_count or 0}")
            for dupe in dupes:
                print(f"    DELETE id={dupe.id}  ingested={dupe.is_ingested}  chunks={dupe.chunks_count or 0}")
                to_delete.append(dupe)

        print(f"\n{'─'*60}")
        print(f"  Rows to delete : {len(to_delete)}")
        print(f"  Rows to keep   : {len(all_books) - len(to_delete)}")

        if not to_delete:
            print("\n  No duplicates found — database is clean!")
            return

        if dry_run:
            print("\n  DRY RUN — nothing deleted. Run without --dry-run to apply.")
            return

        for book in to_delete:
            session.delete(book)
        session.commit()
        print(f"\n  Deleted {len(to_delete)} duplicate rows.")
        print("  Done — duplicates will not reappear on next ingest.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove duplicate Book rows from VidyaAI DB")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be deleted without actually deleting")
    args = parser.parse_args()
    fix_duplicates(dry_run=args.dry_run)
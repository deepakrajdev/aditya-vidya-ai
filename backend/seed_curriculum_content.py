#!/usr/bin/env python3
"""Backfill stored curriculum summaries/topics for all catalog chapters."""

import argparse

from sqlmodel import Session, select

from .database import Book, build_catalog_assets, create_db_and_tables, engine


def seed_curriculum_content(class_grade: str | None = None, subject: str | None = None, force: bool = False) -> None:
    create_db_and_tables()

    with Session(engine) as session:
        statement = select(Book)
        books = session.exec(statement).all()

        filtered = [
            book
            for book in books
            if (not class_grade or book.class_grade == class_grade) and (not subject or book.subject == subject.lower())
        ]

        if not filtered:
            print("No chapters matched the requested filters.")
            return

        updated_count = 0
        for book in filtered:
            has_content = all([book.summary_text, book.topics_json, book.key_points_json, book.content_excerpt])
            if has_content and not force:
                continue

            assets = build_catalog_assets(book.class_grade, book.subject, book.chapter)
            book.summary_text = assets["summary_text"]
            book.topics_json = assets["topics_json"]
            book.key_points_json = assets["key_points_json"]
            book.content_excerpt = assets["content_excerpt"]
            session.add(book)
            updated_count += 1

        session.commit()
        print(f"Updated {updated_count} chapters out of {len(filtered)} matched records.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed stored chapter summaries/topics for the curriculum catalog")
    parser.add_argument("--class", dest="class_grade", help="Filter by class grade")
    parser.add_argument("--subject", help="Filter by subject")
    parser.add_argument("--force", action="store_true", help="Regenerate stored content even if already present")
    args = parser.parse_args()

    seed_curriculum_content(args.class_grade, args.subject, args.force)

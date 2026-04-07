#!/usr/bin/env python3
"""
VidyaAI - NCERT Auto-Download + Ingestion Runner
==================================================
Place this file in the PROJECT ROOT (same level as the `backend/` folder).

WHAT IT DOES
------------
1. Downloads NCERT PDFs directly from ncert.nic.in (official government site).
   All book codes are verified from NCERT's own textbook download page.
2. Creates the correct folder structure under data/ncert/classX/
3. Ingests all PDFs into ChromaDB via your FastAPI backend.

Usage (run from project root, NOT from inside backend/):
    cd "C:\\Users\\aditya\\Downloads\\canara hsbc\\vidya AI"

    python ingest_all.py --scan                  # See what exists
    python ingest_all.py --class 10              # Download + ingest Class 10
    python ingest_all.py --class 6 7 8 9 10      # Multiple classes
    python ingest_all.py --all                   # All classes 4-12
    python ingest_all.py --all --force           # Re-download + re-ingest everything
    python ingest_all.py --class 8 --download-only   # Only download, skip ingestion
    python ingest_all.py --class 10 --ingest-only    # Only ingest (PDFs already on disk)
    python ingest_all.py --class 10 --token xyz      # Custom admin token
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# 1.  Resolve project root — works no matter where you `cd` before running
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_PATH  = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent
if PROJECT_ROOT.name == "backend":      # accidentally placed inside backend/
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BACKEND_DIR = PROJECT_ROOT / "backend"
DATA_ROOT   = PROJECT_ROOT / "data" / "ncert"

if not BACKEND_DIR.exists():
    print(f"\n[FATAL] Cannot find backend/ at: {PROJECT_ROOT}")
    print("  → Place ingest_all.py in the SAME folder as backend/")
    print(f"  → Current location: {SCRIPT_PATH}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# 2.  NCERT book catalogue
#     Source: https://ncert.nic.in/textbook.php  (official NCERT page)
#     URL pattern: https://ncert.nic.in/textbook/pdf/{book_code}{chapter:02d}.pdf
#
#     Each entry: (book_code, max_chapters, folder_name, subject_key)
#
#     max_chapters is the upper bound to TRY — the downloader will silently
#     skip chapters that return 404 (some books have fewer chapters than the
#     official "0-N" range on the site).
# ─────────────────────────────────────────────────────────────────────────────
NCERT_BOOKS: dict[str, list[tuple[str, int, str, str]]] = {

    # ── Class 4 ──────────────────────────────────────────────────────────────
    "4": [
        ("demh1", 14, "math_chapters",    "math"),        # Math-Magic
        ("deap1", 27, "evs_chapters",     "science"),     # Looking Around (EVS)
        ("deen1",  9, "english_chapters", "english"),     # Marigold
    ],

    # ── Class 5 ──────────────────────────────────────────────────────────────
    "5": [
        ("eemh1", 14, "math_chapters",    "math"),        # Math-Magic
        ("eeap1", 22, "evs_chapters",     "science"),     # Looking Around (EVS)
        ("eeen1", 10, "english_chapters", "english"),     # Marigold
    ],

    # ── Class 6 ──────────────────────────────────────────────────────────────
    "6": [
        ("femh1", 14, "math_chapters",    "math"),        # Mathematics
        ("fesc1", 16, "science_chapters", "science"),     # Science
        ("fehl1", 10, "english_honeysuckle", "english"),  # Honeysuckle
        ("fepw1", 10, "english_pact_sun",    "english"),  # A Pact With The Sun
        ("fess1", 11, "social_history",   "history"),     # Our Past (History)
        ("fess2",  8, "social_geography", "geography"),   # The Earth Our Habitat
        ("fess3",  9, "social_civics",    "civics"),      # Social and Political Life
    ],

    # ── Class 7 ──────────────────────────────────────────────────────────────
    "7": [
        ("gemh1", 15, "math_chapters",    "math"),        # Mathematics
        ("gesc1", 18, "science_chapters", "science"),     # Science
        ("gehc1", 10, "english_honeycomb","english"),     # Honeycomb
        ("geah1", 10, "english_alien_hand","english"),    # An Alien Hand (Suppl.)
        ("gess1", 10, "social_history",   "history"),     # Our Pasts-II
        ("gess2",  9, "social_geography", "geography"),   # Our Environment
        ("gess3",  9, "social_civics",    "civics"),      # Social and Political Life
    ],

    # ── Class 8 ──────────────────────────────────────────────────────────────
    "8": [
        ("hemh1", 16, "math_chapters",       "math"),     # Mathematics
        ("hesc1", 18, "science_chapters",    "science"),  # Science
        ("hehd1", 10, "english_honeydew",    "english"),  # Honeydew
        ("heih1", 11, "english_it_happened", "english"),  # It So Happened (Suppl.)
        ("hess2", 10, "social_history",      "history"),  # Our Pasts-III (History)
        ("hess4",  6, "social_geography",    "geography"),# Resource and Development
        ("hess3", 10, "social_civics",       "civics"),   # Social and Political Life
    ],

    # ── Class 9 ──────────────────────────────────────────────────────────────
    "9": [
        ("iemh1", 15, "math_chapters",    "math"),        # Mathematics
        ("iesc1", 15, "science_chapters", "science"),     # Science
        ("iebe1", 11, "english_beehive",  "english"),     # Beehive
        ("iemo1", 10, "english_moments",  "english"),     # Moments (Suppl.)
        ("iess3",  5, "social_history",   "history"),     # India & Contemporary World-I
        ("iess1",  6, "social_geography", "geography"),   # Contemporary India-I
        ("iess4",  5, "social_civics",    "civics"),      # Democratic Politics-I
        ("iess2",  4, "social_economics", "economics"),   # Economics
    ],

    # ── Class 10 ─────────────────────────────────────────────────────────────
    "10": [
        ("jemh1", 15, "math_chapters",       "math"),     # Mathematics
        ("jesc1", 16, "science_chapters",    "science"),  # Science
        ("jeff1", 11, "english_first_flight","english"),  # First Flight
        ("jefp1", 10, "english_footprints",  "english"),  # Footprints Without Feet
        ("jess3",  5, "social_history",      "history"),  # India & Contemporary World-II
        ("jess1",  7, "social_geography",    "geography"),# Contemporary India-II
        ("jess4",  8, "social_civics",       "civics"),   # Democratic Politics-II
        ("jess2",  5, "social_economics",    "economics"),# Understanding Economic Dev.
    ],

    # ── Class 11 ─────────────────────────────────────────────────────────────
    "11": [
        ("kemh1", 16, "math_chapters",      "math"),      # Mathematics
        ("keph1",  8, "physics_part1",      "physics"),   # Physics Part-I
        ("keph2",  7, "physics_part2",      "physics"),   # Physics Part-II
        ("kech1",  7, "chemistry_part1",    "chemistry"), # Chemistry Part-I
        ("kech2",  7, "chemistry_part2",    "chemistry"), # Chemistry Part-II
        ("kebo1", 22, "biology_chapters",   "biology"),   # Biology
        ("kehb1", 14, "english_hornbill",   "english"),   # Hornbill
        ("kesp1",  8, "english_snapshots",  "english"),   # Snapshots (Suppl.)
        ("kehs1", 11, "history_chapters",   "history"),   # Themes in World History
        ("kegy1",  7, "geography_india_env","geography"),  # India Physical Environment
        ("kegy2", 16, "geography_physical", "geography"),  # Fundamentals of Physical Geography
        ("keps1", 10, "civics_pol_theory",  "civics"),    # Political Theory
        ("keps2", 10, "civics_constitution","civics"),    # India Constitution at Work
        ("keec1", 10, "economics_indian",   "economics"), # Indian Economic Development
        ("kest1",  9, "economics_stats",    "economics"), # Statistics for Economics
    ],

    # ── Class 12 ─────────────────────────────────────────────────────────────
    "12": [
        ("lemh1",  6, "math_part1",         "math"),      # Mathematics Part-I
        ("lemh2",  7, "math_part2",         "math"),      # Mathematics Part-II
        ("leph1",  8, "physics_part1",      "physics"),   # Physics Part-I
        ("leph2",  6, "physics_part2",      "physics"),   # Physics Part-II
        ("lech1",  9, "chemistry_part1",    "chemistry"), # Chemistry Part-I
        ("lech2",  7, "chemistry_part2",    "chemistry"), # Chemistry Part-II
        ("lebo1", 16, "biology_chapters",   "biology"),   # Biology
        ("lefl1", 14, "english_flamingo",   "english"),   # Flamingo
        ("levt1",  8, "english_vistas",     "english"),   # Vistas (Suppl.)
        ("lehs1",  4, "history_part1",      "history"),   # Themes in Indian History-I
        ("lehs2",  5, "history_part2",      "history"),   # Themes in Indian History-II
        ("lehs3",  6, "history_part3",      "history"),   # Themes in Indian History-III
        ("legy1", 10, "geography_human",    "geography"), # Fundamentals of Human Geography
        ("legy2", 12, "geography_india",    "geography"), # India - People and Economy
        ("leps1",  9, "civics_world_pol",   "civics"),    # Contemporary World Politics
        ("leps2",  9, "civics_india_pol",   "civics"),    # Politics in India since Independence
        ("leec1",  6, "economics_macro",    "economics"), # Introductory Macroeconomics
        ("leec2",  6, "economics_micro",    "economics"), # Introductory Microeconomics
    ],
}

NCERT_BASE  = "https://ncert.nic.in/textbook/pdf"
ALL_CLASSES = [str(g) for g in range(4, 13)]

SUBJECT_HINTS: dict[str, list[str]] = {
    "math":      ["math", "maths", "mathematics", "ganit"],
    "science":   ["science", "vigyan", "evs", "looking_around"],
    "english":   ["english", "first_flight", "footprint", "honeydew", "beehive",
                  "marigold", "honeysuckle", "hornbill", "flamingo", "it_happened",
                  "alien_hand", "moments", "snapshots", "vistas", "honeycomb",
                  "pact_sun"],
    "history":   ["history", "our_past", "ourpast", "bharat", "world_hist",
                  "indian_hist", "contemporary_world"],
    "geography": ["geography", "earth_our", "resource", "physical", "human_geo",
                  "india_env", "india_people", "contemporary_india"],
    "civics":    ["civics", "social_civic", "democratic", "political", "pol_theory",
                  "constitution", "world_pol", "india_pol"],
    "economics": ["economics", "social_eco", "economic", "macro", "micro",
                  "arthashastra", "stats"],
    "physics":   ["physics"],
    "chemistry": ["chemistry"],
    "biology":   ["biology"],
}


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Download a single PDF
# ─────────────────────────────────────────────────────────────────────────────
def _download_pdf(url: str, dest: Path, retries: int = 3) -> bool:
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
                    )
                },
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = resp.read()
            if len(data) < 500:
                return False
            if not data.startswith(b"%PDF"):
                return False
            dest.write_bytes(data)
            return True
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False                  # chapter doesn't exist — normal
            if attempt == retries:
                print(f" [HTTP {exc.code}]", end="", flush=True)
                return False
            time.sleep(1.5 * attempt)
        except urllib.error.URLError as exc:
            if attempt == retries:
                print(f" [URL ERR: {exc.reason}]", end="", flush=True)
                return False
            time.sleep(2 * attempt)
        except Exception as exc:
            if attempt == retries:
                print(f" [ERR: {exc}]", end="", flush=True)
                return False
            time.sleep(2)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Download all books for a class
# ─────────────────────────────────────────────────────────────────────────────
def download_class(class_grade: str, force: bool = False) -> dict:
    books = NCERT_BOOKS.get(class_grade)
    if not books:
        print(f"  [WARN] No download map for Class {class_grade} — skipping")
        return {"downloaded": 0, "skipped": 0, "failed": 0}

    stats = {"downloaded": 0, "skipped": 0, "failed": 0}

    for book_code, max_chapters, folder_name, subject in books:
        folder = DATA_ROOT / f"class{class_grade}" / folder_name
        folder.mkdir(parents=True, exist_ok=True)

        print(f"\n  [{subject.upper():<10}]  {folder_name}/  (code={book_code}, up to {max_chapters} chapters)")

        for ch in range(1, max_chapters + 1):
            filename = f"{book_code}{ch:02d}.pdf"
            dest     = folder / filename
            url      = f"{NCERT_BASE}/{filename}"

            if dest.exists() and dest.stat().st_size > 500 and not force:
                print(f"    SKIP  {filename}  (already downloaded)")
                stats["skipped"] += 1
                continue

            print(f"    GET   {filename} … ", end="", flush=True)
            ok = _download_pdf(url, dest)
            if ok:
                kb = dest.stat().st_size // 1024
                print(f"OK  ({kb} KB)")
                stats["downloaded"] += 1
            else:
                # 404 is expected for chapters beyond the actual book length
                print("skip (not found)")
                if dest.exists():
                    dest.unlink()
                # not counted as failure — many books just have fewer chapters
                stats["skipped"] += 1

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Ingest helpers
# ─────────────────────────────────────────────────────────────────────────────
def infer_subject(folder_name: str) -> str | None:
    lowered = folder_name.lower().replace("-", "_").replace(" ", "_")
    for subject, hints in SUBJECT_HINTS.items():
        if any(hint in lowered for hint in hints):
            return subject
    return None


def _chapter_from_filename(class_grade: str, subject: str, filename: str, catalog: dict) -> tuple[int, str]:
    subject_catalog = catalog.get(class_grade, {}).get(subject.lower(), [])
    for pattern in [r"(?:ch|chapter)[_\s-]?(\d+)", r"(\d{2})\.pdf$"]:
        m = re.search(pattern, filename.lower())
        if m:
            num = int(m.group(1))
            if 1 <= num <= len(subject_catalog):
                return num, subject_catalog[num - 1]
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    return 0, stem


def _register_book(class_grade, subject, chapter_num, chapter_name, filename, engine, Book) -> int:
    """
    Find-or-create a Book row. Uses THREE checks to prevent duplicates:
      1. Exact match on (class_grade, subject, chapter_num)
      2. Exact match on (class_grade, subject, chapter name)
      3. Case-insensitive match on chapter name (catches catalog vs ingested mismatches)
    Only creates a new row if ALL three checks find nothing.
    """
    from sqlmodel import Session, select

    subj = subject.lower()

    with Session(engine) as session:
        # Check 1 — by chapter number (most reliable)
        if chapter_num > 0:
            existing = session.exec(
                select(Book).where(
                    Book.class_grade == class_grade,
                    Book.subject     == subj,
                    Book.chapter_num == chapter_num,
                )
            ).first()
            if existing:
                return existing.id

        # Check 2 — by exact chapter name
        existing = session.exec(
            select(Book).where(
                Book.class_grade == class_grade,
                Book.subject     == subj,
                Book.chapter     == chapter_name,
            )
        ).first()
        if existing:
            return existing.id

        # Check 3 — case-insensitive chapter name (catalog may differ in casing)
        all_same_subject = session.exec(
            select(Book).where(
                Book.class_grade == class_grade,
                Book.subject     == subj,
            )
        ).all()
        chapter_lower = chapter_name.strip().lower()
        for book in all_same_subject:
            if book.chapter.strip().lower() == chapter_lower:
                return book.id

        # Nothing found — safe to insert
        book = Book(
            class_grade=class_grade,
            subject=subj,
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


def ingest_class(class_grade: str, force: bool, token: str) -> dict:
    stats = {"total": 0, "success": 0, "skipped": 0, "failed": 0}
    class_path = DATA_ROOT / f"class{class_grade}"

    all_pdfs = list(class_path.rglob("*.pdf")) if class_path.exists() else []
    if not all_pdfs:
        print(f"\n  No PDFs on disk for Class {class_grade} — nothing to ingest.")
        return stats

    try:
        from backend.database import Book, CATALOG, create_db_and_tables, engine
        from backend.main import app
    except ImportError as exc:
        print(f"\n  [FATAL] Cannot import backend: {exc}")
        raise

    from sqlmodel import Session
    from fastapi.testclient import TestClient

    create_db_and_tables()
    client = TestClient(app)

    for folder in sorted(f for f in class_path.iterdir() if f.is_dir()):
        subject = infer_subject(folder.name)
        if not subject:
            print(f"\n  [SKIP folder] No subject inferred from: {folder.name}")
            continue
        pdfs = sorted(folder.glob("*.pdf"))
        if not pdfs:
            continue

        print(f"\n  [{subject.upper():<10}]  {len(pdfs)} PDFs  ({folder.name}/)")

        for pdf in pdfs:
            stats["total"] += 1
            chapter_num, chapter_name = _chapter_from_filename(class_grade, subject, pdf.name, CATALOG)
            book_id = _register_book(class_grade, subject, chapter_num, chapter_name, pdf.name, engine, Book)

            with Session(engine) as session:
                book = session.get(Book, book_id)
                if not book:
                    print(f"    FAIL  {pdf.name}: DB row missing after register")
                    stats["failed"] += 1
                    continue
                if book.is_ingested and (book.chunks_count or 0) > 0 and not force:
                    print(f"    SKIP  {pdf.name}  ({book.chapter})")
                    stats["skipped"] += 1
                    continue
                final_chapter = book.chapter

            try:
                with pdf.open("rb") as fh:
                    response = client.post(
                        "/upload-pdf",
                        files={"file": (pdf.name, fh, "application/pdf")},
                        data={
                            "subject":     subject,
                            "class_grade": class_grade,
                            "chapter":     final_chapter,
                            "book_id":     str(book_id),
                            "token":       token,
                        },
                    )
                if response.status_code == 200:
                    chunks = response.json().get("chunks_added", 0)
                    print(f"    OK    {pdf.name}  →  {final_chapter}  ({chunks} chunks)")
                    stats["success"] += 1
                else:
                    print(f"    FAIL  {pdf.name}: HTTP {response.status_code} — {response.text[:120]}")
                    stats["failed"] += 1
            except Exception as exc:
                print(f"    FAIL  {pdf.name}: {exc}")
                stats["failed"] += 1

    if stats["success"] > 0:
        print(f"\n  Seeding summaries + metadata for Class {class_grade}…")
        try:
            from backend.prepare_content import prepare_content
            prepare_content(class_grade=class_grade)
            print("  Done.")
        except Exception as exc:
            print(f"  [WARN] prepare_content failed (non-fatal): {exc}")

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Scan
# ─────────────────────────────────────────────────────────────────────────────
def scan_data_folder() -> None:
    print(f"\nProject root : {PROJECT_ROOT}")
    print(f"Data root    : {DATA_ROOT}\n")
    if not DATA_ROOT.exists():
        print("  data/ncert/ does not exist yet.")
        print("  Run:  python ingest_all.py --all   to download everything.\n")
        return
    found = False
    for grade in ALL_CLASSES:
        cp = DATA_ROOT / f"class{grade}"
        if not cp.exists():
            continue
        found = True
        total = len(list(cp.rglob("*.pdf")))
        print(f"Class {grade}  ({total} PDFs total)")
        for folder in sorted(f for f in cp.iterdir() if f.is_dir()):
            subject = infer_subject(folder.name)
            pdfs    = list(folder.glob("*.pdf"))
            label   = f"[{subject.upper()}]" if subject else f"[??]"
            print(f"  {label:<12}  {len(pdfs):>3} PDFs  ← {folder.name}/")
    if not found:
        print("  No class folders found. Run:  python ingest_all.py --all\n")


# ─────────────────────────────────────────────────────────────────────────────
# 7.  CLI
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="VidyaAI — NCERT auto-download + ingestion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Run from the PROJECT ROOT (where backend/ lives):
  cd "C:\\Users\\aditya\\Downloads\\canara hsbc\\vidya AI"

  python ingest_all.py --scan
  python ingest_all.py --class 8
  python ingest_all.py --class 6 7 8 9 10
  python ingest_all.py --all
  python ingest_all.py --all --force
  python ingest_all.py --class 8 --download-only
  python ingest_all.py --class 10 --ingest-only
  python ingest_all.py --class 10 --token my-secret
        """,
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--class", dest="classes", nargs="+", metavar="GRADE",
                      help="One or more grades, e.g. --class 6 7 10")
    mode.add_argument("--all",  action="store_true", help="All classes 4-12")
    mode.add_argument("--scan", action="store_true", help="Only scan; no download/ingest")

    parser.add_argument("--force",         action="store_true",
                        help="Re-download and re-ingest even if already done")
    parser.add_argument("--download-only", dest="download_only", action="store_true",
                        help="Download PDFs only; skip ChromaDB ingestion")
    parser.add_argument("--ingest-only",   dest="ingest_only",   action="store_true",
                        help="Ingest only; assume PDFs already on disk")
    parser.add_argument("--token", default="admin-secret",
                        help="Admin token for /upload-pdf (default: admin-secret)")

    args = parser.parse_args()

    if args.scan:
        scan_data_folder()
        return

    grades: list[str] = ALL_CLASSES if args.all else args.classes
    for g in grades:
        if g not in ALL_CLASSES:
            parser.error(f"Invalid grade '{g}'. Must be 4-12.")

    print(f"\n{'='*68}")
    print(f"  VidyaAI Ingestion Runner")
    print(f"  Project root  : {PROJECT_ROOT}")
    print(f"  Data root     : {DATA_ROOT}")
    print(f"  Classes       : {', '.join(grades)}")
    print(f"  Force         : {args.force}")
    print(f"  Download only : {args.download_only}")
    print(f"  Ingest only   : {args.ingest_only}")
    print(f"{'='*68}")

    dl_totals  = {"downloaded": 0, "skipped": 0, "failed": 0}
    ing_totals = {"total": 0, "success": 0, "skipped": 0, "failed": 0}
    wall_start = time.time()

    for grade in grades:
        print(f"\n{'─'*68}")
        print(f"  CLASS {grade}")
        print(f"{'─'*68}")
        t0 = time.time()

        # ── Download phase ────────────────────────────────────────────────────
        if not args.ingest_only:
            class_path    = DATA_ROOT / f"class{grade}"
            existing_pdfs = list(class_path.rglob("*.pdf")) if class_path.exists() else []
            if existing_pdfs and not args.force:
                print(f"\n  Folder exists with {len(existing_pdfs)} PDFs.")
                print("  Skipping download (use --force to re-download).")
            else:
                action = "Re-downloading" if existing_pdfs else "Downloading"
                print(f"\n  {action} from ncert.nic.in…")
                dl = download_class(grade, force=args.force)
                for k in dl_totals:
                    dl_totals[k] += dl.get(k, 0)
                print(
                    f"\n  Download: {dl['downloaded']} new"
                    f"  |  {dl['skipped']} skipped"
                    f"  |  {dl['failed']} failed"
                )

        # ── Ingest phase ──────────────────────────────────────────────────────
        if not args.download_only:
            print(f"\n  Ingesting into ChromaDB…")
            try:
                ing = ingest_class(grade, force=args.force, token=args.token)
            except Exception as exc:
                print(f"\n  [ERROR] Ingestion crashed for Class {grade}: {exc}")
                import traceback; traceback.print_exc()
                ing = {"total": 0, "success": 0, "skipped": 0, "failed": 1}
            for k in ing_totals:
                ing_totals[k] += ing.get(k, 0)

        elapsed = time.time() - t0
        print(f"\n  Class {grade} done in {elapsed:.1f}s")

    total_elapsed = time.time() - wall_start
    print(f"\n{'='*68}")
    print(f"  ALL DONE  ({total_elapsed:.1f}s total)")
    if not args.ingest_only:
        print(f"  PDFs downloaded : {dl_totals['downloaded']}")
        print(f"  PDFs skipped    : {dl_totals['skipped']}  (already on disk or no chapter)")
    if not args.download_only:
        print(f"  Chunks added    : {ing_totals['success']}")
        print(f"  Already ingested: {ing_totals['skipped']}")
        print(f"  Ingest failures : {ing_totals['failed']}")
        print(f"  Total PDFs seen : {ing_totals['total']}")
    print(f"{'='*68}\n")


if __name__ == "__main__":
    main()
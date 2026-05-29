"""
sync_jobs.py — Sync Obsidian .md files from obsidian/jobs/ into jobs.db.

Bridges the gap between human-editable Obsidian notes and the SQLite
jobs database that agents and CLI commands query.

Each .md file in obsidian/jobs/ represents one job application. The
YAML frontmatter maps to companies, applications, interviews, and
contacts tables.

Entity relationship:
  companies 1──N applications 1──N interviews
  companies 1──N contacts

Usage:
    python3 sync_jobs.py                          # Full sync, report to stdout
    python3 sync_jobs.py --dry-run                # Preview only, no writes
    python3 sync_jobs.py --dir /path/to/files     # Custom file directory
"""
import argparse
import logging
import sys
import uuid
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

# Allow running from anywhere by resolving engine/ sibling dir
_ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGINE_DIR))

import db_manager as db

logger = logging.getLogger("engine.sync_jobs")

# Resolve paths
_ENGINE_DIR = Path(__file__).resolve().parent.parent
_OBSIDIAN_JOBS_DIR = _ENGINE_DIR.parent.parent / "obsidian" / "jobs"
if not _OBSIDIAN_JOBS_DIR.exists():
    _OBSIDIAN_JOBS_DIR = _ENGINE_DIR.parent / "obsidian" / "jobs"


def _parse_frontmatter(file_path: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception:
        return {}
    if not text.startswith("---"):
        return {}
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    try:
        fm = yaml.safe_load(m.group(1))
        return fm if isinstance(fm, dict) else {}
    except Exception:
        return {}


def _strip_frontmatter(text: str) -> str:
    """Return remaining text after removing the YAML frontmatter block."""
    if not text.startswith("---"):
        return text
    m = re.match(r"^---\s*\n.*?\n---\s*\n?", text, re.DOTALL)
    if m:
        return text[m.end():]
    return text


def _str(val: Any) -> str:
    """Safely convert a value to string, defaulting to empty."""
    if val is None:
        return ""
    return str(val).strip()


def _bool(val: Any) -> bool:
    """Parse a value as boolean. Accepts YAML booleans, 'true'/'false', 1/0."""
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val == 1
    return _str(val).lower() in ("true", "yes", "1")


def _company_id_from_name(name: str) -> str:
    """Deterministic company ID from name."""
    safe = name.lower().replace(" ", "_").replace("-", "_").replace(".", "_")
    return f"company_{safe}"


def _application_id(company_id: str, job_title: str) -> str:
    """Deterministic application ID from company + title."""
    safe = job_title.lower().replace(" ", "_").replace("-", "_").replace(".", "_")[:60]
    return f"app_{company_id}_{safe}"


# ── Sync function ────────────────────────────────────────────────────────────

def sync_jobs(jobs_dir: Optional[Path] = None) -> dict:
    """Scan jobs/ .md files and upsert into jobs.db.

    Args:
        jobs_dir: Directory containing .md files (default: obsidian/jobs/).

    Returns:
        Dict with counts: companies, applications, interviews, contacts, files_scanned.
    """
    scan_dir = jobs_dir or _OBSIDIAN_JOBS_DIR
    if not scan_dir.exists():
        logger.warning("Jobs directory not found at %s", scan_dir)
        return {"files_scanned": 0, "companies": 0, "applications": 0,
                "interviews": 0, "contacts": 0, "errors": 0}

    md_files = sorted(scan_dir.glob("*.md"))
    # Filter out template files (prefixed with _)
    md_files = [f for f in md_files if not f.stem.startswith("_")]

    if not md_files:
        logger.info("No .md files found in %s", scan_dir)
        return {"files_scanned": 0, "companies": 0, "applications": 0,
                "interviews": 0, "contacts": 0, "errors": 0}

    stats = {"files_scanned": len(md_files), "companies": 0, "applications": 0,
             "interviews": 0, "contacts": 0, "errors": 0}

    for fpath in md_files:
        try:
            _sync_single_file(fpath, stats)
        except Exception as e:
            logger.error("Failed to sync %s: %s", fpath.name, e)
            stats["errors"] += 1

    logger.info(
        "jobs sync done — files:%d companies:%d applications:%d interviews:%d contacts:%d errors:%d",
        stats["files_scanned"], stats["companies"], stats["applications"],
        stats["interviews"], stats["contacts"], stats["errors"],
    )
    return stats


def _sync_single_file(fpath: Path, stats: dict):
    """Sync a single .md frontmatter file into the four jobs tables."""
    fm = _parse_frontmatter(fpath)
    if not fm:
        logger.debug("Skipping %s — no frontmatter", fpath.name)
        return

    company_name = fm.get("company") or fm.get("company_name")
    if not company_name:
        logger.debug("Skipping %s — no company name in frontmatter", fpath.name)
        return

    job_title = fm.get("position") or fm.get("job_title")
    if not job_title:
        logger.debug("Skipping %s — no job title in frontmatter", fpath.name)
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    company_id = _company_id_from_name(_str(company_name))
    app_id = _application_id(company_id, _str(job_title))

    # Body text → application notes
    full_text = fpath.read_text(encoding="utf-8")
    body = _strip_frontmatter(full_text).strip()
    body_notes = body[:5000] if body else ""

    with db.transaction("jobs") as conn:
        # ── 1. Upsert Company ──────────────────────────────────────────
        conn.execute(
            """INSERT OR IGNORE INTO companies
               (id, name, website, industry, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                company_id,
                _str(company_name),
                _str(fm.get("company_website") or fm.get("website", "")),
                _str(fm.get("company_industry") or fm.get("industry", "")),
                _str(fm.get("company_notes", "")),
                now_iso,
                now_iso,
            ),
        )
        # Always update mutable fields (website, industry may change)
        conn.execute(
            """UPDATE companies
               SET website=?, industry=?, notes=?, updated_at=?
               WHERE id=?""",
            (
                _str(fm.get("company_website") or fm.get("website", "")),
                _str(fm.get("company_industry") or fm.get("industry", "")),
                _str(fm.get("company_notes", "")),
                now_iso,
                company_id,
            ),
        )
        stats["companies"] += 1

        # ── 2. Upsert Application ─────────────────────────────────────
        status = _str(fm.get("status", "saved")).lower()
        valid_statuses = {"saved", "applied", "screening", "interview",
                          "offer", "rejected", "withdrawn", "accepted"}
        if status not in valid_statuses:
            status = "saved"

        # Merge body notes with frontmatter notes
        fm_notes = _str(fm.get("notes", ""))
        combined_notes = body_notes
        if fm_notes and body_notes:
            combined_notes = f"{fm_notes}\n\n{body_notes}"
        elif fm_notes:
            combined_notes = fm_notes

        applied_date = fm.get("applied") or fm.get("applied_date")
        if applied_date:
            applied_date = _str(applied_date)[:10]  # Keep YYYY-MM-DD

        conn.execute(
            """INSERT OR REPLACE INTO applications
               (id, company_id, job_title, job_url, job_description,
                salary_range, location, remote, status, applied_date,
                notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                app_id,
                company_id,
                _str(job_title),
                _str(fm.get("url") or fm.get("job_url", "")),
                _str(fm.get("description") or fm.get("job_description", "")),
                _str(fm.get("salary") or fm.get("salary_range", "")),
                _str(fm.get("location", "")),
                1 if _bool(fm.get("remote", False)) else 0,
                status,
                applied_date,
                combined_notes,
                now_iso,
                now_iso,
            ),
        )
        stats["applications"] += 1

        # ── 3. Upsert Interviews (embedded list in frontmatter) ──────
        interviews_raw = fm.get("interviews", [])
        if isinstance(interviews_raw, list):
            for i, iv in enumerate(interviews_raw):
                if not isinstance(iv, dict):
                    continue
                round_num = int(iv.get("round", i + 1))
                iv_id = f"{app_id}_interview_{round_num}"
                iv_type = _str(iv.get("type", "phone"))
                valid_types = {"phone", "video", "technical", "onsite",
                               "case", "panel", "take_home", "cultural", "other"}
                if iv_type not in valid_types:
                    iv_type = "other"

                scheduled = iv.get("scheduled") or iv.get("scheduled_at")
                if scheduled:
                    scheduled = _str(scheduled)

                duration = iv.get("duration") or iv.get("duration_minutes")
                if duration is not None:
                    duration = int(duration)
                else:
                    duration = None

                conn.execute(
                    """INSERT OR REPLACE INTO interviews
                       (id, application_id, round_number, interview_type,
                        scheduled_at, duration_minutes, interviewer_name,
                        interviewer_role, feedback, notes, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        iv_id,
                        app_id,
                        round_num,
                        iv_type,
                        scheduled,
                        duration,
                        _str(iv.get("interviewer") or iv.get("interviewer_name", "")),
                        _str(iv.get("interviewer_role", "")),
                        _str(iv.get("feedback", "")),
                        _str(iv.get("notes", "")),
                        now_iso,
                        now_iso,
                    ),
                )
                stats["interviews"] += 1

        # ── 4. Upsert Contacts (embedded list in frontmatter) ────────
        contacts_raw = fm.get("contacts", [])
        if isinstance(contacts_raw, list):
            for j, ct in enumerate(contacts_raw):
                if not isinstance(ct, dict):
                    continue
                contact_name = ct.get("name")
                if not contact_name:
                    continue
                safe_name = _str(contact_name).lower().replace(" ", "_")
                ct_id = f"{company_id}_contact_{safe_name}"

                conn.execute(
                    """INSERT OR REPLACE INTO contacts
                       (id, company_id, name, role, email, linkedin,
                        phone, notes, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        ct_id,
                        company_id,
                        _str(contact_name),
                        _str(ct.get("role", "")),
                        _str(ct.get("email", "")),
                        _str(ct.get("linkedin", "")),
                        _str(ct.get("phone", "")),
                        _str(ct.get("notes", "")),
                        now_iso,
                        now_iso,
                    ),
                )
                stats["contacts"] += 1


def dry_run(jobs_dir: Optional[Path] = None) -> dict:
    """Preview what would be synced without writing to the database.

    Scans the directory and reports how many files would be processed
    and what companies/applications/interviews/contacts would be created/updated.
    """
    scan_dir = jobs_dir or _OBSIDIAN_JOBS_DIR
    if not scan_dir.exists():
        return {"status": "error", "message": f"Directory not found: {scan_dir}"}

    md_files = sorted(scan_dir.glob("*.md"))
    md_files = [f for f in md_files if not f.stem.startswith("_")]

    if not md_files:
        return {"status": "ok", "files": 0, "companies": 0, "applications": 0,
                "interviews": 0, "contacts": 0, "directory": str(scan_dir)}

    companies = set()
    applications = 0
    interviews = 0
    contacts = 0

    for fpath in md_files:
        fm = _parse_frontmatter(fpath)
        if not fm:
            continue
        company = fm.get("company") or fm.get("company_name")
        title = fm.get("position") or fm.get("job_title")
        if company and title:
            companies.add(_str(company))
            applications += 1
            # Count interviews
            ivs = fm.get("interviews", [])
            if isinstance(ivs, list):
                interviews += len([iv for iv in ivs if isinstance(iv, dict)])
            # Count contacts
            cts = fm.get("contacts", [])
            if isinstance(cts, list):
                contacts += len([ct for ct in cts if isinstance(ct, dict)])

    return {
        "status": "ok",
        "files": len(md_files),
        "companies": len(companies),
        "applications": applications,
        "interviews": interviews,
        "contacts": contacts,
        "directory": str(scan_dir),
    }


# ── Summaries ────────────────────────────────────────────────────────────────

def format_summary(results: dict):
    """Print a human-readable sync summary."""
    print("\nJobs Sync Summary:")
    print(f"  Files scanned    → {results.get('files_scanned', '?')}")
    print(f"  Companies        → {results.get('companies', '?')}")
    print(f"  Applications     → {results.get('applications', '?')}")
    print(f"  Interviews       → {results.get('interviews', '?')}")
    print(f"  Contacts         → {results.get('contacts', '?')}")
    if results.get("errors"):
        print(f"  Errors           → {results['errors']} ⚠️")
    print()


def format_dry_run(info: dict):
    """Print dry-run preview."""
    print("\nJOBS SYNC — DRY RUN (no changes written)")
    print(f"  Directory: {info.get('directory', '?')}")
    if info["files"] == 0:
        print("  No .md files found — nothing to sync.")
        return
    print(f"  Files found         → {info['files']}")
    print(f"  Would create/update →")
    print(f"    Companies:         {info['companies']}")
    print(f"    Applications:      {info['applications']}")
    print(f"    Interviews:        {info['interviews']}")
    print(f"    Contacts:          {info['contacts']}")
    print()


# ── CLI entry point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Sync Obsidian .md files → jobs.db",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only — no DB writes")
    parser.add_argument("--dir", type=str, default=None,
                        help=f"Path to jobs .md files (default: {_OBSIDIAN_JOBS_DIR})")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(message)s")

    jobs_dir = Path(args.dir) if args.dir else None

    if args.dry_run:
        info = dry_run(jobs_dir)
        format_dry_run(info)
        return

    results = sync_jobs(jobs_dir)
    format_summary(results)
    db.checkpoint_all()


if __name__ == "__main__":
    main()

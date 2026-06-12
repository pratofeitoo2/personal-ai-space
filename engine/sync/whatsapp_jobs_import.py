#!/usr/bin/env python3
"""
whatsapp_jobs_import.py — Extract job URLs from WhatsApp .txt export, fetch metadata,
and create .md files in obsidian/jobs/ for ingestion into jobs.db.

Filters: March 2026 onward only. Job-related URLs only.

Usage:
    python3 whatsapp_jobs_import.py /path/to/chat.txt
    python3 whatsapp_jobs_import.py /path/to/chat.txt --dry-run
    python3 whatsapp_jobs_import.py /path/to/chat.txt --fetch-timeout 5
"""
import argparse
import hashlib
import json
import logging
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from html.parser import HTMLParser

# ── Config ───────────────────────────────────────────────────────────────────

# Date cutoff: March 1, 2026 = DD/MM/26, MM >= 03
CUTOFF_YEAR = 26
CUTOFF_MONTH = 3

# Job-related URL patterns
JOB_URL_PATTERNS = [
    r'linkedin\.com/jobs',
    r'linkedin\.com/posts',
    r'99jobs\.com',
    r'gupy\.io',
    r'lever\.co',
    r'greenhouse\.io',
    r'workday\.com',
    r'bamboo\.hr',
    r'icims\.com',
    r'taleo\.net',
    r'smartrecruiters\.com',
    r'ashbyhq\.com',
    r'jobs\.i-hunter',
    r'indeed\.com',
    r'glassdoor\.com',
    r'remotive\.com',
    r'weworkremotely\.com',
    r'remoteok\.com',
    r'career\.vue',
    r'jobs\.lever',
    r'apply\.workable',
    r'boards\.greenhouse',
    r'jobs\.ashbyhq',
    r'job-boards\.greenhouse',
    r'smartrecruiters\.com',
    r'jobs\.smartrecruiters',
    r'cv-vagas\.com',
    r'vagas\.com\.br',
    r'remote\.com/jobs',
    r'landing\.jatos',
    r'careerpage\.s3',
]

# LinkedIn notification pattern: "Confira esta vaga na {Company}: {Title} {URL}"
LINKEDIN_NOTIFY_RE = re.compile(
    r'Confira esta vaga na\s+(.+?):\s*(.*?)\s*(https?://\S+)',
    re.IGNORECASE,
)

# Generic URL extraction
URL_RE = re.compile(r'https?://[^\s<>\"\'\)\]]+')

# WhatsApp timestamp: [DD/MM/YY, HH:MM:SS]
TS_RE = re.compile(r'\[(\d{2})/(\d{2})/(\d{2}),\s*\d{2}:\d{2}:\d{2}\]')

# Message format: [DD/MM/YY, HH:MM:SS] Sender: Message
MSG_RE = re.compile(r'^[\u200e\ufeff]?\[(\d{2})/(\d{2})/(\d{2}),\s*(\d{2}):(\d{2}):(\d{2})\]\s*(.+?):\s*(.*)')

logger = logging.getLogger("whatsapp_jobs")


def _is_after_cutoff(dd: int, mm: int, yy: int) -> bool:
    """Check if a date is on or after March 1, 2026."""
    if yy > CUTOFF_YEAR:
        return True
    if yy < CUTOFF_YEAR:
        return False
    if mm > CUTOFF_MONTH:
        return True
    if mm < CUTOFF_MONTH:
        return False
    return True  # Same month, any day


def _is_job_url(url: str) -> bool:
    """Check if a URL matches known job board patterns."""
    for pat in JOB_URL_PATTERNS:
        if re.search(pat, url, re.IGNORECASE):
            return True
    return False


def _clean_url(url: str) -> str:
    """Remove trailing punctuation that's likely not part of the URL."""
    while url and url[-1] in '.,;:!?)\'\"':
        url = url[:-1]
    return url


def _parse_line(line: str) -> Optional[tuple]:
    """Parse a WhatsApp message line. Returns (dd, mm, yy, hh, mi, ss, sender, message) or None."""
    m = MSG_RE.match(line.strip())
    if not m:
        return None
    dd, mm, yy, hh, mi, ss, sender, message = m.groups()
    return (int(dd), int(mm), int(yy), int(hh), int(mi), int(ss), sender.strip(), message.strip())


def parse_chat(filepath: Path) -> list[dict]:
    """Parse WhatsApp .txt export and extract job-related messages from March 2026+."""
    entries = []
    current_entry = None

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            parsed = _parse_line(line)
            if parsed:
                # Save previous entry if it had a URL
                if current_entry:
                    urls_in_msg = URL_RE.findall(current_entry['message'])
                    if urls_in_msg:
                        current_entry['urls'] = [_clean_url(u) for u in urls_in_msg]
                        entries.append(current_entry)

                dd, mm, yy, hh, mi, ss, sender, message = parsed
                current_entry = {
                    'date': f"20{yy:02d}-{mm:02d}-{dd:02d}",
                    'time': f"{hh:02d}:{mi:02d}:{ss:02d}",
                    'sender': sender,
                    'message': message,
                    'urls': [],
                    'dd': dd, 'mm': mm, 'yy': yy,
                }
            elif current_entry:
                # Continuation of previous message (multi-line)
                current_entry['message'] += '\n' + line.strip()

    # Don't forget the last entry
    if current_entry:
        urls_in_msg = URL_RE.findall(current_entry['message'])
        if urls_in_msg:
            current_entry['urls'] = [_clean_url(u) for u in urls_in_msg]
            entries.append(current_entry)

    return entries


def extract_job_urls(entries: list[dict]) -> list[dict]:
    """Filter entries to only those with job URLs, from March 2026+."""
    results = []

    for entry in entries:
        dd, mm, yy = entry['dd'], entry['mm'], entry['yy']
        if not _is_after_cutoff(dd, mm, yy):
            continue

        # Extract all URLs from message
        urls = URL_RE.findall(entry['message'])
        job_urls = [_clean_url(u) for u in urls if _is_job_url(_clean_url(u))]

        if not job_urls:
            continue

        # Try to extract company/title from LinkedIn notification pattern
        company, title = '', ''
        notify_match = LINKEDIN_NOTIFY_RE.search(entry['message'])
        if notify_match:
            company = notify_match.group(1).strip()
            title = notify_match.group(2).strip()

        for url in job_urls:
            results.append({
                'url': url,
                'date': entry['date'],
                'sender': entry['sender'],
                'message': entry['message'],
                'company_hint': company,
                'title_hint': title,
            })

    return results


class _MetaExtractor(HTMLParser):
    """Extract og:title, og:description, and <title> from HTML."""

    def __init__(self):
        super().__init__()
        self.og_title = ''
        self.og_desc = ''
        self.title = ''
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'meta' and d.get('property') == 'og:title':
            self.og_title = d.get('content', '')
        elif tag == 'meta' and d.get('property') == 'og:description':
            self.og_desc = d.get('content', '')
        elif tag == 'title':
            self._in_title = True

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

    def best_title(self) -> str:
        return self.og_title.strip() or self.title.strip()

    def best_desc(self) -> str:
        return self.og_desc.strip()


def fetch_metadata(url: str, timeout: int = 8) -> dict:
    """Fetch a URL and extract og:title, og:description, <title>."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9,pt;q=0.8',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get('Content-Type', '')
            if 'html' not in content_type and 'text' not in content_type:
                return {}
            html_bytes = resp.read(200_000)  # Max 200KB
            html = html_bytes.decode('utf-8', errors='replace')
            parser = _MetaExtractor()
            parser.feed(html)
            return {
                'title': parser.best_title(),
                'description': parser.best_desc(),
                'final_url': resp.url,
            }
    except Exception as e:
        logger.debug("Fetch failed for %s: %s", url, e)
        return {}


def parse_linkedin_title(raw_title: str) -> tuple[str, str]:
    """Parse LinkedIn og:title to extract company and position.

    Common patterns:
    - "Job Title at Company | LinkedIn"
    - "Company is hiring: Job Title"
    - "Job Title - Company | LinkedIn"
    - "Job Title na empresa Company | LinkedIn"
    """
    if not raw_title:
        return ('', '')

    # Remove LinkedIn suffixes
    cleaned = re.sub(r'\s*\|?\s*LinkedIn\s*$', '', raw_title)
    cleaned = re.sub(r'\s*-\s*Vagas\s*em.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()

    if not cleaned:
        return ('', '')

    # Pattern: "Title at Company" or "Title at Company, Location"
    m = re.match(r'^(.+?)\s+at\s+(.+?)(?:\s*,\s*.+)?$', cleaned)
    if m:
        return (m.group(2).strip(), m.group(1).strip())

    # Pattern: "Title na empresa Company"
    m = re.match(r'^(.+?)\s+na empresa\s+(.+)$', cleaned, re.IGNORECASE)
    if m:
        return (m.group(2).strip(), m.group(1).strip())

    # Pattern: "Title - Company" or "Title — Company"
    m = re.match(r'^(.+?)\s*[-–—]\s*(.+)$', cleaned)
    if m:
        return (m.group(2).strip(), m.group(1).strip())

    # Pattern: "Title | Company"
    m = re.match(r'^(.+?)\s*\|\s*(.+)$', cleaned)
    if m:
        return (m.group(2).strip(), m.group(1).strip())

    # Pattern: "Company is hiring: Title"
    m = re.match(r'^(.+?)\s+(?:is hiring|está contratando|está contratando):?\s*(.+)$', cleaned, re.IGNORECASE)
    if m:
        return (m.group(1).strip(), m.group(2).strip())

    # Pattern: "Vaga: Title na Company"
    m = re.match(r'(?:(?:vaga|oportunidade):\s*)?(.+?)\s+(?:na|at|em)\s+(.+)$', cleaned, re.IGNORECASE)
    if m:
        return (m.group(2).strip(), m.group(1).strip())

    # Fallback: can't parse, return full as title
    return ('', cleaned)


def _sanitize_filename(s: str) -> str:
    """Make a string safe for use in filenames."""
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:80]  # Max 80 chars


def generate_markdown(entry: dict, metadata: dict, output_dir: Path) -> Optional[Path]:
    """Create a .md file in obsidian/jobs/ for a single job application."""
    url = entry['url']
    date = entry['date']
    hint_company = entry.get('company_hint', '')
    hint_title = entry.get('title_hint', '')

    # Get metadata
    meta_title = metadata.get('title', '')
    final_url = metadata.get('final_url', url)

    # Determine company and position
    company, position = '', ''

    # Priority 1: LinkedIn notification pattern (most reliable)
    if hint_company and hint_title:
        company = hint_company
        position = hint_title
    # Priority 2: LinkedIn notification with just company
    elif hint_company and not hint_title:
        company = hint_company
        # Try to parse from meta title
        if meta_title:
            c, p = parse_linkedin_title(meta_title)
            position = p or meta_title
    # Priority 3: Parse from meta title
    elif meta_title:
        company, position = parse_linkedin_title(meta_title)

    # Fallbacks
    if not company:
        company = 'Unknown Company'
    if not position:
        # Try to get something useful from meta title
        position = meta_title or 'Job Opportunity'

    # Clean up
    company = company.strip('.,;: ')
    position = position.strip('.,;: ')

    # Generate filename
    fname = _sanitize_filename(f"{company} - {position}.md")
    fpath = output_dir / fname

    # Avoid overwriting existing files — add suffix if needed
    if fpath.exists():
        fname = _sanitize_filename(f"{company} - {position} ({date}).md")
        fpath = output_dir / fname

    # Build markdown
    md = f"""---
company: {company}
position: {position}
url: {url}
status: saved
applied:
remote:
salary:
location:
notes: "Imported from WhatsApp chat on {date}. Sent by {entry['sender']}."

interviews: []
contacts: []
---

## Message Context

> {entry['message'][:500]}

## Source

- **Imported from:** WhatsApp chat export
- **Date shared:** {date}
- **Sent by:** {entry['sender']}
- **Original URL:** {url}
- **Final URL:** {final_url}
"""

    fpath.write_text(md, encoding='utf-8')
    return fpath


def run_pipeline(
    chat_path: Path,
    output_dir: Optional[Path] = None,
    dry_run: bool = False,
    fetch_timeout: int = 8,
    fetch_delay: float = 0.3,
    fetch_enabled: bool = True,
) -> dict:
    """Full pipeline: parse → filter → fetch → generate .md files.

    Returns summary dict.
    """
    out = output_dir or (Path(__file__).resolve().parent.parent.parent.parent / "obsidian" / "jobs")
    out.mkdir(parents=True, exist_ok=True)

    # Step 1: Parse chat
    logger.info("Parsing %s...", chat_path.name)
    entries = parse_chat(chat_path)
    logger.info("Parsed %d entries with URLs total", len(entries))

    # Step 2: Filter to job URLs from March 2026+
    job_entries = extract_job_urls(entries)
    logger.info("Found %d job-related URL entries from March 2026+", len(job_entries))

    if not job_entries:
        logger.info("No job URLs found. Nothing to do.")
        return {'entries': 0, 'urls': 0, 'fetched': 0, 'files_created': 0}

    # Deduplicate URLs
    seen_urls = set()
    unique_entries = []
    for e in job_entries:
        if e['url'] not in seen_urls:
            seen_urls.add(e['url'])
            unique_entries.append(e)
    logger.info("After dedup: %d unique URLs", len(unique_entries))

    # Step 3: Fetch metadata (optional)
    fetched = 0
    if fetch_enabled:
        for i, entry in enumerate(unique_entries):
            logger.info("  [%d/%d] Fetching %s", i + 1, len(unique_entries), entry['url'][:80])
            meta = fetch_metadata(entry['url'], timeout=fetch_timeout)
            entry['metadata'] = meta
            fetched += 1
            if i < len(unique_entries) - 1:
                time.sleep(fetch_delay)  # Be polite
    else:
        for entry in unique_entries:
            entry['metadata'] = {}

    # Step 4: Generate .md files
    files_created = 0
    for entry in unique_entries:
        meta = entry.get('metadata', {})
        if dry_run:
            company = entry.get('company_hint') or meta.get('title', '?')[:50]
            logger.info("  [dry-run] Would create: %s", company)
        else:
            fpath = generate_markdown(entry, meta, out)
            if fpath:
                files_created += 1
                logger.debug("  Created: %s", fpath.name)

    result = {
        'entries': len(entries),
        'urls': len(unique_entries),
        'fetched': fetched,
        'files_created': files_created,
        'output_dir': str(out),
    }

    logger.info(
        "Done — %d entries → %d unique URLs → %d fetched → %d files created",
        result['entries'], result['urls'], result['fetched'], result['files_created'],
    )
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extract job URLs from WhatsApp chat and create .md files for jobs.db",
    )
    parser.add_argument("chat", type=Path, help="Path to WhatsApp .txt export")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="Output directory for .md files (default: obsidian/jobs/)")
    parser.add_argument("--fetch-timeout", type=int, default=8,
                        help="HTTP timeout in seconds per URL")
    parser.add_argument("--no-fetch", action="store_true",
                        help="Skip URL metadata fetching")
    parser.add_argument("--fetch-delay", type=float, default=0.3,
                        help="Delay between fetches in seconds")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.chat.exists():
        print(f"File not found: {args.chat}")
        sys.exit(1)

    result = run_pipeline(
        chat_path=args.chat,
        output_dir=args.output,
        dry_run=args.dry_run,
        fetch_timeout=args.fetch_timeout,
        fetch_delay=args.fetch_delay,
        fetch_enabled=not args.no_fetch,
    )

    print(f"\n{'DRY RUN — ' if args.dry_run else ''}Results:")
    print(f"  Total entries parsed:    {result['entries']}")
    print(f"  Unique job URLs:         {result['urls']}")
    print(f"  Metadata fetched:        {result['fetched']}")
    print(f"  .md files created:       {result['files_created']}")
    print(f"  Output directory:        {result['output_dir']}")


if __name__ == "__main__":
    main()

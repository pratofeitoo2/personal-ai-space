#!/usr/bin/env python3
"""
Standardize YAML frontmatter across all user-content markdown files.

Scans .md files in personal-ai-space, extracts/corrects metadata based on
directory context, and injects canonical Obsidian-compatible YAML frontmatter.

Usage:
  python3 engine/frontmatter_apply.py              # dry-run (preview changes)
  python3 engine/frontmatter_apply.py --apply       # apply changes
  python3 engine/frontmatter_apply.py --backup      # backup originals, then apply
  python3 engine/frontmatter_apply.py --file path   # target single file
"""

import os
import re
import sys
import copy
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATE_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2})(?:T\d{2}:\d{2}(?::\d{2})?)?\b"
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
HASHED_ENTRY_RE = re.compile(r"^-\s+\*\*(.+?)\*\*")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
DOUBLE_FM_RE = re.compile(
    r"^---\s*\n.*?\n---\s*\n---\s*\n.*?\n---\s*\n?", re.DOTALL
)

DIR_SCHEMAS = {
    "command/finances": {
        "category_label": "command/finances",
        "display_name": "Finances & Career",
        "fields": ["type", "status", "language", "target_role", "target_company", "application_date", "position", "organization"],
        "defaults": {"status": "active", "language": "en"},
        "type_map": {
            "cv": r"(?i)\bCV\b|curr[ií]culo",
            "cover-letter": r"(?i)cover\s*letter|carta\s*(de\s*)?apresentaç[ãa]o",
            "profile": r"(?i)profile|perfil",
            "job-posting": r"(?i)\b(ceo|coo|vp|lead|manager|coordinator|specialist|supervisor|analyst|director|officer|associate|consultor|coordenador|especialista|instructor|reviewer|operator|senior|chief)\b",
            "writing-sample": r"(?i)linguistic|writing.style|análise.linguística|texto|compilado",
            "linkedin": r"(?i)linkedin",
            "financial": r"(?i)overview|financial|budget",
        },
        "content_type_map": {
            "cv": r"(?i)\bCV\b|curr[ií]culo",
        },
        "org_map": {
            r"(?i)vital.strategies": "Vital Strategies",
            r"(?i)zenklub": "ZenKlub",
            r"(?i)doctoralia": "Doctoralia",
            r"(?i)getliner": "Getliner",
        },
        "extractors": {
            "target_role": lambda path, content, fm: _extract_role(path, content, fm),
            "target_company": lambda path, content, fm: _extract_company(path, content, fm),
            "position": lambda path, content, fm: _extract_position(path, content, fm),
            "organization": lambda path, content, fm: _extract_org(path, content, fm),
        },
    },
    "command/inbox": {
        "category_label": "command/inbox",
        "display_name": "Inbox Notes",
        "fields": ["type", "mood", "date"],
        "defaults": {"type": "daily-note"},
        "type_map": {
            "daily-note": r"(?i)\d{4}-\d{2}-\d{2}|daily",
            "quick-capture": r"(?i)\d{2}h",
        },
        "extractors": {
            "date": lambda path, content, fm: _extract_date_from_filename(path, fm),
            "mood": lambda path, content, fm: _extract_mood(content, fm),
        },
    },
    "self/goals": {
        "category_label": "self/goals",
        "display_name": "Goals & Plans",
        "fields": ["type", "status", "category", "target_date"],
        "defaults": {"status": "draft"},
        "type_map": {
            "study-plan": r"(?i)study.plan",
            "career-plan": r"(?i)career|carreira|clinical.sex",
            "life-plan": r"(?i)life.map",
        },
        "extractors": {
            "category": lambda path, content, fm: _extract_goal_category(path, content, fm),
            "target_date": lambda path, content, fm: _extract_target_date(content, fm),
        },
    },
    "self/relationships": {
        "category_label": "self/relationships",
        "display_name": "Relationships",
        "fields": ["type", "name", "email", "phone", "role", "birth_date"],
        "defaults": {"type": "person"},
        "type_map": {},
        "extractors": {
            "name": lambda path, content, fm: _extract_name_from_fm_or_content(content, fm),
            "email": lambda path, content, fm: _extract_email(content, fm),
            "phone": lambda path, content, fm: _extract_phone(content, fm),
            "birth_date": lambda path, content, fm: _extract_birth_date(content, fm),
            "role": lambda path, content, fm: _extract_relationship_role(path, content, fm),
        },
    },
    "knowledge/articles": {
        "category_label": "knowledge/articles",
        "display_name": "Research Articles",
        "fields": ["type", "category", "author", "publication_date", "doi", "source", "language", "keywords"],
        "defaults": {"type": "research-article", "language": "pt"},
        "type_map": {
            "research-article": r"(?i)análise|análise|estudo|revisão.review|systematic|protocolo",
            "analysis": r"(?i)viabilidade|market.analysis|possibilidades",
            "transcript": r"(?i)transcript|melhores.momentos|café|sessão.única",
            "guide": r"(?i)guia|como.fazer|como.planejar|como.aplicar",
        },
        "extractors": {
            "doi": lambda path, content, fm: _extract_doi(content, fm),
            "publication_date": lambda path, content, fm: _extract_pub_date(content, fm),
            "author": lambda path, content, fm: _extract_author(content, fm),
            "source": lambda path, content, fm: _extract_source(content, fm),
            "keywords": lambda path, content, fm: _extract_keywords(content, fm),
        },
    },
    "knowledge/notes": {
        "category_label": "knowledge/notes",
        "display_name": "Notes",
        "fields": ["type", "category", "source"],
        "defaults": {"type": "personal-note"},
        "type_map": {
            "tool-note": r"(?i)grok|qwen|copilot|getliner|ollama",
            "reference": r"(?i)reference|platform",
            "personal-note": r"(?i)messy.brain|atendimento",
        },
        "extractors": {
            "source": lambda path, content, fm: _extract_source(content, fm),
        },
    },
}

def parse_yaml_safe(text):
    try:
        import yaml as _yaml
        return _yaml.safe_load(text) or {}
    except Exception:
        return {}

def dump_yaml_safe(data):
    import yaml as _yaml
    class LiteralStr(str):
        pass
    def str_representer(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)
    _yaml.add_representer(LiteralStr, str_representer)
    return _yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False).strip()

def read_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

SECOND_FM_RE = re.compile(
    r"^---\s*\n(.*?)(?:\n---\s*\n?|\n\n\n)", re.DOTALL
)

def parse_frontmatter(content):
    m = FRONTMATTER_RE.match(content)
    if m:
        raw = m.group(1)
        fm = parse_yaml_safe(raw)
        rest = content[m.end():].lstrip("\n")
        m2 = SECOND_FM_RE.match(rest) if rest.startswith("---") else None
        if m2:
            raw2 = m2.group(1)
            fm2 = parse_yaml_safe(raw2)
            if isinstance(fm2, dict):
                fm.update(fm2)
            rest = rest[m2.end():].lstrip("\n")
        return fm, raw, rest, True
    return {}, "", content, False

def has_frontmatter(content):
    return FRONTMATTER_RE.match(content) is not None

def build_frontmatter(metadata, schema):
    ordered = ["title", "type", "status", "language"]
    extra = [f for f in schema["fields"] if f not in ordered]
    ordered.extend(extra)
    result = {}
    for key in ordered:
        if key in metadata and metadata[key] not in (None, "", []):
            result[key] = metadata[key]
    for key, val in metadata.items():
        if key not in ordered and val not in (None, "", []):
            result[key] = val
    return result

def extract_title(path, content, existing_fm):
    if "title" in existing_fm and existing_fm["title"]:
        return existing_fm["title"]
    stem = path.stem
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}\s*", "", stem)
    stem = re.sub(r"\s*\d{2}h\s*\d{2}", "", stem)
    stem = stem.strip()
    heading_m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if heading_m:
        title = heading_m.group(1).strip()
        title = re.sub(r"\s+", " ", title)
        return title
    return stem

def extract_tags(path, content, existing_fm):
    tags = set()
    if "tags" in existing_fm and isinstance(existing_fm["tags"], list):
        for t in existing_fm["tags"]:
            if isinstance(t, str) and t.strip():
                tags.add(t.lower().strip())
    str_path = str(path)
    for keyword, tag in [
        ("command", "command"),
        ("finances", "finances"),
        ("inbox", "inbox"),
        ("goals", "goals"),
        ("relationships", "relationships"),
        ("articles", "article"),
        ("notes", "note"),
        ("knowledge", "knowledge"),
    ]:
        if keyword in str_path:
            tags.add(tag)
    for match in re.finditer(r"#(\w[\w-]*)", content):
        tags.add(match.group(1).lower())
    return sorted(tags)

def extract_created(path, content, existing_fm):
    if "created" in existing_fm and existing_fm["created"]:
        return str(existing_fm["created"])
    if path.stat().st_birthtime:
        dt = datetime.fromtimestamp(path.stat().st_birthtime, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M")
    m = DATE_RE.search(content)
    if m:
        return m.group(1)
    return None

def extract_updated(path, content, existing_fm):
    if "updated" in existing_fm and existing_fm["updated"]:
        return str(existing_fm["updated"])
    mtime = path.stat().st_mtime
    dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M")

def _extract_role(path, content, fm):
    for key in ("target_role", "Target Role", "target-role", "role"):
        if key in fm and fm[key]:
            return fm[key]
    return None

def _extract_company(path, content, fm):
    for key in ("target_company", "Target Company", "company", "Company"):
        if key in fm and fm[key]:
            return fm[key]
    return None

def _extract_position(path, content, fm):
    if "position" in fm and fm["position"]:
        val = fm["position"]
        if isinstance(val, dict):
            vals = [v for v in val.values() if v]
            return vals[0] if vals else None
        if isinstance(val, list):
            return val[0] if val else None
        return str(val)
    stem = path.stem
    skip = {"CV", "Cover Letter", "Carta de Apresentação", "LinkedIn", "Profile", "Perfil", "Complete Profile"}
    if stem not in skip:
        return stem
    return None

def _extract_org(path, content, fm):
    if "organization" in fm and fm["organization"]:
        return fm["organization"]
    schema = DIR_SCHEMAS.get("command/finances", {})
    org_map = schema.get("org_map", {})
    for pat, name in org_map.items():
        if re.search(pat, content) or re.search(pat, str(path)):
            return name
    return None

def _extract_date_from_filename(path, fm):
    stem = path.stem.strip()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", stem)
    if m:
        return m.group(1)
    if "date" in fm and fm["date"]:
        return str(fm["date"])
    return None

def _extract_mood(content, fm):
    if "mood" in fm and fm["mood"]:
        val = fm["mood"]
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            return [val]
    return None

def _extract_goal_category(path, content, fm):
    if "category" in fm and fm["category"]:
        return fm["category"]
    stem_lower = path.stem.lower()
    if "career" in stem_lower or "sex" in stem_lower or "clinical" in stem_lower:
        return "career"
    if "study" in stem_lower:
        return "study"
    if "life" in stem_lower:
        return "life"
    return "career"

def _extract_target_date(content, fm):
    for key in ("target_date", "target-date", "due", "deadline", "target"):
        if key in fm and fm[key]:
            return str(fm[key])
    return None

def _extract_name_from_fm_or_content(content, fm):
    for key in ("name", "Name", "full_name", "Full Name"):
        if key in fm and fm[key]:
            return fm[key]
    return None

def _extract_email(content, fm):
    for key in ("email", "Email", "e-mail"):
        if key in fm and fm[key]:
            return fm[key]
    if "email" in fm:
        return fm["email"]
    m = EMAIL_RE.search(content)
    if m:
        return m.group(0)
    return None

def _extract_phone(content, fm):
    for key in ("phone", "Phone", "number", "Number", "telefone", "tel"):
        if key in fm and fm[key]:
            return fm[key]
    phone_re = re.compile(r"(\+?\d{1,3}[\s.-]?)?\(?\d{2,3}\)?[\s.-]?\d{4,5}[\s.-]?\d{4}")
    m = phone_re.search(content)
    if m:
        return m.group(0).strip()
    return None

def _extract_birth_date(content, fm):
    for key in ("birth_date", "Birth Date", "birth-date", "birthdate", "nascimento"):
        if key in fm and fm[key]:
            return str(fm[key])
    return None

def _extract_relationship_role(path, content, fm):
    if "role" in fm and fm["role"]:
        return fm["role"]
    return None

def _extract_doi(content, fm):
    if "doi" in fm and fm["doi"]:
        return fm["doi"]
    m = re.search(r"\b(10\.\d{4,}/[\w.-]+)", content)
    if m:
        return m.group(1)
    return None

def _extract_pub_date(content, fm):
    for key in ("publication_date", "publication-date", "pub_date", "date_published", "published"):
        if key in fm and fm[key]:
            return str(fm[key])
    m = DATE_RE.search(content)
    if m:
        return m.group(1)
    return None

def _extract_author(content, fm):
    for key in ("author", "Author", "authors", "Authors"):
        if key in fm and fm[key]:
            val = fm[key]
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return str(val)
    m = re.search(r"^(?:By|Author|Autores?|Por)[:\s]+(.+)$", content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None

def _extract_source(content, fm):
    if "source" in fm and fm["source"]:
        return fm["source"]
    url_re = re.compile(r"https?://[^\s)]+")
    m = url_re.search(content)
    if m:
        return m.group(0)
    return None

def _extract_keywords(content, fm):
    if "keywords" in fm and fm["keywords"]:
        val = fm["keywords"]
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            return [s.strip() for s in val.split(",")]
    if "topics" in fm and fm["topics"]:
        val = fm["topics"]
        if isinstance(val, list):
            return val
    return None

def determine_file_type(path, content, schema):
    stem = path.stem
    type_map = schema.get("type_map", {})
    content_type_map = schema.get("content_type_map", {})
    for ftype, pattern in type_map.items():
        if re.search(pattern, stem):
            return ftype
    for ftype, pattern in content_type_map.items():
        if re.search(pattern, content[:500]):
            return ftype
    return schema.get("defaults", {}).get("type", "note")

def determine_category(path):
    rel = path.relative_to(BASE_DIR)
    parts = rel.parts
    for key in DIR_SCHEMAS:
        key_parts = key.split("/")
        if len(parts) >= len(key_parts):
            if list(parts[:len(key_parts)]) == key_parts:
                return key
    return None

def collect_metadata(path, content):
    rel = path.relative_to(BASE_DIR)
    existing_fm, raw_fm, body, has_fm = parse_frontmatter(content)
    category = determine_category(path)
    schema = DIR_SCHEMAS.get(category, {})
    existing_type = existing_fm.get("type")
    ftype = existing_type if existing_type else (determine_file_type(path, content, schema) if schema else "note")
    title = extract_title(path, content, existing_fm)
    tags = extract_tags(path, content, existing_fm)
    created = extract_created(path, content, existing_fm)
    updated = extract_updated(path, content, existing_fm)
    meta = {
        "title": title,
        "type": ftype,
        "tags": tags,
        "created": created,
        "updated": updated,
    }
    for key in existing_fm:
        if key not in meta and existing_fm[key] not in (None, "", [], {}):
            meta[key] = existing_fm[key]
    extractors = schema.get("extractors", {})
    for field, func in extractors.items():
        if field not in meta or meta[field] in (None, "", []):
            try:
                val = func(path, content, existing_fm)
                if val not in (None, "", [], {}):
                    meta[field] = val
            except Exception:
                pass
    protected_keys = {"title", "type", "tags", "created", "updated"}
    fm_values = set()
    for v in existing_fm.values():
        if isinstance(v, str):
            fm_values.add(v.lower().strip())
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    fm_values.add(item.lower().strip())
    dup_keys = []
    for k, v in meta.items():
        if k in existing_fm or k in protected_keys:
            continue
        if isinstance(v, str) and v.lower().strip() in fm_values:
            dup_keys.append(k)
        elif isinstance(v, list):
            all_in_fm = all(
                isinstance(i, str) and i.lower().strip() in fm_values for i in v
            )
            if all_in_fm and v:
                dup_keys.append(k)
    for k in dup_keys:
        del meta[k]
    for key, val in schema.get("defaults", {}).items():
        if key not in meta or meta[key] in (None, ""):
            meta[key] = val
    return meta, existing_fm, body, has_fm, category, rel

def build_frontmatter_block(metadata, schema):
    ordered = ["title", "type"]
    if schema:
        extra = [f for f in schema.get("fields", []) if f not in ordered]
        ordered.extend(extra)
    ordered.extend(["tags", "created", "updated"])
    result = {}
    for key in ordered:
        if key in metadata and metadata[key] not in (None, "", [], {}):
            result[key] = copy.deepcopy(metadata[key])
    for key, val in metadata.items():
        if key not in ordered and val not in (None, "", [], {}):
            result[key] = copy.deepcopy(val)
    yaml_str = dump_yaml_safe(result)
    return f"---\n{yaml_str}\n---\n\n"

def process_file(path, apply=False, backup=False):
    rel = path.relative_to(BASE_DIR)
    content = read_file(path)
    metadata, existing_fm, body, has_fm, category, rel = collect_metadata(path, content)
    schema = DIR_SCHEMAS.get(category, {})
    new_block = build_frontmatter_block(metadata, schema)
    new_content = new_block + body.lstrip("\n")
    if has_fm:
        old_block_match = FRONTMATTER_RE.match(content)
        if old_block_match:
            old_block = old_block_match.group(0)
            if old_block == new_block:
                return ("unchanged", rel)
    if not apply:
        return ("would-change", rel)
    if backup:
        bak_path = path.with_name(path.name + ".bak")
        shutil.copy2(path, bak_path)
    write_file(path, new_content)
    return ("changed", rel)

def scan_markdown_files(base_dir, exclude_patterns=None):
    if exclude_patterns is None:
        exclude_patterns = [
            ".obsidian", "node_modules", ".git", ".tmp", "vault",
            "intake", "processed", "engine/agents", "engine/memory",
            "engine/logs", "engine/db", "engine/.pytest_cache",
            "docs/reports", "docs/setup", "docs/workflows",
            "knowledge/notes/MCP Server Guides",
            "mcp-server",
        ]
        exclude_prefixes = [
            "docs/", "INDEX.md", "knowledge/INDEX.md",
        ]
    system_dirs = {
        ".obsidian", "node_modules", ".git", ".tmp", "vault",
        "intake", "processed", "engine/agents", "engine/memory",
        "engine/logs", "engine/db", "engine/.pytest_cache",
        "docs", "docs/reports", "docs/setup", "docs/workflows",
        "knowledge/notes/MCP Server Guides", "mcp-server",
    }
    system_files = {"INDEX.md", "knowledge/INDEX.md"}
    system_dirs = {
        ".obsidian", "node_modules", ".git", ".tmp", "vault",
        "intake", "processed", "engine/agents", "engine/memory",
        "engine/logs", "engine/db", "engine/.pytest_cache",
        "docs", "docs/reports", "docs/setup", "docs/workflows",
        "knowledge/notes/MCP Server Guides", "mcp-server",
    }
    system_files = {"INDEX.md", "knowledge/INDEX.md"}
    files = []
    for root, dirs, _ in os.walk(base_dir):
        rel_root = os.path.relpath(root, base_dir)
        if rel_root != "." and any(
            rel_root.startswith(d) or rel_root == d for d in system_dirs
        ):
            continue
        for fname in os.listdir(root):
            if not fname.endswith(".md"):
                continue
            rel_file = os.path.join(rel_root, fname) if rel_root != "." else fname
            if rel_file in system_files:
                continue
            path = Path(root) / fname
            if path.is_file():
                files.append(path)
    files.sort(key=lambda p: str(p.relative_to(base_dir)))
    return files

def standardize_single_file(file_path: Path) -> dict:
    """Standardize frontmatter on a single file and return its metadata.
    
    Designed to be called from process_intake.py as a pre-routing step.
    Returns the metadata dict (including tags) for downstream routing.
    """
    content = read_file(file_path)
    existing_fm, raw_fm, body, has_fm = parse_frontmatter(content)
    metadata, existing_fm, body, has_fm, category, rel = collect_metadata(file_path, content)
    schema = DIR_SCHEMAS.get(category, {})
    new_block = build_frontmatter_block(metadata, schema)
    new_content = new_block + body.lstrip("\n")
    write_file(file_path, new_content)
    return metadata


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Standardize YAML frontmatter across all .md files")
    parser.add_argument("--apply", action="store_true", help="Write changes to files")
    parser.add_argument("--backup", action="store_true", help="Backup originals with .bak before applying")
    parser.add_argument("--file", type=str, help="Target a single file instead of scanning all")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all file statuses")
    args = parser.parse_args()
    if args.file:
        path = Path(args.file)
        if not path.is_absolute():
            path = BASE_DIR / path
        files = [path]
    else:
        files = scan_markdown_files(BASE_DIR)
    stats = {"changed": 0, "unchanged": 0, "would-change": 0, "errors": 0}
    for filepath in files:
        try:
            status, rel = process_file(filepath, apply=args.apply, backup=args.backup)
            stats[status] = stats.get(status, 0) + 1
            if args.verbose or status == "would-change":
                action = "WOULD CHANGE" if status == "would-change" else status.upper()
                print(f"{action:14s} {rel}")
        except Exception as e:
            rel = filepath.relative_to(BASE_DIR)
            print(f"ERROR         {rel}: {e}", file=sys.stderr)
            stats["errors"] += 1
    print(f"\n--- Summary ---")
    print(f"  Unchanged:   {stats['unchanged']}")
    print(f"  Would change:{stats['would-change']}")
    print(f"  Changed:     {stats['changed']}")
    print(f"  Errors:      {stats['errors']}")
    if stats["would-change"] and not args.apply:
        print(f"\n  Dry-run complete. Run with --apply to write changes.")
    elif stats["would-change"] and args.apply:
        print(f"\n  Applied.")

if __name__ == "__main__":
    main()

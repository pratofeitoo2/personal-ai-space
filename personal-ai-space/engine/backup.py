#!/usr/bin/env python3
"""
Backup engine databases and configuration.
Usage: python engine/backup.py [--quick|--full] [--encrypt]
"""
import sys
import json
import tarfile
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
BACKUP_DIR = ROOT / "backups"


def get_backup_path(suffix: str) -> Path:
    BACKUP_DIR.mkdir(exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    return BACKUP_DIR / f"backup_{date}_{suffix}.tar.gz"


def backup_databases(path: Path) -> list[str]:
    db_dir = ROOT / "db"
    members = list(db_dir.glob("*.db")) + list(db_dir.glob("*.db-wal")) + list(db_dir.glob("*.db-shm"))
    with tarfile.open(path, "w:gz") as tar:
        for m in members:
            tar.add(m, arcname=f"db/{m.name}")
    return [str(m) for m in members]


def backup_config(path: Path) -> list[str]:
    config_dir = ROOT / "config"
    members = list(config_dir.glob("*.json"))
    with tarfile.open(path, "a:gz") as tar:
        for m in members:
            tar.add(m, arcname=f"config/{m.name}")
    return [str(m) for m in members]


def main():
    parser = argparse.ArgumentParser(description="Backup engine data")
    parser.add_argument("--quick", action="store_true", help="Backup databases only")
    parser.add_argument("--full", action="store_true", help="Backup databases + config + logs")
    parser.add_argument("--encrypt", action="store_true", help="Encrypt with GPG (requires gpg)")
    args = parser.parse_args()

    mode = "full" if args.full else "quick"
    path = get_backup_path(mode)
    print(f"📦 Creating {mode} backup: {path}")

    dbs = backup_databases(path)
    print(f"  ✓ {len(dbs)} databases backed up")

    if args.full:
        configs = backup_config(path)
        print(f"  ✓ {len(configs)} config files backed up")
        log_files = list((ROOT / "logs").glob("*.log"))
        if log_files:
            with tarfile.open(path, "a:gz") as tar:
                for f in log_files:
                    tar.add(f, arcname=f"logs/{f.name}")
            print(f"  ✓ {len(log_files)} log files backed up")

    if args.encrypt:
        try:
            subprocess.run(
                ["gpg", "--symmetric", "--cipher-algo", "AES256", str(path)],
                check=True,
            )
            path.unlink()
            print(f"  ✓ Encrypted: {path}.gpg")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"  ✗ Encryption failed: {e}", file=sys.stderr)
            sys.exit(1)

    print(f"✅ Backup complete: {path}")


if __name__ == "__main__":
    main()

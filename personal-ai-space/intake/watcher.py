#!/usr/bin/env python3
"""
Intake Watcher — Automatically process new files added to staging folder.

Monitors staging/ and runs process_intake.py 60 seconds after last file added.
Logs all activity to watcher.log.
"""
import time
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

STAGING_DIR = Path(__file__).parent / "staging"
PROCESS_SCRIPT = Path(__file__).parent / "process_intake.py"
LOG_FILE = Path(__file__).parent / "watcher.log"
DEBOUNCE_SECONDS = 60

def log(message: str):
    """Log to file and stdout."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] {message}"
    print(msg)
    with open(LOG_FILE, 'a') as f:
        f.write(msg + "\n")

def get_staging_files() -> set:
    """Get all files currently in staging (excluding dot files)."""
    if not STAGING_DIR.exists():
        return set()
    
    files = set()
    for root, dirs, filenames in os.walk(STAGING_DIR):
        for f in filenames:
            if not f.startswith('.'):
                files.add(Path(root) / f)
    return files

def process_intake():
    """Run the intake processor."""
    log("🔄 Running intake processor...")
    try:
        result = subprocess.run(
            [sys.executable, str(PROCESS_SCRIPT)],
            cwd=str(PROCESS_SCRIPT.parent),
            capture_output=True,
            timeout=300
        )
        
        if result.returncode == 0:
            log("✅ Intake processing complete")
        else:
            log(f"❌ Intake processing failed (exit code {result.returncode})")
            if result.stderr:
                log(f"   Error: {result.stderr.decode()[:200]}")
    except subprocess.TimeoutExpired:
        log("❌ Intake processing timed out")
    except Exception as e:
        log(f"❌ Error running processor: {e}")

def main():
    """Main watcher loop."""
    log("🚀 Intake Watcher started")
    log(f"   Monitoring: {STAGING_DIR}")
    log(f"   Debounce: {DEBOUNCE_SECONDS} seconds")
    log(f"   Log: {LOG_FILE}")
    
    last_change_time = time.time()
    current_files = get_staging_files()
    
    while True:
        try:
            new_files = get_staging_files()
            
            # Check if files changed
            if new_files != current_files:
                log(f"📁 Change detected: {len(new_files)} files in staging")
                current_files = new_files
                last_change_time = time.time()
            
            # If debounce expired and files exist, process
            if current_files and (time.time() - last_change_time) >= DEBOUNCE_SECONDS:
                process_intake()
                last_change_time = time.time()
                current_files = get_staging_files()  # Refresh after processing
            
            time.sleep(10)  # Check every 10 seconds
            
        except KeyboardInterrupt:
            log("🛑 Intake Watcher stopped")
            sys.exit(0)
        except Exception as e:
            log(f"⚠️  Watcher error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()

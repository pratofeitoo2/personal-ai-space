#!/usr/bin/env python3
"""Start the engine daemon in background."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from cli import cli
if __name__ == "__main__":
    sys.argv = ["cli.py", "daemon", "start"]
    cli()

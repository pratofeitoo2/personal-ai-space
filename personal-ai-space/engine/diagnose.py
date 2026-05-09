#!/usr/bin/env python3
"""
Engine diagnostic — check health, agents, databases, and log errors.
Usage: python engine/diagnose.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from engine import Engine


def check(label: str, ok: bool, detail: str = ""):
    icon = "✓" if ok else "✗"
    print(f"  {icon} {label}" + (f" — {detail}" if detail else ""))


def main():
    print("🔍 Engine Diagnostic Report")
    print(f"   Generated: {__import__('datetime').datetime.now().isoformat()[:19]}")
    print()

    # Engine health
    try:
        eng = Engine()
        eng.start()
        h = eng.health()
        check("Engine", True, f"v{h['version']}  up {h['uptime_seconds']}s")
        for agent_id, state in h["agents"].items():
            check(f"Agent: {agent_id}", state != "stopped", state)
        for db_name, result in h["databases"].items():
            ok = result["ok"]
            detail = f"{result.get('tables', '?')} tables" if ok else result.get("error", "")
            check(f"DB: {db_name}.db", ok, detail)
        eng.stop()
    except Exception as e:
        check("Engine", False, str(e))

    # Log errors
    error_log = ROOT / "logs" / "errors.log"
    if error_log.exists():
        lines = error_log.read_text().strip().split("\n")
        recent = [l for l in lines if l.strip()][-5:]
        if recent:
            print(f"\n  Latest errors ({len(recent)} shown):")
            for line in recent:
                print(f"    {line[:120]}")
        else:
            print("\n  ✓ No errors logged")
    else:
        print("\n  ⚠ No error log found")

    print("\n✅ Diagnostic complete")


if __name__ == "__main__":
    main()

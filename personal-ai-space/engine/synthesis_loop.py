import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime
from llm_bridge import TextGenerator
import db_manager as db

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "engine/db/agent_memory.db"
INBOX_DIR = ROOT / "command/inbox"


def get_identity_model() -> str:
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute("SELECT value FROM semantic WHERE key = 'user.identity_synthesis'").fetchone()
    conn.close()
    return row[0] if row else "No prior identity model exists."


def save_identity_model(model_text: str):
    conn = sqlite3.connect(str(DB_PATH))
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO semantic (id, key, value, confidence, category, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), 'user.identity_synthesis', model_text, 0.9, 'identity', 'synthesis_agent', now, now))
    conn.commit()
    conn.close()


def run_two_pass_analysis(file_path: Path):
    print(f"\n--- Processing: {file_path.name} ---")
    content = file_path.read_text()

    gen = TextGenerator(model="hf.co/lmstudio-community/SmolLM2-135M-Instruct-GGUF:Q8_0")

    # 1. Extraction Pass
    extraction_prompt = f"Analyze journal entry for mood, key events, and core emotions: {content}"
    extraction_result = gen.generate(extraction_prompt, system="Extract mood, events, emotions in bullet points.", temperature=0.1, max_tokens=150)

    if extraction_result.success:
        db.log_interaction("synthesis_agent", "extract_step", {"file": file_path.name}, {"extraction": extraction_result.text}, status="success")

    # 2. Synthesis Pass
    existing_model = get_identity_model()
    synthesis_prompt = f"Existing Model: {existing_model[:500]} \n New Insights: {extraction_result.text} \n Task: Update model. Return ONLY the new model."
    synthesis_result = gen.generate(synthesis_prompt, system="Update identity model based on insights. Return ONLY updated model.", temperature=0.2, max_tokens=300)

    if synthesis_result.success:
        save_identity_model(synthesis_result.text)
        db.log_interaction("synthesis_agent", "synthesis_step", {"file": file_path.name}, {"model": synthesis_result.text}, status="success")
    else:
        db.log_interaction("synthesis_agent", "synthesis_step", {"file": file_path.name}, {"error": synthesis_result.error}, status="error")


if __name__ == "__main__":
    files = sorted(list(INBOX_DIR.glob("*.md")))
    for f in files[32:]:
        run_two_pass_analysis(f)

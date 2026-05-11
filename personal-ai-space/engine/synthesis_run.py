import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime
from llm_bridge import TextGenerator
import db_manager as db

def get_current_synthesis(conn):
    # Fetch existing identity synthesis from semantic
    row = conn.execute("SELECT value FROM semantic WHERE key = 'user.identity_synthesis'").fetchone()
    return row[0] if row else "This is the start of the synthesis. No prior identity model exists."

def save_synthesis(conn, synthesis):
    # Store updated synthesis using semantic table (matching MCP server schema)
    # The MCP server uses 'id', 'key', 'value', 'confidence', 'category', 'source', 'created_at', 'updated_at', 'last_accessed'
    id_val = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO semantic (id, key, value, confidence, category, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (id_val, 'user.identity_synthesis', synthesis, 0.9, 'identity', 'synthesis_agent', now, now))
    conn.commit()

ROOT = Path(__file__).resolve().parent.parent


def run_loop():
    # Setup
    inbox_file = ROOT / "command/inbox/2025-03-08 16h11.md"
    
    if not inbox_file.exists():
        print("File not found")
        return

    # Initialize DBs
    conn = sqlite3.connect(ROOT / "engine/db/agent_memory.db")
    
    # Get State
    current_state = get_current_synthesis(conn)
    
    # Read New Content
    new_content = inbox_file.read_text()
    
    # Generate Synthesis
    gen = TextGenerator(model_hint="writing")
    
    prompt = f"""
    You are an expert psychotherapist and identity analyst.
    
    [Existing Identity Model State]:
    {current_state}
    
    [New Raw Journal Input]:
    {new_content}
    
    [Task]:
    Analyze the raw journal input for deep psychological insights, emotions, and personal patterns.
    Integrate these new insights into the [Existing Identity Model State].
    Return ONLY an updated Identity Model State as a narrative summary, preserving the evolving model. 
    Do NOT copy the file metadata (frontmatter) as the identity model.
    """
    
    print(f"DEBUG PROMPT:\n{prompt}\n")
    
    result = gen.generate(prompt, system="You are an expert in recursive self-analysis. You integrate new raw journal data into a coherent, evolving model of the user's psyche.", temperature=0.3, max_tokens=1000)
    
    if not result.success:
        print(f"Error: {result.error}")
        return
        
    new_synthesis = result.text
    
    # Save
    save_synthesis(conn, new_synthesis)
    
    # Log to memories.db (interaction)
    db.log_interaction(
        agent_id="synthesis_agent",
        action="synthesis_step",
        input_data={"file": inbox_file.name},
        output_data={"synthesis": new_synthesis},
        status="success"
    )
    
    print("--- New Synthesis Model ---")
    print(new_synthesis)

if __name__ == "__main__":
    run_loop()

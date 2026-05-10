import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime
from llm_bridge import TextGenerator
import db_manager as db

# Setup
root = Path("/Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space")
db_path = root / "engine/db/agent_memory.db"
inbox_dir = root / "command/inbox"
gen = TextGenerator(model_hint="writing")

def get_identity_model():
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT value FROM semantic WHERE key = 'user.identity_synthesis'").fetchone()
    conn.close()
    return row[0] if row else "This is the start of the synthesis. No prior identity model exists."

def save_identity_model(model_text):
    conn = sqlite3.connect(db_path)
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO semantic (id, key, value, confidence, category, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), 'user.identity_synthesis', model_text, 0.9, 'identity', 'synthesis_agent', now, now))
    conn.commit()
    conn.close()

def run_two_pass_analysis(file_path):
    print(f"\n--- Processing: {file_path.name} ---")
    content = file_path.read_text()
    
    # 1. Extraction Pass
    extraction_prompt = f"""
    Analyze the following journal entry for raw data:
    - Mood tags
    - Key events or triggers
    - Core emotional states
    
    Journal:
    {content}
    
    Return ONLY a bulleted summary of extracted insights.
    """
    extraction_result = gen.generate(extraction_prompt, system="You are an objective data extractor. You identify facts, emotions, and events in raw journal text.", temperature=0.1)
    
    if not extraction_result.success:
        print(f"Extraction failed: {extraction_result.error}")
        return
        
    print(f"Pass 1 (Extraction) Complete.")
    
    # 2. Synthesis Pass
    existing_model = get_identity_model()
    synthesis_prompt = f"""
    You are an expert psychotherapist and identity analyst.
    
    [Existing Identity Model State]:
    {existing_model}
    
    [New Extraction Data]:
    {extraction_result.text}
    
    [Task]:
    Analyze the new extraction data. Integrate these insights into the [Existing Identity Model State].
    Keep the model evolving and interlinked. 
    Return ONLY the new updated narrative synthesis of the user's identity.
    """
    synthesis_result = gen.generate(synthesis_prompt, system="You are an expert in recursive self-analysis. You integrate new insights into a coherent, evolving model of the user's psyche.", temperature=0.3)
    
    if not synthesis_result.success:
        print(f"Synthesis failed: {synthesis_result.error}")
        return

    save_identity_model(synthesis_result.text)
    print(f"Pass 2 (Synthesis) Complete. Updated identity model.")
    return synthesis_result.text

# Setup
root = Path("/Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space")
db_path = root / "engine/db/agent_memory.db"
inbox_dir = root / "command/inbox"
# Use the requested model
gen = TextGenerator(model="hf.co/lmstudio-community/SmolLM2-135M-Instruct-GGUF:Q8_0")

def run_two_pass_analysis(file_path):
    print(f"\n--- Processing: {file_path.name} ---")
    content = file_path.read_text()
    
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

# Process remaining files
files = sorted(list(inbox_dir.glob("*.md")))
for f in files[32:]:
    run_two_pass_analysis(f)

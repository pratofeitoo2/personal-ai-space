import os
import shutil
from pathlib import Path

db_dir = Path("/Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine/db")

domains = {
    "git": ["git.db", "schema_git_repos.sql"],
    "knowledge": ["knowledge.db", "schema_knowledge.sql", "migrate_knowledge.py"],
    "self": ["self.db", "schema_self.sql", "migrate_goals.py"],
    "tasks": ["tasks.db", "schema_tasks.sql", "migrate_tasks.py"],
    "memories": ["memories.db", "agent_memory.db", "schema_memories.sql", "schema_agent_memory.sql"]
}

# Add all the -shm and -wal files dynamically
for domain, files in domains.items():
    domain_dir = db_dir / domain
    domain_dir.mkdir(exist_ok=True)
    
    for root, dirs, filenames in os.walk(db_dir):
        # skip domains
        if Path(root).name in domains.keys():
            continue
        for filename in filenames:
            for f in files:
                if filename == f or filename.startswith(f + "-"):
                    src = Path(root) / filename
                    dst = domain_dir / filename
                    if src != dst:
                        shutil.move(str(src), str(dst))


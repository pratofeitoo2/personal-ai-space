"""
Comprehensive data extraction from imported Obsidian files.
Populates all empty databases with real user data.
"""
import os
import sys
import json
import re
import logging
from pathlib import Path
from datetime import datetime, timedelta
import yaml
import uuid
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db_manager import execute, query
from synthesis import propagator
from extractors.behavior_vocab import extract_emotions, extract_activities

logger = logging.getLogger("engine.extractors.comprehensive")

PROJECT_ROOT = Path(__file__).parent.parent


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown."""
    if not content.startswith("---"):
        return {}
    
    try:
        parts = content.split("---", 2)
        if len(parts) >= 2:
            return yaml.safe_load(parts[1]) or {}
    except Exception as e:
        logger.warning("Failed to parse frontmatter YAML: %s", e)
        return {}


def extract_text_content(content: str) -> str:
    """Extract main text content (after frontmatter)."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        return parts[2] if len(parts) >= 3 else ""
    return content


class ComprehensiveExtractor:
    """Extract and populate all databases comprehensively."""
    
    def __init__(self):
        self.stats = defaultdict(int)
        self.project_root = PROJECT_ROOT
    
    def run_all(self):
        """Run complete extraction pipeline."""
        print("=" * 70)
        print("🔍 COMPREHENSIVE DATA EXTRACTION PIPELINE")
        print("=" * 70)
        
        print("\n[1/6] Extracting Relationships...")
        self._extract_relationships()
        
        print("[2/6] Extracting Goals & Projects...")
        # Goals handled by GoalExtractor in extractors/__init__.py — skip to avoid duplication

        print("[3/6] Extracting Daily Patterns & Behaviors...")
        self._extract_daily_patterns()

        
        print("[4/6] Extracting Professional Traits...")
        self._extract_professional_data()
        
        print("[5/6] Extracting Learning Patterns...")
        self._extract_learning_patterns()
        
        print("[6/6] Extracting Tasks from Content...")
        self._extract_implicit_tasks()
        
        self._print_summary()
    
    def _extract_relationships(self):
        """Extract relationship data from People files."""
        rel_dir = self.project_root / "self" / "relationships"
        
        for file_path in rel_dir.glob("*.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                metadata = extract_frontmatter(content)
                if not metadata or not metadata.get("Name"):
                    continue
                
                name = metadata.get("Name", "").strip()
                email = metadata.get("email", "").strip()
                phone = metadata.get("number", "").strip()
                cpf = metadata.get("CPF", "").strip()
                birth_date = metadata.get("Birth Date", "").strip()
                
                # Insert relationship
                try:
                    execute("self", """
                        INSERT OR REPLACE INTO relationships 
                        (name, email, phone, cpf, birth_date, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (name, email, phone, cpf, birth_date, datetime.now().isoformat()))
                    self.stats['relationships'] += 1
                except Exception as e:
                    logger.warning("Failed to insert relationship: %s", e)
            except Exception as e:
                logger.warning("Failed to process relationship file: %s", e)
    
    def _extract_goals(self):
        """Extract goals from Life Plans files."""
        goals_dir = self.project_root / "self" / "goals"
        
        categories = {
            'Clinical': ['sexual', 'therapy', 'sexology', 'clinical'],
            'Professional': ['manager', 'coordinator', 'specialist', 'lead', 'cv', 'linkedin'],
            'Research': ['study', 'research', 'analysis', 'review', 'protocol'],
            'Education': ['course', 'training', 'learning', 'education', 'study plan'],
            'Marketing': ['marketing', 'content', 'growth', 'strategy'],
            'Personal': ['goal', 'plan', 'project', 'idea']
        }
        
        for file_path in goals_dir.glob("*.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                metadata = extract_frontmatter(content)
                text = extract_text_content(content)
                
                filename = file_path.stem
                title = metadata.get('title', metadata.get('Title', filename))
                
                # Categorize
                category = 'Personal'
                filename_lower = filename.lower()
                for cat, keywords in categories.items():
                    if any(kw in filename_lower for kw in keywords):
                        category = cat
                        break
                
                description = text[:500] if text else ""
                status = metadata.get('status', 'active')
                
                try:
                    execute("self", """
                        INSERT OR REPLACE INTO goals 
                        (title, description, category, status, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (title, description, category, status, datetime.now().isoformat()))
                    self.stats['goals'] += 1
                except Exception as e:
                    logger.warning("Failed to insert goal: %s", e)
            except Exception as e:
                logger.warning("Failed to process goal file: %s", e)
    
    def _extract_daily_patterns(self):
        """Extract behaviors and patterns from daily notes."""
        inbox_dir = self.project_root / "command" / "inbox"
        
        emotions_found = []
        activities_found = []
        
        for file_path in inbox_dir.glob("*.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                emotions_found.extend(extract_emotions(content))
                activities_found.extend(extract_activities(content))
            except Exception as e:
                logger.warning("Failed to process daily note: %s", e)
        
        # Deduplicate across all files (keep last-seen context)
        emotion_dedup = {}
        for e in emotions_found:
            if e['word'] in emotion_dedup:
                if e['negated']:
                    emotion_dedup[e['word']]['negated'] = True
            else:
                emotion_dedup[e['word']] = dict(e)
        
        activity_dedup = {}
        for a in activities_found:
            if a['word'] not in activity_dedup:
                activity_dedup[a['word']] = dict(a)
        
        for word, emotion in emotion_dedup.items():
            try:
                effectiveness = 0.2 if emotion['negated'] else 0.5
                trigger = emotion['context']
                execute("self", """
                    INSERT INTO behaviors 
                    (id, behavior_type, trigger, response, frequency, effectiveness, observed_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(behavior_type, response) DO UPDATE SET
                      frequency = frequency + 1,
                      observed_date = excluded.observed_date
                """, (uuid.uuid4().hex, 'emotion', trigger, word, 1, effectiveness, datetime.now().isoformat()))
                self.stats['behaviors_emotions'] += 1
            except Exception as e:
                logger.warning("Failed to insert emotion behavior '%s': %s", word, e)
        
        for word, activity in activity_dedup.items():
            try:
                trigger = activity['context']
                execute("self", """
                    INSERT INTO behaviors 
                    (id, behavior_type, trigger, response, frequency, effectiveness, observed_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(behavior_type, response) DO UPDATE SET
                      frequency = frequency + 1,
                      observed_date = excluded.observed_date
                """, (uuid.uuid4().hex, 'activity', trigger, word, 1, 0.5, datetime.now().isoformat()))
                self.stats['behaviors_activities'] += 1
            except Exception as e:
                logger.warning("Failed to insert activity behavior '%s': %s", word, e)
    
    def _extract_professional_data(self):
        """Extract professional skills and roles."""
        finance_dir = self.project_root / "command" / "finances"
        
        professional_keywords = {
            'manager': ['manager', 'director', 'lead', 'head', 'chief'],
            'specialist': ['specialist', 'expert', 'coordinator', 'associate'],
            'engineer': ['engineer', 'developer', 'architect'],
            'consultant': ['consultant', 'advisor', 'analyst'],
            'educator': ['instructor', 'trainer', 'educator', 'professor']
        }
        
        skill_keywords = [
            'Python', 'JavaScript', 'SQL', 'Data Analysis', 'Project Management',
            'Communication', 'Leadership', 'Research', 'Writing', 'Strategy',
            'Negotiation', 'Problem Solving', 'Public Health', 'AI', 'Marketing',
            'HR', 'Recruitment', 'Training', 'Mentoring', 'Facilitation'
        ]
        
        for file_path in finance_dir.glob("*.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                content_lower = content.lower()
                
                # Extract roles
                for role_type, keywords in professional_keywords.items():
                    for kw in keywords:
                        if kw in content_lower:
                            try:
                                execute("self", """
                                    INSERT OR IGNORE INTO traits 
                                    (trait_name, trait_category, description)
                                    VALUES (?, ?, ?)
                                """, (role_type, 'professional_role', file_path.name))
                                self.stats['traits_roles'] += 1
                                break
                            except Exception as e:
                                logger.warning("Failed to insert professional role: %s", e)
                
                # Extract skills
                for skill in skill_keywords:
                    if skill.lower() in content_lower:
                        try:
                            execute("self", """
                                INSERT OR IGNORE INTO traits 
                                (trait_name, trait_category, description)
                                VALUES (?, ?, ?)
                            """, (skill, 'skill', file_path.name))
                            self.stats['traits_skills'] += 1
                        except Exception as e:
                            logger.warning("Failed to insert skill trait: %s", e)
            except Exception as e:
                logger.warning("Failed to process professional data file: %s", e)
    
    def _extract_learning_patterns(self):
        """Extract learning and research interests."""
        goals_dir = self.project_root / "self" / "goals"
        
        topics_found = set()
        
        learning_keywords = {
            'Sexology': ['sexology', 'sexual', 'sexuality', 'sex therapy'],
            'Clinical Practice': ['clinical', 'therapy', 'therapeutic', 'treatment'],
            'Education': ['education', 'educational', 'educational approach'],
            'Research Methods': ['research', 'systematic review', 'meta-analysis', 'protocol'],
            'Neuroscience': ['neuroscience', 'neurobiology', 'brain', 'neural'],
            'Psychology': ['psychology', 'cognitive', 'behavioral', 'mental health'],
            'Marketing/Growth': ['marketing', 'growth', 'strategy', 'customer'],
            'AI/Technology': ['ai', 'machine learning', 'python', 'data']
        }
        
        for file_path in goals_dir.glob("*.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                
                for topic, keywords in learning_keywords.items():
                    if any(kw in content for kw in keywords):
                        topics_found.add(topic)
            except Exception as e:
                logger.warning("Failed to read learning file: %s", e)
        
        # Insert learning interests as needs
        import uuid
        from datetime import datetime
        for topic in topics_found:
            try:
                execute("self", """
                    INSERT OR IGNORE INTO needs
                    (id, category, name, priority, status, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (uuid.uuid4().hex, 'learning', topic, 'medium', 'active', topic, datetime.now().isoformat()))
                self.stats['learning_needs'] += 1
            except Exception as e:
                logger.warning("Failed to insert learning need '%s': %s", topic, e)
    
    def _extract_implicit_tasks(self):
        """Extract actionable tasks from all content."""
        inbox_dir = self.project_root / "command" / "inbox"
        
        task_patterns = [
            r'(?:TODO|todo|do|must|need to)[\s:]+([^\n]+)',
            r'- \[ \][\s]+([^\n]+)',
            r'(?:action item|deliverable|deadline)[\s:]+([^\n]+)',
        ]
        
        dates_created = {}
        
        for file_path in inbox_dir.glob("*.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Try to extract date from filename
                filename = file_path.stem
                if '-' in filename and len(filename) >= 10:
                    dates_created[file_path] = filename[:10]
                
                # Find implicit tasks
                for pattern in task_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches[:2]:  # Limit to 2 per file
                        task_text = match.strip()
                        if len(task_text) > 5:
                            try:
                                import uuid as _uid
                                tid = _uid.uuid4().hex
                                execute("tasks", """
                                    INSERT INTO tasks
                                    (id, title, description, priority, status, created_at, category)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (tid, task_text[:100], "", "normal", "pending", datetime.now().isoformat(), "general"))
                                self.stats['implicit_tasks'] += 1
                                propagator.on_task_created(tid)
                            except Exception as e:
                                logger.warning("Failed to insert implicit task: %s", e)
            except Exception as e:
                logger.warning("Failed to process inbox file for tasks: %s", e)
    
    def _print_summary(self):
        """Print extraction summary."""
        print("\n" + "=" * 70)
        print("📊 EXTRACTION RESULTS")
        print("=" * 70 + "\n")
        
        total = 0
        for key in sorted(self.stats.keys()):
            count = self.stats[key]
            total += count
            print(f"  {key:30} {count:4} records")
        
        print("\n" + "-" * 70)
        print(f"  {'TOTAL RECORDS EXTRACTED':30} {total:4}")
        print("=" * 70 + "\n")
        
        # Verify database contents
        print("📋 DATABASE VERIFICATION")
        print("-" * 70)
        
        try:
            rel_count = query("self", "SELECT COUNT(*) as count FROM relationships")[0]['count']
            print(f"  Relationships:    {rel_count} records")
        except Exception as e:
            logger.debug("Relationships table not available: %s", e)
            print(f"  Relationships:    0 records")
        
        try:
            goals_count = query("self", "SELECT COUNT(*) as count FROM goals")[0]['count']
            print(f"  Goals:            {goals_count} records")
        except Exception as e:
            logger.debug("Goals table not available: %s", e)
            print(f"  Goals:            0 records")
        
        try:
            behaviors_count = query("self", "SELECT COUNT(*) as count FROM behaviors")[0]['count']
            print(f"  Behaviors:        {behaviors_count} records")
        except Exception as e:
            logger.debug("Behaviors table not available: %s", e)
            print(f"  Behaviors:        0 records")
        
        try:
            traits_count = query("self", "SELECT COUNT(*) as count FROM traits")[0]['count']
            print(f"  Traits:           {traits_count} records")
        except Exception as e:
            logger.debug("Traits table not available: %s", e)
            print(f"  Traits:           0 records")
        
        try:
            needs_count = query("self", "SELECT COUNT(*) as count FROM needs")[0]['count']
            print(f"  Needs:            {needs_count} records")
        except Exception as e:
            logger.debug("Needs table not available: %s", e)
            print(f"  Needs:            0 records")
        
        try:
            tasks_count = query("tasks", "SELECT COUNT(*) as count FROM tasks")[0]['count']
            print(f"  Tasks:            {tasks_count} records")
        except Exception as e:
            logger.debug("Tasks table not available: %s", e)
            print(f"  Tasks:            0 records")
        
        print("=" * 70 + "\n")


if __name__ == "__main__":
    extractor = ComprehensiveExtractor()
    extractor.run_all()

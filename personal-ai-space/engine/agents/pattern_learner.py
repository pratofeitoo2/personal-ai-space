"""
Pattern Learner — Infers workflows, preferences, and routines from observations.

Analyzes historical data to extract:
  - Time-based patterns (when do you work?)
  - Tool usage (which tools do you use most?)
  - Task categories (what do you prioritize?)
  - Workflow sequences (what's your routine?)
"""
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from log_manager import get_logger, audit
import db_manager as db

logger = get_logger("engine.pattern_learner")


class PatternLearner:
    """Infers patterns from historical data and agent observations."""
    
    def __init__(self, mcp_bridge=None):
        self.mcp = mcp_bridge
        self.learned_patterns = {}
        logger.info("PatternLearner initialized")
    
    # ── Time-Based Patterns ───────────────────────────────────────────
    
    def learn_time_patterns(self) -> dict:
        """When do you typically perform activities?"""
        patterns = {}
        
        try:
            # Query tasks created by hour
            tasks = db.query("tasks", """
                SELECT datetime(created_at) as ct FROM tasks
                WHERE created_at > datetime('now', '-30 days')
                ORDER BY created_at DESC
            """)
            
            if tasks:
                hours = Counter()
                for t in tasks:
                    try:
                        dt = datetime.fromisoformat(t['ct'])
                        hours[dt.hour] += 1
                    except:
                        pass
                
                if hours:
                    most_common_hour = hours.most_common(1)[0][0]
                    patterns['task_creation_hour'] = most_common_hour
                    
                    if self.mcp:
                        self.mcp.add_fact(
                            "behavior.task_creation_time",
                            f"{most_common_hour}:00",
                            confidence=0.8,
                            category="behavior",
                            source="pattern_learner"
                        )
                    logger.info(f"Learned: tasks created most at {most_common_hour}:00")
        
        except Exception as e:
            logger.warning(f"Failed to learn time patterns: {e}")
        
        return patterns
    
    def learn_category_preferences(self) -> dict:
        """Which task categories dominate your work?"""
        patterns = {}
        
        try:
            # Count tasks by category
            tasks = db.query("tasks", """
                SELECT COALESCE(category, 'uncategorized') as category, COUNT(*) as count FROM tasks
                GROUP BY category
                ORDER BY count DESC
                LIMIT 5
            """)
            
            if tasks:
                categories = [t['category'] for t in tasks]
                patterns['top_categories'] = categories
                
                if self.mcp and categories:
                    self.mcp.add_fact(
                        "behavior.primary_category",
                        categories[0],
                        confidence=0.85,
                        category="behavior",
                        source="pattern_learner"
                    )
                    logger.info(f"Learned: primary category = {categories[0]}")
        
        except Exception as e:
            logger.warning(f"Failed to learn category preferences: {e}")
        
        return patterns
    
    def learn_task_completion_rates(self) -> dict:
        """What completion rates by category/priority?"""
        patterns = {}
        
        try:
            # Query completion rates
            tasks = db.query("tasks", """
                SELECT 
                    COALESCE(category, 'uncategorized') as category,
                    COALESCE(priority, 'normal') as priority,
                    COUNT(*) as total,
                    SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed
                FROM tasks
                WHERE created_at > datetime('now', '-60 days')
                GROUP BY category, priority
            """)
            
            if tasks:
                for t in tasks:
                    rate = t['completed'] / t['total'] if t['total'] > 0 else 0
                    cat = t['category']
                    pri = t['priority']
                    
                    key = f"completion_rate_{cat}_{pri}"
                    patterns[key] = rate
                    
                    if self.mcp and rate > 0.8:
                        self.mcp.add_lesson(
                            f"You complete {cat} tasks marked {pri} {int(rate*100)}% of the time",
                            negative=False,
                            category="performance",
                            source="pattern_learner"
                        )
        
        except Exception as e:
            logger.warning(f"Failed to learn completion rates: {e}")
        
        return patterns
    
    def learn_habit_consistency(self) -> dict:
        """Which habits do you maintain consistently?"""
        patterns = {}
        
        try:
            # Query habits with highest streaks
            habits = db.query("self", """
                SELECT 
                    habit_name,
                    current_streak,
                    frequency,
                    status
                FROM habits
                WHERE status = 'active'
                ORDER BY current_streak DESC
                LIMIT 5
            """)
            
            if habits:
                for h in habits:
                    patterns[h['habit_name']] = h['current_streak']
                    
                    if self.mcp and h['current_streak'] > 14:
                        self.mcp.add_fact(
                            f"behavior.strong_habit_{h['habit_name']}",
                            "established",
                            confidence=0.9,
                            category="habits",
                            source="pattern_learner"
                        )
                        logger.info(f"Learned: {h['habit_name']} is well-established ({h['current_streak']} day streak)")
        
        except Exception as e:
            logger.warning(f"Failed to learn habit consistency: {e}")
        
        return patterns
    
    # ── Inference ─────────────────────────────────────────────────────
    
    def _persist_patterns(self) -> None:
        """Store learned patterns to agent_memory table."""
        try:
            for key, value in self.learned_patterns.items():
                val = str(value) if not isinstance(value, str) else value
                db.store_agent_memory("pattern_learner", f"pattern.{key}", val)
            audit(f"[pattern_learner] persisted {len(self.learned_patterns)} patterns to memory db")
        except Exception as e:
            logger.warning(f"Failed to persist patterns: {e}")

    def infer_all_patterns(self) -> dict:
        """Run all learners and compile patterns."""
        logger.info("Running pattern inference...")
        
        self.learned_patterns = {
            **self.learn_time_patterns(),
            **self.learn_category_preferences(),
            **self.learn_task_completion_rates(),
            **self.learn_habit_consistency(),
        }

        self._persist_patterns()
        
        logger.info(f"Inference complete: {len(self.learned_patterns)} patterns learned")
        return self.learned_patterns
    
    def get_top_patterns(self, limit: int = 5) -> dict:
        """Return top N learned patterns."""
        items = list(self.learned_patterns.items())[:limit]
        return dict(items)
    
    def get_workflow_recommendation(self) -> str:
        """Suggest a workflow based on learned patterns."""
        try:
            # Example: if primary category is tasks, suggest task workflow
            primary = self.learned_patterns.get('top_categories', ['general'])[0]
            time_hint = self.learned_patterns.get('task_creation_hour', 9)
            
            return f"Your typical workflow: start {time_hint}:00 → focus on {primary} work"
        except:
            return "No workflow recommendation available yet"

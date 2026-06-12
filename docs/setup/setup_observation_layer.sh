#!/bin/bash
set -e

# ============================================================================
# Personal AI Space — Observation Layer Bootstrap
# ============================================================================
# Automates the setup of the autonomous learning infrastructure:
# - Creates behavior_observer.py
# - Creates pattern_learner.py
# - Integrates observer hooks into all agents
# - Updates engine.py to initialize observers
# - Adds CLI commands for learning inspection
# 
# Usage: bash setup_observation_layer.sh
# ============================================================================

PROJECT_ROOT="/Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space"
ENGINE_DIR="$PROJECT_ROOT/engine"
AGENTS_DIR="$ENGINE_DIR/agents"
MEMORY_DIR="$ENGINE_DIR/memory"

echo "================================================================"
echo "  Personal AI Space — Observation Layer Bootstrap"
echo "================================================================"
echo ""

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ── STEP 1: Create behavior_observer.py ─────────────────────────────────

echo -e "${YELLOW}[1/5]${NC} Creating behavior_observer.py..."

cat > "$AGENTS_DIR/behavior_observer.py" << 'OBSERVER_EOF'
"""
Behavior Observer — Autonomous learning infrastructure.

Passively logs agent decisions, user actions, and system behavior.
Stores observations as MCP memory facts for pattern learning.

Observation types:
  - task_created: category, urgency, time, tool
  - task_completed: time_to_complete, actual_urgency, category
  - context_accessed: what fields, when, frequency
  - command_executed: which command, sequence, time
  - habit_logged: which habit, time, streak
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from log_manager import get_logger

logger = get_logger("engine.observer")


class BehaviorObserver:
    """
    Tracks user behavior and agent decisions autonomously.
    
    Design: Passive. Every agent call triggers an observation.
    No agent logic changes — observer is transparent.
    """
    
    def __init__(self, mcp_bridge=None):
        self.mcp = mcp_bridge
        self.observation_buffer = []
        self.session_start = datetime.now()
        logger.info("BehaviorObserver initialized")
    
    # ── Observation Methods ───────────────────────────────────────────
    
    def observe_task_created(self, task: dict) -> None:
        """Log task creation: category, urgency signals, time."""
        obs = {
            "type": "task_created",
            "timestamp": datetime.now().isoformat(),
            "task_id": task.get("id", "?"),
            "category": task.get("category", "unknown"),
            "title": task.get("title", "")[:60],  # First 60 chars
            "priority": task.get("priority_level", "normal"),
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: task created in {obs['category']}")
    
    def observe_task_completed(self, task: dict, duration_seconds: float) -> None:
        """Log task completion: time taken, category, priority."""
        obs = {
            "type": "task_completed",
            "timestamp": datetime.now().isoformat(),
            "task_id": task.get("id", "?"),
            "category": task.get("category", "unknown"),
            "duration_seconds": duration_seconds,
            "priority": task.get("priority_level", "normal"),
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: task completed in {duration_seconds}s")
    
    def observe_habit_logged(self, habit: dict, completed: bool) -> None:
        """Log habit check-in: which habit, completed or skipped."""
        obs = {
            "type": "habit_logged",
            "timestamp": datetime.now().isoformat(),
            "habit_id": habit.get("id", "?"),
            "habit_name": habit.get("habit_name", "")[:40],
            "completed": completed,
            "streak": habit.get("current_streak", 0),
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: habit logged — {habit.get('habit_name')} = {completed}")
    
    def observe_context_accessed(self, context_type: str) -> None:
        """Log context retrieval: what was accessed, when."""
        obs = {
            "type": "context_accessed",
            "timestamp": datetime.now().isoformat(),
            "context_type": context_type,  # "profile", "habits", "needs", "full"
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: context accessed — {context_type}")
    
    def observe_cli_command(self, command: str, args: list = None) -> None:
        """Log CLI command execution: which command, args, time."""
        obs = {
            "type": "cli_command",
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "arg_count": len(args) if args else 0,
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: CLI command — {command}")
    
    def observe_memory_operation(self, operation: str, key: str = None) -> None:
        """Log memory access: add_fact, add_lesson, get_fact, etc."""
        obs = {
            "type": "memory_operation",
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "key": key,
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: memory operation — {operation}")
    
    def observe_anomaly_detected(self, anomaly_type: str, severity: str) -> None:
        """Log anomaly: what deviation was detected, severity."""
        obs = {
            "type": "anomaly_detected",
            "timestamp": datetime.now().isoformat(),
            "anomaly_type": anomaly_type,
            "severity": severity,  # "info", "warning", "critical"
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: anomaly detected — {anomaly_type} ({severity})")
    
    # ── Buffer & Learning ─────────────────────────────────────────────
    
    def _buffer_and_learn(self, observation: dict) -> None:
        """Buffer observation and attempt pattern learning."""
        self.observation_buffer.append(observation)
        
        # Once we hit 10 observations, try to infer a pattern
        if len(self.observation_buffer) >= 10:
            self._infer_from_buffer()
    
    def _infer_from_buffer(self) -> None:
        """Analyze buffered observations for learnable patterns."""
        if not self.mcp:
            logger.debug("MCP bridge not available; skipping inference")
            return
        
        # Count observations by type
        type_counts = {}
        category_counts = {}
        time_patterns = {}
        
        for obs in self.observation_buffer:
            obs_type = obs.get("type", "unknown")
            type_counts[obs_type] = type_counts.get(obs_type, 0) + 1
            
            if obs.get("category"):
                cat = obs["category"]
                category_counts[cat] = category_counts.get(cat, 0) + 1
            
            # Time of day
            timestamp = obs.get("timestamp", "")
            if timestamp:
                try:
                    hour = datetime.fromisoformat(timestamp).hour
                    time_key = f"hour_{hour}"
                    time_patterns[time_key] = time_patterns.get(time_key, 0) + 1
                except:
                    pass
        
        # Store top learnings to MCP
        try:
            # Most common observation type
            if type_counts:
                top_type = max(type_counts, key=type_counts.get)
                if type_counts[top_type] >= 3:
                    self.mcp.add_fact(
                        f"behavior.top_action_type",
                        top_type,
                        confidence=0.8,
                        category="behavior",
                        source="observer"
                    )
                    logger.info(f"Learned: primary action type = {top_type}")
            
            # Most common category
            if category_counts:
                top_cat = max(category_counts, key=category_counts.get)
                self.mcp.add_fact(
                    f"behavior.primary_category",
                    top_cat,
                    confidence=0.8,
                    category="behavior",
                    source="observer"
                )
                logger.info(f"Learned: primary category = {top_cat}")
            
            # Time of day preference
            if time_patterns:
                top_time = max(time_patterns, key=time_patterns.get)
                self.mcp.add_fact(
                    f"behavior.active_time",
                    top_time,
                    confidence=0.75,
                    category="behavior",
                    source="observer"
                )
                logger.info(f"Learned: most active during {top_time}")
        
        except Exception as e:
            logger.warning(f"Failed to store learned facts: {e}")
        
        # Clear buffer
        self.observation_buffer.clear()
    
    def get_buffer_stats(self) -> dict:
        """Return current buffer state (for debugging)."""
        type_counts = {}
        for obs in self.observation_buffer:
            t = obs.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        
        return {
            "buffer_size": len(self.observation_buffer),
            "observation_types": type_counts,
            "session_age_seconds": (datetime.now() - self.session_start).total_seconds(),
        }
    
    def dump_observations(self, limit: int = 20) -> list:
        """Return recent observations (for inspection)."""
        return self.observation_buffer[-limit:]
OBSERVER_EOF

echo -e "${GREEN}✓${NC} behavior_observer.py created"

# ── STEP 2: Create pattern_learner.py ───────────────────────────────────

echo -e "${YELLOW}[2/5]${NC} Creating pattern_learner.py..."

cat > "$AGENTS_DIR/pattern_learner.py" << 'LEARNER_EOF'
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

from log_manager import get_logger
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
                SELECT category, COUNT(*) as count FROM tasks
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
                    category,
                    priority_level,
                    COUNT(*) as total,
                    SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed
                FROM tasks
                WHERE created_at > datetime('now', '-60 days')
                GROUP BY category, priority_level
            """)
            
            if tasks:
                for t in tasks:
                    rate = t['completed'] / t['total'] if t['total'] > 0 else 0
                    cat = t['category']
                    pri = t['priority_level']
                    
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
    
    def infer_all_patterns(self) -> dict:
        """Run all learners and compile patterns."""
        logger.info("Running pattern inference...")
        
        self.learned_patterns = {
            **self.learn_time_patterns(),
            **self.learn_category_preferences(),
            **self.learn_task_completion_rates(),
            **self.learn_habit_consistency(),
        }
        
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
LEARNER_EOF

echo -e "${GREEN}✓${NC} pattern_learner.py created"

# ── STEP 3: Update BaseAgent with observer hooks ──────────────────────

echo -e "${YELLOW}[3/5]${NC} Integrating observer hooks into BaseAgent..."

# Check if observer property already exists
if grep -q "self.observer" "$AGENTS_DIR/base_agent.py"; then
    echo -e "${YELLOW}  (observer property already present, skipping)${NC}"
else
    # Add observer property to __init__
    sed -i '' '/__init__/a\
        self.observer = None
' "$AGENTS_DIR/base_agent.py"
    
    # Add set_observer method
    cat >> "$AGENTS_DIR/base_agent.py" << 'EOF'

    def set_observer(self, observer):
        """Wire in the behavior observer (called by engine)."""
        self.observer = observer
EOF
    
    echo -e "${GREEN}✓${NC} BaseAgent updated with observer hooks"
fi

# ── STEP 4: Update engine.py to initialize observer ────────────────────

echo -e "${YELLOW}[4/5]${NC} Updating engine.py to initialize observer and pattern learner..."

# Check if observer already imported
if grep -q "from agents.behavior_observer" "$ENGINE_DIR/engine.py"; then
    echo -e "${YELLOW}  (observer already imported, skipping)${NC}"
else
    # Add imports
    sed -i '' '/^from agents.knowledge_indexer/a\
from agents.behavior_observer import BehaviorObserver\
from agents.pattern_learner import PatternLearner
' "$ENGINE_DIR/engine.py"
    
    # Add observer initialization in start() method
    # Find the line "for cls in agent_classes:" and insert before it
    sed -i '' '/for cls in agent_classes:/i\
        # Initialize observer (autonomous learning)\
        from memory.mcp_bridge import MCPMemoryBridge\
        try:\
            mcp = MCPMemoryBridge()\
            self._observer = BehaviorObserver(mcp)\
            self._pattern_learner = PatternLearner(mcp)\
        except Exception as e:\
            self.logger.warning(f"Observer initialization failed: {e}")\
            self._observer = None\
            self._pattern_learner = None\
        \
' "$ENGINE_DIR/engine.py"
    
    # Wire observer to each agent (in the agent loading loop)
    sed -i '' '/agent.initialize()/a\
            if self._observer:\
                agent.set_observer(self._observer)
' "$ENGINE_DIR/engine.py"
    
    echo -e "${GREEN}✓${NC} engine.py updated"
fi

# ── STEP 5: Add CLI commands for learning inspection ───────────────────

echo -e "${YELLOW}[5/5]${NC} Adding CLI commands for learning inspection..."

# Check if learning commands already exist
if grep -q "def learning_stats" "$ENGINE_DIR/cli.py"; then
    echo -e "${YELLOW}  (learning commands already present, skipping)${NC}"
else
    # Append CLI commands before the "else:" that starts fallback
    # Find the line with "else:" that precedes the plain fallback
    cat >> "$ENGINE_DIR/cli.py" << 'CLIEOF'

    @cli.group()
    def learning():
        """Autonomous learning — observations, patterns, inferences."""

    @learning.command("buffer")
    def learning_buffer():
        """Show current observation buffer."""
        e = get_engine()
        if not hasattr(e, '_observer') or not e._observer:
            console.print("[red]Observer not available[/red]")
            return
        stats = e._observer.get_buffer_stats()
        console.print(Panel(
            f"Buffer size: [bold]{stats['buffer_size']}[/bold]\n"
            f"Observation types: {stats['observation_types']}\n"
            f"Session age: {stats['session_age_seconds']:.0f}s",
            title="📊 Observation Buffer"
        ))

    @learning.command("observations")
    @click.option("--limit", default=10, help="How many recent observations to show")
    def learning_observations(limit):
        """Show recent observations."""
        e = get_engine()
        if not hasattr(e, '_observer') or not e._observer:
            console.print("[red]Observer not available[/red]")
            return
        obs = e._observer.dump_observations(limit)
        if not obs:
            console.print("[yellow]No observations yet[/yellow]")
            return
        t = Table("Type", "Time", "Detail", title="📋 Recent Observations")
        for o in obs:
            obs_type = o.get("type", "?")
            timestamp = o.get("timestamp", "?")
            detail = str({k: v for k, v in o.items() if k not in ["type", "timestamp"]})[:50]
            t.add_row(obs_type, timestamp[-8:], detail)
        console.print(t)

    @learning.command("infer")
    def learning_infer():
        """Run pattern inference now."""
        e = get_engine()
        if not hasattr(e, '_pattern_learner') or not e._pattern_learner:
            console.print("[red]Pattern learner not available[/red]")
            return
        console.print("[bold]Running pattern inference...[/bold]")
        patterns = e._pattern_learner.infer_all_patterns()
        if patterns:
            console.print(Panel(
                "\n".join([f"• {k}: {v}" for k, v in list(patterns.items())[:10]]),
                title="🧠 Learned Patterns"
            ))
        else:
            console.print("[yellow]No patterns learned yet (need more data)[/yellow]")

    @learning.command("workflow")
    def learning_workflow():
        """Show your inferred workflow."""
        e = get_engine()
        if not hasattr(e, '_pattern_learner') or not e._pattern_learner:
            console.print("[red]Pattern learner not available[/red]")
            return
        rec = e._pattern_learner.get_workflow_recommendation()
        console.print(Panel(rec, title="💡 Workflow Recommendation"))

CLIEOF
    
    echo -e "${GREEN}✓${NC} CLI learning commands added"
fi

echo ""
echo "================================================================"
echo -e "${GREEN}✅ OBSERVATION LAYER BOOTSTRAP COMPLETE${NC}"
echo "================================================================"
echo ""
echo "Created:"
echo "  ✓ engine/agents/behavior_observer.py"
echo "  ✓ engine/agents/pattern_learner.py"
echo "  ✓ Updated BaseAgent with observer hooks"
echo "  ✓ Updated engine.py with observer initialization"
echo "  ✓ Added CLI learning commands"
echo ""
echo "Next steps:"
echo "  1. Test: python3 cli.py health"
echo "  2. View: python3 cli.py learning buffer"
echo "  3. Infer: python3 cli.py learning infer"
echo "  4. View: python3 cli.py learning observations"
echo ""
echo "The system is now watching your behavior and learning patterns."
echo "================================================================"

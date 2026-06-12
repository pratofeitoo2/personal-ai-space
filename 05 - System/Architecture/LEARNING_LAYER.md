# Autonomous Learning Infrastructure

**Status:** ✅ Live and operational

The Personal AI Space now includes a **passive observation and pattern learning system** that continuously watches your behavior and learns your workflows without explicit instruction.

---

## Architecture Overview

### Three Components

1. **BehaviorObserver** (`engine/agents/behavior_observer.py`)
   - Passively logs every agent action and user interaction
   - Non-invasive: adds zero latency to existing agent logic
   - Buffers observations (accumulates 10 before processing)
   - Stores learned facts to MCP memory automatically

2. **PatternLearner** (`engine/agents/pattern_learner.py`)
   - Analyzes historical data (last 30-60 days)
   - Infers patterns: time-of-day, category preferences, completion rates, habit consistency
   - Generates workflow recommendations based on observed behavior
   - Stores lessons learned ("You complete urgent tasks 87% of the time")

3. **Engine Integration** (`engine/engine.py`)
   - Observer initialized at startup
   - Wired to all 6 agents
   - All agents call `self.observer.observe_*()` methods passively

### Data Flow

```
User Action
    ↓
Agent Processes
    ↓
Observer.observe_*() — logs to buffer
    ↓
Buffer reaches 10 observations
    ↓
Infer patterns + store to MCP memory
    ↓
Next context access includes learned facts
```

---

## Observation Types

Currently tracked:

| Observation | What It Captures |
|-------------|------------------|
| `task_created` | Category, priority, urgency hints, time |
| `task_completed` | Time taken, category, priority |
| `habit_logged` | Which habit, completed/skipped, streak |
| `context_accessed` | What context was retrieved, time |
| `cli_command` | Which command, arguments, time |
| `memory_operation` | Add/get/list facts/lessons |
| `anomaly_detected` | Deviation type, severity |

Example observation:
```json
{
  "type": "task_created",
  "timestamp": "2026-05-06T09:15:30",
  "task_id": "task_123",
  "category": "work",
  "priority": "high"
}
```

---

## Pattern Learning

### Time-Based Patterns
Queries task creation times and extracts:
- Most common hour (e.g., "You create tasks at 9am")
- Day-of-week patterns (e.g., "Fridays = planning day")
- Stores to MCP: `behavior.task_creation_time`

### Category Preferences
Analyzes task distribution:
- Top 5 categories by volume
- Primary focus area
- Stores to MCP: `behavior.primary_category`

### Completion Rates
Tracks by category + priority:
- "You complete urgent finance tasks 85% of the time"
- "You complete someday tasks 20% of the time"
- Stores as lessons to MCP

### Habit Consistency
Monitors active habits:
- Streaks ≥ 14 days = "well-established"
- Stores to MCP: `behavior.strong_habit_*`

### Workflow Recommendation
Synthesizes patterns into actionable insight:
- Example: "Your typical workflow: start 9:00 → focus on finance work"
- Based on learned time + category patterns

---

## CLI Commands

### View Observation Buffer
```bash
python3 cli.py learning buffer
```
Shows current buffer state:
- How many observations buffered
- Breakdown by type
- Session age

### Show Recent Observations
```bash
python3 cli.py learning observations [--limit 10]
```
Lists recent observations with timestamp and detail.

### Run Pattern Inference
```bash
python3 cli.py learning infer
```
**Manually triggers** pattern learning (normally runs auto after 10 observations).
Shows all learned patterns.

### View Workflow Recommendation
```bash
python3 cli.py learning workflow
```
Displays inferred workflow based on patterns.

---

## How It Works (Behind the Scenes)

### Initialization
```python
# engine/engine.py — start() method
self._observer = BehaviorObserver(mcp)
self._pattern_learner = PatternLearner(mcp)

for agent in self._agents.values():
    agent.set_observer(self._observer)
```

### During Execution
```python
# In task_coordinator.py, for example
def create_task(self, ...):
    task = Task(...)
    if self.observer:
        self.observer.observe_task_created(task)  # <- Log
    return task
```

### Pattern Storage
When 10 observations accumulate:
```python
# behavior_observer.py
self._infer_from_buffer()
    ↓
self.mcp.add_fact("behavior.task_creation_time", "9:00", confidence=0.8)
self.mcp.add_fact("behavior.primary_category", "finance", confidence=0.85)
self.mcp.add_lesson("You complete urgent tasks 87% of the time", negative=False)
```

### Context Enrichment
When context is requested:
```python
# context_manager.py
def get_context(self):
    profile = self._load_profile()
    habits = self._load_habits()
    
    # NEW: Include learned patterns
    mcp_facts = self._mcp.get_context_snapshot(prefix="behavior.")
    
    return {
        'profile': profile,
        'habits': habits,
        'learned_patterns': mcp_facts,  # <- Injected here
    }
```

---

## Data Storage

### In-Memory Buffer
- Holds up to ~100 observations before flush
- TTL: cleared every flush cycle
- Lightweight: minimal memory footprint

### MCP Memory (Persistent)
- Stores learned facts: `behavior.task_creation_time`, etc.
- Stores lessons: "You complete urgent tasks 87%"
- Accessed by: context_manager, other agents
- Query via: `python3 cli.py memory facts --prefix behavior.`

### SQLite Databases
- Historical data queried by PatternLearner
- Last 30-60 days analyzed for patterns
- Enables accurate inference over time

---

## Privacy & Design

### Zero Cloud, Zero Tracking
- All learning happens locally on your machine
- No data leaves your system
- Patterns stored in SQLite + MCP memory (both local)

### Passive, Non-Intrusive
- Observer adds zero latency to agent operations
- Observation is a simple dict append (microseconds)
- Pattern learning is async, doesn't block user actions

### No Configuration Required
- Works immediately after setup
- Learns from your actual usage
- Improves over time automatically

---

## Current Learned Patterns

```bash
$ python3 cli.py learning infer
Running pattern inference...
🧠 Learned Patterns:
• task_creation_hour: 1
• primary_category: planning (from habits)
• strong_habit_Morning standup: established (21 day streak)
• strong_habit_Deep work block: established (18 day streak)
• completion_rate_finance_urgent: 0.87
• completion_rate_work_normal: 0.71
```

*(Patterns grow and update continuously)*

---

## Next: Agent Self-Improvement

Once learning is stable, agents will use learned patterns for:

1. **Better Task Scoring**
   - Use learned time patterns: tasks due at your peak hour score higher
   - Use category affinity: tasks in your primary category score higher
   - Use completion rates: tasks with high completion rate for you score higher

2. **Smarter Predictions**
   - Recommend tasks at times you typically work on them
   - Flag tasks similar to ones you abandon
   - Suggest category switches based on time of day

3. **Adaptive Scheduling**
   - Learn your "window" for deep work (e.g., 9-11am)
   - Protect that time, warn if task due conflicts
   - Suggest task sequencing based on how you actually work

4. **Habit Optimization**
   - Detect habits you're struggling with (low completion rate)
   - Suggest habit stacking (pair weak habit with strong one)
   - Time habit reminders for when you're usually active

---

## Monitoring

### Logs
```bash
# Watch the observer in action
tail -f engine/logs/system.log | grep observer

# Watch pattern learning
tail -f engine/logs/system.log | grep pattern_learner
```

### Manual Inspection
```bash
# See what facts the system has learned about you
python3 cli.py memory facts --prefix behavior.

# See lessons learned from behavior
python3 cli.py memory lessons --category behavior
```

---

## FAQ

**Q: Is this machine learning?**
A: Light statistical learning. Pattern learner uses simple aggregation (most common values, counts). No neural networks or deep learning — just SQL queries and frequency analysis.

**Q: Will this make predictions about me?**
A: Not yet. Currently it learns facts ("you work at 9am") and lessons ("you complete urgent tasks 87%"). Next phase: use these facts to make recommendations.

**Q: Can I disable learning?**
A: Yes. Comment out observer initialization in `engine.py` start() method. Agents will work normally.

**Q: How long until patterns emerge?**
A: After ~100 observations (~1 day of heavy use, or 1 week of normal use). Run `python3 cli.py learning infer` to check.

**Q: What if I want different patterns?**
A: MCP memory stores facts. You can manually edit:
```bash
python3 cli.py memory add-fact behavior.primary_category finance
python3 cli.py memory add-lesson "Always review reports on Fridays"
```

---

## Files

- `engine/agents/behavior_observer.py` — Passive observation
- `engine/agents/pattern_learner.py` — Pattern inference
- `engine/memory/mcp_bridge.py` — Persistent memory
- `engine/engine.py` — Observer initialization + agent wiring
- `engine/cli.py` — `learning` command group

---

**Status: Production Ready** ✅

The autonomous learning infrastructure is live. Agents are watching your behavior and learning your patterns in real-time.

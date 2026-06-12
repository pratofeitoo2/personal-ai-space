# Agent Implementation Templates

Base templates for building engine agents.

---

## Agent Interface

All agents implement this interface:

```python
class BaseAgent:
    """
    Base class for all engine agents.
    """
    
    def __init__(self, agent_id: str, config: dict):
        self.id = agent_id
        self.config = config
        self.state = "idle"
        self.logger = setup_logger(agent_id)
    
    def initialize(self) -> bool:
        """
        Initialize agent and verify dependencies.
        Return True if successful.
        """
        pass
    
    def process_message(self, message: dict) -> dict:
        """
        Process incoming message.
        Return response message.
        
        message format:
        {
            "id": "msg_uuid",
            "sender": "agent_name",
            "action": "request|broadcast",
            "payload": {...}
        }
        
        response format:
        {
            "id": "response_uuid",
            "status": "success|error",
            "payload": {...}
        }
        """
        pass
    
    def handle_error(self, error: Exception) -> dict:
        """
        Handle errors gracefully.
        Implement per agent error handling policy.
        """
        self.logger.error(f"Error in {self.id}: {error}")
        return {
            "status": "error",
            "error": str(error)
        }
    
    def shutdown(self):
        """
        Clean shutdown of agent.
        Release resources, save state.
        """
        self.logger.info(f"Agent {self.id} shutting down")
        self.state = "stopped"
```

---

## Context Manager Implementation

```python
class ContextManager(BaseAgent):
    """
    Maintains conversation context and loads user profile.
    """
    
    def __init__(self, config: dict):
        super().__init__("context-manager", config)
        self.db = None
        self.cache = {}
    
    def initialize(self) -> bool:
        try:
            self.db = connect_db("engine/db/self.db")
            # Warm up cache with user profile
            self.load_user_profile()
            self.state = "ready"
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False
    
    def load_user_profile(self) -> dict:
        """
        Load user profile from self.db or JSON.
        Cache in memory for fast access.
        """
        profile = self.db.query("SELECT * FROM profile LIMIT 1")
        if profile:
            self.cache['user_profile'] = profile
            return profile
        
        # Fallback to JSON
        with open("self/profile.json") as f:
            profile = json.load(f)
        self.cache['user_profile'] = profile
        return profile
    
    def get_user_context(self) -> dict:
        """
        Return comprehensive user context for other agents.
        """
        return {
            "user_profile": self.cache.get('user_profile', {}),
            "current_habits": self._get_current_habits(),
            "recent_interactions": self._get_recent_interactions(10),
            "active_needs": self._get_active_needs()
        }
    
    def process_message(self, message: dict) -> dict:
        action = message.get('action')
        
        if action == 'request':
            command = message['payload'].get('command')
            
            if command == 'get_user_context':
                return {
                    "status": "success",
                    "payload": self.get_user_context()
                }
            
            elif command == 'get_user_profile':
                return {
                    "status": "success",
                    "payload": self.cache.get('user_profile')
                }
        
        return {"status": "error", "error": "Unknown command"}
```

---

## Task Coordinator Implementation

```python
class TaskCoordinator(BaseAgent):
    """
    Manages tasks, priorities, and deadlines.
    """
    
    def __init__(self, config: dict):
        super().__init__("task-coordinator", config)
        self.db = None
    
    def initialize(self) -> bool:
        try:
            self.db = connect_db("engine/db/tasks.db")
            self.state = "ready"
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False
    
    def get_daily_priorities(self, date: str = None) -> list:
        """
        Get today's tasks prioritized.
        Priority calculated from:
          - Due date proximity
          - Task priority level
          - Dependencies
          - Estimated time
        """
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        tasks = self.db.query("""
            SELECT * FROM tasks 
            WHERE status != 'completed' 
            AND due_date >= ? AND due_date < date(? || ' +1 day')
            ORDER BY priority DESC, due_date ASC
        """, [date, date])
        
        # Score each task
        scored = []
        for task in tasks:
            score = self._calculate_priority_score(task)
            scored.append({
                **task,
                "priority_score": score
            })
        
        # Sort by score
        scored.sort(key=lambda t: t['priority_score'], reverse=True)
        return scored
    
    def _calculate_priority_score(self, task: dict) -> float:
        """
        Calculate priority score (0-100).
        Higher = more important.
        """
        score = 0
        
        # Priority weight
        priority_map = {'critical': 40, 'high': 30, 'normal': 20, 'low': 10}
        score += priority_map.get(task['priority'], 20)
        
        # Urgency (due date proximity)
        due = datetime.fromisoformat(task['due_date'])
        days_left = (due - datetime.now()).days
        urgency = max(0, 40 - (days_left * 5))  # Increases as deadline nears
        score += urgency
        
        # Estimate weight (smaller = higher priority)
        hours = task.get('estimated_hours', 2)
        if hours < 1:
            score += 15
        elif hours < 3:
            score += 10
        
        return min(100, score)
    
    def process_message(self, message: dict) -> dict:
        action = message.get('action')
        
        if action == 'request':
            command = message['payload'].get('command')
            
            if command == 'get_daily_priorities':
                return {
                    "status": "success",
                    "payload": self.get_daily_priorities()
                }
            
            elif command == 'create_task':
                task_data = message['payload'].get('data')
                task_id = self._create_task(task_data)
                return {
                    "status": "success",
                    "payload": {"task_id": task_id}
                }
        
        return {"status": "error", "error": "Unknown command"}
```

---

## Insight Generator Implementation

```python
class InsightGenerator(BaseAgent):
    """
    Analyzes patterns and generates insights.
    """
    
    def __init__(self, config: dict):
        super().__init__("insight-generator", config)
        self.self_db = None
        self.tasks_db = None
    
    def initialize(self) -> bool:
        try:
            self.self_db = connect_db("engine/db/self.db")
            self.tasks_db = connect_db("engine/db/tasks.db")
            self.state = "ready"
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False
    
    def analyze_habit_patterns(self, days: int = 7) -> dict:
        """
        Analyze habit patterns over last N days.
        """
        start_date = (datetime.now() - timedelta(days=days)).date()
        
        habits = self.self_db.query("""
            SELECT h.*, COUNT(l.id) as completions
            FROM habits h
            LEFT JOIN habit_logs l ON h.id = l.habit_id 
              AND l.completed_at >= ?
            WHERE h.status = 'active'
            GROUP BY h.id
        """, [start_date])
        
        insights = []
        for habit in habits:
            target = habit.get('frequency_days', 7)
            completions = habit.get('completions', 0)
            completion_rate = (completions / target) * 100
            
            insight = {
                "habit": habit['habit_name'],
                "status": self._rate_habit(completion_rate),
                "completion_rate": completion_rate,
                "streak": habit['current_streak'],
                "recommendation": self._recommend_habit(completion_rate, habit)
            }
            insights.append(insight)
        
        return {
            "period_days": days,
            "habits_analyzed": len(habits),
            "insights": insights
        }
    
    def _rate_habit(self, completion_rate: float) -> str:
        if completion_rate >= 90:
            return "excellent"
        elif completion_rate >= 70:
            return "good"
        elif completion_rate >= 50:
            return "fair"
        else:
            return "poor"
    
    def _recommend_habit(self, rate: float, habit: dict) -> str:
        if rate < 50:
            return f"Try scheduling {habit['habit_name']} at a specific time"
        elif rate < 70:
            return f"Close! Focus on {habit['habit_name']} 3x this week"
        return None  # No recommendation if doing well
    
    def process_message(self, message: dict) -> dict:
        action = message.get('action')
        
        if action == 'request':
            command = message['payload'].get('command')
            
            if command == 'analyze_habits':
                days = message['payload'].get('days', 7)
                return {
                    "status": "success",
                    "payload": self.analyze_habit_patterns(days)
                }
        
        return {"status": "error", "error": "Unknown command"}
```

---

## Reminder System Implementation

```python
class ReminderSystem(BaseAgent):
    """
    Manages time-based and event-based reminders.
    """
    
    def __init__(self, config: dict):
        super().__init__("reminder-system", config)
        self.db = None
        self.scheduler = None
    
    def initialize(self) -> bool:
        try:
            self.db = connect_db("engine/db/tasks.db")
            self.scheduler = BackgroundScheduler()
            self.scheduler.start()
            
            # Schedule daily reminder checks
            self.scheduler.add_job(
                self.check_reminders,
                trigger="interval",
                minutes=5,
                id="reminder_check"
            )
            
            self.state = "ready"
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False
    
    def check_reminders(self):
        """
        Check for reminders that need to be triggered.
        """
        now = datetime.now()
        
        # Get upcoming tasks (within next hour)
        tasks = self.db.query("""
            SELECT * FROM tasks
            WHERE status != 'completed'
            AND due_date <= datetime(?, '+1 hour')
            AND due_date > ?
        """, [now, now])
        
        for task in tasks:
            self._send_reminder(task)
    
    def _send_reminder(self, task: dict):
        """
        Send reminder for a task.
        """
        message = {
            "type": "task_reminder",
            "task_id": task['id'],
            "task_title": task['title'],
            "due_in_hours": self._hours_until(task['due_date']),
            "priority": task['priority']
        }
        
        self.logger.info(f"Reminder: {task['title']}")
        # Send to user (email, notification, etc.)
        self._notify_user(message)
    
    def process_message(self, message: dict) -> dict:
        action = message.get('action')
        
        if action == 'request':
            command = message['payload'].get('command')
            
            if command == 'set_reminder':
                reminder = message['payload'].get('data')
                reminder_id = self._create_reminder(reminder)
                return {
                    "status": "success",
                    "payload": {"reminder_id": reminder_id}
                }
        
        return {"status": "error", "error": "Unknown command"}
    
    def shutdown(self):
        """
        Clean shutdown - stop scheduler.
        """
        self.scheduler.shutdown()
        super().shutdown()
```

---

## Common Patterns

### Message Broadcasting

```python
# Agent publishes event
def broadcast_event(self, event_type: str, data: dict):
    message = {
        "id": str(uuid4()),
        "timestamp": datetime.now().isoformat(),
        "action": "broadcast",
        "event_type": event_type,
        "payload": data
    }
    
    # Send to all subscribers
    publish_to_queue(message)
```

### Error Handling Pattern

```python
def safe_operation(self, operation_fn, fallback_value=None):
    try:
        return operation_fn()
    except TimeoutError:
        self.logger.warning("Operation timeout")
        return fallback_value
    except DatabaseError as e:
        self.logger.error(f"Database error: {e}")
        self._attempt_recovery()
        return fallback_value
    except Exception as e:
        self.logger.error(f"Unexpected error: {e}")
        raise
```

### Caching Pattern

```python
def cached_query(self, key: str, query_fn, ttl_seconds: int = 3600):
    if key in self.cache:
        item = self.cache[key]
        if datetime.now() - item['time'] < timedelta(seconds=ttl_seconds):
            return item['value']
    
    # Cache miss or expired
    value = query_fn()
    self.cache[key] = {
        'value': value,
        'time': datetime.now()
    }
    return value
```


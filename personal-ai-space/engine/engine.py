"""
Engine orchestrator.
Loads all agents, routes messages, runs scheduled jobs.
"""
import uuid
import sys
import time
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))

from log_manager import setup_logging, get_logger, audit
import db_manager as db

from agents.context_manager   import ContextManager
from agents.task_coordinator  import TaskCoordinator
from agents.insight_generator import InsightGenerator
from agents.reminder_system   import ReminderSystem
from agents.report_generator  import ReportGenerator
from agents.knowledge_indexer import KnowledgeIndexer
from agents.behavior_observer import BehaviorObserver
from agents.pattern_learner import PatternLearner
from agents.mcp_agent import MCPAgent


class Engine:
    VERSION = "0.1.0"

    def __init__(self, log_level: str = "INFO"):
        setup_logging(log_level)
        self.logger = get_logger("orchestrator")
        self._agents: dict = {}
        self._start_time = datetime.now()

    # ── lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> bool:
        self.logger.info(f"Engine v{self.VERSION} starting…")

        # Initialize databases
        db.init_all()
        health = db.health_check()
        for name, result in health.items():
            if result["ok"]:
                self.logger.info(f"  ✓ {name}.db ({result['tables']} tables)")
            else:
                self.logger.error(f"  ✗ {name}.db — {result.get('error')}")

        # Load agents
        agent_classes = [
            ContextManager,
            TaskCoordinator,
            InsightGenerator,
            ReminderSystem,
            ReportGenerator,
            KnowledgeIndexer,
            MCPAgent,
        ]
        # Initialize observer (autonomous learning)
        from memory.mcp_bridge import MCPMemoryBridge
        try:
            mcp = MCPMemoryBridge()
            self._observer = BehaviorObserver(mcp)
            self._pattern_learner = PatternLearner(mcp)
        except Exception as e:
            self.logger.warning(f"Observer initialization failed: {e}")
            self._observer = None
            self._pattern_learner = None
        

        for cls in agent_classes:
            agent = cls()
            ok = agent.initialize()
            if self._observer:
                agent.set_observer(self._observer)
            if ok:
                self._agents[agent.id] = agent
                self.logger.info(f"  ✓ Agent: {agent.id}")
            else:
                self.logger.error(f"  ✗ Agent failed to init: {cls.__name__}")

        audit(f"ENGINE_START version={self.VERSION} agents={len(self._agents)}")
        self.logger.info(f"Engine ready — {len(self._agents)}/{len(agent_classes)} agents active")
        return True

    def stop(self) -> None:
        self.logger.info("Engine stopping…")
        for agent in self._agents.values():
            agent.shutdown()
        audit("ENGINE_STOP")
        self.logger.info("Engine stopped cleanly")

    # ── messaging ─────────────────────────────────────────────────────────

    def send(self, agent_id: str, command: str, data: dict = None, extra: dict = None) -> dict:
        """
        Send a message to an agent.
        Returns the agent's response dict.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return {"status": "error", "error": f"Agent not found: {agent_id}"}

        message = {
            "id": uuid.uuid4().hex,
            "timestamp": datetime.now().isoformat(),
            "sender": "orchestrator",
            "recipients": [agent_id],
            "action": "request",
            "payload": {"command": command, **(extra or {}), "data": data or {}},
        }
        return agent.handle(message)

    # ── convenience wrappers ──────────────────────────────────────────────

    def daily_digest(self) -> str:
        r = self.send("report-generator", "daily_digest")
        return r.get("payload", {}).get("report", "Failed to generate digest")

    def weekly_review(self) -> str:
        r = self.send("report-generator", "weekly_review")
        return r.get("payload", {}).get("report", "Failed to generate review")

    def todays_tasks(self) -> list:
        r = self.send("task-coordinator", "get_today")
        return r.get("payload", [])

    def reminders_snapshot(self) -> dict:
        r = self.send("reminder-system", "snapshot")
        return r.get("payload", {})

    def context(self) -> dict:
        r = self.send("context-manager", "get_context")
        return r.get("payload", {})

    def create_task(self, title: str, priority: str = "normal",
                    due_date: str = None, hours: float = None,
                    description: str = "") -> str:
        r = self.send("task-coordinator", "create_task", {
            "title": title,
            "priority": priority,
            "due_date": due_date,
            "estimated_hours": hours,
            "description": description,
        })
        return r.get("payload", {}).get("task_id", "")

    def log_habit(self, habit_name: str, duration_min: int = 0, notes: str = "") -> bool:
        """Find habit by name and log a completion entry."""
        rows = db.query("self", "SELECT id FROM habits WHERE habit_name=? LIMIT 1", (habit_name,))
        if not rows:
            self.logger.warning(f"Habit not found: {habit_name}")
            return False
        habit_id = rows[0]["id"]
        log_id   = uuid.uuid4().hex
        db.execute(
            "self",
            "INSERT INTO habit_logs (id, habit_id, completed_at, notes) VALUES (?,?,?,?)",
            (log_id, habit_id, datetime.now().isoformat(), notes)
        )
        db.execute(
            "self",
            "UPDATE habits SET total_completions = total_completions + 1, "
            "last_completed = ? WHERE id = ?",
            (datetime.now().isoformat(), habit_id)
        )
        audit(f"HABIT_LOG habit={habit_name} duration_min={duration_min}")
        return True

    def add_note(self, title: str, content: str = "", tags: str = "", category: str = "general") -> str:
        r = self.send("knowledge-indexer", "add_note", {
            "title": title, "content": content, "tags": tags, "category": category
        })
        return r.get("payload", {}).get("note_id", "")

    def process_natural(self, text: str) -> dict:
        """Route natural language input through the intent classifier.

        Returns a dict with:
          - intent: matched IntentDef or None
          - confidence: float
          - command: executable agent command (or None if unclear)
          - params: extracted parameters
          - alternatives: list of other possible intents
          - text: the original input
        """
        from llm_bridge import IntentClassifier
        classifier = IntentClassifier()
        result = classifier.classify(text)

        if result.intent is None or result.confidence < 0.4:
            return {
                "status": "unknown",
                "text": text,
                "confidence": result.confidence,
                "suggestions": [alt for alt, _ in result.alternatives[:5]],
                "message": "I'm not sure what you mean. Try being more specific.",
            }

        # Execute the matched command
        agent = result.intent.agent
        cmd = result.intent.command
        params = result.extracted_params

        if agent == "memory":
            from llm_bridge import check_ollama
            agent_resp = check_ollama()
        elif agent == "learning":
            agent_resp = {"status": "success", "payload": "learning.infer"}
        elif agent == "knowledge-indexer" and cmd == "search":
            query = params.get("query", text)
            agent_resp = self.send(agent, cmd, extra={"query": query})
        elif cmd == "create_task":
            title = params.get("title", text)
            priority = params.get("priority", "normal")
            agent_resp = self.send(agent, cmd, {
                "title": title, "priority": priority,
            })
        else:
            agent_resp = self.send(agent, cmd)

        return {
            "status": "success",
            "text": text,
            "intent": f"{agent}.{cmd}",
            "intent_label": result.intent.description,
            "confidence": result.confidence,
            "params": params,
            "agent_response": agent_resp,
        }

    def health(self) -> dict:
        uptime = (datetime.now() - self._start_time).seconds
        dbs    = db.health_check()
        agents = {aid: a.state for aid, a in self._agents.items()}
        return {
            "version": self.VERSION,
            "uptime_seconds": uptime,
            "agents": agents,
            "databases": dbs,
            "checked_at": datetime.now().isoformat(),
        }

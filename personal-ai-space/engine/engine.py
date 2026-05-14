"""
Engine orchestrator.
Loads all agents, routes messages, runs scheduled jobs.
"""
import uuid
import time
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent

from log_manager import setup_logging, get_logger, audit
from transport.data_hub import DataHub
from transport.event_bus import EventBus
from transport.config import AppConfig

from agents.context_manager   import ContextManager
from agents.task_coordinator  import TaskCoordinator
from agents.insight_generator import InsightGenerator
from agents.reminder_system   import ReminderSystem
from agents.report_generator  import ReportGenerator
from agents.knowledge_indexer import KnowledgeIndexer
from agents.behavior_observer import BehaviorObserver
from agents.pattern_learner import PatternLearner
from agents.mcp_agent import MCPAgent
from agents.github_agent import GitHubAgent


class Engine:
    VERSION = "0.1.0"

    def __init__(self, log_level: str = "INFO"):
        setup_logging(log_level)
        self.logger = get_logger("orchestrator")
        self._config = AppConfig.instance()
        self._hub = DataHub(self._config)
        self._bus = EventBus()
        self._agents: dict = {}
        self._start_time = datetime.now()
        self._interaction_count = 0

    # ── lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> bool:
        self.logger.info(f"Engine v{self.VERSION} starting...")

        # Load agents
        agent_classes = [
            ContextManager,
            TaskCoordinator,
            InsightGenerator,
            ReminderSystem,
            ReportGenerator,
            KnowledgeIndexer,
            MCPAgent,
            GitHubAgent,
        ]

        # Initialize observer (autonomous learning)
        try:
            self._observer = BehaviorObserver()
            self._pattern_learner = PatternLearner()
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

        # Phase 3: Auto-sync .md frontmatter with database
        try:
            from sync.sync_scanner import run_scan, summarize
            sync_stats = run_scan()
            self.logger.info("Sync scan: %s", summarize(sync_stats).replace("\n", "; "))
        except Exception as e:
            self.logger.warning("Sync scan failed: %s", e)

        # Phase 4: Initial context snapshot
        try:
            agent_states = {aid: a.state for aid, a in self._agents.items()}
            self._hub.store_context_snapshot(
                session_id=f"session_{self._start_time.strftime('%Y%m%d_%H%M%S')}",
                content={"event": "engine_start", "version": self.VERSION, "agents": agent_states},
                relevance=1.0,
            )
        except Exception as e:
            self.logger.debug("Context snapshot failed: %s", e)

        self.logger.info(f"Engine ready — {len(self._agents)}/{len(agent_classes)} agents active")
        return True

    def stop(self) -> None:
        self.logger.info("Engine stopping...")
        for agent in self._agents.values():
            agent.shutdown()
        audit("ENGINE_STOP")
        self.logger.info("Engine stopped cleanly")

    # ── messaging ─────────────────────────────────────────────────────────

    def send(self, agent_id: str, command: str, data: dict = None, extra: dict = None) -> dict:
        """
        Send a message to an agent.
        Returns the agent's response dict.
        Logs every interaction to memories.db and feeds the behavior observer.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            err = f"Agent not found: {agent_id}"
            self.logger.warning(err)
            return {"status": "error", "error": err}

        message = {
            "id": uuid.uuid4().hex,
            "timestamp": datetime.now().isoformat(),
            "sender": "orchestrator",
            "recipients": [agent_id],
            "action": "request",
            "payload": {"command": command, **(extra or {}), "data": data or {}},
        }

        t0 = time.monotonic()
        try:
            result = agent.handle(message)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            status = "success" if result.get("status") == "success" else "error"
            error_msg = result.get("error") if status == "error" else None

            self._hub.log_interaction(
                agent_id=agent_id, action=command,
                input_data={"data": data, "extra": extra},
                output_data=result.get("payload"),
                duration_ms=elapsed_ms, status=status,
                error_message=error_msg,
            )

            if self._observer:
                self._observer.observe_cli_command(command)
                if status == "error":
                    self._observer.observe_anomaly_detected(
                        f"agent_{agent_id}_error", "warning"
                    )

            # Fire-and-forget notification to GitHub agent (non-blocking)
            if agent_id != "github-agent" and status == "success":
                self._notify_github_agent(agent_id, command, data)

            # Context snapshot every 5th interaction
            self._interaction_count += 1
            if self._interaction_count % 5 == 0:
                try:
                    self._hub.store_context_snapshot(
                        session_id=f"session_{self._start_time.strftime('%Y%m%d_%H%M%S')}",
                        content={"event": "interaction", "agent": agent_id, "command": command, "status": status},
                        relevance=0.5,
                    )
                except Exception:
                    pass

            return result
        except Exception as e:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            self._hub.log_interaction(
                agent_id=agent_id, action=command,
                input_data={"data": data, "extra": extra},
                duration_ms=elapsed_ms,
                status="error", error_message=str(e),
            )
            raise

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
        """Find habit by name, log completion, update streak, propagate via DataHub."""
        return self._hub.log_habit_completion(habit_name, duration_min, notes)

    def add_note(self, title: str, content: str = "", tags: str = "", category: str = "general") -> str:
        r = self.send("knowledge-indexer", "add_note", {
            "title": title, "content": content, "tags": tags, "category": category
        })
        return r.get("payload", {}).get("note_id", "")

    def process_natural(self, text: str) -> dict:
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
        elif cmd == "mcp_route":
            from llm_bridge import llm_route_mcp_tool
            tools_resp = self.send("mcp-agent", "mcp_tools")
            tools = tools_resp.get("payload", {}).get("tools", [])
            if not tools:
                agent_resp = {
                    "status": "error",
                    "error": "No MCP tools available — no servers connected or enabled.",
                }
            else:
                route = llm_route_mcp_tool(text, tools)
                if route.success and route.tool_name:
                    agent_resp = self.send(
                        "mcp-agent", "mcp_call", {
                            "server_id": route.server_id,
                            "tool_name": route.tool_name,
                            "arguments": route.arguments,
                        }
                    )
                    if isinstance(agent_resp, dict):
                        agent_resp["_route"] = {
                            "tool": route.tool_name,
                            "server": route.server_id,
                            "args": route.arguments,
                        }
                else:
                    agent_resp = {
                        "status": "error",
                        "error": route.reason or "Could not determine which tool to use.",
                        "_route": {"tool": None, "reason": route.reason},
                    }
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

    def run_sync(self) -> str:
        """Manually trigger frontmatter sync scan."""
        try:
            from sync.sync_scanner import run_scan, summarize
            stats = run_scan()
            return summarize(stats)
        except Exception as e:
            return f"Sync failed: {e}"

    def health(self) -> dict:
        uptime = (datetime.now() - self._start_time).seconds
        db_stats = self._hub.health_check()
        agents = {aid: a.state for aid, a in self._agents.items()}
        return {
            "version": self.VERSION,
            "uptime_seconds": uptime,
            "agents": agents,
            "databases": db_stats,
            "checked_at": datetime.now().isoformat(),
        }

    def observer_buffer(self) -> dict:
        if not hasattr(self, '_observer') or not self._observer:
            return {"buffer_size": 0, "observation_types": {}, "session_age_seconds": 0}
        return self._observer.get_buffer_stats()

    def observer_observations(self, limit: int = 10) -> list:
        if not hasattr(self, '_observer') or not self._observer:
            return []
        return self._observer.dump_observations(limit)

    def pattern_infer(self) -> dict:
        if not hasattr(self, '_pattern_learner') or not self._pattern_learner:
            return {}
        return self._pattern_learner.infer_all_patterns()

    def pattern_workflow(self) -> str:
        if not hasattr(self, '_pattern_learner') or not self._pattern_learner:
            return "No workflow recommendation available yet"
        return self._pattern_learner.get_workflow_recommendation()

    # ── GitHub Agent convenience wrappers ──────────────────────────────────

    def git_status(self, repo_path: str = None) -> dict:
        params = {"repo_path": repo_path} if repo_path else {}
        return self.send("github-agent", "status", params)

    def git_sync_now(self, repo_path: str = None, message: str = None) -> dict:
        params = {}
        if repo_path:
            params["repo_path"] = repo_path
        if message:
            params["message"] = message
        return self.send("github-agent", "sync_now", params)

    def git_repo_list(self) -> dict:
        return self.send("github-agent", "repo_list")

    def _notify_github_agent(self, agent_id: str, action: str, data: dict) -> None:
        gh = self._agents.get("github-agent")
        if not gh or gh.state != "ready":
            return
        try:
            gh.handle({
                "id": uuid.uuid4().hex,
                "timestamp": datetime.now().isoformat(),
                "sender": "orchestrator",
                "recipients": ["github-agent"],
                "action": "request",
                "payload": {
                    "command": "event",
                    "parameters": {
                        "event_type": "agent_work_completed",
                        "data": {
                            "agent_id": agent_id,
                            "action": action,
                            "timestamp": datetime.now().isoformat(),
                            "details": data,
                        },
                    },
                },
            })
        except Exception as e:
            self.logger.debug(f"GitHub agent notification failed: {e}")

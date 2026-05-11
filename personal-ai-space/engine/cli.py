#!/usr/bin/env python3
"""
Personal AI Space — Command Line Interface
Usage: python cli.py [COMMAND] [OPTIONS]
"""
import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

try:
    import click
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.panel import Panel
    from rich import print as rprint
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from engine import Engine

console = Console() if HAS_RICH else None
_engine: Engine = None
DAEMON_BASE = "http://127.0.0.1:19876"


class DaemonProxy:
    """Thin proxy that forwards Engine method calls to the running daemon via HTTP.

    Each attribute access returns a callable that POSTs to /engine with the
    method name and arguments.  Sub-attributes (e.g. _observer) are resolved
    by the server-side Engine helpers (observer_buffer, etc.).
    """

    def __init__(self, base_url: str = DAEMON_BASE):
        self._base = base_url

    def __getattr__(self, name):
        import urllib.request
        import json

        def _call(*args, **kwargs):
            payload = json.dumps({"method": name, "args": args, "kwargs": kwargs}).encode()
            req = urllib.request.Request(
                f"{self._base}/engine",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            try:
                resp = urllib.request.urlopen(req, timeout=15)
                return json.loads(resp.read())
            except Exception as e:
                return {"error": str(e)}

        return _call


def _try_daemon() -> DaemonProxy | None:
    """Return a DaemonProxy if the daemon is running, else None."""
    pid_file = Path("/tmp/pai-engine.pid")
    if not pid_file.exists():
        return None
    try:
        import urllib.request
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # process exists?
        resp = urllib.request.urlopen(f"{DAEMON_BASE}/health", timeout=2)
        if resp.status == 200:
            return DaemonProxy()
    except Exception:
        pass
    return None


def get_engine() -> Engine | DaemonProxy:
    global _engine
    if _engine is not None:
        return _engine
    proxy = _try_daemon()
    if proxy is not None:
        return proxy
    _engine = Engine()
    _engine.start()
    return _engine


def out(text: str):
    if HAS_RICH and console:
        console.print(Markdown(text))
    else:
        print(text)


def out_json(data):
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


if HAS_RICH:
    import click

    @click.group()
    def cli():
        """🧠 Personal AI Space — your engine."""
        pass

    # ── health ────────────────────────────────────────────────────────────

    @cli.command()
    def health():
        """Show engine health and agent status."""
        e = get_engine()
        h = e.health()
        t = Table(title="Engine Health", show_header=True)
        t.add_column("Component", style="bold")
        t.add_column("Status")
        t.add_column("Detail")

        t.add_row("Engine", f"v{h['version']}", f"up {h['uptime_seconds']}s")
        for agent_id, state in h["agents"].items():
            t.add_row(f"  {agent_id}", "✅" if state != "stopped" else "❌", state)
        for db_name, result in h["databases"].items():
            ok = "✅" if result["ok"] else "❌"
            detail = f"{result.get('tables', '?')} tables" if result["ok"] else result.get("error", "")
            t.add_row(f"  {db_name}.db", ok, detail)

        console.print(t)

    # ── digest / report ───────────────────────────────────────────────────

    @cli.command()
    def digest():
        """Show today's daily digest."""
        e = get_engine()
        out(e.daily_digest())

    @cli.command()
    def review():
        """Show weekly review."""
        e = get_engine()
        out(e.weekly_review())

    # ── sync ──────────────────────────────────────────────────────────────

    @cli.command()
    def sync():
        """Manually sync .md frontmatter with database."""
        e = get_engine()
        out(e.run_sync())

    # ── tasks ─────────────────────────────────────────────────────────────

    @cli.group()
    def task():
        """Manage tasks."""
        pass

    @task.command("list")
    @click.option("--all", "show_all", is_flag=True, help="Show all open tasks")
    def task_list(show_all):
        """List today's tasks (or all open)."""
        e = get_engine()
        tasks = e.todays_tasks() if not show_all else \
                e.send("task-coordinator", "get_all_open").get("payload", [])

        if not tasks:
            console.print("[dim]No tasks found.[/dim]")
            return

        t = Table(title="Tasks", show_header=True)
        t.add_column("#", justify="right")
        t.add_column("Title")
        t.add_column("Priority")
        t.add_column("Status")
        t.add_column("Due")

        PCOLOR = {"critical": "red", "high": "orange3", "normal": "yellow", "low": "dim"}
        for i, task in enumerate(tasks, 1):
            p = task.get("priority", "normal")
            t.add_row(
                str(i),
                task.get("title", "?"),
                f"[{PCOLOR.get(p, 'white')}]{p}[/]",
                task.get("status", "?"),
                str(task.get("due_date", "—"))[:10],
            )
        console.print(t)

    @task.command("add")
    @click.argument("title")
    @click.option("--priority", "-p", default="normal",
                  type=click.Choice(["critical", "high", "normal", "low"]))
    @click.option("--due",  "-d", default=None, help="Due date YYYY-MM-DD")
    @click.option("--hours", "-h", default=None, type=float, help="Estimated hours")
    @click.option("--desc",  "-D", default="", help="Description")
    def task_add(title, priority, due, hours, desc):
        """Add a new task."""
        e = get_engine()
        task_id = e.create_task(title, priority, due, hours, desc)
        console.print(f"[green]✓ Task created:[/green] {task_id}")

    @task.command("done")
    @click.argument("task_id")
    def task_done(task_id):
        """Mark a task as completed."""
        e = get_engine()
        r = e.send("task-coordinator", "update_status", {
            "task_id": task_id, "new_status": "completed"
        })
        if r["status"] == "success":
            console.print(f"[green]✓ Task {task_id} marked completed[/green]")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @task.command("summary")
    def task_summary():
        """Show task completion summary."""
        e = get_engine()
        r = e.send("task-coordinator", "summary")
        out_json(r.get("payload", {}))

    # ── habits ────────────────────────────────────────────────────────────

    @cli.group()
    def habit():
        """Track habits."""
        pass

    @habit.command("log")
    @click.argument("name")
    @click.option("--duration", "-d", default=0, type=int, help="Duration in minutes")
    @click.option("--notes", "-n", default="", help="Optional notes")
    def habit_log(name, duration, notes):
        """Log a habit completion."""
        e = get_engine()
        ok = e.log_habit(name, duration, notes)
        if ok:
            console.print(f"[green]✓ Habit logged:[/green] {name}")
        else:
            console.print(f"[red]✗ Habit not found:[/red] {name}")

    @habit.command("insights")
    @click.option("--days", "-d", default=7, type=int)
    def habit_insights(days):
        """Show habit insights and patterns."""
        e = get_engine()
        r = e.send("insight-generator", "analyse_habits", extra={"days": days})
        data = r.get("payload", {})
        for h in data.get("insights", []):
            icon = {"excellent": "✅", "good": "✅", "fair": "⚠️", "poor": "❌"}.get(h["rating"], "⚪")
            console.print(
                f"{icon} [bold]{h['habit']}[/bold] — "
                f"{h['completion_pct']}% | streak: {h.get('streak', 0)} days"
            )
            if h.get("recommendation"):
                console.print(f"   [dim]{h['recommendation']}[/dim]")

    # ── reminders ─────────────────────────────────────────────────────────

    @cli.command()
    def reminders():
        """Show reminders: overdue, today, and upcoming."""
        e = get_engine()
        snap = e.reminders_snapshot()

        if snap.get("overdue"):
            t = Table(title="🚨 Overdue", show_header=False)
            t.add_column("Title")
            t.add_column("Due")
            for task in snap["overdue"]:
                t.add_row(task["title"], str(task.get("due_date", "?"))[:10])
            console.print(t)

        if snap.get("due_today"):
            t = Table(title="📅 Due Today", show_header=False)
            t.add_column("Title")
            t.add_column("Priority")
            for task in snap["due_today"]:
                t.add_row(task["title"], task.get("priority", "?"))
            console.print(t)

        if not snap.get("overdue") and not snap.get("due_today"):
            console.print("[green]✓ All clear — nothing overdue or due today[/green]")

    # ── knowledge ─────────────────────────────────────────────────────────

    @cli.group()
    def note():
        """Manage notes and knowledge."""
        pass

    @note.command("add")
    @click.argument("title")
    @click.option("--content", "-c", default="", help="Note body")
    @click.option("--tags",    "-t", default="", help="Comma-separated tags")
    @click.option("--category","-C", default="general")
    def note_add(title, content, tags, category):
        """Add a note to the knowledge base."""
        e = get_engine()
        note_id = e.add_note(title, content, tags, category)
        console.print(f"[green]✓ Note created:[/green] {note_id}")

    @note.command("search")
    @click.argument("query")
    def note_search(query):
        """Search the knowledge base."""
        e = get_engine()
        r = e.send("knowledge-indexer", "search", extra={"query": query})
        results = r.get("payload", [])
        if not results:
            console.print("[dim]No results found.[/dim]")
            return
        for n in results:
            console.print(f"[bold]{n['title']}[/bold] [{n.get('category','')}] — {n.get('tags','')}")

    @note.command("stats")
    def note_stats():
        """Show knowledge base statistics."""
        e = get_engine()
        r = e.send("knowledge-indexer", "stats")
        out_json(r.get("payload", {}))

    # ── context ───────────────────────────────────────────────────────────

    @cli.command()
    def context():
        """Show your current context (profile + habits + needs)."""
        e = get_engine()
        ctx = e.context()
        profile = ctx.get("profile") or {}
        if profile:
            console.print(Panel(
                f"Name: [bold]{profile.get('name','?')}[/bold]\n"
                f"Timezone: {profile.get('timezone','?')}\n"
                f"Style: {profile.get('work_style','?')}",
                title="👤 Your Profile"
            ))
        habits = ctx.get("habits", [])
        if habits:
            console.print(f"[bold]Active habits:[/bold] {len(habits)}")
            for h in habits[:5]:
                console.print(f"  - {h.get('habit_name','?')} (streak: {h.get('current_streak',0)})")
        needs = ctx.get("needs", [])
        if needs:
            console.print(f"[bold]Active needs:[/bold] {len(needs)}")
            for n in needs[:3]:
                console.print(f"  - [{n.get('priority','?')}] {n.get('name','?')}")

        # Show MCP memory facts if available
        mcp_facts = ctx.get("mcp_facts", {})
        if mcp_facts:
            console.print(f"\n[bold]🧠 MCP memory facts:[/bold] {len(mcp_facts)}")
            for k, v in list(mcp_facts.items())[:8]:
                console.print(f"  {k} = {v}")

    # ── serve / daemon ─────────────────────────────────────────────────────

    @cli.command()
    @click.option("--host", default="127.0.0.1", help="Bind address")
    @click.option("--port", default=19876, type=int, help="Port number")
    def serve(host, port):
        """Run engine as a persistent HTTP server (foreground)."""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json

        engine = get_engine()
        h = engine.health()
        console.print(f"[green]✓ Engine v{h['version']} started[/green]")
        console.print(f"[dim]  {len(h['agents'])} agents, {len(h['databases'])} databases[/dim]")
        console.print(f"[dim]  Listening on http://{host}:{port}[/dim]")

        class EngineHandler(BaseHTTPRequestHandler):
            def _json(self, code, data):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data, default=str).encode())

            def do_GET(self):
                if self.path == "/health":
                    self._json(200, engine.health())
                elif self.path == "/stats":
                    self._json(200, {
                        "uptime_seconds": engine.health()["uptime_seconds"],
                        "agent_count": len(engine._agents),
                        "agent_states": {a: s.state for a, s in engine._agents.items()},
                    })
                else:
                    self._json(404, {"error": "not found"})

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode() if length else "{}")

                if self.path == "/execute":
                    result = engine.send(
                        body.get("agent", ""),
                        body.get("command", ""),
                        body.get("data", {}),
                    )
                    self._json(200, result)
                elif self.path == "/engine":
                    method = body.get("method", "")
                    args   = body.get("args", [])
                    kwargs = body.get("kwargs", {})
                    fn     = getattr(engine, method, None)
                    if fn is None:
                        self._json(404, {"error": f"Unknown method: {method}"})
                    else:
                        try:
                            result = fn(*args, **kwargs)
                            self._json(200, result)
                        except Exception as e:
                            self._json(500, {"error": str(e)})
                else:
                    self._json(404, {"error": "not found"})

            def log_message(self, fmt, *args):
                engine.logger.debug(f"HTTP: {fmt % args}")

        try:
            HTTPServer((host, port), EngineHandler).serve_forever()
        except KeyboardInterrupt:
            engine.stop()
            console.print("\n[yellow]Engine stopped[/yellow]")

    @cli.group()
    def daemon():
        """Manage the background engine daemon."""

    @daemon.command("start")
    @click.option("--host", default="127.0.0.1")
    @click.option("--port", default=19876, type=int)
    def daemon_start(host, port):
        """Start the engine daemon in background."""
        import subprocess
        pid_file = Path("/tmp/pai-engine.pid")

        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, 0)
                console.print("[red]Engine is already running[/red]")
                return
            except (OSError, ValueError):
                pid_file.unlink(missing_ok=True)

        log_file = ROOT / "logs" / "daemon.log"
        log_file.parent.mkdir(exist_ok=True)

        proc = subprocess.Popen(
            [sys.executable, str(ROOT / "cli.py"), "serve", "--host", host, "--port", str(port)],
            stdout=log_file.open("a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        pid_file.write_text(str(proc.pid))
        console.print(f"[green]✓ Engine daemon started (PID {proc.pid})[/green]")
        console.print(f"[dim]  Log: {log_file}[/dim]")

    @daemon.command("stop")
    def daemon_stop():
        """Stop the engine daemon."""
        pid_file = Path("/tmp/pai-engine.pid")
        if not pid_file.exists():
            console.print("[yellow]No engine daemon running[/yellow]")
            return
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 15)
            pid_file.unlink(missing_ok=True)
            console.print(f"[green]✓ Engine daemon stopped (PID {pid})[/green]")
        except ProcessLookupError:
            console.print("[yellow]Process not found — removing stale PID file[/yellow]")
            pid_file.unlink(missing_ok=True)
        except OSError as e:
            console.print(f"[red]Failed to stop: {e}[/red]")

    @daemon.command("status")
    def daemon_status():
        """Show whether the engine daemon is running."""
        pid_file = Path("/tmp/pai-engine.pid")
        if not pid_file.exists():
            console.print("[yellow]Engine daemon is not running[/yellow]")
            return
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            import urllib.request
            try:
                resp = urllib.request.urlopen("http://127.0.0.1:19876/health", timeout=2)
                data = json.loads(resp.read())
                t = Table(title=f"Engine Daemon (PID {pid})", show_header=True)
                t.add_column("Component")
                t.add_column("Status")
                t.add_column("Detail")
                t.add_row("Engine", "✅", f"v{data['version']}  up {data['uptime_seconds']}s")
                for agent_id, state in data["agents"].items():
                    t.add_row(f"  {agent_id}", "✅" if state != "stopped" else "❌", state)
                for db_name, result in data["databases"].items():
                    ok = "✅" if result["ok"] else "❌"
                    detail = f"{result.get('tables', '?')} tables" if result["ok"] else result.get("error", "")
                    t.add_row(f"  {db_name}.db", ok, detail)
                console.print(t)
            except Exception:
                console.print(f"[yellow]Daemon process exists (PID {pid}) but not responding on HTTP[/yellow]")
        except (OSError, ValueError):
            console.print("[yellow]Stale PID file — daemon is not running[/yellow]")
            pid_file.unlink(missing_ok=True)

    @cli.group()
    def memory():
        """MCP agent memory — facts & lessons."""

    @memory.command("stats")
    def memory_stats():
        """Show MCP memory statistics."""
        e = get_engine()
        r = e.send("context-manager", "mcp_stats")
        data = r.get("payload", {})
        if data.get("error"):
            console.print(f"[red]{data['error']}[/red]")
        else:
            console.print(Panel(
                f"Semantic facts: [bold]{data.get('semantic', '?')}[/bold]\n"
                f"Lessons: [bold]{data.get('lessons', '?')}[/bold]\n"
                f"Events: [bold]{data.get('events', '?')}[/bold]",
                title="🧠 MCP Memory Stats"
            ))

    @memory.command("facts")
    @click.option("--prefix", default=None, help="Filter by key prefix")
    def memory_facts(prefix):
        """List semantic facts stored in MCP memory."""
        e = get_engine()
        r = e.send("context-manager", "list_facts", extra={"prefix": prefix})
        facts = r.get("payload", {}).get("facts", [])
        if not facts:
            console.print("[yellow]No facts found[/yellow]")
            return
        t = Table("Key", "Value", "Confidence", "Category", title="🧠 Memory Facts")
        for f in facts:
            if isinstance(f, dict):
                t.add_row(
                    f.get("key", ""),
                    str(f.get("value", ""))[:60],
                    str(f.get("confidence", "")),
                    f.get("category", "") or "",
                )
        console.print(t)

    @memory.command("add-fact")
    @click.argument("key")
    @click.argument("value")
    @click.option("--confidence", default=0.8, type=float)
    @click.option("--category", default=None)
    def memory_add_fact(key, value, confidence, category):
        """Store a semantic fact in MCP memory."""
        e = get_engine()
        r = e.send("context-manager", "add_fact", extra={
            "key": key, "value": value, "confidence": confidence, "category": category
        })
        if r.get("payload", {}).get("stored"):
            console.print(f"[green]✓[/green] Stored: {key} = {value}")
        else:
            console.print(f"[red]✗ Failed to store fact[/red]")

    @memory.command("add-lesson")
    @click.argument("text")
    @click.option("--negative", is_flag=True, help="Mark as 'avoid' lesson")
    @click.option("--category", default=None)
    def memory_add_lesson(text, negative, category):
        """Store a lesson learned in MCP memory."""
        e = get_engine()
        r = e.send("context-manager", "add_lesson", extra={
            "text": text, "negative": negative, "category": category
        })
        label = "⛔ Avoid" if negative else "✅ Do"
        if r.get("payload", {}).get("stored"):
            console.print(f"[green]✓[/green] Lesson stored [{label}]: {text}")
        else:
            console.print(f"[red]✗ Failed to store lesson[/red]")

    @memory.command("lessons")
    @click.option("--category", default=None)
    @click.option("--negative", is_flag=True)
    def memory_lessons(category, negative):
        """List lessons stored in MCP memory."""
        e = get_engine()
        r = e.send("context-manager", "list_lessons", extra={
            "category": category, "negative_only": negative
        })
        lessons = r.get("payload", {}).get("lessons", [])
        if not lessons:
            console.print("[yellow]No lessons found[/yellow]")
            return
        t = Table("Type", "Text", "Category", title="📚 Lessons Learned")
        for lesson in lessons:
            if isinstance(lesson, dict):
                kind = "⛔ Avoid" if lesson.get("negative") else "✅ Do"
                t.add_row(kind, str(lesson.get("text", ""))[:80], lesson.get("category", "") or "")
        console.print(t)

    @memory.command("sync-profile")
    def memory_sync_profile():
        """Re-sync user profile into MCP memory."""
        e = get_engine()
        r = e.send("context-manager", "sync_profile")
        msg = r.get("payload", {}).get("message", "Done")
        console.print(f"[green]{msg}[/green]")

    @cli.group()
    def learning():
        """Autonomous learning — observations, patterns, inferences."""

    @learning.command("buffer")
    def learning_buffer():
        """Show current observation buffer."""
        e = get_engine()
        if isinstance(e, DaemonProxy):
            stats = e.observer_buffer()
        else:
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
        if isinstance(e, DaemonProxy):
            obs = e.observer_observations(limit)
        else:
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
        if not isinstance(e, DaemonProxy) and (not hasattr(e, '_pattern_learner') or not e._pattern_learner):
            console.print("[red]Pattern learner not available[/red]")
            return
        console.print("[bold]Running pattern inference...[/bold]")
        patterns = e.pattern_infer() if isinstance(e, DaemonProxy) else e._pattern_learner.infer_all_patterns()
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
        if not isinstance(e, DaemonProxy) and (not hasattr(e, '_pattern_learner') or not e._pattern_learner):
            console.print("[red]Pattern learner not available[/red]")
            return
        rec = e.pattern_workflow() if isinstance(e, DaemonProxy) else e._pattern_learner.get_workflow_recommendation()
        console.print(Panel(rec, title="💡 Workflow Recommendation"))

    # ── MCP servers ─────────────────────────────────────────────────────────

    @cli.group()
    def mcp():
        """External MCP server tools (mail, WhatsApp, etc.)."""
        pass

    @mcp.command("status")
    def mcp_status():
        """Show MCP server connections and tool counts."""
        e = get_engine()
        r = e.send("mcp-agent", "mcp_status")
        data = r.get("payload", {})
        servers = data.get("servers", [])
        if not servers:
            console.print("[dim]No MCP servers configured.[/dim]")
            return
        t = Table(title="MCP Servers", show_header=True)
        t.add_column("Server")
        t.add_column("Status")
        t.add_column("Transport")
        t.add_column("Tools")
        for s in servers:
            status = "✅ Connected" if s["connected"] else "⚪ Disabled/Off"
            t.add_row(s["name"], status, s["transport"], str(s["tools_count"]))
        console.print(t)
        tot = data.get("tools_total", 0)
        console.print(f"\n[dim]Total tools available: {tot}[/dim]")

    @mcp.command("tools")
    def mcp_tools():
        """List all available tools from connected MCP servers."""
        e = get_engine()
        r = e.send("mcp-agent", "mcp_tools")
        data = r.get("payload", {})
        tools = data.get("tools", [])
        if not tools:
            console.print("[yellow]No tools discovered. Run: mcp discover[/yellow]")
            return
        t = Table(title="Available MCP Tools", show_header=True)
        t.add_column("Server")
        t.add_column("Tool")
        t.add_column("Description")
        for tool in tools:
            desc = tool.get("description", "")[:60]
            t.add_row(tool["server_id"], tool["name"], desc)
        console.print(t)

    @mcp.command("call")
    @click.argument("server_id")
    @click.argument("tool_name")
    @click.option("--args", "-a", default="{}", help="JSON arguments")
    def mcp_call(server_id, tool_name, args):
        """Call a tool on an MCP server (experimental)."""
        e = get_engine()
        try:
            arguments = json.loads(args)
        except json.JSONDecodeError:
            console.print("[red]Invalid JSON in --args[/red]")
            return
        r = e.send("mcp-agent", "mcp_call", {
            "server_id": server_id, "tool_name": tool_name, "arguments": arguments,
        })
        payload = r.get("payload", {}) if r["status"] == "success" else r
        if payload.get("status") == "error":
            console.print(f"[red]✗ {payload.get('error', 'Unknown error')}[/red]")
            return
        for text in payload.get("content", []):
            console.print(text)

    @mcp.command("discover")
    def mcp_discover():
        """Re-discover tools from all enabled MCP servers."""
        e = get_engine()
        r = e.send("mcp-agent", "mcp_discover")
        data = r.get("payload", {})
        console.print(f"[green]✓[/green] {data.get('servers_connected', 0)} servers connected")
        console.print(f"[green]✓[/green] {data.get('tools_total', 0)} tools discovered")
        for sid, tools in data.get("tools_by_server", {}).items():
            console.print(f"  [bold]{sid}[/bold]: {', '.join(tools)}")

    # ── natural language ────────────────────────────────────────────────────

    @cli.command()
    @click.argument("text", nargs=-1, required=True)
    @click.option("--enhance", is_flag=True, help="Add LLM-generated narrative (requires Ollama + model)")
    def nl(text, enhance):
        """Speak naturally — 'what should I do today?'"""
        e = get_engine()
        text = " ".join(text)
        result = e.process_natural(text)

        if result["status"] == "unknown":
            console.print(f"[yellow]🤷 {result['message']}[/yellow]")
            if result.get("suggestions"):
                console.print("\n[bold]Did you mean:[/bold]")
                for s in result["suggestions"]:
                    console.print(f"  • {s}")
            return

        label = result.get("intent_label", result["intent"])
        conf = result.get("confidence", 0)
        console.print(f"[dim]→ {label} ({conf:.0%} confidence)[/dim]\n")

        agent_resp = result.get("agent_response", {})

        if result["intent"] == "report-generator.daily_digest":
            report = agent_resp.get("payload", {}).get("report", "")
            if enhance:
                from llm_bridge import enrich_digest_opener
                opener = enrich_digest_opener(
                    due_today=report.count("Due today"),
                    overdue=report.count("Overdue"),
                    at_risk_habits=report.count("at risk"),
                    habit_count=len([l for l in report.split("\n") if l.startswith("- ✅") or l.startswith("- ⚠") or l.startswith("- ❌") or l.startswith("- ✅")]),
                )
                if opener:
                    console.print(f"[bold]📝 {opener}[/bold]\n")
            out(report)
        elif result["intent"] == "report-generator.weekly_review":
            out(agent_resp.get("payload", {}).get("report", ""))
        elif result["intent"] == "task-coordinator.get_today":
            tasks = agent_resp.get("payload", [])
            if not tasks:
                console.print("[green]✓ Nothing due today — you're clear![/green]")
                if enhance:
                    from llm_bridge import TextGenerator
                    gen = TextGenerator()
                    r = gen.generate(
                        "Given that Paulo has no tasks due today, write a short encouraging "
                        "sentence suggesting he could use the free time for deep work or planning.",
                        system="Warm, concise, encouraging. One sentence.",
                        temperature=0.7, max_tokens=80,
                    )
                    if r.success:
                        console.print(f"   [dim]{r.text}[/dim]")
            else:
                t = Table(title="Today's Tasks", show_header=True)
                t.add_column("#", justify="right")
                t.add_column("Title")
                t.add_column("Priority")
                t.add_column("Due")
                PCOLOR = {"critical": "red", "high": "orange3", "normal": "yellow", "low": "dim"}
                for i, task in enumerate(tasks, 1):
                    p = task.get("priority", "normal")
                    t.add_row(str(i), task["title"], f"[{PCOLOR.get(p, 'white')}]{p}[/]",
                              str(task.get("due_date", "—"))[:10])
                console.print(t)
        elif result["intent"] == "task-coordinator.summary":
            out_json(agent_resp.get("payload", {}))
        elif result["intent"] == "insight-generator.analyse_habits":
            data = agent_resp.get("payload", {})
            if enhance:
                from llm_bridge import enrich_habit_insights
                narration = enrich_habit_insights(data)
                if narration:
                    console.print(f"[bold]📝 {narration}[/bold]\n")
            for h in data.get("insights", []):
                icon = {"excellent": "✅", "good": "✅", "fair": "⚠️", "poor": "❌"}.get(h["rating"], "⚪")
                console.print(f"{icon} [bold]{h['habit']}[/bold] — {h['completion_pct']}% | streak: {h.get('streak', 0)}d")
                if h.get("recommendation"):
                    console.print(f"   [dim]{h['recommendation']}[/dim]")
        elif result["intent"] == "task-coordinator.create_task":
            task_id = agent_resp.get("payload", {}).get("task_id", "")
            title = result.get("params", {}).get("title", "")
            console.print(f"[green]✓ Added:[/green] {title} [dim]({task_id})[/dim]")
        elif result["intent"] == "knowledge-indexer.search":
            results = agent_resp.get("payload", [])
            if not results:
                console.print("[dim]No results found.[/dim]")
            else:
                for n in results:
                    console.print(f"[bold]{n['title']}[/bold] [{n.get('category','')}] — {n.get('tags','')}")
        elif result["intent"] == "context-manager.get_context":
            ctx = agent_resp.get("payload", {})
            profile = ctx.get("profile") or {}
            if profile:
                console.print(f"👤 [bold]{profile.get('name','?')}[/bold] — {profile.get('work_style','?')} — {profile.get('timezone','?')}")
            habits = ctx.get("habits", [])
            if habits:
                console.print(f"💪 {len(habits)} active habits")
            needs = ctx.get("needs", [])
            if needs:
                console.print(f"📋 {len(needs)} active needs")
        else:
            out_json(agent_resp)

    # ── llm health ──────────────────────────────────────────────────────────

    @cli.group()
    def llm():
        """LLM integration status and model management."""
        pass

    @llm.command("status")
    def llm_status():
        """Check if Ollama is running and what models are available."""
        from llm_bridge import check_ollama
        status = check_ollama()
        if status["available"]:
            console.print(f"[green]✓ Ollama is running[/green]")
            if status["models"]:
                t = Table("Available Models", title="📦 Ollama Models")
                for m in status["models"]:
                    t.add_row(m)
                console.print(t)
            else:
                console.print("[yellow]No models pulled yet. Run: ollama pull <model>[/yellow]")
        else:
            console.print(f"[red]✗ Ollama not reachable[/red]")
            console.print(f"[dim]{status['error']}[/dim]")
            console.print("\nInstall: [bold]brew install ollama[/bold] then [bold]ollama serve[/bold]")

    @llm.command("classify")
    @click.argument("text", nargs=-1, required=True)
    def llm_classify(text):
        """Test intent classification without executing."""
        from llm_bridge import IntentClassifier
        text = " ".join(text)
        classifier = IntentClassifier()
        result = classifier.classify(text)
        if result.intent:
            console.print(f"[bold]Intent:[/bold] {result.intent.agent}.{result.intent.command}")
            console.print(f"[bold]Label:[/bold] {result.intent.description}")
            console.print(f"[bold]Confidence:[/bold] {result.confidence:.1%}")
            if result.extracted_params:
                console.print(f"[bold]Params:[/bold] {result.extracted_params}")
        else:
            console.print(f"[yellow]No intent matched[/yellow]")
        if result.alternatives:
            console.print("\n[dim]Alternatives:[/dim]")
            for desc, conf in result.alternatives[:3]:
                console.print(f"  {desc} ({conf:.0%})")

else:
    # Plain fallback if rich/click not installed
    def cli():
        e = Engine()
        e.start()
        print("\n=== Daily Digest ===")
        print(e.daily_digest())
        print("\n=== Reminder Snapshot ===")
        import json
        print(json.dumps(e.reminders_snapshot(), indent=2, default=str))
        e.stop()


if __name__ == "__main__":
    if HAS_RICH:
        cli()
    else:
        cli()

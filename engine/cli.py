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
        return None  # daemon not available, fall through to local engine
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

    @habit.command("complete")
    @click.argument("habit_id")
    @click.option("--notes", "-n", default=None, help="Optional notes")
    def habit_complete(habit_id, notes):
        """Mark a habit as completed for today (atomic: updates streak + log)."""
        from sync.sync_habits import mark_habit_complete
        try:
            result = mark_habit_complete(habit_id, notes)
            console.print(f"[green]✅ {result['habit_id']}[/green] — streak: {result['new_streak']}")
        except ValueError as e:
            console.print(f"[red]✗ {e}[/red]")

    @habit.command("today")
    def habit_today():
        """Show today's habit completion status."""
        from sync.sync_habits import get_habits_today_status
        habits = get_habits_today_status()
        for h in habits:
            icon = "[green]✅[/green]" if h["status"] == "completed" else "⬜"
            console.print(f"  {icon} {h['habit_name']}")

    @habit.command("at-risk")
    def habit_at_risk():
        """Show habits needing attention (streak at risk)."""
        from sync.sync_habits import get_habits_at_risk
        habits = get_habits_at_risk()
        if not habits:
            console.print("[green]Todos os hábitos em dia![/green]")
            return
        for h in habits:
            last = h['last_completed'] or 'nunca'
            console.print(f"  [yellow]⚠️[/yellow] {h['habit_name']} — streak: {h['current_streak']}, último: {last}")

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

    @note.command("reindex")
    def note_reindex():
        """Rebuild the knowledge term-frequency index from all notes."""
        e = get_engine()
        r = e.send("knowledge-indexer", "build_index")
        data = r.get("payload", {})
        console.print(
            f"[green]✓ Index rebuilt:[/green] "
            f"{data.get('indexed_terms', 0)} terms "
            f"from {data.get('processed_notes', 0)} notes"
        )

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
        engine.start_scheduler()
        h = engine.health()
        s = engine.scheduler_status()
        console.print(f"[green]✓ Engine v{h['version']} started[/green]")
        console.print(f"[dim]  {len(h['agents'])} agents, {len(h['databases'])} databases[/dim]")
        console.print(f"[dim]  {s['jobs_loaded']} scheduler jobs loaded[/dim]")
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
                    h = engine.health()
                    self._json(200, {
                        "uptime_seconds": h["uptime_seconds"],
                        "agent_count": len(engine._agents),
                        "agent_states": {a: s.state for a, s in engine._agents.items()},
                        "scheduler": engine.scheduler_status(),
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

    # ── behaviors ─────────────────────────────────────────────────────────────

    @cli.group()
    def behaviors():
        """Analyze behavior patterns — emotions, activities, trends."""

    @behaviors.command("report")
    @click.option("--raw", is_flag=True, help="Output raw JSON instead of formatted report")
    def behaviors_report(raw):
        """Show behavior analytics: trends, correlations, anomalies."""
        from analytics.behavior_analytics import BehaviorAnalytics
        ba = BehaviorAnalytics()
        if raw:
            out_json(ba.full_report())
        else:
            console.print(ba)

    # ── scheduler ────────────────────────────────────────────────────────────

    @cli.group()
    def scheduler():
        """Manage the background job scheduler."""

    @scheduler.command("status")
    def scheduler_status():
        """Show scheduler status and loaded jobs."""
        e = get_engine()
        if isinstance(e, DaemonProxy):
            s = e.scheduler_status()
        else:
            s = e.scheduler_status() if hasattr(e, '_scheduler') else {"running": False, "jobs": []}
        if not s.get("running"):
            console.print("[yellow]Scheduler not running[/yellow]")
        else:
            console.print(f"[green]✓ Scheduler running[/green]")
            console.print(f"[dim]  {s['jobs_loaded']} jobs loaded[/dim]")
            for j in s.get("jobs", []):
                last = j.get("last_run", "")
                last_str = f" (last: {last})" if last else ""
                console.print(f"  • {j['name']} [{j['type']}]{last_str}")
            console.print("\n[yellow]Note:[/yellow] Scheduler runs alongside 'cli.py serve' (HTTP daemon)")
            console.print("  Use: [bold]python cli.py daemon start[/bold] to start the daemon")

    @scheduler.command("observations")
    @click.option("--limit", default=20, help="Number of recent observations")
    def scheduler_observations(limit):
        """Show recent behavioral observations stored in self.db."""
        e = get_engine()
        try:
            hub = e._hub if hasattr(e, '_hub') else None
            if not hub and isinstance(e, DaemonProxy):
                console.print("[yellow]Observations not available via daemon proxy (run 'cli.py serve' directly)[/yellow]")
                return
            obs = hub.get_observations(limit=limit)
            if not obs:
                console.print("[yellow]No observations yet. Start the daemon and use the system.[/yellow]")
                return
            t = Table("Type", "Time", "Source", "Data Preview", title="📋 Recent Observations")
            for o in obs:
                data_str = str(o.get("data", ""))[:60]
                t.add_row(o.get("obs_type", "?"), str(o.get("observed_at", "?"))[-19:],
                          o.get("source", "?"), data_str)
            console.print(t)
        except Exception as ex:
            console.print(f"[red]Error: {ex}[/red]")

    @scheduler.command("stats")
    def scheduler_obs_stats():
        """Show observation statistics."""
        e = get_engine()
        try:
            hub = e._hub if hasattr(e, '_hub') else None
            if not hub:
                console.print("[yellow]Not available[/yellow]")
                return
            stats = hub.get_observation_stats()
            console.print(Panel(
                f"Total observations: [bold]{stats['total']}[/bold]\n"
                f"Last 24h: [bold]{stats['last_24h']}[/bold]\n"
                f"By type: {stats['by_type']}",
                title="📊 Observation Stats"
            ))
        except Exception as ex:
            console.print(f"[red]Error: {ex}[/red]")

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

    # ── jobs ─────────────────────────────────────────────────────────────────

    @cli.group()
    def jobs():
        """Track job applications — companies, applications, interviews."""

    @jobs.command("sync")
    @click.option("--dir", type=click.Path(exists=True), default=None,
                  help=f"Path to jobs .md files (default: obsidian/jobs/)")
    @click.option("--dry-run", is_flag=True, help="Preview only, no DB writes")
    def jobs_sync(dir, dry_run):
        """Sync Obsidian .md files → jobs.db."""
        from sync.sync_jobs import sync_jobs, format_summary, dry_run as dr_preview

        if dry_run:
            info = dr_preview(Path(dir) if dir else None)
            console.print(f"\n[bold]JOBS SYNC — DRY RUN (no changes written)[/bold]")
            console.print(f"  Directory: {info.get('directory', '?')}")
            if info["files"] == 0:
                console.print("  [dim]No .md files found — nothing to sync.[/dim]")
                return
            console.print(f"  Files found:           {info['files']}")
            console.print(f"  Would create/update →")
            console.print(f"    Companies:           {info['companies']}")
            console.print(f"    Applications:        {info['applications']}")
            console.print(f"    Interviews:          {info['interviews']}")
            console.print(f"    Contacts:            {info['contacts']}")
            return

        with console.status("[bold green]Syncing jobs...[/bold green]"):
            results = sync_jobs(Path(dir) if dir else None)
        format_summary(results)

    @jobs.command("list")
    @click.option("--status", "-s", default=None,
                  help="Filter by status (saved, applied, interview, offer, ...)")
    def jobs_list(status):
        """List all job applications from jobs.db."""
        import db_manager as _db

        if status:
            status = status.strip().lower()
            rows = _db.query("jobs",
                "SELECT a.id, a.job_title, c.name as company, a.status, a.applied_date, a.location "
                "FROM applications a JOIN companies c ON a.company_id = c.id "
                "WHERE a.status = ? ORDER BY a.created_at DESC", (status,))
        else:
            rows = _db.query("jobs",
                "SELECT a.id, a.job_title, c.name as company, a.status, a.applied_date, a.location "
                "FROM applications a JOIN companies c ON a.company_id = c.id "
                "ORDER BY a.created_at DESC")

        if not rows:
            console.print("[dim]No job applications found.[/dim]")
            return

        t = Table(title=f"Job Applications{' (' + status + ')' if status else ''}",
                  show_header=True)
        t.add_column("Title")
        t.add_column("Company")
        t.add_column("Status")
        t.add_column("Applied")
        t.add_column("Location")

        for r in rows:
            t.add_row(
                r.get("job_title", "?")[:40],
                r.get("company", "?")[:25],
                r.get("status", "?"),
                str(r.get("applied_date", ""))[:10],
                r.get("location", "")[:20],
            )
        console.print(t)

    @jobs.command("statuses")
    def jobs_statuses():
        """Show application pipeline counts."""
        import db_manager as _db

        rows = _db.query("jobs",
            "SELECT status, count(*) as n FROM applications GROUP BY status ORDER BY n DESC")

        if not rows:
            console.print("[dim]No applications yet.[/dim]")
            return

        t = Table(title="Application Pipeline", show_header=True)
        t.add_column("Status")
        t.add_column("Count")

        status_colors = {
            "saved": "dim", "applied": "blue", "screening": "cyan",
            "interview": "yellow", "offer": "green", "rejected": "red",
            "withdrawn": "dim", "accepted": "green",
        }
        for r in rows:
            color = status_colors.get(r["status"], "white")
            t.add_row(f"[{color}]{r['status']}[/]", str(r["n"]))
        console.print(t)

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

    # ── github ────────────────────────────────────────────────────────────────

    @cli.group()
    def github():
        """GitHub Specialist Agent — git operations, repo management, sync."""
        pass

    @github.command("status")
    @click.option("--repo-path", "-r", help="Path to git repository")
    def github_status(repo_path):
        """Get git status for a repo."""
        e = get_engine()
        r = e.send("github-agent", "status", {"repo_path": repo_path})
        if r["status"] == "success":
            payload = r.get("payload", {})
            if not repo_path:
                console.print(f"[green]GitHub Agent ready[/green] — {payload.get('repos_tracked', 0)} repos tracked")
                return
            t = Table(title=f"Git Status: {repo_path}", show_header=True)
            t.add_column("Field")
            t.add_column("Value")
            t.add_row("Branch", payload.get("branch", "?"))
            t.add_row("Staged", str(len(payload.get("staged", []))))
            t.add_row("Modified", str(len(payload.get("modified", []))))
            t.add_row("Untracked", str(len(payload.get("untracked", []))))
            t.add_row("Ahead/Behind", f"{payload.get('ahead', 0)}/{payload.get('behind', 0)}")
            console.print(t)
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("clone")
    @click.argument("url")
    @click.option("--path", "-p", help="Local clone path (default: auto)")
    def github_clone(url, path):
        """Clone a repository."""
        e = get_engine()
        r = e.send("github-agent", "clone", {"url": url, "path": path or url.split("/")[-1].replace(".git", "")})
        if r["status"] == "success":
            console.print(f"[green]✓ Cloned:[/green] {r['payload'].get('path')}")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("init")
    @click.argument("path")
    def github_init(path):
        """Initialize a git repository."""
        e = get_engine()
        r = e.send("github-agent", "init", {"path": path})
        if r["status"] == "success":
            console.print(f"[green]✓ Initialized:[/green] {path}")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("branch-list")
    @click.option("--repo-path", "-r", required=True, help="Path to git repository")
    def github_branch_list(repo_path):
        """List branches in a repository."""
        e = get_engine()
        r = e.send("github-agent", "branch_list", {"repo_path": repo_path})
        if r["status"] == "success":
            branches = r["payload"].get("branches", [])
            t = Table(title=f"Branches in {repo_path}", show_header=True)
            t.add_column("Branch")
            t.add_column("Current")
            for b in branches:
                current = "✓" if b.get("current") else ""
                t.add_row(b.get("name", ""), current)
            console.print(t)
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("branch-create")
    @click.option("--repo-path", "-r", required=True, help="Path to git repository")
    @click.option("--branch-name", "-b", required=True, help="Branch name")
    @click.option("--base", help="Base branch (default: HEAD)")
    def github_branch_create(repo_path, branch_name, base):
        """Create a new branch."""
        e = get_engine()
        r = e.send("github-agent", "branch_create", {"repo_path": repo_path, "branch_name": branch_name, "base": base})
        if r["status"] == "success":
            console.print(f"[green]✓ Branch created:[/green] {branch_name}")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("branch-delete")
    @click.option("--repo-path", "-r", required=True, help="Path to git repository")
    @click.option("--branch-name", "-b", required=True, help="Branch name")
    @click.option("--force", "-f", is_flag=True, help="Force delete")
    def github_branch_delete(repo_path, branch_name, force):
        """Delete a branch."""
        e = get_engine()
        r = e.send("github-agent", "branch_delete", {"repo_path": repo_path, "branch_name": branch_name, "force": force})
        if r["status"] == "success":
            console.print(f"[green]✓ Branch deleted:[/green] {branch_name}")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("commit")
    @click.option("--repo-path", "-r", required=True, help="Path to git repository")
    @click.option("--message", "-m", required=True, help="Commit message")
    def github_commit(repo_path, message):
        """Commit changes."""
        e = get_engine()
        r = e.send("github-agent", "commit", {"repo_path": repo_path, "message": message})
        if r["status"] == "success":
            payload = r["payload"]
            console.print(f"[green]✓ Committed:[/green] {payload.get('hash', '')[:7]} — {message}")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("log")
    @click.option("--repo-path", "-r", required=True, help="Path to git repository")
    @click.option("-n", default=10, type=int, help="Number of commits")
    def github_log(repo_path, n):
        """Show commit log."""
        e = get_engine()
        r = e.send("github-agent", "log", {"repo_path": repo_path, "n": n})
        if r["status"] == "success":
            commits = r["payload"].get("commits", [])
            if not commits:
                console.print("[dim]No commits yet[/dim]")
                return
            t = Table(title=f"Recent Commits in {repo_path}", show_header=True)
            t.add_column("Hash")
            t.add_column("Author")
            t.add_column("Message")
            for c in commits:
                t.add_row(c.get("hash", "")[:7], c.get("author", ""), c.get("message", "")[:50])
            console.print(t)
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("pull")
    @click.option("--repo-path", "-r", required=True, help="Path to git repository")
    def github_pull(repo_path):
        """Pull from remote."""
        e = get_engine()
        r = e.send("github-agent", "pull", {"repo_path": repo_path})
        if r["status"] == "success":
            console.print(f"[green]✓ Pulled:[/green] {repo_path}")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("push")
    @click.option("--repo-path", "-r", required=True, help="Path to git repository")
    @click.option("--force", "-f", is_flag=True, help="Force push")
    def github_push(repo_path, force):
        """Push to remote."""
        e = get_engine()
        r = e.send("github-agent", "push", {"repo_path": repo_path, "force": force})
        if r["status"] == "success":
            console.print(f"[green]✓ Pushed:[/green] {repo_path}")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("worktree-add")
    @click.option("--repo-path", "-r", required=True, help="Path to git repository")
    @click.option("--path", "-p", required=True, help="Worktree path")
    @click.option("--branch", "-b", required=True, help="Branch for worktree")
    def github_worktree_add(repo_path, path, branch):
        """Add a worktree."""
        e = get_engine()
        r = e.send("github-agent", "worktree_add", {"repo_path": repo_path, "path": path, "branch": branch})
        if r["status"] == "success":
            console.print(f"[green]✓ Worktree added:[/green] {path} ({branch})")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("worktree-list")
    @click.option("--repo-path", "-r", required=True, help="Path to git repository")
    def github_worktree_list(repo_path):
        """List worktrees."""
        e = get_engine()
        r = e.send("github-agent", "worktree_list", {"repo_path": repo_path})
        if r["status"] == "success":
            trees = r["payload"].get("worktrees", [])
            if not trees:
                console.print("[dim]No worktrees[/dim]")
                return
            t = Table(title=f"Worktrees in {repo_path}", show_header=True)
            t.add_column("Path")
            t.add_column("Branch")
            t.add_column("HEAD")
            for w in trees:
                t.add_row(w.get("path", ""), w.get("branch", ""), w.get("head", ""))
            console.print(t)
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("repo-discover")
    @click.option("--paths", "-p", multiple=True, help="Paths to scan (default: current dir)")
    def github_repo_discover(paths):
        """Discover git repositories."""
        e = get_engine()
        r = e.send("github-agent", "repo_discover", {"paths": list(paths) if paths else ["."]})
        if r["status"] == "success":
            repos = r["payload"].get("repos", [])
            console.print(f"[green]✓ Found:[/green] {len(repos)} repos")
            for repo in repos:
                console.print(f"  • {repo.get('path')} ({repo.get('branch', '?')})")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("repo-register")
    @click.option("--repo-path", "-r", required=True, help="Path to git repository")
    def github_repo_register(repo_path):
        """Register a repo for tracking."""
        e = get_engine()
        r = e.send("github-agent", "repo_register", {"repo_path": repo_path})
        if r["status"] == "success":
            console.print(f"[green]✓ Registered:[/green] {repo_path}")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("repo-list")
    def github_repo_list():
        """List registered/tracked repos."""
        e = get_engine()
        r = e.send("github-agent", "repo_list", {})
        if r["status"] == "success":
            repos = r["payload"].get("repos", [])
            if not repos:
                console.print("[dim]No repos registered. Run: github repo-discover[/dim]")
                return
            t = Table(title="Registered Repos", show_header=True)
            t.add_column("Path")
            t.add_column("Branch")
            for repo in repos:
                t.add_row(repo.get("path", ""), repo.get("branch", "?"))
            console.print(t)
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("sync-now")
    def github_sync_now():
        """Trigger immediate sync."""
        e = get_engine()
        r = e.send("github-agent", "sync_now", {})
        if r["status"] == "success":
            console.print(f"[green]✓ Sync triggered[/green]")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("sync-metadata")
    @click.option("--repo-path", "-r", help="Path to git repository (optional, syncs all if omitted)")
    def github_sync_metadata(repo_path):
        """Sync metadata (branches, worktrees, default branch) for repositories."""
        e = get_engine()
        r = e.send("github-agent", "sync_metadata", {"repo_path": repo_path})
        if r["status"] == "success":
            payload = r.get("payload", {})
            if repo_path:
                console.print(f"[green]✓ Metadata synced for:[/green] {repo_path}")
            else:
                console.print(f"[green]✓ Metadata synced for[/green] {payload.get('synced_count', 0)} [green]repos[/green]")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("gh-repo-info")
    @click.argument("repo")
    def github_gh_repo_info(repo):
        """Get GitHub repository info."""
        e = get_engine()
        r = e.send("github-agent", "gh_repo_info", {"repo": repo})
        if r["status"] == "success":
            info = r["payload"]
            t = Table(title=f"GitHub: {repo}", show_header=True)
            t.add_column("Field")
            t.add_column("Value")
            for k, v in info.items():
                t.add_row(k, str(v)[:60])
            console.print(t)
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("gh-pr-list")
    @click.argument("repo")
    @click.option("--state", default="open", type=click.Choice(["open", "closed", "all"]))
    def github_gh_pr_list(repo, state):
        """List pull requests."""
        e = get_engine()
        r = e.send("github-agent", "gh_pr_list", {"repo": repo, "state": state})
        if r["status"] == "success":
            prs = r["payload"].get("prs", [])
            if not prs:
                console.print(f"[dim]No {state} PRs[/dim]")
                return
            t = Table(title=f"PRs: {repo} ({state})", show_header=True)
            t.add_column("Number")
            t.add_column("Title")
            t.add_column("Author")
            t.add_column("State")
            for pr in prs:
                t.add_row(str(pr.get("number", "")), pr.get("title", "")[:40], pr.get("author", ""), pr.get("state", ""))
            console.print(t)
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("gh-ci-status")
    @click.argument("repo")
    def github_gh_ci_status(repo):
        """Get CI status."""
        e = get_engine()
        r = e.send("github-agent", "gh_ci_status", {"repo": repo})
        if r["status"] == "success":
            status = r["payload"]
            console.print(f"[bold]CI Status:[/bold] {repo}")
            console.print(f"  Runs: {status.get('total_runs', '?')}")
            console.print(f"  Passing: {status.get('passing', '?')}")
            console.print(f"  Failing: {status.get('failing', '?')}")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    @github.command("event")
    @click.option("--agent", "-a", required=True, help="Agent ID (e.g., 'task-coordinator')")
    @click.option("--command", "-c", required=True, help="Command executed")
    @click.option("--data", "-d", default="{}", help="JSON data")
    def github_event(agent, command, data):
        """Track cross-agent event (for agent work tracking)."""
        e = get_engine()
        try:
            data_obj = json.loads(data)
        except json.JSONDecodeError:
            console.print("[red]Invalid JSON in --data[/red]")
            return
        r = e.send("github-agent", "event", {"agent_id": agent, "command": command, "data": data_obj})
        if r["status"] == "success":
            console.print(f"[green]✓ Event tracked:[/green] {agent} -> {command}")
        else:
            console.print(f"[red]✗ {r.get('error')}[/red]")

    # ── sessions ─────────────────────────────────────────────────────────────

    @cli.group()
    def sessions():
        """Session data extraction and analysis."""

    @sessions.command("extract")
    @click.option("--opencode-db", type=click.Path(), help="Path to OpenCode database")
    @click.option("--self-db", type=click.Path(), help="Path to self.db")
    def sessions_extract(opencode_db, self_db):
        """Extract signals from OpenCode sessions into self.db."""
        from extractors.session_extractor import extract_all_sessions

        console.print("[bold]Extracting session data...[/bold]")
        stats = extract_all_sessions(opencode_db, self_db)

        console.print(f"\n[green]✓ Extraction complete[/green]")
        console.print(f"  Sessions processed: {stats['sessions_processed']}")
        console.print(f"  Signals extracted: {stats['signals_extracted']}")
        console.print(f"  Metadata records: {stats['metadata_extracted']}")
        if stats['errors'] > 0:
            console.print(f"  [red]Errors: {stats['errors']}[/red]")

    @sessions.command("stats")
    @click.option("--self-db", type=click.Path(), help="Path to self.db")
    def sessions_stats(self_db):
        """Show session extraction statistics."""
        import sqlite3
        from pathlib import Path

        db_path = self_db or str(Path(__file__).parent.parent / "db" / "self" / "self.db")
        conn = sqlite3.connect(db_path)

        try:
            total_sessions = conn.execute("SELECT COUNT(*) FROM session_metadata").fetchone()[0]
            total_signals = conn.execute("SELECT COUNT(*) FROM session_signals").fetchone()[0]

            signal_types = conn.execute("""
                SELECT signal_type, COUNT(*) as count
                FROM session_signals
                GROUP BY signal_type
            """).fetchall()

            console.print(f"\n[bold]Session Extraction Stats[/bold]")
            console.print(f"  Total sessions: {total_sessions}")
            console.print(f"  Total signals: {total_signals}")
            console.print(f"\n  Signals by type:")
            for st in signal_types:
                console.print(f"    {st[0]}: {st[1]}")
        finally:
            conn.close()

    @sessions.command("infer-traits")
    def sessions_infer_traits():
        """Infer traits from session data into the traits table."""
        from analytics.trait_inference import TraitInferrer

        inferrer = TraitInferrer()
        stats = inferrer.infer_all()

        console.print(f"\n[green]✓ Trait inference complete[/green]")
        for group, count in stats.items():
            if group != "total":
                console.print(f"  {group}: {count} trait(s)")
        console.print(f"  [bold]Total traits written: {stats['total']}[/bold]")

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

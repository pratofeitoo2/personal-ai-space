#!/usr/bin/env python3
"""
Personal AI Space — Command Line Interface
Usage: python cli.py [COMMAND] [OPTIONS]
"""
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


def get_engine() -> Engine:
    global _engine
    if _engine is None:
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

---
tags:
  - pai/engine
  - pai/control
created: 2026-05-09T18:26:25
updated: 2026-05-09T20:07
---

# AI Engine Command Center

> One-click buttons for the Personal AI Powerhouse engine.
> Click a button → output appears inline. Use ✕ to clear.
> Powered by [[PAI RunSH]] v1.2 (enhanced fork with output capture).

Engine path: `personal-ai-space/engine/`

## 🔍 Status & Health

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py context
%%%
📋 Show Context
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py health
%%%
❤️ Engine Health
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py llm status
%%%
🤖 LLM Status
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py llm classify "what should I do today?"
%%%
🔬 Test: Classify Intent
```

## 📅 Daily Briefing

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py digest
%%%
📈 Daily Digest
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py reminders
%%%
⏰ Reminders
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py review
%%%
📊 Weekly Review
```

## ✅ Tasks

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py task list
%%%
📋 Today's Tasks
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py task list --all
%%%
📋 All Open Tasks
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py task summary
%%%
📊 Task Summary
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py task add "Review AI goals" --priority high
%%%
➕ Add: Review AI Goals
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py task add "Learn TypeScript" --priority high --due 2026-05-15 --hours 3
%%%
➕ Add: Learn TypeScript
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py task add "Weekly planning" --priority normal
%%%
➕ Add: Weekly Planning
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py task done TASK-001
%%%
✅ Done: Mark Task Complete
```

> *Replace `TASK-001` with the actual task ID from the task list output.*

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py habit insights
%%%
📊 Habit Insights
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py habit insights --days 30
%%%
📊 Habit Insights (30 days)
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py habit log "morning-routine" --duration 30
%%%
✅ Log: Morning Routine
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py habit log "coding" --duration 120
%%%
✅ Log: Coding Session
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py habit log "exercise" --duration 45
%%%
✅ Log: Exercise
```

## 🧠 Learning & Patterns

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py learning observations
%%%
📋 Recent Observations
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py learning observations --limit 20
%%%
📋 Recent Observations (20)
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py learning buffer
%%%
📦 Observation Buffer
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py learning infer
%%%
🧠 Run Inference
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py learning workflow
%%%
💡 Workflow Recommendation
```

## 🧠 MCP Memory

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py memory stats
%%%
📊 Memory Stats
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py memory facts
%%%
📋 List Facts
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py memory facts --prefix user
%%%
📋 User Facts
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py memory lessons
%%%
📚 List Lessons
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py memory sync-profile
%%%
🔄 Sync Profile
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py memory add-fact preference.notifications "prefers morning check-ins"
%%%
➕ Add: Notification Preference
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py memory add-fact user.language Portuguese --confidence 0.95
%%%
➕ Add: Language Fact
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py memory add-lesson "LLM context must be capped to 8K on M1" --category engineering
%%%
➕ Add: Engineering Lesson
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py memory add-lesson "Always back up before updates" --negative
%%%
➕ Add: Avoid Lesson (Negative)
```

## 📚 Knowledge Base

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py note stats
%%%
📊 KB Stats
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py note add "Quick thought" --tags "idea" --category general
%%%
➕ Add: Quick Thought
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py note add "React patterns" --content "Notes about hooks" --tags "react,frontend"
%%%
➕ Add: React Patterns
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py note search "architecture"
%%%
🔍 Search: Architecture
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py note search "MCP"
%%%
🔍 Search: MCP
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py note search "habits"
%%%
🔍 Search: Habits
```

## 🔌 MCP Tools

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py mcp status
%%%
🔌 MCP Status
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py mcp tools
%%%
🧰 MCP Tools List
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py mcp discover
%%%
🔄 Rediscover Tools
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py mcp call mail send_email --args '{"to": "me@example.com", "subject": "Test", "text": "Hello"}'
%%%
📧 MCP Call: Send Email
```

> *Replace `mail`, `send_email`, and `--args` with actual server/tool/args from `mcp tools` output.*

## 💬 Natural Language

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl "what's on my plate today?"
%%%
🔮 What's on my plate?
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl --enhance "how are my habits looking?"
%%%
🔮✨ Enhanced: Habits
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl "how are my habits" --enhance
%%%
🔮✨ Enhanced: Habits (alt)
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl --enhance "summarize my week"
%%%
🔮✨ Enhanced: Week
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl "how are my habits looking?"
%%%
🔮 Habit Check
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl "how are my habits this week"
%%%
🔮 Habit Check (Week)
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl --enhance "how are my habits looking?"
%%%
🔮✨ Enhanced: Habits
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl "what did I learn this week?"
%%%
🔮 What I Learned
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl "check my tasks"
%%%
🔮 Task Check
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl "remind me what I need to do"
%%%
🔮 Remind Me
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl "what should I do today"
%%%
🔮 What should I do today?
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl "add a task to review the budget"
%%%
🔮 Add: Review Budget
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl "what's overdue"
%%%
🔮 What's Overdue?
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl "send an email to Maria saying I'm running late"
%%%
📧 MCP: Send Email via NL
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl "check my Gmail inbox"
%%%
📧 MCP: Check Gmail
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py nl "look up John's contact"
%%%
📧 MCP: Look Up Contact
```

---

## 🚀 Daemon Management

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py daemon status
%%%
🔄 Daemon Status
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py daemon start
%%%
🚀 Daemon Start
```

```runsh
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine && python3 cli.py daemon stop
%%%
🛑 Daemon Stop
```

*Powered by PAI RunSH v1.2 · Commands run from `personal-ai-space/engine/`*
*Click the button → output appears inline. Use ✕ to clear. Hover to see full command.*
*Edit this note to change preset values, or copy a block into any other note.*

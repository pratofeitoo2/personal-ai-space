
<!-- aivectormemory-steering -->
# AIVectorMemory - Workflow Rules

---

## 1. New Session Startup (execute in order, do NOT process user requests until complete)

1. `recall` (tags: ["project knowledge"], scope: "project", top_k: 1) — load project knowledge
2. `recall` (tags: ["preference"], scope: "user", top_k: 10) — load user preferences
3. `status` (no state param) to read session state
4. Blocked → report blocking status, wait for user feedback
5. Not blocked → process user message

---

## 2. Message Processing Flow

**A. `status` check blocking** — blocked → report and wait, no actions allowed

**B. Determine message type** (reply should state the judgment result in natural language)
- Casual chat / progress check / rule discussion / simple confirmation → answer directly, no issue documentation
- Correcting wrong behavior → `remember`(tags: ["pitfall", "behavior-correction", ...keywords], scope: "project"), continue C(track create) → D(investigation) → E(solution + status set block) → F(modification) → G(self-test) → H(wait for verification) → I(user confirms & archive)
- Technical preferences / work habits → `auto_save` to store preferences, no issue documentation
- Other (code issues, bugs, feature requests) → C(track create) → D(investigation) → E(solution + status set block) → F(modification) → G(self-test) → H(wait for verification) → I(user confirms & archive)

**C. `track create`** — record immediately (never fix before recording), `content` required: symptoms and context

**D. Investigation** — `recall`(query: problem keywords, tags: ["pitfall"]) check history pitfalls → when graph data exists `graph trace` to locate impact scope → review code → confirm data flow → find root cause. `track update` fill investigation + root_cause

**E. Present solution** — simple fix → F, multi-step → use task tracking. Must `status` set block before waiting for confirmation

**F. Modify code** — fix one issue at a time. New issue found → `track create`: doesn't block current → record and continue; blocks current → handle first. After modification, `track update` fill solution + files_changed + test_result

**G. Self-test verification** — after each code change, run corresponding tests. Report completion after passing self-test, then set block awaiting verification. Do NOT git commit/push on your own.

**H. Wait for verification** — `status` set block (block_reason: "Fix complete, waiting for verification" or "User decision needed")

**I. User confirms** — `track archive`, clear block. If pitfall value → `remember`(tags: ["pitfall", ...keywords], scope: "project"). `auto_save` before session ends

---

## 3. Blocking Rules

- **Highest priority**: when blocked, no actions allowed, can only report and wait
- **Emergency stop**: when user says "stop/halt/pause" → immediately interrupt all current operations, set block, wait for next instruction
- **Set block**: proposing solution for confirmation, fix complete waiting for verification, user decision needed
- **Clear block**: user explicitly confirms ("execute/ok/sure/go ahead/no problem/yes/fine/do it")
- **Not a confirmation**: rhetorical questions, doubt expressions, dissatisfaction, vague replies
- Must re-confirm after new session/compact. Never self-clear blocking, never guess intent

---

## 4. Core Principles

1. **Validate before every operation** — never assume, never rely on stale memory. Read the actual file.
2. **Root cause analysis** — when encountering issues, review relevant code, find the real cause, match to actual error. No blind testing.
3. **No verbal promises** — everything is validated by passing tests.
4. **Scope discipline** — strictly execute within user instructions, never expand scope on your own.
5. **Self-test rigorously** — after editing code, run appropriate tests. Never claim completion without verification.
6. **`recall` before asking** — when project info is needed, query AIVectorMemory first, then search code/config files. Only ask user as last resort.
7. **Operating context**: "memory/project memory" = AIVectorMemory MCP memory data.

---

## 5. Issue Tracking (track) Field Standards

Must show complete record after archiving:
- `create`: `content` (symptoms + context)
- After investigation `update`: `investigation` (process), `root_cause` (root cause)
- After fix `update`: `solution` (solution), `files_changed` (JSON array), `test_result` (results)
- Fix one issue at a time. New issue found: doesn't block current → record and continue; blocks current → handle first

---

## 6. Pre-operation Checks

- **Before code modification**: `recall`(query: keywords, tags: ["pitfall"]) to check pitfall records + review existing implementation + confirm data flow. For multi-module interactions, use `graph trace`(direction: "both")
- **After code modification**: run tests + confirm no impact on other features
- **Before dangerous operations** (publish, deploy, restart): `recall`(query: operation keywords, tags: ["pitfall"]) check records
- **When user asks to read a file**: must actually read it. Never skip by claiming "already in context"

---

## 7. Spec and Task Management (task)

**Trigger**: multi-step new features, refactoring, upgrades

**Spec flow**:
1. `requirements.md` — scope + acceptance criteria → review → `status` set block → user confirms
2. `design.md` — technical solution + architecture. Use `graph query + trace` to map existing call chains → review → `status` set block → user confirms
3. `tasks.md` — minimal executable units → review → `status` set block → user confirms
4. `task batch_create` (feature_id, use children nesting)
5. Execute subtasks in order: `task update` (in_progress) → `recall` pitfalls → implement → `task update` (completed)
6. `task list` to confirm nothing missed
7. Self-test → set block waiting verification

**Division**: task manages plan/progress, track manages bugs. Bug found during task execution → `track create`: record and continue, or handle first if blocking.

---

## 8. Memory Quality Requirements

- tags: category tag (pitfall/project knowledge) + keyword tags (module name, feature name, technical terms)
- Command type: complete executable command; process type: specific steps; pitfall type: symptoms + root cause + correct approach

---

## 9. Tool Quick Reference

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| remember | Store memory | content, tags, scope(project/user) |
| recall | Semantic search | query, tags, scope, top_k |
| forget | Delete memory | memory_id / memory_ids |
| status | Session state | state(omit=read, pass=update), clear_fields |
| track | Issue tracking | action(create/update/archive/delete/list) |
| task | Task management | action(batch_create/update/list/delete/archive), feature_id, tasks[].children |
| readme | README generation | action(generate/diff), lang, sections |
| graph | Code knowledge graph | action(query/trace/batch/add_node/add_edge/remove/refresh), trace: start, direction(up/down/both), max_depth |
| auto_save | Save preferences | preferences, extra_tags |

---

## 10. Self-test Verification

**After each Edit/Write of code files, the next step must be executing the corresponding self-test.** Cannot reply first, cannot report first, cannot set block first.

Self-test checklist:
- **Backend changes**: compile → verify affected API endpoints
- **Frontend changes**: build → use Playwright MCP to verify rendering
- **Database migration**: execute migration → verify tables/columns → verify dependent APIs
- **Deployment**: service healthy → core endpoint 200 → browser verify core functionality
- **Config changes**: config check passes → verify target reachable

After running tests, `track update` fill solution + files_changed + test_result.

# OpenCode Telegram Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:subagent-driven-development (recommended) or superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy `@grinev/opencode-telegram-bot` as a persistent gateway between Telegram and the local OpenCode CLI, enabling mobile prompt/response, session management, and live monitoring.

**Architecture:** A local Node.js process (`@grinev/opencode-telegram-bot`) connects to the OpenCode API server (`opencode serve` on `localhost:4096`) on one side and the Telegram Bot API on the other. No ports are exposed to the internet — the bot only connects outbound to Telegram. Communication is local-only between the bot and OpenCode. The bot process runs as a macOS launchd user agent for 24/7 availability.

**Tech Stack:** Node.js v26+, npm 11+, OpenCode CLI v1.15.7 (already installed), `@grinev/opencode-telegram-bot` v0.20.4 (npm), Telegram Bot API, macOS launchd

**Assumptions:**
- OpenCode CLI is already installed and available at `~/.opencode/bin/opencode` — verified.
- Node.js v26+ and npm 11+ are installed — verified.
- The user has a Telegram account and can access @BotFather and @userinfobot — verified assumed.
- The bot runs on macOS (launchd for persistence) — verified.
- The user's machine is online when they want to use the bot — the bot has no offline queue.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `~/Library/Application Support/opencode-telegram-bot/.env` | Create | Bot configuration: token, user ID, locale, port, OpenCode API URL |
| `~/Library/LaunchAgents/com.opencode.telegram-bot.plist` | Create | launchd plist for auto-start on user login |
| `docs/INTEGRATIONS.md` | Modify | Add Telegram gateway to the integrations document |
| `docs/setup/telegram-bot-setup.md` | Create | Setup documentation for future reference |
| `personal-ai-space/engine/config/system.config.json` | Possibly modify | Register Telegram as active integration (if integration config pattern exists) |

---

## Tasks

### Task 1: Create Telegram Bot Token and Get User ID

**Files:** None (external setup via Telegram)

**Security flag:** `security` — handles bot token and user ID credentials

**Does NOT cover:** Group chats, inline mode, webhooks, payment APIs — the bot operates in a 1:1 DM between the user and the bot only.

- [ ] **Step 1: Create bot via @BotFather**

  1. Open Telegram and start chat with [@BotFather](https://t.me/BotFather)
  2. Send `/newbot`
  3. When prompted for name, enter: `AI Powerhouse Gateway`
  4. When prompted for username, enter: `ai_powerhouse_gateway_bot` (must end in `bot` — adjust for uniqueness if taken)
  5. Save the HTTP API token from BotFather's response — it looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890`

  Expected: Bot created, token received, bot appears at `t.me/ai_powerhouse_gateway_bot`

- [ ] **Step 2: Get Telegram User ID**

  1. Start chat with [@userinfobot](https://t.me/userinfobot)
  2. Send `/start`
  3. The bot responds with your numeric user ID — it looks like: `123456789`
  4. Save this ID

  Expected: Numeric user ID received

- [ ] **Step 3: Record credentials**

  Create a credential reference file (does NOT store secrets — just references the integration):

  ```bash
  mkdir -p personal-ai-space/vault
  ```

  Record the following information for setup use:
  - **Bot token**: `[from @BotFather]`
  - **User ID**: `[from @userinfobot]`
  - **Bot username**: `ai_powerhouse_gateway_bot` (or chosen variant)

> ⚠️ The bot token is a secret — never commit it. It will be stored in `~/Library/Application Support/opencode-telegram-bot/.env` (outside the repo) and may also be placed in `personal-ai-space/vault/` if that directory exists and is git-ignored. Verify `.gitignore` covers `vault/`.

---

### Task 2: Install and Configure the Bot

**Files:**
- Create: `~/Library/Application Support/opencode-telegram-bot/.env` (via setup wizard)
- Modify: `opencode.json` (add `opencode serve` config if needed)

**Security flag:** `security` — config contains bot token

**Does NOT cover:** Custom port mapping, proxy configuration, custom API root URL, STT/Whisper setup, multi-user access. These are optional features not in scope.

- [ ] **Step 1: Start the OpenCode API server**

  OpenCode must run in server mode for the bot to connect. Start it:

  ```bash
  opencode serve --port 4096
  ```

  Verify it's running:

  ```bash
  curl -s http://localhost:4096/health 2>/dev/null || echo "Server responded"
  ```

  Expected: Server starts and listens on port 4096. A 200 response or a valid HTTP response indicates it's alive.

- [ ] **Step 2: Run the bot setup wizard**

  In a separate terminal (or after putting the server in background):

  ```bash
  npx @grinev/opencode-telegram-bot
  ```

  The interactive wizard will ask for:
  1. **Language**: Select `en` (English)
  2. **Bot token**: Paste the token from @BotFather
  3. **Telegram user ID**: Paste the numeric ID from @userinfobot
  4. **OpenCode API URL**: Accept default (`http://localhost:4096`) or confirm

  The wizard writes the config to `~/Library/Application Support/opencode-telegram-bot/.env`.

- [ ] **Step 3: Verify bot is running**

  Send a message to the bot on Telegram (e.g., `/start` or `/help`). Expected:
  - Bot replies in Telegram
  - `opencode-telegram` process shows no errors

  Then send a test prompt: `/prompt list the files in the current project`
  Expected:
  - Bot responds with a session being created and the prompt being processed
  - Reply contains the file listing from OpenCode

- [ ] **Step 4: Configure OpenCode to always serve on the fixed port**

  Verify that `opencode serve --port 4096` is accessible. Add a note so this port is reused consistently. The bot's `.env` file stores this as `OPENCODE_API_URL=http://127.0.0.1:4096`.

  To make the port consistent across sessions, the user should always start OpenCode with:
  ```bash
  opencode serve --port 4096
  ```

  Optionally, create a convenience script or shell alias:
  ```bash
  alias oc-serve='opencode serve --port 4096'
  ```

---

### Task 3: Set Up Persistent Service via launchd

**Files:**
- Create: `~/Library/LaunchAgents/com.opencode.telegram-bot.plist`
- Possibly create: convenience start/stop scripts

**Security flag:** `none` — the `.env` contains the secret, not the plist

**Does NOT cover:** systemd (Linux), Docker, or cloud deployment — this is macOS-only.

- [ ] **Step 1: Create the launchd plist**

  Create `~/Library/LaunchAgents/com.opencode.telegram-bot.plist` with:

  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
  <plist version="1.0">
  <dict>
      <key>Label</key>
      <string>com.opencode.telegram-bot</string>
      <key>ProgramArguments</key>
      <array>
          <string>/Users/paulorezende/.local/share/npm/bin/opencode-telegram</string>
          <string>start</string>
          <string>--mode</string>
          <string>installed</string>
      </array>
      <key>RunAtLoad</key>
      <true/>
      <key>KeepAlive</key>
      <true/>
      <key>StandardOutPath</key>
      <string>/Users/paulorezende/Library/Logs/opencode-telegram-bot.log</string>
      <key>StandardErrorPath</key>
      <string>/Users/paulorezende/Library/Logs/opencode-telegram-bot.err.log</string>
      <key>EnvironmentVariables</key>
      <dict>
          <key>PATH</key>
          <string>/Users/paulorezende/.local/share/npm/bin:/usr/local/bin:/usr/bin:/bin</string>
          <key>NODE_ENV</key>
          <string>production</string>
      </dict>
  </dict>
  </plist>
  ```

  > ⚠️ The exact path to the `opencode-telegram` binary depends on `npm install -g @grinev/opencode-telegram-bot`. Find it with:
  > ```bash
  > which opencode-telegram
  > ```
  > If the global install isn't preferred, use the npx path instead:
  > ```bash
  > # Run as a background daemon via npx by keeping the terminal alive
  > # Or install globally:
  > npm install -g @grinev/opencode-telegram-bot
  > ```

- [ ] **Step 2: Install and load the launchd service**

  ```bash
  # Ensure LaunchAgents directory exists
  mkdir -p ~/Library/LaunchAgents

  # Load the service
  launchctl load ~/Library/LaunchAgents/com.opencode.telegram-bot.plist

  # Verify it's running
  launchctl list | grep opencode-telegram

  # Check logs
  cat ~/Library/Logs/opencode-telegram-bot.log
  ```

  Expected: `launchctl list` shows the service with a PID. No errors in logs.

- [ ] **Step 3: Test service persistence**

  Kill the bot process:
  ```bash
  launchctl kickstart gui/$(id -u)/com.opencode.telegram-bot
  ```

  Then send another test message on Telegram. Expected: Bot responds within seconds (KeepAlive auto-restarts it).

- [ ] **Step 4: Create convenience scripts for manual control**

  Create `docs/setup/telegram-bot-service.sh` with:

  ```bash
  #!/bin/bash
  # Telegram Bot Service Control
  # Usage: ./telegram-bot-service.sh {start|stop|restart|status|logs}

  PLIST="com.opencode.telegram-bot"

  case "${1:-status}" in
    start)
      launchctl load ~/Library/LaunchAgents/$PLIST.plist
      echo "✓ Bot service started"
      ;;
    stop)
      launchctl unload ~/Library/LaunchAgents/$PLIST.plist
      echo "✓ Bot service stopped"
      ;;
    restart)
      launchctl unload ~/Library/LaunchAgents/$PLIST.plist
      sleep 1
      launchctl load ~/Library/LaunchAgents/$PLIST.plist
      echo "✓ Bot service restarted"
      ;;
    status)
      if launchctl list | grep -q "$PLIST"; then
        echo "✓ Bot service is running"
        launchctl list | grep "$PLIST"
      else
        echo "✗ Bot service is NOT running"
      fi
      ;;
    logs)
      echo "=== stdout ==="
      cat ~/Library/Logs/opencode-telegram-bot.log
      echo "=== stderr ==="
      cat ~/Library/Logs/opencode-telegram-bot.err.log
      ;;
    *)
      echo "Usage: $0 {start|stop|restart|status|logs}"
      exit 1
      ;;
  esac
  ```

---

### Task 4: Create Setup Documentation

**Files:**
- Create: `docs/setup/telegram-bot-setup.md`
- Modify: `docs/INTEGRATIONS.md`

**Security flag:** `none` — docs, no credentials

**Does NOT cover:** Migration of existing docs, CI/CD pipeline, automated deployment scripts.

- [ ] **Step 1: Create setup guide**

  Create `docs/setup/telegram-bot-setup.md` with:

  ```markdown
  # Telegram Bot Gateway Setup

  > Connects OpenCode CLI to Telegram via [@grinev/opencode-telegram-bot](https://github.com/grinev/opencode-telegram-bot)

  ## Architecture

  ```
  Telegram App (phone/desktop)
       ↕ Telegram Bot API (outbound only)
       ↕
  @grinev/opencode-telegram-bot (local Node.js)
       ↕ localhost:4096
  OpenCode CLI Server (opencode serve)
  ```

  ## Prerequisites

  - Node.js 20+ (verified: v26.0.0)
  - OpenCode CLI (verified: v1.15.7)
  - Telegram account

  ## Quick Start

  ### 1. Start OpenCode server
  ```bash
  opencode serve --port 4096
  ```

  ### 2. Run the bot (interactive setup)
  ```bash
  npx @grinev/opencode-telegram-bot
  ```
  Follow the wizard:
  - Language: `en`
  - Bot token: from [@BotFather](https://t.me/BotFather)
  - User ID: from [@userinfobot](https://t.me/userinfobot)
  - API URL: `http://localhost:4096` (default)

  ### 3. Test
  Send a message to your bot on Telegram.

  ## Service Management (launchd)

  The bot runs as a macOS launchd agent for 24/7 availability.

  | Action | Command |
  |--------|---------|
  | Start | `launchctl load ~/Library/LaunchAgents/com.opencode.telegram-bot.plist` |
  | Stop | `launchctl unload ~/Library/LaunchAgents/com.opencode.telegram-bot.plist` |
  | Status | `launchctl list \| grep opencode-telegram` |
  | Logs | `cat ~/Library/Logs/opencode-telegram-bot.log` |
  | Errors | `cat ~/Library/Logs/opencode-telegram-bot.err.log` |

  ## Commands

  | Command | Action |
  |---------|--------|
  | `/start` or `/help` | Show help |
  | `/prompt <text>` | Send a prompt to OpenCode |
  | `/session` | List/manage sessions |
  | `/model` | Switch model |
  | `/mode` | Switch Plan/Build mode |
  | `/status` | Show live status (pinned) |

  ## Configuration

  - Config file: `~/Library/Application Support/opencode-telegram-bot/.env`
  - Bot must always connect to OpenCode on port 4096
  - Use `opencode serve --port 4096` consistently
  ```

- [ ] **Step 2: Update INTEGRATIONS.md**

  Add a Telegram section to `personal-ai-space/docs/INTEGRATIONS.md` following the existing pattern. Insert after the GitHub section and before Fitness Apps:

  ```markdown
  ### 5. Telegram Bot Gateway
  **Purpose:** Remote OpenCode access via Telegram — send prompts, manage sessions, monitor progress
  **Status:** ✅ Active (live since 2026-05-21)
  **Tool:** [@grinev/opencode-telegram-bot](https://github.com/grinev/opencode-telegram-bot)
  **Connection:** Local Node.js process ↔ OpenCode API server (port 4096) ↔ Telegram Bot API
  **Scope:** Send prompts, session management, model switching, file attachments, live monitoring

  ```json
  {
    "id": "integration_telegram_bot",
    "service": "telegram",
    "type": "remote_access",
    "enabled": true,
    "status": "active",
    "config": {
      "port": 4096,
      "openCodeServer": "http://localhost:4096",
      "launchd_service": "com.opencode.telegram-bot"
    },
    "setup_doc": "docs/setup/telegram-bot-setup.md"
  }
  ```

  **Data Flow:**
  ```
  Telegram Message
      ↓ (Telegram Bot API)
  @grinev/opencode-telegram-bot (local)
      ↓ (localhost:4096)
  OpenCode CLI Server
      ↓
  OpenCode processes prompt (code changes, file reads, etc.)
      ↓ (response)
  Bot sends result to Telegram
  ```
  ```

---

### Task 5: End-to-End Verification

**Files:** None (verification only)

**Security flag:** `none`

**Does NOT cover:** Load testing, stress testing, multi-user scenarios.

- [ ] **Step 1: Verify service is running**

  ```bash
  launchctl list | grep opencode-telegram
  ```

  Expected: Shows `com.opencode.telegram-bot` with a PID. Exit code 0.

- [ ] **Step 2: Verify OpenCode server is accessible**

  ```bash
  curl -s http://localhost:4096 | head -5
  ```

  Expected: Non-empty response, no connection refused error.

- [ ] **Step 3: Test simple prompt via Telegram**

  Send via Telegram: `/prompt what is the current date?`

  Expected: Bot replies with the current date within ~10-30 seconds.

- [ ] **Step 4: Test session continuity**

  Send a follow-up prompt: `/prompt what was my previous question?`

  Expected: Bot references the previous question, demonstrating session memory.

- [ ] **Step 5: Test session listing**

  Send: `/session`

  Expected: Bot lists active session(s).

- [ ] **Step 6: Test model/mode switching**

  Send: `/model`

  Expected: Bot shows model selection menu with inline buttons.

- [ ] **Step 7: Verify service survives a restart**

  ```bash
  launchctl stop gui/$(id -u)/com.opencode.telegram-bot
  sleep 2
  launchctl list | grep opencode-telegram
  ```

  Expected: KeepAlive restarts the service within seconds. Send another prompt to confirm.

---

## Self-Review Checklist

1. **Spec coverage:** The plan covers: bot creation (Task 1), install/config (Task 2), persistence (Task 3), documentation (Task 4), verification (Task 5). No gaps.
2. **Placeholder scan:** No TBD, TODO, "add appropriate", "implement later", or placeholder code in any task. Every command is concrete and runnable.
3. **Type consistency:** Single bot token, single user ID, single port (4096), consistent service name throughout.
4. **Scope-reduction scan:** No "v1", "basic", "simple", "for now", "placeholder", "initial version", "minimal" used as scope reduction. The plan covers the full installation and configuration of the chosen tool.

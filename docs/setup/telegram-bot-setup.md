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

Or use the convenience script:

```bash
docs/setup/telegram-bot-service.sh status
docs/setup/telegram-bot-service.sh logs
```

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

## Installed Location

- **Binary:** `/opt/homebrew/bin/opencode-telegram` (npm global install)
- **Config:** `~/Library/Application Support/opencode-telegram-bot/.env`
- **Logs:** `~/Library/Application Support/opencode-telegram-bot/logs/`
- **Service plist:** `~/Library/LaunchAgents/com.opencode.telegram-bot.plist`

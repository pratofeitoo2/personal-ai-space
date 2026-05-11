# Gmail Access Setup

## Approach

Gmail is accessed via **Apple Mail** on macOS using the [`mail-bridge`](https://github.com/anomalyco/opencode) CLI tool at `~/.claude/mail-bridge`.

## Prerequisites

1. **Gmail account configured in Apple Mail** on macOS
2. **Gmail App Password** (not your regular password) generated at:
   https://myaccount.google.com/apppasswords
3. **macOS Automation permission** granted to the terminal app for Mail.app
   (System Settings > Privacy & Security > Automation)

## How it works

The `mail-bridge` sends AppleScript commands to Mail.app, which handles IMAP/SMTP communication with Gmail. No direct IMAP credentials are needed — Mail.app manages authentication.

## Available Commands

| Command | Description |
|---------|-------------|
| `accounts` | List all email accounts |
| `mailboxes [account]` | List mailboxes for an account |
| `list [mailbox] [account] [count]` | List recent messages (default: INBOX, 20) |
| `unread [mailbox] [account] [--all] [--max N] [--since X]` | List unread messages |
| `search <query> [max] [account] [--unread] [--since X]` | Search messages by subject/sender |
| `read <index> [mailbox] [account] [--mark-read]` | Read a message by index |
| `send <to> <subject> <body> [attachment] [--from email] [--force]` | Send email |
| `delete <index> [mailbox] [account] [--force]` | Move message to trash |

## Usage

```bash
# List recent inbox messages
~/.claude/mail-bridge list

# Check unread
~/.claude/mail-bridge unread

# Read a specific message (preserves unread status)
~/.claude/mail-bridge read 1

# Send email (opens compose window for review)
~/.claude/mail-bridge send "recipient@example.com" "Subject" "Body text"
```

## MCP Server Attempt

The `gmail-mcp` MCP server (IMAP/SMTP-based with app password) exists in the MCP catalog but did not expose its tools in this environment. The `mail-bridge` approach was used instead.

# MCP Docker Gateway & Multi-Server Architecture

## Overview

The `MCP_DOCKER` environment acts as a **Universal Gateway**, allowing the agent to discover, configure, and connect to multiple independent MCP (Model Context Protocol) servers in parallel. 

## Core Infrastructure

This system utilizes a gateway that manages the lifecycle of remote MCP servers:

- **Discovery**: `mcp-find` searches a central catalog for available servers.
- **Management**: `mcp-add` and `mcp-remove` dynamic activation/deactivation of tools.
- **Persistence**: `mcp-create-profile` and `mcp-activate-profile` save snapshots of active server configurations.
- **Execution**: `mcp-exec` allows direct tool calls to these servers.

## How the Gateway Handles Multi-Server Integration

1. **Isolation**: Each server (e.g., `gmail-mcp`, `mcp-discord`, `slack`) runs in its own context, preventing dependency conflicts.
2. **Secrets Management**: Sensitive credentials (API keys, App Passwords) are passed via `mcp-config-set` or environment variables at the gateway level.
3. **Aggregation**: When multiple servers are added, the agent sees a unified set of tools from all active providers.

## Key Management Tools

### Discovery & Setup
```bash
# Search for specific capabilities
mcp-find "github"

# Configure a server (secrets included)
mcp-config-set server="gmail-mcp" config='{"email_address":"user@gmail.com", "email_password":"..."}'

# Activate tools
mcp-add "gmail-mcp"
```

### Profile Management
Profiles allow switching between different operational modes (e.g., "Personal", "Work", "DevTools"):
```bash
# Save current state as a profile
mcp-create-profile "my-daily-setup"

# Load previously saved tools
mcp-activate-profile "my-daily-setup"
```

## Strategy for Gmail Tools
While the `gmail-mcp` (catalog-based) provides a direct IMAP/SMTP gateway, this project successfully pivoted to the **Apple Mail Bridge** (`~/.claude/mail-bridge`) which leverages the native macOS Mail.app as a localized gateway for Gmail, avoiding many of the authentication and connectivity hurdles of standalone Docker-based IMAP clients.

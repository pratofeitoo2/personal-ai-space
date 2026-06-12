#!/bin/bash
# Wrapper for TablePro MCP — bridges user ~/Library path to the binary's hardcoded /Library path
HANDSHAKE_SRC="$HOME/Library/Application Support/TablePro/mcp-handshake.json"
HANDSHAKE_DST="/Library/Application Support/TablePro/mcp-handshake.json"
HANDSHAKE_DIR="/Library/Application Support/TablePro"

# Ensure destination directory exists (may fail if no sudo, but we try)
if [ ! -d "$HANDSHAKE_DIR" ]; then
  mkdir -p "$HANDSHAKE_DIR" 2>/dev/null
fi

# Copy handshake if source exists and destination is missing/stale
if [ -f "$HANDSHAKE_SRC" ]; then
  cp "$HANDSHAKE_SRC" "$HANDSHAKE_DST" 2>/dev/null
fi

exec /Applications/TablePro.app/Contents/MacOS/tablepro-mcp

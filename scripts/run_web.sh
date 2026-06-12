#!/bin/bash
# personal-ai-space/run_web.sh
# Start the Personal AI Powerhouse web app
# Usage: ./run_web.sh [--daemon] [--port 5001]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINE_DIR="$SCRIPT_DIR/engine"
WEB_DIR="$SCRIPT_DIR"
PORT="${PAI_WEB_PORT:-5001}"
START_DAEMON=false

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --daemon) START_DAEMON=true; shift ;;
        --port) PORT="$2"; shift 2 ;;
        *) shift ;;
    esac
done

echo "Personal AI Powerhouse — Web App"
echo "——————————————————————————————————"

# Start daemon if requested
if $START_DAEMON; then
    echo "Starting engine daemon..."
    cd "$ENGINE_DIR"
    python3 cli.py daemon start 2>/dev/null || echo "  (daemon may already be running)"
    cd "$SCRIPT_DIR"
fi

# Check daemon
echo "Checking daemon..."
if curl -s http://127.0.0.1:19876/health > /dev/null 2>&1; then
    echo "  Daemon is running"
else
    echo "  Daemon not running — start with: cd engine && python3 cli.py daemon start"
    echo "  Dashboard will work but engine proxy features will be unavailable"
fi

echo ""

# Create static/templates dirs if missing
mkdir -p "$WEB_DIR/web/static" "$WEB_DIR/web/templates"

echo "Starting web server on http://0.0.0.0:$PORT"
echo "   Access from any device on your local network"
echo "   Press Ctrl+C to stop"
echo ""

cd "$WEB_DIR"
exec python3 -c "
from web.app import create_app
app = create_app()
app.run(host='0.0.0.0', port=$PORT, debug=False)
"

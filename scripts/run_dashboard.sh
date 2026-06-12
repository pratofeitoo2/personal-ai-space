#!/bin/bash

# Personal AI Dashboard Launcher
# This script starts the dashboard server

echo "🚀 Starting Personal AI Dashboard..."
echo "=================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if ! python -c "import flask" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the dashboard
echo "🌐 Starting dashboard server..."
echo "📊 Open http://127.0.0.1:5000 in your browser"
echo "🛑 Press Ctrl+C to stop"
echo ""

python dashboard_server.py
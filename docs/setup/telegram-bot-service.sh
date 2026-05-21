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

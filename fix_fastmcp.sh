#!/usr/bin/env bash

# FastMCP Compatibility Fix Script
# Automatically applies the recommended downgrade fix

echo "🔧 FastMCP Compatibility Fix"
echo "================================"
echo ""

# Check current fastmcp version
CURRENT_VERSION=$(pip show fastmcp 2>/dev/null | grep Version | cut -d' ' -f2)
if [ -z "$CURRENT_VERSION" ]; then
    echo "❌ fastmcp is not installed"
    exit 1
fi

echo "Current fastmcp version: $CURRENT_VERSION"
echo ""

if [ "$CURRENT_VERSION" = "2.4.0" ]; then
    echo "✅ fastmcp is already at the correct version (2.4.0)"
    echo ""
    echo "Testing imports..."
    if python3 -c "from fastmcp import FastMCP; print('✅ Import successful')" 2>/dev/null; then
        echo ""
        echo "🎉 Everything is working! You can now test the MCP servers:"
        echo ""
        echo "  task-management-mcp"
        echo "  appointment-mcp"
        echo "  project-context-mcp"
        exit 0
    else
        echo "❌ Import failed despite correct version"
        exit 1
    fi
fi

echo "🔄 Downgrading fastmcp to compatible version 2.4.0..."
echo ""

# Downgrade fastmcp
if pip3 install fastmcp==2.4.0 --force-reinstall; then
    echo ""
    echo "✅ Successfully downgraded fastmcp"
    echo ""
    
    # Verify the fix
    echo "Verifying import..."
    if python3 -c "from fastmcp import FastMCP; print('✅ Import successful')" 2>/dev/null; then
        echo ""
        echo "🎉 Fix applied successfully!"
        echo ""
        echo "You can now test the MCP servers:"
        echo ""
        echo "  export PATH=\"/Library/Frameworks/Python.framework/Versions/3.13/bin:\$PATH\""
        echo "  task-management-mcp"
        echo "  appointment-mcp"
        echo "  project-context-mcp"
        echo ""
        echo "To use with OpenCode:"
        echo "  opencode run 'list my tasks' --mcp task-management-mcp"
        exit 0
    else
        echo ""
        echo "❌ Import still failing after downgrade"
        echo "Please check the manual fix instructions in FASTMCP_COMPATIBILITY_FIX.md"
        exit 1
    fi
else
    echo ""
    echo "❌ Failed to downgrade fastmcp"
    echo "You may need to use: pip3 install fastmcp==2.4.0 --user"
    exit 1
fi
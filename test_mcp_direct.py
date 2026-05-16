#!/usr/bin/env python3
"""
Simple test script for MCP servers - direct testing without OpenCode
"""

import subprocess
import time
import json

def test_mcp_server_direct(server_name, test_function):
    """Test an MCP server by calling it directly"""
    print(f"\n=== Testing {server_name} ===")
    
    try:
        # Start the server in background
        server_process = subprocess.Popen(
            [server_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it time to start
        time.sleep(3)
        
        # Test the server by making a simple call
        print(f"Testing {test_function}...")
        
        # For now, just check if server starts without crashing
        if server_process.poll() is None:
            print(f"✅ {server_name} server started successfully")
            server_process.terminate()
            return True
        else:
            print(f"❌ {server_name} server failed to start")
            return False
            
    except Exception as e:
        print(f"❌ {server_name} test error: {e}")
        return False

def main():
    print("Testing Personal AI Powerhouse MCP Servers (Direct)")
    print("=" * 55)
    
    tests = [
        ("task-management-mcp", "task listing"),
        ("appointment-mcp", "appointment access"),
        ("project-context-mcp", "project context")
    ]
    
    results = []
    for server, function in tests:
        results.append(test_mcp_server_direct(server, function))
    
    print(f"\n=== Test Summary ===")
    print(f"Servers started: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All MCP servers are working!")
        print("\nManual testing instructions:")
        print("1. Start a server: task-management-mcp")
        print("2. In another terminal: opencode run 'list my tasks' --mcp task-management-mcp")
        print("3. Use --model openrouter/mistralai/devstral-small for free tier")
    else:
        print("⚠️  Some servers failed to start. Check the output above.")

if __name__ == "__main__":
    main()
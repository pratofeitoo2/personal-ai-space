#!/usr/bin/env python3
"""
Test script for new MCP servers
"""

import subprocess
import json
import time

def test_mcp_server(server_name, test_command, expected_pattern):
    """Test an MCP server with a simple command"""
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
        time.sleep(2)
        
        # Test with OpenCode using a valid free model
        result = subprocess.run(
            ["opencode", "run", test_command, "--model", "openrouter/mistralai/devstral-small"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Clean up
        server_process.terminate()
        
        if expected_pattern in result.stdout:
            print(f"✅ {server_name} test passed")
            return True
        else:
            print(f"❌ {server_name} test failed")
            print(f"Output: {result.stdout}")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ {server_name} test error: {e}")
        return False

def main():
    print("Testing Personal AI Powerhouse MCP Servers")
    print("=" * 50)
    
    tests = [
        ("task-management-mcp", "List my pending tasks", "list_tasks"),
        ("appointment-mcp", "What appointments do I have today?", "get_appointments"),
        ("project-context-mcp", "Get context for project ai-powerhouse", "get_project_context")
    ]
    
    results = []
    for server, command, pattern in tests:
        results.append(test_mcp_server(server, command, pattern))
    
    print(f"\n=== Test Summary ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All MCP servers are working!")
        print("\nNext steps:")
        print("1. Add MCP servers to opencode.jsonc (already done)")
        print("2. Test with external agents")
        print("3. Build Obsidian integration")
    else:
        print("⚠️  Some tests failed. Check the output above.")

if __name__ == "__main__":
    main()
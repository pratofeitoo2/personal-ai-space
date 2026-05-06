#!/usr/bin/env node

/**
 * pi-memory: Main entry point
 *
 * Initializes the MCP server with lifecycle hooks and starts
 * listening for client connections.
 *
 * Usage:
 *   npx tsx src/index.ts
 *   node dist/index.js (after build)
 */

import { PiMemoryServer } from "./bootstrap.js";
import { MemoryStore } from "./store.js";
import { NLPRouter, createNLPRouter } from "./nlp-interface.js";
import { homedir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

// Resolve to engine/db/ inside the project — keep memory co-located with the rest of the databases
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_DB_DIR = resolve(__dirname, "..", "..", "..", "db");

/**
 * Global state for lifecycle management
 */
let piMemoryServer: PiMemoryServer | null = null;
let sessionActive = false;

/**
 * Initialize the pi-memory MCP server
 */
async function initialize(): Promise<void> {
  try {
    console.log("[pi-memory] Initializing server...");

    // DB lives in engine/db/ alongside all other project databases
    const config = {
      dbPath: join(PROJECT_DB_DIR, "agent_memory.db"),
      contextBudget: 8000,
      confidenceThreshold: 0.8,
      injectionMode: "selective" as const,
    };

    piMemoryServer = new PiMemoryServer(config);

    // Register lifecycle hooks
    piMemoryServer.onLifecycleHooks({
      sessionStart: async (cwd: string) => {
        sessionActive = true;
        console.log(`[pi-memory] Session started in: ${cwd}`);
      },

      beforeAgentRun: async (prompt: string, cwd: string) => {
        // Optionally add custom pre-agent logic
        console.log(
          `[pi-memory] Before agent run in: ${cwd} (${prompt.length} chars)`
        );
        return null; // Will use default context injection
      },

      agentEnd: async (messages: any[]) => {
        // Optionally add custom post-agent logic
        console.log(
          `[pi-memory] Agent ended with ${messages.length} messages`
        );
      },

      sessionShutdown: async () => {
        sessionActive = false;
        console.log("[pi-memory] Session shutdown triggered");
      },
    });

    console.log("[pi-memory] Server initialized successfully");
  } catch (error) {
    console.error("[pi-memory] Initialization failed:", error);
    process.exit(1);
  }
}

/**
 * Start the MCP server
 */
async function start(): Promise<void> {
  try {
    if (!piMemoryServer) {
      throw new Error("Server not initialized");
    }

    console.log("[pi-memory] Starting MCP server on stdio...");
    await piMemoryServer.start();
    console.log("[pi-memory] Server is running. Waiting for connections...");
  } catch (error) {
    console.error("[pi-memory] Failed to start server:", error);
    process.exit(1);
  }
}

/**
 * Handle graceful shutdown
 */
async function shutdown(): Promise<void> {
  try {
    console.log("[pi-memory] Shutting down...");

    if (piMemoryServer && sessionActive) {
      // Trigger session shutdown if still active
      await piMemoryServer.sessionShutdown();
    }

    console.log("[pi-memory] Shutdown complete");
    process.exit(0);
  } catch (error) {
    console.error("[pi-memory] Error during shutdown:", error);
    process.exit(1);
  }
}

/**
 * Example: Demonstrate server usage programmatically
 * This shows how to use the PiMemoryServer in code
 */
export async function demonstrateUsage(): Promise<void> {
  console.log("\n=== Pi-Memory Server Demonstration ===\n");

  try {
    // Create server instance
    const server = new PiMemoryServer({
      dbPath: join(PROJECT_DB_DIR, "agent_memory_demo.db"),
      contextBudget: 8000,
      confidenceThreshold: 0.8,
      injectionMode: "selective",
    });

    // Start session
    console.log("1. Starting session...");
    await server.sessionStart(process.cwd());

    // Build context for prompt
    console.log("2. Building context for sample prompt...");
    const context = await server.beforeAgentRun("How do I commit changes?");
    if (context) {
      console.log("   Context:", context.substring(0, 200) + "...");
    }

    // Simulate agent messages
    console.log("3. Simulating agent messages...");
    await server.agentEnd([
      { role: "user", content: "How do I commit with conventional commits?" },
      {
        role: "assistant",
        content: "Use: git commit -m 'type(scope): description'",
      },
    ]);

    // Shutdown session
    console.log("4. Shutting down session...");
    await server.sessionShutdown();

    console.log("\n✅ Demonstration complete\n");
  } catch (error) {
    console.error("❌ Demonstration failed:", error);
  }
}

/**
 * Main entry point
 */
async function main(): Promise<void> {
  // Parse command line arguments
  const args = process.argv.slice(2);

  if (args.includes("--demo")) {
    // Run demonstration mode
    await demonstrateUsage();
    return;
  }

  if (args.includes("--help")) {
    console.log(`
pi-memory MCP Server

Usage:
  npx tsx src/index.ts              Start the MCP server on stdio
  npx tsx src/index.ts --demo       Run a demonstration
  npx tsx src/index.ts --help       Show this help message

Environment Variables:
  PI_MEMORY_DB        Path to memory database
  PI_MEMORY_BUDGET    Context budget in characters (default: 8000)
  PI_MEMORY_CONFIDENCE  Min confidence threshold (default: 0.8)
  PI_MEMORY_MODE      Injection mode: 'selective' or 'fallback' (default: selective)
    `);
    return;
  }

  // Normal operation: start server
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);

  await initialize();
  await start();
}

// Run main entry point
main().catch((error) => {
  console.error("[pi-memory] Unexpected error:", error);
  process.exit(1);
});

// Export server for testing and programmatic use
export { PiMemoryServer };
export { MemoryStore };
export { NLPRouter, createNLPRouter };
export type {
  IntentType,
  ToolCall,
  RouteResult,
  ToolResult,
  ToolMap,
} from "./nlp-interface.js";

import { readFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { homedir } from "node:os";
import { MemoryStore, SemanticEntry, LessonEntry } from "./store.js";

// Dynamic imports for MCP SDK to handle version compatibility
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let Server: any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let StdioServerTransport: any;

try {
  const mcpSdk = require("@modelcontextprotocol/sdk");
  Server = mcpSdk.Server;
  const mcpStdio = require("@modelcontextprotocol/sdk/server/stdio");
  StdioServerTransport = mcpStdio.StdioServerTransport;
} catch {
  // MCP SDK will be available at runtime if this is run as a proper MCP server
  console.warn(
    "[pi-memory] Warning: MCP SDK not found at compile time. This is expected if dependencies aren't installed."
  );
}

/**
 * Configuration interface for PiMemoryServer
 */
export interface PiMemoryConfig {
  dbPath: string;
  contextBudget: number; // Max chars for injected context
  confidenceThreshold: number; // Min confidence to store facts (0.0-1.0)
  injectionMode: "selective" | "fallback"; // How to inject memory
}

/**
 * Path resolution configuration
 */
interface PathPlaceholders {
  PROJECT: string;
  TEAM: string;
  HOME: string;
}

/**
 * Lifecycle hooks for session management
 */
export interface LifecycleHooks {
  sessionStart?: (cwd: string) => Promise<void>;
  beforeAgentRun?: (prompt: string, cwd: string) => Promise<string | null>;
  agentEnd?: (messages: any[]) => Promise<void>;
  sessionShutdown?: () => Promise<void>;
}

/**
 * PiMemoryServer: MCP server with memory lifecycle integration
 *
 * Implements:
 * - 5 MCP tools for memory management
 * - 4 lifecycle hooks for session integration
 * - Config cascade loading (project → team → global)
 * - Selective injection of context based on relevance
 */
export class PiMemoryServer {
  private server: any;
  private store: MemoryStore | null = null;
  private config: PiMemoryConfig;
  private hooks: LifecycleHooks = {};
  private sessionCwd: string = process.cwd();
  private pendingMessages: {
    userMessages: string[];
    assistantMessages: string[];
  } = {
    userMessages: [],
    assistantMessages: [],
  };

  constructor(config?: Partial<PiMemoryConfig>) {
    this.server = new Server({
      name: "pi-memory",
      version: "1.0.0",
    });

    // Default config
    this.config = {
      dbPath: join(homedir(), ".pi", "memory", "memory.db"),
      contextBudget: 8000,
      confidenceThreshold: 0.8,
      injectionMode: "selective",
      ...config,
    };

    this.setupTools();
    this.setupErrorHandling();
  }

  /**
   * Setup MCP tools
   */
  private setupTools(): void {
    // Tool 1: memory_search
    this.server.setRequestHandler(
      "tools/call",
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      async (request: any) => {
        if (!this.store) {
          throw new Error("MemoryStore not initialized");
        }

        const { name, arguments: args } = request.params;

        switch (name) {
          case "memory_search":
            return this.handleMemorySearch(args as { query: string });

          case "memory_remember":
            return this.handleMemoryRemember(args as {
              key: string;
              value: string;
              confidence?: number;
            });

          case "memory_forget":
            return this.handleMemoryForget(args as { key: string });

          case "memory_lessons":
            return this.handleMemoryLessons(args as { category?: string });

          case "memory_stats":
            return this.handleMemoryStats();

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      }
    );

    // Define tools for discovery
    this.server.setRequestHandler("tools/list", async () => {
      return {
        tools: this.getToolDefinitions(),
      };
    });
  }

  /**
   * Get MCP tool definitions
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private getToolDefinitions(): any[] {
    return [
      {
        name: "memory_search",
        description:
          "Search semantic memory by keyword. Returns top matching facts with confidence scores.",
        inputSchema: {
          type: "object" as const,
          properties: {
            query: {
              type: "string",
              description: "Search query (e.g., 'commit style', 'database')",
            },
          },
          required: ["query"],
        },
      },
      {
        name: "memory_remember",
        description:
          "Add or update a fact in semantic memory. Useful for explicit corrections or user-provided preferences.",
        inputSchema: {
          type: "object" as const,
          properties: {
            key: {
              type: "string",
              description:
                "Fact key (e.g., 'pref.commit_style', 'project.rosie.language')",
            },
            value: {
              type: "string",
              description: "Fact value (e.g., 'conventional commits')",
            },
            confidence: {
              type: "number",
              description:
                "Confidence score (0.0-1.0, default 0.8). Higher = more trusted.",
              minimum: 0,
              maximum: 1,
            },
          },
          required: ["key", "value"],
        },
      },
      {
        name: "memory_forget",
        description: "Delete a fact from semantic memory by key.",
        inputSchema: {
          type: "object" as const,
          properties: {
            key: {
              type: "string",
              description:
                "Fact key to delete (e.g., 'pref.commit_style')",
            },
          },
          required: ["key"],
        },
      },
      {
        name: "memory_lessons",
        description:
          "List learned corrections and validated approaches. Optionally filter by category.",
        inputSchema: {
          type: "object" as const,
          properties: {
            category: {
              type: "string",
              description:
                "Filter by category (e.g., 'vault', 'git', 'security'). Omit to show all.",
            },
          },
          required: [],
        },
      },
      {
        name: "memory_stats",
        description: "Get memory statistics: total facts, lessons, and events.",
        inputSchema: {
          type: "object" as const,
          properties: {},
          required: [],
        },
      },
    ];
  }

  /**
   * Handle memory_search tool call
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private async handleMemorySearch(args: {
    query: string;
  }): Promise<any> {
    if (!this.store) {
      throw new Error("MemoryStore not initialized");
    }

    try {
      const { query } = args;
      const facts = this.store.listFacts(undefined, 10);

      // Simple keyword matching (in real implementation, would use FTS or semantic search)
      const queryLower = query.toLowerCase();
      const matches = facts.filter(
        (f) =>
          f.key.toLowerCase().includes(queryLower) ||
          f.value.toLowerCase().includes(queryLower)
      );

      if (matches.length === 0) {
        return {
          content: [
            {
              type: "text",
              text: `No facts found matching "${query}"`,
            },
          ],
        };
      }

      const results = matches.map((f) => `• ${f.key}: ${f.value} (${f.confidence})`).join("\n");

      return {
        content: [
          {
            type: "text",
            text: `Found ${matches.length} fact(s):\n${results}`,
          },
        ],
      };
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      return {
        content: [
          {
            type: "text",
            text: `Error searching memory: ${msg}`,
            isError: true,
          },
        ],
      };
    }
  }

  /**
   * Handle memory_remember tool call
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private async handleMemoryRemember(args: {
    key: string;
    value: string;
    confidence?: number;
  }): Promise<any> {
    if (!this.store) {
      throw new Error("MemoryStore not initialized");
    }

    try {
      const { key, value, confidence = 0.8 } = args;

      if (confidence < this.config.confidenceThreshold) {
        return {
          content: [
            {
              type: "text",
              text: `Confidence ${confidence} below threshold ${this.config.confidenceThreshold}. Fact not stored.`,
            },
          ],
        };
      }

      this.store.addFact(key, value, confidence, undefined, "user");

      return {
        content: [
          {
            type: "text",
            text: `Remembered: ${key} = "${value}" (confidence: ${confidence})`,
          },
        ],
      };
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      return {
        content: [
          {
            type: "text",
            text: `Error remembering fact: ${msg}`,
            isError: true,
          },
        ],
      };
    }
  }

  /**
   * Handle memory_forget tool call
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private async handleMemoryForget(args: {
    key: string;
  }): Promise<any> {
    if (!this.store) {
      throw new Error("MemoryStore not initialized");
    }

    try {
      const { key } = args;
      const deleted = this.store.deleteFact(key);

      if (deleted) {
        return {
          content: [
            {
              type: "text",
              text: `Forgot: ${key}`,
            },
          ],
        };
      } else {
        return {
          content: [
            {
              type: "text",
              text: `Fact not found: ${key}`,
            },
          ],
        };
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      return {
        content: [
          {
            type: "text",
            text: `Error forgetting fact: ${msg}`,
            isError: true,
          },
        ],
      };
    }
  }

  /**
   * Handle memory_lessons tool call
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private async handleMemoryLessons(args: {
    category?: string;
  }): Promise<any> {
    if (!this.store) {
      throw new Error("MemoryStore not initialized");
    }

    try {
      const { category } = args;
      const lessons = this.store.listLessons(category, undefined, 20);

      if (lessons.length === 0) {
        const msg = category
          ? `No lessons found in category: ${category}`
          : "No lessons found";
        return {
          content: [
            {
              type: "text",
              text: msg,
            },
          ],
        };
      }

      const formatted = lessons
        .map((l) => {
          const sign = l.negative ? "❌ DON'T:" : "✅ DO:";
          const cat = l.category ? ` [${l.category}]` : "";
          return `${sign}${cat} ${l.text}`;
        })
        .join("\n");

      return {
        content: [
          {
            type: "text",
            text: `Lessons (${lessons.length}):\n${formatted}`,
          },
        ],
      };
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      return {
        content: [
          {
            type: "text",
            text: `Error retrieving lessons: ${msg}`,
            isError: true,
          },
        ],
      };
    }
  }

  /**
   * Handle memory_stats tool call
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private async handleMemoryStats(): Promise<any> {
    if (!this.store) {
      throw new Error("MemoryStore not initialized");
    }

    try {
      const stats = this.store.getStats();

      return {
        content: [
          {
            type: "text",
            text: `Memory Statistics:
• Semantic facts: ${stats.semantic}
• Lessons learned: ${stats.lessons}
• Audit events: ${stats.events}
• Database: ${this.config.dbPath}
• Config mode: ${this.config.injectionMode}
• Confidence threshold: ${this.config.confidenceThreshold}`,
          },
        ],
      };
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      return {
        content: [
          {
            type: "text",
            text: `Error getting stats: ${msg}`,
            isError: true,
          },
        ],
      };
    }
  }

  /**
   * Setup error handling
   */
  private setupErrorHandling(): void {
    this.server.onClose = () => {
      if (this.store) {
        this.store.close();
      }
    };
  }

  /**
   * Load config with cascade: project-local → team-local → global
   */
  private loadConfig(cwd: string): PiMemoryConfig {
    const placeholders: PathPlaceholders = {
      PROJECT: cwd,
      TEAM: join(cwd, "../.."),
      HOME: homedir(),
    };

    // Try project-local config
    try {
      const projectConfig = this.loadConfigFile(
        join(cwd, ".pi", "config.json"),
        placeholders
      );
      if (projectConfig) {
        return { ...this.config, ...projectConfig };
      }
    } catch {
      // Continue to next level
    }

    // Try team-local config
    try {
      const teamConfig = this.loadConfigFile(
        join(cwd, "../../.pi", "config.json"),
        placeholders
      );
      if (teamConfig) {
        return { ...this.config, ...teamConfig };
      }
    } catch {
      // Continue to next level
    }

    // Try global config
    try {
      const globalConfig = this.loadConfigFile(
        join(homedir(), ".pi", "config.json"),
        placeholders
      );
      if (globalConfig) {
        return { ...this.config, ...globalConfig };
      }
    } catch {
      // Use defaults
    }

    return this.config;
  }

  /**
   * Load config file and resolve path placeholders
   */
  private loadConfigFile(
    filePath: string,
    placeholders: PathPlaceholders
  ): Partial<PiMemoryConfig> | null {
    if (!existsSync(filePath)) {
      return null;
    }

    try {
      const content = readFileSync(filePath, "utf-8");
      const parsed = JSON.parse(content);

      // Resolve path placeholders
      if (parsed.dbPath && typeof parsed.dbPath === "string") {
        parsed.dbPath = this.resolvePath(parsed.dbPath, placeholders);
      }

      return parsed;
    } catch (error) {
      throw new Error(`Failed to load config from ${filePath}: ${error}`);
    }
  }

  /**
   * Resolve path with placeholders
   */
  private resolvePath(path: string, placeholders: PathPlaceholders): string {
    let resolved = path;

    // Replace placeholders
    resolved = resolved.replace("${PROJECT}", placeholders.PROJECT);
    resolved = resolved.replace("${TEAM}", placeholders.TEAM);
    resolved = resolved.replace("${HOME}", placeholders.HOME);

    // Resolve to absolute path
    return resolve(resolved);
  }

  /**
   * Register lifecycle hooks
   */
  public onLifecycleHooks(hooks: Partial<LifecycleHooks>): void {
    this.hooks = { ...this.hooks, ...hooks };
  }

  /**
   * Lifecycle: Session start
   * Initialize MemoryStore and load/inject memory
   */
  public async sessionStart(cwd: string = process.cwd()): Promise<void> {
    this.sessionCwd = cwd;

    // Load config with cascade
    const config = this.loadConfig(cwd);
    this.config = { ...this.config, ...config };

    // Initialize MemoryStore
    this.store = new MemoryStore();
    this.store.initialize({
      dbPath: this.config.dbPath,
      logFn: (msg) => console.log(`[pi-memory] ${msg}`),
    });

    // Call user-defined hook
    if (this.hooks.sessionStart) {
      await this.hooks.sessionStart(cwd);
    }

    const stats = this.store.getStats();
    console.log(
      `📚 Memory loaded: ${stats.semantic} facts, ${stats.lessons} lessons`
    );
  }

  /**
   * Lifecycle: Before agent run
   * Build and inject context from memory
   */
  public async beforeAgentRun(prompt: string): Promise<string | null> {
    if (!this.store) {
      throw new Error("MemoryStore not initialized");
    }

    try {
      // Build context block based on prompt relevance
      const contextLines: string[] = [];
      let charCount = 0;

      // Get relevant facts
      const facts = this.store.listFacts(undefined, 20);
      const relevantFacts = facts.slice(0, 10); // Simplified: would use semantic search in production

      // Add facts
      for (const fact of relevantFacts) {
        const line = `• ${fact.key}: ${fact.value}`;
        if (charCount + line.length > this.config.contextBudget) {
          break;
        }
        contextLines.push(line);
        charCount += line.length;
      }

      // Add lessons
      if (charCount < this.config.contextBudget * 0.8) {
        const lessons = this.store.listLessons(undefined, undefined, 10);
        for (const lesson of lessons) {
          const sign = lesson.negative ? "❌ DON'T:" : "✅ DO:";
          const line = `${sign} ${lesson.text}`;
          if (charCount + line.length > this.config.contextBudget) {
            break;
          }
          contextLines.push(line);
          charCount += line.length;
        }
      }

      // Build context block
      const contextBlock =
        contextLines.length > 0
          ? `<memory>\n${contextLines.join("\n")}\n</memory>\n\n`
          : "";

      // Call user-defined hook
      if (this.hooks.beforeAgentRun) {
        const customContext = await this.hooks.beforeAgentRun(
          prompt,
          this.sessionCwd
        );
        return customContext ? customContext + contextBlock : contextBlock;
      }

      return contextBlock;
    } catch (error) {
      console.error("Error building context:", error);
      return null;
    }
  }

  /**
   * Lifecycle: Agent end
   * Collect messages for later consolidation
   */
  public async agentEnd(messages: any[]): Promise<void> {
    try {
      // Extract messages from various formats
      for (const msg of messages) {
        if (typeof msg === "string") {
          this.pendingMessages.userMessages.push(msg);
        } else if (msg.role === "user" && msg.content) {
          const content =
            typeof msg.content === "string"
              ? msg.content
              : JSON.stringify(msg.content);
          this.pendingMessages.userMessages.push(content);
        } else if (msg.role === "assistant" && msg.content) {
          const content =
            typeof msg.content === "string"
              ? msg.content
              : JSON.stringify(msg.content);
          this.pendingMessages.assistantMessages.push(content);
        }
      }

      // Call user-defined hook
      if (this.hooks.agentEnd) {
        await this.hooks.agentEnd(messages);
      }
    } catch (error) {
      console.error("Error in agentEnd hook:", error);
    }
  }

  /**
   * Lifecycle: Session shutdown
   * Trigger consolidation and store learned facts
   */
  public async sessionShutdown(): Promise<void> {
    if (!this.store) {
      throw new Error("MemoryStore not initialized");
    }

    try {
      // Only consolidate if we have enough messages
      const totalMessages =
        this.pendingMessages.userMessages.length +
        this.pendingMessages.assistantMessages.length;

      if (totalMessages < 3) {
        console.log(
          `⏭️  Session too short (${totalMessages} messages). Skipping consolidation.`
        );
        this.store.close();
        return;
      }

      console.log(`🔄 Consolidating ${totalMessages} messages from session...`);

      // In a real implementation, this would call an LLM to extract knowledge
      // For now, we just log the pending messages
      console.log(
        `💾 Pending consolidation: ${this.pendingMessages.userMessages.length} user messages, ${this.pendingMessages.assistantMessages.length} assistant messages`
      );

      // Call user-defined hook
      if (this.hooks.sessionShutdown) {
        await this.hooks.sessionShutdown();
      }

      // Reset pending messages
      this.pendingMessages = {
        userMessages: [],
        assistantMessages: [],
      };

      // Close store
      this.store.close();
      console.log("✅ Session shutdown complete");
    } catch (error) {
      console.error("Error in sessionShutdown:", error);
      if (this.store) {
        this.store.close();
      }
    }
  }

  /**
   * Get the MCP server instance
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  public getServer(): any {
    return this.server;
  }

  /**
   * Start the MCP server with stdio transport
   */
  public async start(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.log("[pi-memory] MCP server started");
  }
}

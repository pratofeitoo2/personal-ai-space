#!/usr/bin/env node

/**
 * pi-memory Demo CLI: Interactive demonstration and testing interface
 *
 * Features:
 * - Run pre-built playground demonstrations
 * - Interactive REPL for testing custom queries
 * - Export memory state to JSON
 * - Compare tool calling vs natural language approaches
 *
 * Usage:
 *   npx tsx src/demo-cli.ts              Run playground demos
 *   npx tsx src/demo-cli.ts --interactive    Interactive mode
 *   npx tsx src/demo-cli.ts --export     Export current state
 *
 * Interactive Commands:
 *   add-fact <key> <value> [confidence] [category]    Add a new fact
 *   search <query>                                     Search facts
 *   list-facts                                         List all facts
 *   add-lesson <text> [negative] [category]           Add a lesson
 *   list-lessons                                       List all lessons
 *   context [query]                                    Build context block
 *   stats                                              Show memory statistics
 *   export                                             Export to JSON
 *   help                                               Show commands
 *   exit                                               Exit interactive mode
 */

import { MemoryStore } from "./store.js";
import { Injector } from "./injector.js";
import { Playground, runPlayground } from "./playground.js";
import { join } from "node:path";
import { homedir, tmpdir } from "node:os";
import { createReadStream, createWriteStream, existsSync } from "node:fs";
import { createInterface } from "node:readline";

/**
 * Demo CLI: Command-line interface for pi-memory demonstrations
 */
class DemoCli {
  private store: MemoryStore;
  private injector: Injector;
  private workingDb: string;
  private isInteractive: boolean = false;

  constructor(dbPath?: string) {
    this.workingDb = dbPath || join(tmpdir(), `pi-memory-demo-${Date.now()}.db`);
    this.store = new MemoryStore();
    this.injector = new Injector(this.store, {
      contextBudget: 8000,
      minConfidence: 0.7,
      injectionMode: "selective",
    });
  }

  /**
   * Initialize the store
   */
  async initialize(): Promise<void> {
    this.store.initialize({
      dbPath: this.workingDb,
      logFn: (msg) => {
        if (this.isInteractive) {
          // Silence logs in interactive mode
        }
      },
    });
  }

  /**
   * Show help message
   */
  showHelp(): void {
    console.log(`
╔════════════════════════════════════════════════════════════════╗
║           π Memory Clone - Demo CLI Help                       ║
╚════════════════════════════════════════════════════════════════╝

Commands:
  add-fact <key> <value> [confidence] [category]
    Add a semantic fact to memory
    Example: add-fact pref.editor "VS Code" 0.95 "Preferences"

  search <query>
    Search for facts by natural language query
    Example: search "editor preferences"

  list-facts [prefix]
    List all facts, optionally filter by key prefix
    Example: list-facts pref

  get-fact <key>
    Retrieve a specific fact by key
    Example: get-fact pref.editor

  delete-fact <key>
    Delete a fact from memory
    Example: delete-fact pref.editor

  add-lesson <text> [negative] [category]
    Add a lesson (0=validation, 1=correction)
    Example: add-lesson "Always validate input" 0 "Best Practices"

  list-lessons [category]
    List all lessons, optionally filter by category
    Example: list-lessons

  context [query]
    Build and display context injection block
    Example: context "editor setup"

  stats
    Show memory store statistics

  export [path]
    Export memory state to JSON
    Example: export memory-backup.json

  compare-approaches <scenario>
    Compare tool calling vs natural language approaches
    Example: compare-approaches "developer setup"

  help
    Show this help message

  clear
    Clear all facts and lessons

  exit / quit
    Exit interactive mode
    `);
  }

  /**
   * Add a fact via CLI
   */
  async addFact(args: string[]): Promise<void> {
    if (args.length < 2) {
      console.error("❌ Usage: add-fact <key> <value> [confidence] [category]");
      return;
    }

    const [key, value, confStr, category] = args;
    const confidence = confStr ? parseFloat(confStr) : 0.8;

    if (isNaN(confidence) || confidence < 0 || confidence > 1) {
      console.error("❌ Confidence must be a number between 0 and 1");
      return;
    }

    try {
      this.store.addFact(key, value, confidence, category);
      console.log(`✓ Added fact: ${key}`);
      console.log(`  Value: ${value}`);
      console.log(`  Confidence: ${Math.round(confidence * 100)}%`);
      if (category) console.log(`  Category: ${category}`);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error(`❌ Error: ${msg}`);
    }
  }

  /**
   * Search facts
   */
  async searchFacts(query: string): Promise<void> {
    if (!query.trim()) {
      console.error("❌ Please provide a search query");
      return;
    }

    try {
      const results = this.injector.searchFacts(query, 10);
      console.log(`\n📊 Search results for: "${query}"\n`);

      if (results.length === 0) {
        console.log("  No relevant facts found.");
        return;
      }

      for (const result of results) {
        const relevance = Math.round(result.relevance * 100);
        const confidence = Math.round(result.entry.confidence * 100);
        console.log(`  ◆ ${result.entry.key}`);
        console.log(`    Value: ${result.entry.value}`);
        console.log(`    Relevance: ${relevance}% | Confidence: ${confidence}%`);
        console.log("");
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error(`❌ Error: ${msg}`);
    }
  }

  /**
   * List facts
   */
  async listFacts(prefix?: string): Promise<void> {
    try {
      const facts = this.store.listFacts(prefix, 50, "confidence");
      console.log(`\n📚 Facts (${facts.length} total)${prefix ? ` [prefix: ${prefix}]` : ""}\n`);

      if (facts.length === 0) {
        console.log("  No facts found.");
        return;
      }

      for (const fact of facts) {
        const confidence = Math.round(fact.confidence * 100);
        console.log(`  • ${fact.key}`);
        console.log(`    ${fact.value}`);
        console.log(`    Confidence: ${confidence}%${fact.category ? ` | Category: ${fact.category}` : ""}`);
        console.log("");
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error(`❌ Error: ${msg}`);
    }
  }

  /**
   * Get a specific fact
   */
  async getFact(key: string): Promise<void> {
    try {
      const fact = this.store.getFact(key);
      if (!fact) {
        console.log(`❌ Fact not found: ${key}`);
        return;
      }

      console.log(`\n✓ Fact: ${key}`);
      console.log(`  Value: ${fact.value}`);
      console.log(`  Confidence: ${Math.round(fact.confidence * 100)}%`);
      console.log(`  Category: ${fact.category || "none"}`);
      console.log(`  Source: ${fact.source}`);
      console.log(`  Created: ${fact.created_at}`);
      console.log(`  Updated: ${fact.updated_at}`);
      console.log(`  Last accessed: ${fact.last_accessed || "never"}`);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error(`❌ Error: ${msg}`);
    }
  }

  /**
   * Delete a fact
   */
  async deleteFact(key: string): Promise<void> {
    try {
      const deleted = this.store.deleteFact(key);
      if (deleted) {
        console.log(`✓ Deleted fact: ${key}`);
      } else {
        console.log(`❌ Fact not found: ${key}`);
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error(`❌ Error: ${msg}`);
    }
  }

  /**
   * Add a lesson
   */
  async addLesson(args: string[]): Promise<void> {
    if (args.length < 1) {
      console.error("❌ Usage: add-lesson <text> [negative] [category]");
      return;
    }

    const [text, negStr, category] = args;
    const negative: 0 | 1 = negStr === "1" ? 1 : 0;

    try {
      this.store.addLesson(text, negative, category);
      const type = negative === 1 ? "correction" : "validation";
      console.log(`✓ Added lesson (${type})`);
      console.log(`  Text: ${text}`);
      if (category) console.log(`  Category: ${category}`);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error(`❌ Error: ${msg}`);
    }
  }

  /**
   * List lessons
   */
  async listLessons(category?: string): Promise<void> {
    try {
      const lessons = this.store.listLessons(category, undefined, 50);
      console.log(`\n📖 Lessons (${lessons.length} total)${category ? ` [category: ${category}]` : ""}\n`);

      if (lessons.length === 0) {
        console.log("  No lessons found.");
        return;
      }

      const corrections = lessons.filter((l) => l.negative === 1);
      const validations = lessons.filter((l) => l.negative === 0);

      if (corrections.length > 0) {
        console.log("  ⚠ Corrections (learned from mistakes):");
        for (const lesson of corrections) {
          console.log(`    • ${lesson.text}`);
          if (lesson.used_count > 0) console.log(`      Used: ${lesson.used_count}x`);
        }
        console.log("");
      }

      if (validations.length > 0) {
        console.log("  ✓ Validations (best practices):");
        for (const lesson of validations) {
          console.log(`    • ${lesson.text}`);
          if (lesson.used_count > 0) console.log(`      Used: ${lesson.used_count}x`);
        }
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error(`❌ Error: ${msg}`);
    }
  }

  /**
   * Build context block
   */
  async buildContext(query?: string): Promise<void> {
    try {
      const block = this.injector.buildContextBlock({ query });
      console.log(
        `\n📋 Context Block${query ? ` [query: "${query}"]` : ""}:\n`
      );
      console.log(block.text);
      console.log(
        `\nStats: ${block.stats.semanticCount} facts, ${block.stats.lessonCount} lessons, ${block.stats.totalCharacters} chars`
      );
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error(`❌ Error: ${msg}`);
    }
  }

  /**
   * Show statistics
   */
  async showStats(): Promise<void> {
    try {
      const stats = this.store.getStats();
      console.log(`\n📊 Memory Store Statistics:\n`);
      console.log(`  Semantic facts: ${stats.semantic}`);
      console.log(`  Lessons learned: ${stats.lessons}`);
      console.log(`  Audit events: ${stats.events}`);

      if (stats.semantic > 0) {
        const facts = this.store.listFacts(undefined, 1, "confidence");
        if (facts.length > 0) {
          const avgConfidence = Math.round(
            (facts.reduce((sum, f) => sum + f.confidence, 0) / facts.length) * 100
          );
          console.log(`  Avg confidence: ~${avgConfidence}%`);
        }
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error(`❌ Error: ${msg}`);
    }
  }

  /**
   * Export memory to JSON
   */
  async exportMemory(path?: string): Promise<void> {
    try {
      const exportPath =
        path || join(process.cwd(), `memory-export-${Date.now()}.json`);

      const facts = this.store.listFacts(undefined, 1000);
      const lessons = this.store.listLessons(undefined, undefined, 1000);
      const stats = this.store.getStats();

      const exportData = {
        timestamp: new Date().toISOString(),
        statistics: stats,
        facts: facts.map((f) => ({
          key: f.key,
          value: f.value,
          confidence: f.confidence,
          category: f.category,
          source: f.source,
          createdAt: f.created_at,
          updatedAt: f.updated_at,
        })),
        lessons: lessons.map((l) => ({
          id: l.id,
          text: l.text,
          category: l.category,
          type: l.negative === 1 ? "correction" : "validation",
          source: l.source,
          createdAt: l.created_at,
          usedCount: l.used_count,
        })),
      };

      const fs = require("node:fs");
      fs.writeFileSync(exportPath, JSON.stringify(exportData, null, 2));
      console.log(`✓ Exported to: ${exportPath}`);
      console.log(`  Facts: ${facts.length}`);
      console.log(`  Lessons: ${lessons.length}`);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error(`❌ Error: ${msg}`);
    }
  }

  /**
   * Compare tool calling vs natural language
   */
  async compareApproaches(scenario: string): Promise<void> {
    console.log(
      `\n📊 Comparing Tool Calling vs Natural Language for: "${scenario}"\n`
    );

    // Pre-populate with context
    const context = [
      {
        key: "project.framework",
        value: "Express.js with TypeScript",
        confidence: 0.95,
      },
      {
        key: "project.database",
        value: "PostgreSQL with Knex migrations",
        confidence: 0.93,
      },
      {
        key: "tool.testing",
        value: "Jest with supertest",
        confidence: 0.90,
      },
    ];

    for (const fact of context) {
      this.store.addFact(fact.key, fact.value, fact.confidence);
    }

    // Approach 1: Direct tool calls
    console.log("1️⃣  TOOL CALLING APPROACH");
    console.log("   Commands:");
    console.log("   → search_facts('express database setup')");
    console.log("   → get_context_block(query='database')");
    console.log("   → add_fact('project.patterns', 'Repository pattern', 0.85)");

    const toolResults = this.injector.searchFacts("express database setup", 5);
    console.log(`\n   Result: Found ${toolResults.length} relevant facts`);

    // Approach 2: Natural language query
    console.log("\n2️⃣  NATURAL LANGUAGE APPROACH");
    console.log(`   Query: "How should I set up the ${scenario}?"`);

    const nlQuery = `How should I set up the ${scenario}?`;
    const nlResults = this.injector.searchFacts(nlQuery, 5);
    const nlContext = this.injector.buildContextBlock({ query: nlQuery });

    console.log(`\n   Result: Found ${nlResults.length} relevant facts`);
    console.log(`   Context size: ${nlContext.text.length} chars`);
    console.log(`   Context includes: ${nlContext.stats.semanticCount} facts\n`);

    // Comparison
    console.log("📈 COMPARISON:");
    console.log(
      `   Tool approach: Precise, requires explicit commands, predictable`
    );
    console.log(
      `   NL approach: Flexible, requires less setup, context-aware\n`
    );
  }

  /**
   * Clear all data
   */
  async clear(): Promise<void> {
    const allFacts = this.store.listFacts(undefined, 10000);
    const allLessons = this.store.listLessons(undefined, undefined, 10000);

    for (const fact of allFacts) {
      this.store.deleteFact(fact.key);
    }

    for (const lesson of allLessons) {
      this.store.deleteLesson(lesson.id);
    }

    console.log(
      `✓ Cleared memory: ${allFacts.length} facts and ${allLessons.length} lessons deleted`
    );
  }

  /**
   * Process a CLI command
   */
  async processCommand(input: string): Promise<boolean> {
    const [command, ...args] = input.trim().split(/\s+/);

    switch (command) {
      case "add-fact":
        await this.addFact(args);
        break;
      case "search":
        await this.searchFacts(args.join(" "));
        break;
      case "list-facts":
        await this.listFacts(args[0]);
        break;
      case "get-fact":
        await this.getFact(args[0]);
        break;
      case "delete-fact":
        await this.deleteFact(args[0]);
        break;
      case "add-lesson":
        await this.addLesson(args);
        break;
      case "list-lessons":
        await this.listLessons(args[0]);
        break;
      case "context":
        await this.buildContext(args.join(" "));
        break;
      case "stats":
        await this.showStats();
        break;
      case "export":
        await this.exportMemory(args[0]);
        break;
      case "compare-approaches":
        await this.compareApproaches(args.join(" "));
        break;
      case "clear":
        await this.clear();
        break;
      case "help":
        this.showHelp();
        break;
      case "exit":
      case "quit":
        console.log("\n👋 Goodbye!\n");
        return false;
      default:
        if (command) {
          console.error(`❌ Unknown command: ${command}. Type 'help' for available commands.`);
        }
    }

    return true;
  }

  /**
   * Interactive REPL mode
   */
  async interactiveMode(): Promise<void> {
    this.isInteractive = true;

    console.log(`
╔════════════════════════════════════════════════════════════════╗
║              π Memory Clone - Interactive Mode                 ║
╚════════════════════════════════════════════════════════════════╝

Type 'help' for available commands
    `);

    const rl = createInterface({
      input: process.stdin,
      output: process.stdout,
      prompt: "π> ",
    });

    rl.prompt();

    rl.on("line", async (input: string) => {
      const shouldContinue = await this.processCommand(input);
      if (shouldContinue) {
        rl.prompt();
      } else {
        rl.close();
      }
    });

    rl.on("close", () => {
      this.cleanup();
      process.exit(0);
    });
  }

  /**
   * Run playground demonstrations
   */
  async runPlayground(verbose: boolean = false): Promise<void> {
    console.log("Launching playground...\n");
    await runPlayground(verbose);
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    try {
      if (this.store.isReady()) {
        this.store.close();
      }
    } catch (error) {
      // Silently ignore cleanup errors
    }
  }
}

/**
 * Main CLI entry point
 */
async function main(): Promise<void> {
  const args = process.argv.slice(2);

  const cli = new DemoCli();
  await cli.initialize();

  if (args.includes("--interactive") || args.includes("-i")) {
    await cli.interactiveMode();
  } else if (args.includes("--playground") || args.includes("-p")) {
    const verbose = args.includes("--verbose") || args.includes("-v");
    await cli.runPlayground(verbose);
  } else if (args.includes("--help") || args.includes("-h")) {
    cli.showHelp();
  } else {
    // Default: run playground
    await cli.runPlayground(false);
  }

  cli.cleanup();
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});

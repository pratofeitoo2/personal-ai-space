#!/usr/bin/env node

import * as readline from "readline";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { MemoryStore, SemanticEntry, LessonEntry } from "./store.js";
import { Injector, SearchResult } from "./injector.js";

/**
 * Type definitions for CLI commands
 */
interface CommandResult {
  type: "success" | "error" | "info";
  message: string;
  data?: unknown;
}

interface ParsedCommand {
  type:
    | "search"
    | "remember"
    | "lessons"
    | "stats"
    | "help"
    | "export"
    | "clear"
    | "config"
    | "quit"
    | "unknown";
  args?: string[];
  rawInput: string;
}

/**
 * Simple NLP router for parsing natural language commands
 */
class SimpleNLPRouter {
  /**
   * Parse user input into structured commands
   */
  public parse(input: string): ParsedCommand {
    const trimmed = input.trim().toLowerCase();

    // Special commands
    if (
      trimmed === "help" ||
      trimmed === "?" ||
      trimmed.startsWith("help ")
    ) {
      return {
        type: "help",
        rawInput: input,
        args: trimmed === "help" || trimmed === "?" ? [] : trimmed.slice(5).split(" "),
      };
    }

    if (trimmed === "quit" || trimmed === "exit") {
      return { type: "quit", rawInput: input };
    }

    if (trimmed === "clear" || trimmed === "reset") {
      return { type: "clear", rawInput: input };
    }

    if (trimmed === "config" || trimmed === "settings") {
      return { type: "config", rawInput: input };
    }

    if (trimmed === "export" || trimmed === "save") {
      return { type: "export", rawInput: input };
    }

    if (trimmed === "stats" || trimmed === "statistics" || trimmed === "summary") {
      return { type: "stats", rawInput: input };
    }

    // Search commands: "search ...", "find ...", "lookup ...", "what is ...", "tell me about ..."
    if (
      trimmed.startsWith("search ") ||
      trimmed.startsWith("find ") ||
      trimmed.startsWith("lookup ") ||
      trimmed.startsWith("what ") ||
      trimmed.startsWith("tell me about ")
    ) {
      let query = "";
      if (trimmed.startsWith("search ")) query = trimmed.slice(7);
      else if (trimmed.startsWith("find ")) query = trimmed.slice(5);
      else if (trimmed.startsWith("lookup ")) query = trimmed.slice(7);
      else if (trimmed.startsWith("what ")) query = trimmed.slice(5);
      else if (trimmed.startsWith("tell me about ")) query = trimmed.slice(14);

      return {
        type: "search",
        args: [query],
        rawInput: input,
      };
    }

    // Remember/save commands: "remember ...", "save ...", "note ...", "remember that ...", "i should ..."
    if (
      trimmed.startsWith("remember ") ||
      trimmed.startsWith("save ") ||
      trimmed.startsWith("note ") ||
      trimmed.startsWith("i should ") ||
      trimmed.startsWith("remember that ")
    ) {
      let text = "";
      if (trimmed.startsWith("remember that ")) text = trimmed.slice(14);
      else if (trimmed.startsWith("remember ")) text = trimmed.slice(9);
      else if (trimmed.startsWith("save ")) text = trimmed.slice(5);
      else if (trimmed.startsWith("note ")) text = trimmed.slice(5);
      else if (trimmed.startsWith("i should ")) text = trimmed.slice(9);

      return {
        type: "remember",
        args: [text],
        rawInput: input,
      };
    }

    // Lesson commands: "lesson: ...", "avoid: ...", "learned: ...", "don't ...", "never ..."
    if (
      trimmed.startsWith("lesson:") ||
      trimmed.startsWith("avoid:") ||
      trimmed.startsWith("learned:") ||
      trimmed.startsWith("don't ") ||
      trimmed.startsWith("never ")
    ) {
      let text = "";
      let negative = false;

      if (trimmed.startsWith("lesson:")) text = trimmed.slice(7).trim();
      else if (trimmed.startsWith("avoid:")) {
        text = trimmed.slice(6).trim();
        negative = true;
      } else if (trimmed.startsWith("learned:")) text = trimmed.slice(8).trim();
      else if (trimmed.startsWith("don't ")) {
        text = trimmed.slice(6).trim();
        negative = true;
      } else if (trimmed.startsWith("never ")) {
        text = trimmed.slice(6).trim();
        negative = true;
      }

      return {
        type: "lessons",
        args: [text, negative ? "negative" : "positive"],
        rawInput: input,
      };
    }

    return {
      type: "unknown",
      rawInput: input,
    };
  }
}

/**
 * Output formatting utilities
 */
class OutputFormatter {
  /**
   * Format search results as a table
   */
  public static formatSearchResults(results: SearchResult[]): string {
    if (results.length === 0) {
      return "No results found.";
    }

    let output = "\n📋 Search Results:\n";
    output += "─".repeat(80) + "\n";

    results.forEach((result, index) => {
      const entry = result.entry;
      const confidence = Math.round(entry.confidence * 100);
      const relevance = Math.round(result.relevance * 100);
      const category = entry.category ? ` [${entry.category}]` : "";

      output += `${index + 1}. ${entry.key}${category}\n`;
      output += `   Value: ${entry.value}\n`;
      output += `   Confidence: ${confidence}% | Relevance: ${relevance}%\n`;

      if (entry.last_accessed) {
        output += `   Last accessed: ${this.formatDate(entry.last_accessed)}\n`;
      }
      output += "\n";
    });

    output += "─".repeat(80);
    return output;
  }

  /**
   * Format memory stats with simple bar chart
   */
  public static formatStats(facts: number, lessons: number, events: number): string {
    const maxWidth = 50;

    const factBar = this.drawBar(facts, Math.max(facts, lessons, 1), maxWidth);
    const lessonBar = this.drawBar(lessons, Math.max(facts, lessons, 1), maxWidth);
    const eventBar = this.drawBar(events, Math.max(events, 1), maxWidth);

    let output = "\n📊 Memory Statistics:\n";
    output += "─".repeat(80) + "\n";
    output += `Facts:    ${factBar} ${facts}\n`;
    output += `Lessons:  ${lessonBar} ${lessons}\n`;
    output += `Events:   ${eventBar} ${events}\n`;
    output += "─".repeat(80);

    return output;
  }

  /**
   * Format lessons as a formatted list
   */
  public static formatLessons(lessons: LessonEntry[]): string {
    if (lessons.length === 0) {
      return "No lessons learned yet.";
    }

    let output = "\n💡 Learned Lessons:\n";
    output += "─".repeat(80) + "\n";

    lessons.forEach((lesson, index) => {
      const prefix = lesson.negative ? "❌ Avoid:" : "✅ Do:";
      const category = lesson.category ? ` [${lesson.category}]` : "";
      const usedCount = lesson.used_count > 0 ? ` (used ${lesson.used_count}x)` : "";

      output += `${index + 1}. ${prefix}${category}\n`;
      output += `   ${lesson.text}${usedCount}\n`;
      output += `   Created: ${this.formatDate(lesson.created_at)}\n\n`;
    });

    output += "─".repeat(80);
    return output;
  }

  /**
   * Format a fact entry
   */
  public static formatFact(fact: SemanticEntry): string {
    const confidence = Math.round(fact.confidence * 100);
    const category = fact.category ? ` [${fact.category}]` : "";

    let output = "\n✅ Fact Saved:\n";
    output += "─".repeat(80) + "\n";
    output += `Key:        ${fact.key}\n`;
    output += `Value:      ${fact.value}\n`;
    output += `Confidence: ${confidence}%${category}\n`;
    output += `Created:    ${this.formatDate(fact.created_at)}\n`;
    output += "─".repeat(80);

    return output;
  }

  /**
   * Format a lesson entry
   */
  public static formatLesson(lesson: LessonEntry): string {
    const prefix = lesson.negative ? "❌ Avoided:" : "✅ Learned:";
    const category = lesson.category ? ` [${lesson.category}]` : "";

    let output = "\n💡 Lesson Recorded:\n";
    output += "─".repeat(80) + "\n";
    output += `${prefix}${category}\n`;
    output += `${lesson.text}\n`;
    output += `Created: ${this.formatDate(lesson.created_at)}\n`;
    output += "─".repeat(80);

    return output;
  }

  /**
   * Format an error message
   */
  public static formatError(error: string): string {
    return `\n❌ Error: ${error}\n`;
  }

  /**
   * Format an info message
   */
  public static formatInfo(message: string): string {
    return `\nℹ️  ${message}`;
  }

  /**
   * Draw a simple bar chart
   */
  private static drawBar(value: number, max: number, width: number): string {
    const filled = Math.round((value / max) * width);
    const empty = width - filled;
    return "█".repeat(filled) + "░".repeat(empty);
  }

  /**
   * Format a date string
   */
  private static formatDate(dateStr: string): string {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString() + " " + date.toLocaleTimeString();
    } catch {
      return dateStr;
    }
  }

  /**
   * Format help text
   */
  public static formatHelp(): string {
    let output = "\n📚 Memory Assistant Help:\n";
    output += "─".repeat(80) + "\n\n";

    output += "🔍 SEARCH:\n";
    output += "  • search typescript\n";
    output += "  • find React best practices\n";
    output += "  • what is database indexing\n";
    output += "  • tell me about SQL optimization\n\n";

    output += "💾 REMEMBER (save facts):\n";
    output += "  • remember TypeScript has strict typing\n";
    output += "  • save React hooks must be called conditionally\n";
    output += "  • note SQL indexing improves query speed\n";
    output += "  • i should use git rebase for clean history\n\n";

    output += "💡 LESSONS (learned rules):\n";
    output += "  • lesson: Always write unit tests first\n";
    output += "  • learned: Code review catches 90% of bugs\n";
    output += "  • avoid: Never commit without testing\n";
    output += "  • don't hardcode configuration values\n";
    output += "  • never skip database backups\n\n";

    output += "⚙️ SYSTEM COMMANDS:\n";
    output += "  • stats        - Show memory statistics\n";
    output += "  • config       - Show configuration\n";
    output += "  • export       - Export memory to JSON file\n";
    output += "  • clear        - Delete all memory (confirmation required)\n";
    output += "  • help         - Show this help message\n";
    output += "  • quit/exit    - Exit the application\n\n";

    output += "💬 NATURAL LANGUAGE:\n";
    output += "  Just type naturally! The assistant will parse your intent.\n";

    output += "─".repeat(80);
    return output;
  }

  /**
   * Format config/settings
   */
  public static formatConfig(store: MemoryStore, injector: Injector): string {
    const stats = store.getStats();
    const config = injector.getConfig();

    let output = "\n⚙️ Configuration:\n";
    output += "─".repeat(80) + "\n";
    output += `Memory Store: Ready\n`;
    output += `  Facts: ${stats.semantic}\n`;
    output += `  Lessons: ${stats.lessons}\n`;
    output += `  Events: ${stats.events}\n\n`;

    output += `Injector Config:\n`;
    output += `  Context Budget: ${config.contextBudget} bytes\n`;
    output += `  Min Confidence: ${Math.round(config.minConfidence * 100)}%\n`;
    output += `  Injection Mode: ${config.injectionMode}\n`;

    output += "─".repeat(80);
    return output;
  }

  /**
   * Format export completion
   */
  public static formatExport(filename: string): string {
    return `✅ Memory exported to: ${filename}`;
  }
}

/**
 * Main CLI class for interactive REPL
 */
class MemoryAssistantCLI {
  private store: MemoryStore;
  private injector: Injector;
  private nlp: SimpleNLPRouter;
  private rl: readline.Interface;
  private isRunning: boolean = true;
  private multilineMode: boolean = false;
  private multilineBuffer: string[] = [];

  constructor(store: MemoryStore, injector: Injector) {
    this.store = store;
    this.injector = injector;
    this.nlp = new SimpleNLPRouter();

    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: true,
    });

    this.rl.on("close", () => {
      this.isRunning = false;
      process.exit(0);
    });
  }

  /**
   * Start the interactive REPL
   */
  public async start(): Promise<void> {
    console.clear();
    console.log("\n🧠 Memory Assistant");
    console.log("═".repeat(80));
    console.log(
      "Memory Assistant ready. Type commands naturally or 'help' for options.\n"
    );

    await this.repl();
  }

  /**
   * Main REPL loop
   */
  private async repl(): Promise<void> {
    while (this.isRunning) {
      try {
        const input = await this.prompt("You: ");

        if (!input) {
          continue;
        }

        // Handle multi-line input
        if (this.multilineMode) {
          if (input.toLowerCase() === "done") {
            const fullInput = this.multilineBuffer.join("\n");
            this.multilineMode = false;
            this.multilineBuffer = [];

            const command = this.nlp.parse(fullInput);
            await this.executeCommand(command);
          } else {
            this.multilineBuffer.push(input);
            console.log('(Enter "done" to submit or continue typing)');
          }
          continue;
        }

        const command = this.nlp.parse(input);
        await this.executeCommand(command);
      } catch (error) {
        if (error instanceof Error && error.message === "readline was closed") {
          break;
        }
        console.error(
          OutputFormatter.formatError(
            error instanceof Error ? error.message : "Unknown error"
          )
        );
      }
    }
  }

  /**
   * Execute a parsed command
   */
  private async executeCommand(command: ParsedCommand): Promise<void> {
    try {
      switch (command.type) {
        case "search":
          await this.handleSearch(command.args?.[0] || "");
          break;

        case "remember":
          await this.handleRemember(command.args?.[0] || "");
          break;

        case "lessons":
          await this.handleLesson(
            command.args?.[0] || "",
            command.args?.[1] === "negative"
          );
          break;

        case "stats":
          this.handleStats();
          break;

        case "help":
          console.log(OutputFormatter.formatHelp());
          break;

        case "export":
          await this.handleExport();
          break;

        case "clear":
          await this.handleClear();
          break;

        case "config":
          this.handleConfig();
          break;

        case "quit":
          await this.handleQuit();
          break;

        case "unknown":
          console.log(
            OutputFormatter.formatInfo(
              "Command not understood. Try 'help' for examples."
            )
          );
          break;
      }
    } catch (error) {
      console.error(
        OutputFormatter.formatError(
          error instanceof Error ? error.message : "Unknown error"
        )
      );
    }
  }

  /**
   * Handle search command
   */
  private async handleSearch(query: string): Promise<void> {
    if (!query.trim()) {
      console.log(OutputFormatter.formatError("Please provide a search query."));
      return;
    }

    const results = this.injector.searchFacts(query, 10);

    if (results.length === 0) {
      console.log(
        OutputFormatter.formatInfo(
          "No facts found matching your query. Use 'remember' to save facts."
        )
      );
    } else {
      console.log(OutputFormatter.formatSearchResults(results));
    }
  }

  /**
   * Handle remember command
   */
  private async handleRemember(text: string): Promise<void> {
    if (!text.trim()) {
      console.log(OutputFormatter.formatError("Please provide something to remember."));
      return;
    }

    // Parse key-value from text (e.g., "TypeScript: has strict typing" -> key: "TypeScript", value: "has strict typing")
    const parts = text.split(/:\s*/, 2);
    const key = parts[0].trim() || "general";
    const value = (parts[1] || parts[0]).trim();

    if (!value) {
      console.log(OutputFormatter.formatError("No content to remember."));
      return;
    }

    try {
      this.store.addFact(key, value, 0.85, "general", "user");
      const fact = this.store.getFact(key);
      if (fact) {
        console.log(OutputFormatter.formatFact(fact));
      }
    } catch (error) {
      console.log(
        OutputFormatter.formatError(
          error instanceof Error ? error.message : "Failed to save fact"
        )
      );
    }
  }

  /**
   * Handle lesson command
   */
  private async handleLesson(text: string, negative: boolean = false): Promise<void> {
    if (!text.trim()) {
      console.log(OutputFormatter.formatError("Please provide a lesson."));
      return;
    }

    try {
      this.store.addLesson(text, negative ? 1 : 0, "general", "user");
      
      // Get the most recently added lesson
      const allLessons = this.store.listLessons(undefined, undefined, 1);
      if (allLessons.length > 0) {
        console.log(OutputFormatter.formatLesson(allLessons[0]));
      }
    } catch (error) {
      console.log(
        OutputFormatter.formatError(
          error instanceof Error ? error.message : "Failed to save lesson"
        )
      );
    }
  }

  /**
   * Handle stats command
   */
  private handleStats(): void {
    const stats = this.store.getStats();
    console.log(OutputFormatter.formatStats(stats.semantic, stats.lessons, stats.events));
  }

  /**
   * Handle export command
   */
  private async handleExport(): Promise<void> {
    try {
      const stats = this.store.getStats();
      const facts = this.store.listFacts(undefined, 1000);
      const lessons = this.store.listLessons(undefined, undefined, 1000);

      const exportData = {
        exportedAt: new Date().toISOString(),
        stats: {
          facts: facts.length,
          lessons: lessons.length,
        },
        facts,
        lessons,
      };

      const __filename = fileURLToPath(import.meta.url);
      const __dirname = path.dirname(__filename);
      const exportPath = path.join(
        __dirname,
        "..",
        `memory-export-${Date.now()}.json`
      );

      fs.writeFileSync(exportPath, JSON.stringify(exportData, null, 2));
      console.log(OutputFormatter.formatExport(exportPath));
    } catch (error) {
      console.log(
        OutputFormatter.formatError(
          error instanceof Error ? error.message : "Failed to export memory"
        )
      );
    }
  }

  /**
   * Handle clear command with confirmation
   */
  private async handleClear(): Promise<void> {
    const confirmed = await this.confirm(
      "⚠️  This will delete ALL facts and lessons. Are you sure? (yes/no): "
    );

    if (!confirmed) {
      console.log(OutputFormatter.formatInfo("Cancelled."));
      return;
    }

    try {
      // Delete all facts
      const facts = this.store.listFacts(undefined, 10000);
      facts.forEach((fact) => {
        if (fact.id) {
          this.store.deleteFact(fact.key);
        }
      });

      // Delete all lessons
      const lessons = this.store.listLessons(undefined, undefined, 10000);
      lessons.forEach((lesson) => {
        this.store.deleteLesson(lesson.id);
      });

      console.log(OutputFormatter.formatInfo("Memory cleared successfully."));
    } catch (error) {
      console.log(
        OutputFormatter.formatError(
          error instanceof Error ? error.message : "Failed to clear memory"
        )
      );
    }
  }

  /**
   * Handle config command
   */
  private handleConfig(): void {
    console.log(OutputFormatter.formatConfig(this.store, this.injector));
  }

  /**
   * Handle quit command
   */
  private async handleQuit(): Promise<void> {
    console.log(OutputFormatter.formatInfo("Goodbye! Memory saved."));
    this.isRunning = false;
    this.rl.close();
    process.exit(0);
  }

  /**
   * Prompt for user input
   */
  private prompt(question: string): Promise<string> {
    return new Promise((resolve) => {
      this.rl.question(question, (answer) => {
        resolve(answer);
      });
    });
  }

  /**
   * Confirm action with user
   */
  private confirm(question: string): Promise<boolean> {
    return new Promise((resolve) => {
      this.rl.question(question, (answer) => {
        resolve(answer.toLowerCase() === "yes" || answer.toLowerCase() === "y");
      });
    });
  }
}

/**
 * Demo CLI with sample data
 */
async function runDemoMode(): Promise<void> {
  console.log("\n🎬 Running in DEMO MODE\n");
  console.log("Populating memory with sample facts and lessons...\n");

  // Create temporary in-memory store for demo
  const store = new MemoryStore();
  store.initialize({
    dbPath: ":memory:",
    logFn: () => {},
  });

  const injector = new Injector(store);

  // Add sample facts
  const sampleFacts = [
    {
      key: "TypeScript",
      value: "Statically typed superset of JavaScript with strict mode",
      confidence: 0.95,
      category: "Languages",
    },
    {
      key: "React Hooks",
      value:
        "React Hooks must be called unconditionally at the top level of a component",
      confidence: 0.92,
      category: "React",
    },
    {
      key: "SQL Indexing",
      value: "Database indexes improve query speed but increase write overhead",
      confidence: 0.88,
      category: "Databases",
    },
    {
      key: "Git Rebase",
      value: "Use git rebase to maintain clean commit history on feature branches",
      confidence: 0.85,
      category: "Git",
    },
    {
      key: "Error Handling",
      value: "Always validate input and handle edge cases in production code",
      confidence: 0.9,
      category: "Best Practices",
    },
  ];

  sampleFacts.forEach((fact) => {
    store.addFact(fact.key, fact.value, fact.confidence, fact.category, "demo");
  });

  // Add sample lessons
  const sampleLessons = [
    {
      text: "Test code before deployment",
      negative: false,
      category: "Best Practices",
    },
    {
      text: "Never hardcode secrets or API keys",
      negative: true,
      category: "Security",
    },
    {
      text: "Use environment variables for configuration",
      negative: false,
      category: "Configuration",
    },
    {
      text: "Avoid premature optimization without profiling",
      negative: true,
      category: "Performance",
    },
  ];

  sampleLessons.forEach((lesson) => {
    store.addLesson(lesson.text, lesson.negative ? 1 : 0, "demo", lesson.category);
  });

  console.log("✅ Sample data loaded!\n");
  console.log("Sample facts: TypeScript, React Hooks, SQL Indexing, Git Rebase, Error Handling");
  console.log("Sample lessons: Testing, Security, Configuration, Performance\n");

  // Start CLI
  const cli = new MemoryAssistantCLI(store, injector);
  await cli.start();
}

/**
 * Main entry point
 */
async function main(): Promise<void> {
  try {
    const args = process.argv.slice(2);
    const demoMode = args.includes("--demo");

    if (demoMode) {
      await runDemoMode();
    } else {
      // Create store with actual database
      const __filename = fileURLToPath(import.meta.url);
      const __dirname = path.dirname(__filename);
      const dataDir = path.join(__dirname, "..", "data");
      const dbPath = path.join(dataDir, "memory.db");

      const store = new MemoryStore();
      store.initialize({
        dbPath,
        logFn: () => {},
      });

      const injector = new Injector(store);

      const cli = new MemoryAssistantCLI(store, injector);
      await cli.start();
    }
  } catch (error) {
    console.error(
      "Fatal error:",
      error instanceof Error ? error.message : error
    );
    process.exit(1);
  }
}

// Run the CLI
main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});

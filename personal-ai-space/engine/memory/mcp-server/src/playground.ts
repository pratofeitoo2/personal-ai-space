/**
 * pi-memory Playground: Interactive demonstrations and example workflows
 *
 * This module showcases natural language usage patterns for pi-memory-clone:
 * - Developer preferences and tool configuration
 * - Search and context injection workflows
 * - Lesson extraction and storage
 * - Memory deduplication and merging
 * - Confidence-based filtering and prioritization
 *
 * Run with:
 *   npx tsx src/playground.ts
 */

import { MemoryStore, SemanticEntry, LessonEntry } from "./store.js";
import { Injector } from "./injector.js";
import { join } from "node:path";
import { homedir, tmpdir } from "node:os";
import { rmSync, existsSync } from "node:fs";

/**
 * Formatting utilities for console output
 */
class ConsoleFormatter {
  static section(title: string): void {
    console.log("\n" + "=".repeat(70));
    console.log(`  ${title}`);
    console.log("=".repeat(70) + "\n");
  }

  static subsection(title: string): void {
    console.log(`\n▶ ${title}`);
    console.log("-".repeat(60));
  }

  static example(label: string, content: string): void {
    console.log(`\n  📝 ${label}:`);
    console.log(`     ${content.split("\n").join("\n     ")}`);
  }

  static arrow(label: string): void {
    console.log(`  ➜ ${label}`);
  }

  static success(label: string, value: string): void {
    console.log(`  ✓ ${label}: ${value}`);
  }

  static highlight(label: string, value: string): void {
    console.log(`  ◆ ${label}: ${value}`);
  }

  static timing(operation: string, ms: number): void {
    console.log(`  ⏱ ${operation}: ${ms.toFixed(2)}ms`);
  }

  static code(content: string): void {
    console.log("\n  ```");
    console.log(content.split("\n").map((l) => `  ${l}`).join("\n"));
    console.log("  ```\n");
  }

  static result(content: string): void {
    console.log("\n  📊 Result:");
    console.log(content.split("\n").map((l) => `     ${l}`).join("\n"));
  }
}

/**
 * Playground configuration
 */
interface PlaygroundConfig {
  dbPath: string;
  verbose: boolean;
  runDemos: string[]; // Which demos to run
}

/**
 * Playground: Main demo orchestrator
 */
export class Playground {
  private store: MemoryStore;
  private injector: Injector;
  private config: PlaygroundConfig;
  private demoResults: Record<string, any> = {};
  private totalTime: number = 0;

  constructor(config: Partial<PlaygroundConfig> = {}) {
    this.store = new MemoryStore();
    this.config = {
      dbPath: join(tmpdir(), "pi-memory-playground.db"),
      verbose: config.verbose ?? false,
      runDemos: config.runDemos ?? [
        "dev-preferences",
        "search-inject",
        "lessons",
        "deduplication",
        "confidence-filter",
        "tool-integration",
        "project-context",
        "multi-session",
        "context-budget",
        "real-world-flow",
      ],
      ...config,
    };

    // Clean up any existing test database
    if (existsSync(this.config.dbPath)) {
      rmSync(this.config.dbPath);
    }

    // Initialize store
    this.store.initialize({
      dbPath: this.config.dbPath,
      logFn: this.config.verbose ? (msg) => console.log(`    [Store] ${msg}`) : undefined,
    });

    // Initialize injector
    this.injector = new Injector(this.store, {
      contextBudget: 8000,
      minConfidence: 0.7,
      injectionMode: "selective",
      logFn: this.config.verbose ? (msg) => console.log(`    [Injector] ${msg}`) : undefined,
    });
  }

  /**
   * Run all playground demonstrations
   */
  async runAll(): Promise<void> {
    ConsoleFormatter.section("π Memory Clone - Interactive Playground");

    console.log("This playground demonstrates natural language memory usage patterns:");
    console.log("  • Developer preferences and context");
    console.log("  • Search and intelligent context injection");
    console.log("  • Learning from mistakes and validations");
    console.log("  • Deduplication and confidence-based filtering");
    console.log("  • Real-world multi-session workflows");
    console.log("\n");

    const demos = [
      { name: "dev-preferences", fn: () => this.demoDeveloperPreferences() },
      { name: "search-inject", fn: () => this.demoSearchAndInject() },
      { name: "lessons", fn: () => this.demoExtractAndStoreLessons() },
      { name: "deduplication", fn: () => this.demoDeduplication() },
      { name: "confidence-filter", fn: () => this.demoConfidenceFiltering() },
      { name: "tool-integration", fn: () => this.demoToolIntegration() },
      { name: "project-context", fn: () => this.demoProjectContext() },
      { name: "multi-session", fn: () => this.demoMultiSession() },
      { name: "context-budget", fn: () => this.demoContextBudget() },
      { name: "real-world-flow", fn: () => this.demoRealWorldFlow() },
    ];

    for (const demo of demos) {
      if (this.config.runDemos.includes(demo.name)) {
        try {
          const startTime = performance.now();
          await demo.fn();
          const duration = performance.now() - startTime;
          this.totalTime += duration;
          this.demoResults[demo.name] = { status: "success", duration };
        } catch (error) {
          const msg = error instanceof Error ? error.message : String(error);
          console.error(`❌ Demo failed: ${msg}`);
          this.demoResults[demo.name] = { status: "error", error: msg };
        }
      }
    }

    // Print summary
    this.printSummary();
  }

  /**
   * Demo 1: Developer Preferences
   * Shows how to store and retrieve common developer preferences
   */
  private async demoDeveloperPreferences(): Promise<void> {
    ConsoleFormatter.section("Demo 1: Developer Preferences");
    ConsoleFormatter.arrow("Scenario: Store developer tool preferences and practices");

    // Add preferences as high-confidence facts
    const preferences = [
      {
        key: "pref.editor",
        value: "VS Code with vim extension",
        confidence: 0.95,
        category: "Preferences",
      },
      {
        key: "pref.commit_style",
        value: "Conventional commits with scopes",
        confidence: 0.9,
        category: "Preferences",
      },
      {
        key: "pref.test_approach",
        value: "TDD - write tests first",
        confidence: 0.85,
        category: "Preferences",
      },
      {
        key: "pref.language",
        value: "TypeScript for type safety",
        confidence: 0.92,
        category: "Preferences",
      },
      {
        key: "pref.review_mindset",
        value: "Focus on clarity and maintainability",
        confidence: 0.88,
        category: "Preferences",
      },
    ];

    ConsoleFormatter.subsection("Storing Developer Preferences");
    for (const pref of preferences) {
      this.store.addFact(pref.key, pref.value, pref.confidence, pref.category);
      ConsoleFormatter.success(pref.key, `"${pref.value}" (${Math.round(pref.confidence * 100)}%)`);
    }

    // Retrieve and display
    ConsoleFormatter.subsection("Retrieved Preferences");
    const retrieved = this.store.listFacts("pref");
    for (const fact of retrieved) {
      ConsoleFormatter.example(
        fact.key,
        `${fact.value}\n   Confidence: ${Math.round(fact.confidence * 100)}%`
      );
    }

    // Build context block
    ConsoleFormatter.subsection("Injected Context for System Prompt");
    const context = this.injector.buildContextBlock();
    ConsoleFormatter.result(context.text);

    this.demoResults["dev-preferences"] = {
      stored: preferences.length,
      retrieved: retrieved.length,
      contextSize: context.text.length,
    };
  }

  /**
   * Demo 2: Search and Context Injection
   * Shows natural language queries and relevant context retrieval
   */
  private async demoSearchAndInject(): Promise<void> {
    ConsoleFormatter.section("Demo 2: Search and Context Injection");
    ConsoleFormatter.arrow("Scenario: Search for relevant memory and build injection context");

    // Pre-populate with facts
    const facts = [
      { key: "project.api.framework", value: "Express.js with TypeScript", confidence: 0.9 },
      { key: "project.api.database", value: "PostgreSQL with migrations", confidence: 0.95 },
      { key: "project.api.auth", value: "JWT with refresh tokens", confidence: 0.85 },
      { key: "tool.db_migration", value: "Use Knex.js for schema changes", confidence: 0.92 },
      { key: "tool.testing", value: "Jest with supertest for API routes", confidence: 0.88 },
    ];

    for (const fact of facts) {
      this.store.addFact(fact.key, fact.value, fact.confidence);
    }

    // Simulate different queries
    const queries = [
      "How do I set up the API framework?",
      "Show me database configuration",
      "What testing approach should I use?",
    ];

    for (const query of queries) {
      ConsoleFormatter.subsection(`Query: "${query}"`);

      // Search for relevant facts
      const results = this.injector.searchFacts(query, 5);
      ConsoleFormatter.arrow(`Found ${results.length} relevant facts:`);

      for (const result of results) {
        const relevance = Math.round(result.relevance * 100);
        ConsoleFormatter.highlight(result.entry.key, `${result.entry.value} (${relevance}% relevant)`);
      }

      // Build targeted context
      const context = this.injector.buildContextBlock({ query });
      ConsoleFormatter.result(`Context size: ${context.text.length} chars\nIncludes: ${context.stats.semanticCount} facts, ${context.stats.lessonCount} lessons`);
    }
  }

  /**
   * Demo 3: Extract and Store Lessons
   * Shows how to record learned corrections and validated approaches
   */
  private async demoExtractAndStoreLessons(): Promise<void> {
    ConsoleFormatter.section("Demo 3: Extract and Store Lessons");
    ConsoleFormatter.arrow("Scenario: Record learned mistakes (corrections) and best practices");

    // Record corrections (learned from mistakes)
    ConsoleFormatter.subsection("Storing Corrections (Learned from Mistakes)");
    const corrections = [
      "Don't use string concatenation for SQL, use parameterized queries",
      "Avoid async operations in map(), use Promise.all() instead",
      "Don't forget to handle null/undefined in optional chaining",
      "Avoid deep nesting, refactor into smaller functions",
      "Never commit secrets - use .env files",
    ];

    for (const correction of corrections) {
      this.store.addLesson(correction, 1, "JavaScript", "experience"); // negative=1 = correction
      ConsoleFormatter.success("Correction", correction);
    }

    // Record validations (best practices confirmed)
    ConsoleFormatter.subsection("Storing Validated Approaches");
    const validations = [
      "Use dependency injection for better testability",
      "Always write unit tests before integration tests",
      "Use TypeScript interfaces to document contracts",
      "Implement proper error handling with try-catch and validation",
    ];

    for (const validation of validations) {
      this.store.addLesson(validation, 0, "Best Practice", "experience"); // negative=0 = validation
      ConsoleFormatter.success("Validation", validation);
    }

    // Display stored lessons
    ConsoleFormatter.subsection("Stored Lessons Summary");
    const allLessons = this.store.listLessons();
    const negLessons = allLessons.filter((l) => l.negative === 1);
    const posLessons = allLessons.filter((l) => l.negative === 0);

    console.log(`\n  📚 Corrections: ${negLessons.length}`);
    for (const lesson of negLessons.slice(0, 3)) {
      ConsoleFormatter.example("Correction", lesson.text);
    }

    console.log(`\n  📚 Validations: ${posLessons.length}`);
    for (const lesson of posLessons.slice(0, 3)) {
      ConsoleFormatter.example("Validation", lesson.text);
    }
  }

  /**
   * Demo 4: Deduplication
   * Shows how to handle and merge duplicate facts
   */
  private async demoDeduplication(): Promise<void> {
    ConsoleFormatter.section("Demo 4: Memory Deduplication");
    ConsoleFormatter.arrow("Scenario: Update existing memory with new confidence scores");

    // Add initial fact
    ConsoleFormatter.subsection("Initial Fact");
    this.store.addFact("lang.preference", "TypeScript", 0.7, "Language");
    let fact = this.store.getFact("lang.preference");
    ConsoleFormatter.highlight("Before", `${fact?.value} (confidence: ${fact?.confidence})`);

    // Update with higher confidence (simulates learning)
    ConsoleFormatter.subsection("Updated with New Experience");
    this.store.addFact("lang.preference", "TypeScript with strict mode", 0.95, "Language");
    fact = this.store.getFact("lang.preference");
    ConsoleFormatter.highlight("After", `${fact?.value} (confidence: ${fact?.confidence})`);

    // Show that duplicate detection works
    const allFacts = this.store.listFacts("lang");
    ConsoleFormatter.arrow(`Total facts with 'lang' prefix: ${allFacts.length}`);
    ConsoleFormatter.success("Deduplication", `One entry maintained (not duplicated)`);
  }

  /**
   * Demo 5: Confidence-based Filtering
   * Shows how confidence affects context injection
   */
  private async demoConfidenceFiltering(): Promise<void> {
    ConsoleFormatter.section("Demo 5: Confidence-Based Filtering");
    ConsoleFormatter.arrow("Scenario: Filter facts by confidence threshold");

    // Add facts with varying confidence
    const facts = [
      { key: "certainty.high", value: "TypeScript is better than JS", confidence: 0.98 },
      { key: "certainty.medium", value: "Vim is a good editor", confidence: 0.75 },
      { key: "certainty.low", value: "Python is my favorite language", confidence: 0.45 },
      { key: "certainty.uncertain", value: "Rust for frontend development", confidence: 0.3 },
    ];

    for (const fact of facts) {
      this.store.addFact(fact.key, fact.value, fact.confidence);
    }

    // Show filtering at different thresholds
    const thresholds = [0.9, 0.7, 0.5, 0.0];

    for (const threshold of thresholds) {
      ConsoleFormatter.subsection(`Confidence threshold: ${threshold}`);
      const allFacts = this.store.listFacts("certainty", 100, "confidence");
      const filtered = allFacts.filter((f) => f.confidence >= threshold);

      console.log(`  Total facts: ${allFacts.length}, Filtered (≥${threshold}): ${filtered.length}`);
      for (const fact of filtered) {
        const conf = Math.round(fact.confidence * 100);
        ConsoleFormatter.highlight(fact.key, `${conf}%`);
      }
    }

    // Show injector's confidence threshold
    ConsoleFormatter.subsection("Injector Configuration");
    const injectorConfig = this.injector.getConfig();
    ConsoleFormatter.highlight("Min Confidence", `${injectorConfig.minConfidence}`);
    ConsoleFormatter.highlight("Context Budget", `${injectorConfig.contextBudget} chars`);
    ConsoleFormatter.highlight("Injection Mode", injectorConfig.injectionMode);
  }

  /**
   * Demo 6: Tool Integration Patterns
   * Shows common tool usage patterns and configurations
   */
  private async demoToolIntegration(): Promise<void> {
    ConsoleFormatter.section("Demo 6: Tool Integration Patterns");
    ConsoleFormatter.arrow("Scenario: Store configuration for common development tools");

    const toolConfigs = [
      {
        key: "tool.prettier",
        value: "printWidth: 100, tabs: false, semi: true",
        confidence: 0.92,
      },
      {
        key: "tool.eslint",
        value: "extends: airbnb-typescript, strict null checking",
        confidence: 0.90,
      },
      {
        key: "tool.jest",
        value: "testEnvironment: node, coverage threshold 80%",
        confidence: 0.88,
      },
      {
        key: "tool.git_hooks",
        value: "husky with pre-commit lint and test",
        confidence: 0.85,
      },
      { key: "tool.docker", value: "Node 20 LTS with non-root user", confidence: 0.87 },
    ];

    ConsoleFormatter.subsection("Storing Tool Configurations");
    for (const config of toolConfigs) {
      this.store.addFact(config.key, config.value, config.confidence);
      ConsoleFormatter.success(config.key, config.value);
    }

    // Build and display context
    ConsoleFormatter.subsection("Generated Context for CI/CD Setup");
    const context = this.injector.buildContextBlock();
    ConsoleFormatter.result(context.text.substring(0, 500) + "...");
  }

  /**
   * Demo 7: Project-Specific Context
   * Shows organizing context by project
   */
  private async demoProjectContext(): Promise<void> {
    ConsoleFormatter.section("Demo 7: Project-Specific Context");
    ConsoleFormatter.arrow("Scenario: Store project-specific facts for context injection");

    const projects = {
      "project.api": [
        { key: "project.api.lang", value: "TypeScript", conf: 0.95 },
        { key: "project.api.framework", value: "Express", conf: 0.92 },
        { key: "project.api.db", value: "PostgreSQL", conf: 0.94 },
      ],
      "project.frontend": [
        { key: "project.frontend.lang", value: "TypeScript", conf: 0.95 },
        { key: "project.frontend.framework", value: "React 18", conf: 0.93 },
        { key: "project.frontend.styling", value: "Tailwind CSS", conf: 0.91 },
      ],
      "project.devops": [
        { key: "project.devops.container", value: "Docker with Compose", conf: 0.94 },
        { key: "project.devops.orchestration", value: "Kubernetes", conf: 0.88 },
        { key: "project.devops.monitoring", value: "Prometheus + Grafana", conf: 0.87 },
      ],
    };

    for (const [project, facts] of Object.entries(projects)) {
      ConsoleFormatter.subsection(`Project: ${project}`);
      for (const fact of facts) {
        this.store.addFact(fact.key, fact.value, fact.conf);
        ConsoleFormatter.success(fact.key, fact.value);
      }
    }

    // Search for project-specific context
    ConsoleFormatter.subsection("Searching by Project");
    const apiContext = this.injector.searchFacts("api database", 5);
    const frontendContext = this.injector.searchFacts("frontend react", 5);

    console.log(`\n  API search results: ${apiContext.length} facts`);
    for (const result of apiContext) {
      ConsoleFormatter.highlight(result.entry.key, `${Math.round(result.relevance * 100)}% relevant`);
    }

    console.log(`\n  Frontend search results: ${frontendContext.length} facts`);
    for (const result of frontendContext) {
      ConsoleFormatter.highlight(result.entry.key, `${Math.round(result.relevance * 100)}% relevant`);
    }
  }

  /**
   * Demo 8: Multi-Session Memory
   * Shows how memory persists and evolves across sessions
   */
  private async demoMultiSession(): Promise<void> {
    ConsoleFormatter.section("Demo 8: Multi-Session Memory");
    ConsoleFormatter.arrow("Scenario: Memory accumulation and evolution across sessions");

    // Simulate Session 1
    ConsoleFormatter.subsection("Session 1: Initial Learning");
    this.store.addFact("session1.learned", "Basic setup", 0.6);
    ConsoleFormatter.success("Session 1", "Added initial fact with 60% confidence");

    // Simulate Session 2: Reinforce same learning
    ConsoleFormatter.subsection("Session 2: Reinforcement");
    this.store.addFact("session1.learned", "Basic setup with details", 0.8);
    const fact = this.store.getFact("session1.learned");
    ConsoleFormatter.highlight("After reinforcement", `Confidence updated to ${fact?.confidence}`);

    // Track event history
    ConsoleFormatter.subsection("Memory Evolution");
    const events = this.store.getRecentEvents(5);
    for (const event of events) {
      ConsoleFormatter.example(event.action, event.details || "");
    }

    ConsoleFormatter.success("Multi-Session", "Memory grows and confidence increases over time");
  }

  /**
   * Demo 9: Context Budget Management
   * Shows intelligent trimming when context exceeds budget
   */
  private async demoContextBudget(): Promise<void> {
    ConsoleFormatter.section("Demo 9: Context Budget Management");
    ConsoleFormatter.arrow("Scenario: Handle context size limits intelligently");

    // Add many facts with different confidence levels
    ConsoleFormatter.subsection("Adding facts with various confidence levels");
    for (let i = 0; i < 20; i++) {
      const confidence = 0.5 + (i * 0.025); // 0.5 to 1.0
      this.store.addFact(`budget.fact_${i}`, `Detailed information about fact ${i}`, confidence);
    }

    ConsoleFormatter.arrow("20 facts added across confidence range");

    // Build context with default budget
    ConsoleFormatter.subsection("Full Context (Default Budget: 8000 chars)");
    const fullContext = this.injector.buildContextBlock();
    console.log(`  Full context size: ${fullContext.text.length} chars`);
    console.log(`  Facts included: ${fullContext.stats.semanticCount}`);
    console.log(`  Lessons included: ${fullContext.stats.lessonCount}`);

    // Build context with tight budget
    ConsoleFormatter.subsection("Tight Budget (1000 chars)");
    this.injector.updateConfig({ contextBudget: 1000 });
    const tightContext = this.injector.buildContextBlock();
    console.log(`  Tight context size: ${tightContext.text.length} chars`);
    console.log(`  Facts included: ${tightContext.stats.semanticCount}`);
    console.log(`  Reduction: ${Math.round((1 - tightContext.stats.semanticCount / fullContext.stats.semanticCount) * 100)}%`);

    // Reset budget
    this.injector.updateConfig({ contextBudget: 8000 });
  }

  /**
   * Demo 10: Real-World Workflow
   * Complex multi-step scenario combining multiple features
   */
  private async demoRealWorldFlow(): Promise<void> {
    ConsoleFormatter.section("Demo 10: Real-World Workflow");
    ConsoleFormatter.arrow("Scenario: Complete developer session with learning");

    // Step 1: Load project context
    ConsoleFormatter.subsection("Step 1: Start Session - Load Project Context");
    this.store.addFact("context.project", "authentication-service", 0.98);
    this.store.addFact("context.task", "Fix JWT token refresh bug", 0.95);
    this.store.addFact("codebase.jwt", "Uses jsonwebtoken library", 0.93);
    this.store.addFact("codebase.error", "Token expiry not handled", 0.91);
    ConsoleFormatter.arrow("3 context facts loaded");

    // Step 2: Developer asks a question
    ConsoleFormatter.subsection("Step 2: Developer Query - Search Relevant Context");
    const query = "How do I refresh JWT tokens?";
    ConsoleFormatter.example("Query", query);

    const relevant = this.injector.searchFacts(query, 10);
    console.log(`  Found ${relevant.length} relevant facts`);

    // Step 3: Get context for system prompt
    ConsoleFormatter.subsection("Step 3: Build Context for LLM");
    const contextBlock = this.injector.buildContextBlock({ query });
    ConsoleFormatter.result(
      contextBlock.text.substring(0, 300) + (contextBlock.text.length > 300 ? "..." : "")
    );

    // Step 4: Simulate solution and learning
    ConsoleFormatter.subsection("Step 4: Record Solution and Lessons");
    this.store.addLesson(
      "JWT refresh: Store refresh token in httpOnly cookie, access token in memory",
      0,
      "Authentication"
    );
    this.store.addLesson("Never log tokens or secrets to console", 1, "Security");
    this.store.addFact("solution.jwt_refresh", "Implemented dual-token pattern", 0.95);
    ConsoleFormatter.arrow("2 lessons and solution recorded");

    // Step 5: Final context
    ConsoleFormatter.subsection("Step 5: Updated Memory State");
    const stats = this.store.getStats();
    console.log(`  Total facts: ${stats.semantic}`);
    console.log(`  Total lessons: ${stats.lessons}`);
    console.log(`  Audit events: ${stats.events}`);

    const finalContext = this.injector.buildContextBlock();
    console.log(`\n  Context ready for next session: ${finalContext.text.length} chars`);
  }

  /**
   * Print summary of all demos
   */
  private printSummary(): void {
    ConsoleFormatter.section("Playground Summary");

    console.log("📊 Demo Results:\n");

    for (const [name, result] of Object.entries(this.demoResults)) {
      if (result.status === "success") {
        const duration = result.duration ? ` (${result.duration.toFixed(2)}ms)` : "";
        console.log(`  ✓ ${name}${duration}`);
      } else {
        console.log(`  ✗ ${name}: ${result.error}`);
      }
    }

    // Database statistics
    ConsoleFormatter.subsection("Final Memory Store State");
    const stats = this.store.getStats();
    console.log(`  Semantic facts: ${stats.semantic}`);
    console.log(`  Lessons learned: ${stats.lessons}`);
    console.log(`  Audit events: ${stats.events}`);

    // Performance
    ConsoleFormatter.subsection("Performance");
    console.log(`  Total time: ${this.totalTime.toFixed(2)}ms`);
    console.log(`  Average per demo: ${(this.totalTime / Object.keys(this.demoResults).length).toFixed(2)}ms`);

    // Cleanup
    ConsoleFormatter.subsection("Cleanup");
    this.store.close();
    if (existsSync(this.config.dbPath)) {
      rmSync(this.config.dbPath);
    }
    console.log(`  Cleaned up test database: ${this.config.dbPath}`);

    console.log("\n✨ Playground complete!\n");
  }
}

/**
 * Run the playground standalone
 */
export async function runPlayground(verbose: boolean = false): Promise<void> {
  const playground = new Playground({ verbose });
  await playground.runAll();
}

// Main entry point
if (process.argv[1]?.endsWith("playground.ts") || process.argv[1]?.includes("tsx")) {
  const verbose = process.argv.includes("--verbose");
  runPlayground(verbose).catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
  });
}

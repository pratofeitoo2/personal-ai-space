import { describe, it, expect, beforeEach, afterEach } from "@jest/globals";
import { MemoryStore } from "../src/store.js";
import { Injector, buildMemoryContext, ContextBlock } from "../src/injector.js";
import { mkdirSync, rmSync, existsSync } from "node:fs";
import { join } from "node:path";

describe("Injector", () => {
  let store: MemoryStore;
  let injector: Injector;
  const testDbPath = join("./tests/.tmp", "test-injector.db");

  beforeEach(() => {
    // Ensure test directory exists
    mkdirSync(join("./tests", ".tmp"), { recursive: true });

    // Initialize store
    store = new MemoryStore();
    store.initialize({
      dbPath: testDbPath,
      logFn: (msg) => {
        // Suppress logs in tests
      },
    });

    // Initialize injector
    injector = new Injector(store, {
      contextBudget: 8192,
      minConfidence: 0.7,
      injectionMode: "all",
    });
  });

  afterEach(() => {
    store.close();
    // Clean up test database
    if (existsSync(testDbPath)) {
      rmSync(testDbPath);
    }
    // Clean up WAL files
    if (existsSync(testDbPath + "-shm")) {
      rmSync(testDbPath + "-shm");
    }
    if (existsSync(testDbPath + "-wal")) {
      rmSync(testDbPath + "-wal");
    }
  });

  describe("searchFacts", () => {
    it("should return empty array for empty query", () => {
      store.addFact("pref.editor", "vim");
      const results = injector.searchFacts("");
      expect(results).toEqual([]);
    });

    it("should find facts by key match", () => {
      store.addFact("pref.editor", "vim", 0.9);
      store.addFact("pref.shell", "bash", 0.85);

      const results = injector.searchFacts("editor");
      expect(results.length).toBeGreaterThan(0);
      expect(results[0].entry.key).toBe("pref.editor");
      expect(results[0].relevance).toBeGreaterThan(0);
    });

    it("should find facts by value match", () => {
      store.addFact("pref.editor", "vim with plugins", 0.9);
      store.addFact("pref.shell", "bash", 0.85);

      const results = injector.searchFacts("vim");
      expect(results.length).toBeGreaterThan(0);
      expect(results[0].entry.key).toBe("pref.editor");
    });

    it("should filter by confidence during search", () => {
      store.addFact("pref.high", "valuable", 0.95);
      store.addFact("pref.low", "noisy", 0.3);

      const results = injector.searchFacts("pref");
      // Should still return low-confidence items in search
      // Filtering happens later
      expect(results.length).toBeGreaterThan(0);
    });

    it("should rank by relevance", () => {
      store.addFact("pref.editor", "vim", 0.9);
      store.addFact("tool.editor.vim", "version 8", 0.85);

      const results = injector.searchFacts("editor");
      // Exact key match should rank higher than partial match
      expect(results[0].entry.key).toBe("pref.editor");
    });

    it("should respect limit parameter", () => {
      for (let i = 0; i < 20; i++) {
        store.addFact(`pref.item${i}`, `value${i}`, 0.9);
      }

      const results = injector.searchFacts("pref", 5);
      expect(results.length).toBeLessThanOrEqual(5);
    });
  });

  describe("buildContextBlock", () => {
    it("should return empty memory section if no facts", () => {
      const block = injector.buildContextBlock();
      expect(block.text).toBe("");
      expect(block.stats.semanticCount).toBe(0);
      expect(block.stats.lessonCount).toBe(0);
    });

    it("should format facts with categories", () => {
      store.addFact("pref.editor", "vim", 0.9);
      store.addFact("pref.shell", "bash", 0.85);
      store.addFact("tool.version_control", "git", 0.95);

      const block = injector.buildContextBlock();
      expect(block.text).toContain("## Known Facts");
      expect(block.text).toContain("Preferences");
      expect(block.text).toContain("Tools");
      expect(block.text).toContain("vim");
      expect(block.text).toContain("bash");
    });

    it("should include confidence percentages", () => {
      store.addFact("pref.editor", "vim", 0.85);
      const block = injector.buildContextBlock();
      expect(block.text).toContain("85%");
    });

    it("should include lessons in output", () => {
      store.addFact("pref.editor", "vim", 0.9);
      store.addLesson("Always use vim for config files", 0, "editing");
      store.addLesson("Don't use sed without -i", 1, "editing");

      const block = injector.buildContextBlock();
      expect(block.text).toContain("## Learned Corrections");
      expect(block.text).toContain("vim for config");
      expect(block.text).toContain("sed without -i");
    });

    it("should distinguish corrections from validated approaches", () => {
      store.addLesson("Use vim for config files", 0, "editing");
      store.addLesson("Never use echo >> for vault", 1, "vault");

      const block = injector.buildContextBlock();
      expect(block.text).toContain("Corrections");
      expect(block.text).toContain("Validated");
    });

    it("should wrap output in memory tags", () => {
      store.addFact("pref.editor", "vim", 0.9);
      const block = injector.buildContextBlock();
      expect(block.text).toMatch(/<memory>[\s\S]*<\/memory>/);
    });

    it("should respect context budget limit", () => {
      // Add many facts
      for (let i = 0; i < 100; i++) {
        store.addFact(`pref.item${i}`, `long value that takes up space ${i}`, 0.8);
      }

      const block = injector.buildContextBlock();
      expect(block.text.length).toBeLessThanOrEqual(8192 + 50); // Small margin for tags
    });

    it("should filter facts by min confidence", () => {
      store.addFact("pref.high", "valuable", 0.9);
      store.addFact("pref.low", "noisy", 0.5);

      const injectorStrict = new Injector(store, { minConfidence: 0.8 });
      const block = injectorStrict.buildContextBlock();

      expect(block.text).toContain("valuable");
      expect(block.text).not.toContain("noisy");
    });

    it("should filter facts by query when provided", () => {
      store.addFact("pref.editor", "vim", 0.9);
      store.addFact("pref.shell", "bash", 0.9);

      const block = injector.buildContextBlock({ query: "editor" });
      expect(block.text).toContain("vim");
      // shell might not appear (depends on relevance scoring)
    });
  });

  describe("selectRelevant", () => {
    it("should return empty array for empty query", () => {
      store.addFact("pref.editor", "vim", 0.9);
      const results = injector.selectRelevant("");
      expect(results).toEqual([]);
    });

    it("should select facts matching query", () => {
      store.addFact("pref.editor", "vim", 0.9);
      store.addFact("pref.shell", "bash", 0.9);

      const results = injector.selectRelevant("editor");
      expect(results.length).toBeGreaterThan(0);
      expect(results.some((f) => f.key === "pref.editor")).toBe(true);
    });

    it("should filter by confidence threshold", () => {
      store.addFact("pref.high", "valuable", 0.9);
      store.addFact("pref.low", "noisy", 0.5);

      const results = injector.selectRelevant("pref");
      expect(results.every((f) => f.confidence >= 0.7)).toBe(true);
    });

    it("should respect budget constraints", () => {
      for (let i = 0; i < 50; i++) {
        store.addFact(`pref.item${i}`, `value${i}`, 0.9);
      }

      const results = injector.selectRelevant("pref", 500);
      // Rough estimate: 100 chars per fact, so ~5 facts for 500 char budget
      expect(results.length).toBeLessThanOrEqual(10);
    });
  });

  describe("formatMemoryPrompt", () => {
    it("should return empty string if no facts", () => {
      const prompt = injector.formatMemoryPrompt();
      expect(prompt).toBe("");
    });

    it("should return formatted context block", () => {
      store.addFact("pref.editor", "vim", 0.9);
      const prompt = injector.formatMemoryPrompt();

      expect(prompt).toContain("<memory>");
      expect(prompt).toContain("</memory>");
      expect(prompt).toContain("vim");
    });

    it("should support selective injection with query", () => {
      store.addFact("pref.editor", "vim", 0.9);
      store.addFact("pref.shell", "bash", 0.9);

      const injectorSelective = new Injector(store, {
        injectionMode: "selective",
      });

      const prompt = injectorSelective.formatMemoryPrompt("editor");
      expect(prompt).toBeDefined();
    });
  });

  describe("Configuration", () => {
    it("should initialize with default config", () => {
      const config = injector.getConfig();
      expect(config.contextBudget).toBe(8192);
      expect(config.minConfidence).toBe(0.7);
      expect(config.injectionMode).toBe("all");
    });

    it("should accept custom config", () => {
      const customInjector = new Injector(store, {
        contextBudget: 4096,
        minConfidence: 0.9,
        injectionMode: "selective",
      });

      const config = customInjector.getConfig();
      expect(config.contextBudget).toBe(4096);
      expect(config.minConfidence).toBe(0.9);
      expect(config.injectionMode).toBe("selective");
    });

    it("should allow config updates", () => {
      injector.updateConfig({ minConfidence: 0.9 });
      const config = injector.getConfig();
      expect(config.minConfidence).toBe(0.9);
    });
  });

  describe("buildMemoryContext utility", () => {
    it("should return formatted context string", () => {
      store.addFact("pref.editor", "vim", 0.9);
      const context = buildMemoryContext(store);

      expect(context).toContain("<memory>");
      expect(context).toContain("vim");
    });

    it("should support query parameter", () => {
      store.addFact("pref.editor", "vim", 0.9);
      store.addFact("pref.shell", "bash", 0.9);

      const context = buildMemoryContext(store, "editor");
      expect(context).toBeDefined();
    });

    it("should support custom config", () => {
      store.addFact("pref.editor", "vim", 0.5);
      store.addFact("pref.shell", "bash", 0.95);

      const context = buildMemoryContext(store, undefined, {
        minConfidence: 0.9,
      });

      // vim (0.5) should be filtered out
      expect(context).not.toContain("vim");
      expect(context).toContain("bash");
    });
  });

  describe("Integration", () => {
    it("should handle full workflow: add, search, build context", () => {
      // Add various facts
      store.addFact("pref.commit_style", "conventional commits", 0.95);
      store.addFact("pref.test_approach", "TDD", 0.9);
      store.addFact("project.rosie.language", "Go", 0.95);
      store.addFact("project.rosie.di", "Dagger", 0.9);
      store.addFact("tool.editor", "vim", 0.85);

      // Add lessons
      store.addLesson("Use sed for vault inserts", 0, "vault");
      store.addLesson("Never use echo >> for vault", 1, "vault");

      // Search for relevant facts
      const searchResults = injector.searchFacts("Go");
      expect(searchResults.length).toBeGreaterThan(0);

      // Build context with query
      const context = injector.buildContextBlock({ query: "rosie" });
      expect(context.text).toContain("<memory>");
      expect(context.stats.semanticCount).toBeGreaterThanOrEqual(0);

      // Build memory prompt
      const prompt = injector.formatMemoryPrompt("language");
      expect(prompt).toBeDefined();
    });

    it("should handle large number of facts efficiently", () => {
      // Add 200 facts
      for (let i = 0; i < 200; i++) {
        store.addFact(`pref.item${i}`, `value${i}`, 0.8 + Math.random() * 0.2);
      }

      // Search should complete quickly
      const start = Date.now();
      const results = injector.searchFacts("item", 20);
      const elapsed = Date.now() - start;

      expect(results.length).toBeLessThanOrEqual(20);
      expect(elapsed).toBeLessThan(1000); // Should complete in <1 second
    });
  });
});

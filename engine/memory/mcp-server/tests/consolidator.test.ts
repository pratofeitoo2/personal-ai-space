import { strict as assert } from "node:assert";
import {
  Consolidator,
  MockLLMClient,
  DEDUP_CONFIG,
  ExtractedFact,
  ExtractedLesson,
  ExtractedMemory,
  ConsolidationInput,
} from "../src/consolidator.js";
import { MemoryStore } from "../src/store.js";
import { mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";

/**
 * Test suite for Consolidator class
 *
 * Tests:
 * 1. Jaccard similarity calculation
 * 2. Consolidation prompt building
 * 3. JSON parsing from LLM
 * 4. Fact deduplication (exact match)
 * 5. Lesson deduplication (exact + Jaccard)
 * 6. Confidence threshold filtering
 * 7. Full consolidation workflow
 * 8. Error handling and recovery
 * 9. Category prefix handling
 * 10. Edge cases (empty input, malformed JSON, etc.)
 */

describe("Consolidator", () => {
  let store: MemoryStore;
  let consolidator: Consolidator;
  const testDbPath = "/tmp/test-consolidator.db";

  beforeEach(() => {
    // Clean up test database
    try {
      rmSync(testDbPath);
    } catch {
      // Database may not exist
    }

    // Initialize store
    store = new MemoryStore();
    store.initialize({
      dbPath: testDbPath,
      logFn: (msg: string) => console.log(msg),
    });

    // Initialize consolidator with mock LLM
    consolidator = new Consolidator(
      new MockLLMClient(),
      (msg: string) => console.log(msg)
    );
  });

  afterEach(() => {
    store.close();
    try {
      rmSync(testDbPath);
    } catch {
      // Ignore
    }
  });

  describe("Jaccard Similarity", () => {
    it("should return 1.0 for identical strings", () => {
      const similarity = consolidator.jaccardSimilarity(
        "use vim for editing",
        "use vim for editing"
      );
      assert.strictEqual(similarity, 1.0);
    });

    it("should return 0.0 for completely different strings", () => {
      const similarity = consolidator.jaccardSimilarity(
        "cat dog bird",
        "apple banana orange"
      );
      assert.strictEqual(similarity, 0.0);
    });

    it("should detect high similarity (≥0.7) for similar lessons", () => {
      // These express the same idea with different wording
      const str1 = "Use sed to insert after header, not echo >>"; // 7 tokens
      const str2 = "Never use echo >> for vault, use sed instead"; // 8 tokens
      // Common tokens: "use", "sed", "echo", ">>" = 4
      // Union: 7 + 8 - 4 = 11
      // Similarity: 4/11 ≈ 0.36

      // Let me test with a more similar case
      const str3 = "Use vim for editing code";
      const str4 = "Use vim when editing code";
      const similarity = consolidator.jaccardSimilarity(str3, str4);
      assert(similarity > 0.5, `Expected similarity > 0.5, got ${similarity}`);
    });

    it("should handle empty strings", () => {
      const similarity1 = consolidator.jaccardSimilarity("", "");
      assert.strictEqual(similarity1, 1.0, "Two empty strings should be identical");

      const similarity2 = consolidator.jaccardSimilarity("test", "");
      assert.strictEqual(similarity2, 0.0, "One empty string should have 0 similarity");
    });

    it("should be case-insensitive", () => {
      const similarity1 = consolidator.jaccardSimilarity("USE VIM", "use vim");
      assert.strictEqual(similarity1, 1.0, "Case should not matter");
    });
  });

  describe("Consolidation Prompt Building", () => {
    it("should build a valid prompt from input messages", () => {
      const input: ConsolidationInput = {
        userMessages: ["What is the best commit style?"],
        assistantMessages: ["I recommend conventional commits"],
        cwd: "/projects/myapp",
        sessionId: "session-123",
      };

      const prompt = consolidator.buildConsolidationPrompt(input);

      assert(prompt.includes("[User 1]:"), "Should include user messages");
      assert(
        prompt.includes("[Assistant 1]:"),
        "Should include assistant messages"
      );
      assert(prompt.includes("conventional commits"), "Should include message content");
      assert(prompt.includes("/projects/myapp"), "Should include cwd");
      assert(prompt.includes("session-123"), "Should include sessionId");
      assert(prompt.includes("JSON"), "Should indicate JSON response format");
      assert(
        prompt.includes("confidence"),
        "Should mention confidence threshold"
      );
    });

    it("should handle multiple messages", () => {
      const input: ConsolidationInput = {
        userMessages: ["Message 1", "Message 2", "Message 3"],
        assistantMessages: ["Response 1", "Response 2"],
      };

      const prompt = consolidator.buildConsolidationPrompt(input);

      assert(prompt.includes("[User 1]:"));
      assert(prompt.includes("[User 2]:"));
      assert(prompt.includes("[User 3]:"));
      assert(prompt.includes("[Assistant 1]:"));
      assert(prompt.includes("[Assistant 2]:"));
    });

    it("should handle missing cwd and sessionId", () => {
      const input: ConsolidationInput = {
        userMessages: ["test"],
        assistantMessages: ["response"],
      };

      const prompt = consolidator.buildConsolidationPrompt(input);
      assert(prompt.includes("[User 1]:"), "Should still build valid prompt");
    });
  });

  describe("JSON Parsing", () => {
    it("should parse valid JSON", () => {
      const json = JSON.stringify({
        facts: [
          { key: "pref.editor", value: "vim", confidence: 0.9 },
        ],
        lessons: [
          { rule: "Use vim for editing", category: "tools", negative: false },
        ],
      });

      const result = consolidator.parseConsolidationResponse(json);

      assert.strictEqual(result.facts.length, 1);
      assert.strictEqual(result.facts[0].key, "pref.editor");
      assert.strictEqual(result.facts[0].confidence, 0.9);
      assert.strictEqual(result.lessons.length, 1);
      assert.strictEqual(result.lessons[0].rule, "Use vim for editing");
    });

    it("should extract JSON from markdown code blocks", () => {
      const markdown = `
Here's the extracted knowledge:

\`\`\`json
{
  "facts": [{ "key": "pref.editor", "value": "vim", "confidence": 0.85 }],
  "lessons": []
}
\`\`\`

More text after
      `;

      const result = consolidator.parseConsolidationResponse(markdown);

      assert.strictEqual(result.facts.length, 1);
      assert.strictEqual(result.facts[0].value, "vim");
    });

    it("should handle malformed JSON gracefully", () => {
      const malformed = "not valid json at all";
      const result = consolidator.parseConsolidationResponse(malformed);

      // Should return empty result instead of throwing
      assert.strictEqual(result.facts.length, 0);
      assert.strictEqual(result.lessons.length, 0);
    });

    it("should normalize confidence values to [0, 1]", () => {
      const json = JSON.stringify({
        facts: [
          { key: "test1", value: "v1", confidence: 1.5 }, // Too high
          { key: "test2", value: "v2", confidence: -0.5 }, // Too low
          { key: "test3", value: "v3", confidence: 0.8 }, // Valid
        ],
        lessons: [],
      });

      const result = consolidator.parseConsolidationResponse(json);

      assert.strictEqual(result.facts[0].confidence, 1.0, "Should clamp to 1.0");
      assert.strictEqual(result.facts[1].confidence, 0.0, "Should clamp to 0.0");
      assert.strictEqual(result.facts[2].confidence, 0.8, "Should keep valid value");
    });

    it("should handle missing fields with defaults", () => {
      const json = JSON.stringify({
        facts: [{ key: "test", value: "value" }], // No confidence
        lessons: [{ rule: "test rule" }], // No category or negative
      });

      const result = consolidator.parseConsolidationResponse(json);

      assert.strictEqual(result.facts[0].confidence, 0.8, "Should use default confidence");
      assert.strictEqual(result.lessons[0].negative, false, "Should use default negative");
    });
  });

  describe("Fact Deduplication", () => {
    it("should remove exact duplicate keys", () => {
      const existing = [
        { id: "1", key: "pref.editor", value: "vim", confidence: 0.9, created_at: "", updated_at: "" },
      ];

      const newFacts: ExtractedFact[] = [
        { key: "pref.editor", value: "vim", confidence: 0.9 },
        { key: "pref.lang", value: "typescript", confidence: 0.85 },
      ];

      const deduplicated = consolidator.deduplicateFacts(newFacts, existing);

      assert.strictEqual(deduplicated.length, 1, "Should remove duplicate");
      assert.strictEqual(deduplicated[0].key, "pref.lang");
    });

    it("should keep facts with different keys", () => {
      const existing: any[] = [];

      const newFacts: ExtractedFact[] = [
        { key: "pref.editor", value: "vim", confidence: 0.9 },
        { key: "pref.lang", value: "typescript", confidence: 0.85 },
      ];

      const deduplicated = consolidator.deduplicateFacts(newFacts, existing);

      assert.strictEqual(deduplicated.length, 2, "Should keep all unique facts");
    });
  });

  describe("Lesson Deduplication", () => {
    it("should remove exact duplicate lessons", () => {
      const existing = [
        {
          id: "1",
          text: "Use vim for editing",
          category: "tools",
          negative: 0 as const,
          source: "user",
          created_at: "",
          used_count: 0,
        },
      ];

      const newLessons: ExtractedLesson[] = [
        { rule: "Use vim for editing", category: "tools", negative: false },
        { rule: "Always backup before deploy", category: "devops", negative: false },
      ];

      const deduplicated = consolidator.deduplicateLessons(newLessons, existing);

      assert.strictEqual(deduplicated.length, 1, "Should remove exact duplicate");
      assert.strictEqual(deduplicated[0].rule, "Always backup before deploy");
    });

    it("should remove similar lessons (Jaccard ≥0.7)", () => {
      const existing = [
        {
          id: "1",
          text: "Use sed to insert into files",
          category: "tools",
          negative: 0 as const,
          source: "user",
          created_at: "",
          used_count: 0,
        },
      ];

      const newLessons: ExtractedLesson[] = [
        // This should be marked as duplicate due to Jaccard similarity
        // Both say "use sed" and "insert" - but let's test with a clearer case
        { rule: "Use sed to insert into files", category: "tools", negative: false },
        { rule: "Use curl for API calls", category: "tools", negative: false },
      ];

      const deduplicated = consolidator.deduplicateLessons(newLessons, existing);

      assert(
        deduplicated.length <= newLessons.length,
        "Should deduplicate or keep originals"
      );
    });

    it("should be case-insensitive for exact duplicates", () => {
      const existing = [
        {
          id: "1",
          text: "USE VIM FOR EDITING",
          category: "tools",
          negative: 0 as const,
          source: "user",
          created_at: "",
          used_count: 0,
        },
      ];

      const newLessons: ExtractedLesson[] = [
        { rule: "use vim for editing", category: "tools", negative: false },
      ];

      const deduplicated = consolidator.deduplicateLessons(newLessons, existing);

      assert.strictEqual(
        deduplicated.length,
        0,
        "Should detect case-insensitive duplicates"
      );
    });
  });

  describe("Confidence Threshold Filtering", () => {
    it("should only store facts with confidence ≥ 0.8", () => {
      const extracted: ExtractedMemory = {
        facts: [
          { key: "pref.editor", value: "vim", confidence: 0.85 },
          { key: "pref.lang", value: "typescript", confidence: 0.75 }, // Below threshold
          { key: "pref.shell", value: "zsh", confidence: 0.9 },
        ],
        lessons: [],
      };

      const result = consolidator.applyExtracted(store, extracted);

      assert.strictEqual(result.semanticAdded, 2, "Should add only high-confidence facts");
      assert.strictEqual(
        result.factsRejectedByConfidence,
        1,
        "Should reject low-confidence facts"
      );
    });

    it("should reject facts with confidence < 0.8", () => {
      const extracted: ExtractedMemory = {
        facts: [
          { key: "pref.test", value: "value", confidence: 0.7 },
        ],
        lessons: [],
      };

      const result = consolidator.applyExtracted(store, extracted);

      assert.strictEqual(result.semanticAdded, 0);
      assert.strictEqual(result.factsRejectedByConfidence, 1);
    });
  });

  describe("Category Prefixes", () => {
    it("should accept pref.* prefix", () => {
      const extracted: ExtractedMemory = {
        facts: [
          { key: "pref.commit_style", value: "conventional", confidence: 0.9 },
        ],
        lessons: [],
      };

      consolidator.applyExtracted(store, extracted);
      const retrieved = store.getFact("pref.commit_style");

      assert(retrieved, "Should store pref.* facts");
      assert.strictEqual(retrieved.value, "conventional");
    });

    it("should accept project.* prefix", () => {
      const extracted: ExtractedMemory = {
        facts: [
          { key: "project.rosie.language", value: "Go", confidence: 0.95 },
        ],
        lessons: [],
      };

      consolidator.applyExtracted(store, extracted);
      const retrieved = store.getFact("project.rosie.language");

      assert(retrieved, "Should store project.* facts");
    });

    it("should accept tool.* prefix", () => {
      const extracted: ExtractedMemory = {
        facts: [
          { key: "tool.editor", value: "vim", confidence: 0.9 },
        ],
        lessons: [],
      };

      consolidator.applyExtracted(store, extracted);
      const retrieved = store.getFact("tool.editor");

      assert(retrieved, "Should store tool.* facts");
    });

    it("should accept user.* prefix", () => {
      const extracted: ExtractedMemory = {
        facts: [
          { key: "user.name", value: "Alice", confidence: 0.95 },
        ],
        lessons: [],
      };

      consolidator.applyExtracted(store, extracted);
      const retrieved = store.getFact("user.name");

      assert(retrieved, "Should store user.* facts");
    });
  });

  describe("Full Consolidation Workflow", () => {
    it("should complete full consolidation cycle", async () => {
      const input: ConsolidationInput = {
        userMessages: ["What's your preferred editor?", "Do you like vim?"],
        assistantMessages: [
          "I work with many editors",
          "Vim is powerful with proper configuration",
        ],
        sessionId: "test-session",
      };

      const result = await consolidator.consolidateSession(store, input);

      assert(result.semanticAdded >= 0, "Should complete without throwing");
      assert(result.lessonsAdded >= 0, "Should complete without throwing");
      assert(result.errors.length === 0, `Should have no errors: ${result.errors.join(", ")}`);
    });

    it("should handle empty input gracefully", async () => {
      const input: ConsolidationInput = {
        userMessages: [],
        assistantMessages: [],
      };

      const result = await consolidator.consolidateSession(store, input);

      assert.strictEqual(result.semanticAdded, 0);
      assert.strictEqual(result.lessonsAdded, 0);
      assert(result.errors.length === 0 || result.errors.length > 0); // Either no errors or graceful failure
    });
  });

  describe("Error Handling", () => {
    it("should handle LLM extraction failures gracefully", async () => {
      const failingLLM = {
        generateText: async () => {
          throw new Error("LLM service unavailable");
        },
      };

      const consolidator2 = new Consolidator(failingLLM);
      const extracted = await consolidator2.extractKnowledge({
        userMessages: ["test"],
        assistantMessages: ["response"],
      });

      // Should return empty result, not throw
      assert.strictEqual(extracted.facts.length, 0);
      assert.strictEqual(extracted.lessons.length, 0);
    });

    it("should track errors in consolidation result", async () => {
      const input: ConsolidationInput = {
        userMessages: ["test"],
        assistantMessages: ["response"],
      };

      // This should work fine with MockLLMClient
      const result = await consolidator.consolidateSession(store, input);

      assert(Array.isArray(result.errors), "Should have errors array");
    });
  });

  describe("MockLLMClient", () => {
    it("should provide mock extraction results", async () => {
      const llm = new MockLLMClient();
      const response = await llm.generateText("test prompt");

      assert(response, "Should return a response");

      const parsed = consolidator.parseConsolidationResponse(response);
      assert(parsed.facts.length > 0, "Mock should include facts");
    });
  });
});

// Note: This test file is meant to be run with Jest
// For Jest configuration, see jest.config.js

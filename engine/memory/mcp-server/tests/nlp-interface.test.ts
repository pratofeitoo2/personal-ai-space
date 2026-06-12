/**
 * Tests for NLP Interface
 *
 * Comprehensive test suite for natural language processing router,
 * including intent detection, parameter extraction, and tool routing.
 */

import {
  NLPRouter,
  IntentType,
  ConfidenceLevel,
  RouteResult,
  ToolResult,
} from "../src/nlp-interface";

describe("NLPRouter", () => {
  let router: NLPRouter;

  beforeEach(() => {
    router = new NLPRouter();
  });

  describe("Intent Detection", () => {
    test("should detect REMEMBER intent", () => {
      const inputs = [
        "remember I like TypeScript",
        "save that I prefer vim",
        "note that I use Docker",
        "store my favorite language is Python",
        "i like testing",
        "add that i prefer TDD",
      ];

      inputs.forEach((input) => {
        const result = router.route(input);
        expect(result.intent).toBe(IntentType.REMEMBER);
        expect(result.confidence).toBeGreaterThanOrEqual(0.51);
      });
    });

    test("should detect SEARCH intent", () => {
      const inputs = [
        "what do i know about databases?",
        "find information on TypeScript",
        "search for testing practices",
        "tell me about git workflows",
        "show me what I know about vim",
        "do you know about my preferences?",
      ];

      inputs.forEach((input) => {
        const result = router.route(input);
        expect(result.intent).toBe(IntentType.SEARCH);
        expect(result.confidence).toBeGreaterThanOrEqual(0.51);
      });
    });

    test("should detect FORGET intent", () => {
      const inputs = [
        "forget my old config",
        "delete that preference",
        "remove my outdated notes",
        "clear old settings",
        "erase my previous experience",
        "unlearn that rule",
      ];

      inputs.forEach((input) => {
        const result = router.route(input);
        expect(result.intent).toBe(IntentType.FORGET);
        expect(result.confidence).toBeGreaterThanOrEqual(0.51);
      });
    });

    test("should detect LESSONS intent", () => {
      const inputs = [
        "show me lessons",
        "lessons learned",
        "corrections I've made",
        "show me lessons about git",
        "corrections for security",
        "what lessons learned?",
      ];

      inputs.forEach((input) => {
        const result = router.route(input);
        expect(result.intent).toBe(IntentType.LESSONS);
        expect(result.confidence).toBeGreaterThanOrEqual(0.51);
      });
    });

    test("should detect STATS intent", () => {
      const inputs = [
        "show me stats",
        "how much memory is used?",
        "what's my memory status?",
        "tell me my memory statistics",
        "memory usage?",
      ];

      inputs.forEach((input) => {
        const result = router.route(input);
        expect(result.intent).toBe(IntentType.STATS);
        expect(result.confidence).toBeGreaterThanOrEqual(0.51);
      });
    });

    test("should handle unknown intent gracefully", () => {
      const result = router.route("xyz qwerty asdf");
      expect(result.intent).toBe(IntentType.UNKNOWN);
      expect(result.confidence).toBe(0);
    });

    test("should handle empty input", () => {
      const result = router.route("");
      expect(result.intent).toBe(IntentType.UNKNOWN);
      expect(result.confidence).toBe(0);
    });
  });

  describe("Parameter Extraction - REMEMBER", () => {
    test("should extract simple 'I like X' pattern", () => {
      const result = router.route("remember I like TypeScript");
      expect(result.toolCall.params.key).toBe("pref.typescript");
      expect(result.toolCall.params.value).toBe("TypeScript");
      expect(result.toolCall.params.confidence).toBe(ConfidenceLevel.HIGH);
    });

    test("should extract 'save X as Y' pattern", () => {
      const result = router.route("save my editor as vim");
      expect(result.toolCall.params.key).toBeDefined();
      expect(result.toolCall.params.value).toBe("vim");
    });

    test("should extract category prefix", () => {
      const result = router.route("remember pref.git_style conventional commits");
      expect(result.toolCall.params.key).toContain("pref");
    });

    test("should detect confidence modifiers", () => {
      const highConfidence = router.route("i'm sure I like Docker");
      expect(highConfidence.toolCall.params.confidence).toBe(
        ConfidenceLevel.VERY_HIGH
      );

      const mediumConfidence = router.route("i think I like Python");
      expect(mediumConfidence.toolCall.params.confidence).toBe(
        ConfidenceLevel.MEDIUM
      );

      const lowConfidence = router.route("maybe I like Go");
      expect(lowConfidence.toolCall.params.confidence).toBe(
        ConfidenceLevel.LOW
      );
    });

    test("should extract key=value pattern", () => {
      const result = router.route("remember editor = vim");
      expect(result.toolCall.params.key).toContain("editor");
      expect(result.toolCall.params.value).toBe("vim");
    });
  });

  describe("Parameter Extraction - SEARCH", () => {
    test("should extract query from 'what do i know about X'", () => {
      const result = router.route("what do i know about databases?");
      expect(result.toolCall.params.query).toContain("database");
    });

    test("should extract query from 'find X'", () => {
      const result = router.route("find information on TypeScript");
      expect(result.toolCall.params.query).toBeDefined();
    });

    test("should extract query from 'search for X'", () => {
      const result = router.route("search for testing practices");
      expect(result.toolCall.params.query).toBeDefined();
    });

    test("should handle question marks", () => {
      const result = router.route("what do i know about git?");
      expect(result.toolCall.params.query).not.toContain("?");
    });
  });

  describe("Parameter Extraction - FORGET", () => {
    test("should extract key from 'forget X'", () => {
      const result = router.route("forget my old config");
      expect(result.toolCall.params.key).toContain("config");
    });

    test("should support wildcard patterns", () => {
      const result = router.route("forget old config");
      // Should add wildcard for non-dotted keys
      expect(result.toolCall.params.key).toContain(".");
    });

    test("should preserve explicit dot notation", () => {
      const result = router.route("forget pref.language");
      expect(result.toolCall.params.key).toBe("pref.language");
    });
  });

  describe("Parameter Extraction - LESSONS", () => {
    test("should extract category filter", () => {
      const result = router.route("show me lessons about git");
      expect(result.toolCall.params.category).toContain("git");
    });

    test("should return empty params for generic lessons", () => {
      const result = router.route("show me lessons");
      expect(result.toolCall.params.category).toBeUndefined();
    });
  });

  describe("Tool Routing", () => {
    test("should create valid memory_remember tool call", () => {
      const result = router.route("remember I use Docker");
      expect(result.toolCall.toolName).toBe("memory_remember");
      expect(result.toolCall.params).toHaveProperty("key");
      expect(result.toolCall.params).toHaveProperty("value");
    });

    test("should create valid memory_search tool call", () => {
      const result = router.route("what do i know about testing?");
      expect(result.toolCall.toolName).toBe("memory_search");
      expect(result.toolCall.params).toHaveProperty("query");
    });

    test("should create valid memory_forget tool call", () => {
      const result = router.route("forget my old config");
      expect(result.toolCall.toolName).toBe("memory_forget");
      expect(result.toolCall.params).toHaveProperty("key");
    });

    test("should create valid memory_lessons tool call", () => {
      const result = router.route("show me lessons");
      expect(result.toolCall.toolName).toBe("memory_lessons");
    });

    test("should create valid memory_stats tool call", () => {
      const result = router.route("how much memory is used?");
      expect(result.toolCall.toolName).toBe("memory_stats");
      expect(Object.keys(result.toolCall.params).length).toBe(0);
    });
  });

  describe("Explanation Generation", () => {
    test("should provide explanation for all intents", () => {
      const testCases = [
        "remember I like TypeScript",
        "what do i know about databases?",
        "forget my old config",
        "show me lessons",
        "show me stats",
      ];

      testCases.forEach((input) => {
        const result = router.route(input);
        expect(result.explanation).toBeDefined();
        expect(result.explanation.length).toBeGreaterThan(0);
      });
    });
  });

  describe("Handle Method", () => {
    test("should handle UNKNOWN intent gracefully", async () => {
      const result = await router.handle("xyz asdf", {});
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    test("should call correct tool handler", async () => {
      const mockHandlers = {
        memory_stats: async () => ({
          success: true,
          data: { semantic: 5, lessons: 2, events: 10 },
        }),
      };

      const result = await router.handle("show me stats", mockHandlers);
      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
    });

    test("should handle missing tool gracefully", async () => {
      const result = await router.handle("remember I like Python", {});
      expect(result.success).toBe(false);
      expect(result.error).toContain("Tool not found");
    });

    test("should handle tool execution errors", async () => {
      const mockHandlers = {
        memory_search: async () => ({
          success: false,
          error: "Database error",
        }),
      };

      const result = await router.handle("what do i know?", mockHandlers);
      expect(result.success).toBe(false);
    });
  });

  describe("Conversational Method", () => {
    test("should provide helpful response for empty input", async () => {
      const response = await router.conversational("");
      expect(response).toContain("didn't hear");
    });

    test("should provide helpful response for unknown intent", async () => {
      const response = await router.conversational("xyz asdf");
      expect(response).toContain("not sure");
    });

    test("should provide confirmation without tools", async () => {
      const response = await router.conversational(
        "remember I like TypeScript"
      );
      expect(response).toContain("understood");
    });

    test("should format search results", async () => {
      const mockHandlers = {
        memory_search: async () => ({
          success: true,
          data: [
            {
              key: "pref.language",
              value: "TypeScript",
              confidence: 0.95,
            },
          ],
        }),
      };

      const response = await router.conversational(
        "what do i know about languages?",
        undefined,
        mockHandlers
      );
      expect(response).toContain("Found");
      expect(response).toContain("TypeScript");
    });

    test("should format remember confirmation", async () => {
      const mockHandlers = {
        memory_remember: async (params: Record<string, unknown>) => ({
          success: true,
          data: params,
        }),
      };

      const response = await router.conversational(
        "remember I like Docker",
        undefined,
        mockHandlers
      );
      expect(response).toContain("Stored");
      expect(response).toContain("Docker");
    });

    test("should format stats response", async () => {
      const mockHandlers = {
        memory_stats: async () => ({
          success: true,
          data: { semantic: 10, lessons: 5, events: 25 },
        }),
      };

      const response = await router.conversational(
        "show me stats",
        undefined,
        mockHandlers
      );
      expect(response).toContain("10");
      expect(response).toContain("5");
    });
  });

  describe("System Prompt Generation", () => {
    test("should generate valid system prompt", () => {
      const prompt = router.generateSystemPrompt();
      expect(prompt).toContain("memory_remember");
      expect(prompt).toContain("memory_search");
      expect(prompt).toContain("memory_forget");
      expect(prompt).toContain("memory_lessons");
      expect(prompt).toContain("memory_stats");
    });

    test("should include examples in prompt", () => {
      const examples = [
        { input: "test input", output: "test output" },
      ];
      const prompt = router.generateSystemPrompt(examples);
      expect(prompt).toContain("test input");
      expect(prompt).toContain("test output");
    });

    test("should include extraction rules in prompt", () => {
      const prompt = router.generateSystemPrompt();
      expect(prompt).toContain("Category Detection");
      expect(prompt).toContain("Confidence Levels");
      expect(prompt).toContain("Key/Value Extraction");
    });
  });

  describe("Edge Cases", () => {
    test("should handle multiple intents in one sentence", () => {
      // Should pick the most prominent intent
      const result = router.route("remember that I like to search for TypeScript");
      expect(result.intent).toBe(IntentType.REMEMBER);
    });

    test("should handle very long input", () => {
      const baseInput =
        "remember that I really like very long test descriptions for testing purposes ";
      const longInput = baseInput + baseInput.repeat(5);
      const result = router.route(longInput);
      expect(result.intent).toBe(IntentType.REMEMBER);
    });

    test("should handle case insensitivity", () => {
      const results = [
        router.route("REMEMBER I LIKE TYPESCRIPT"),
        router.route("Remember I Like TypeScript"),
        router.route("remember i like typescript"),
      ];

      results.forEach((result) => {
        expect(result.intent).toBe(IntentType.REMEMBER);
      });
    });

    test("should handle special characters", () => {
      const result = router.route(
        "remember I like TypeScript (v5.0+) & React!"
      );
      expect(result.intent).toBe(IntentType.REMEMBER);
    });

    test("should handle contractions", () => {
      const result = router.route("don't forget to save this");
      expect(result.intent).toBe(IntentType.FORGET);
    });

    test("should extract confidence with contractions", () => {
      const result = router.route("i'm sure I like Python");
      expect(result.toolCall.params.confidence).toBe(
        ConfidenceLevel.VERY_HIGH
      );
    });
  });

  describe("Integration Tests", () => {
    test("should handle full workflow: REMEMBER -> SEARCH -> FORGET", () => {
      // Remember
      const rememberResult = router.route("remember I like TypeScript");
      expect(rememberResult.intent).toBe(IntentType.REMEMBER);
      expect(rememberResult.toolCall.toolName).toBe("memory_remember");

      // Search
      const searchResult = router.route("what do i know about TypeScript?");
      expect(searchResult.intent).toBe(IntentType.SEARCH);
      expect(searchResult.toolCall.toolName).toBe("memory_search");
      expect(searchResult.toolCall.params.query).toContain("TypeScript");

      // Forget
      const forgetResult = router.route("forget my typescript preference");
      expect(forgetResult.intent).toBe(IntentType.FORGET);
      expect(forgetResult.toolCall.toolName).toBe("memory_forget");
    });

    test("should maintain consistency across multiple calls", () => {
      const input = "remember I like Docker";
      const results = [
        router.route(input),
        router.route(input),
        router.route(input),
      ];

      results.forEach((result) => {
        expect(result.intent).toBe(IntentType.REMEMBER);
        expect(result.toolCall.params.key).toBe(results[0].toolCall.params.key);
      });
    });
  });

  describe("Real-world Examples", () => {
    test("should handle example from requirements: remember TypeScript", () => {
      const result = router.route("remember that I like TypeScript");
      expect(result.intent).toBe(IntentType.REMEMBER);
      expect(result.toolCall.toolName).toBe("memory_remember");
      expect(result.toolCall.params.key).toContain("pref");
      expect(result.toolCall.params.value).toContain("TypeScript");
      expect(result.toolCall.params.confidence).toBe(ConfidenceLevel.HIGH);
    });

    test("should handle example from requirements: search databases", () => {
      const result = router.route("what do i know about databases?");
      expect(result.intent).toBe(IntentType.SEARCH);
      expect(result.toolCall.toolName).toBe("memory_search");
      expect(result.toolCall.params.query).toContain("database");
    });

    test("should handle example from requirements: forget config", () => {
      const result = router.route("forget my old config");
      expect(result.intent).toBe(IntentType.FORGET);
      expect(result.toolCall.toolName).toBe("memory_forget");
    });

    test("should handle example from requirements: show lessons", () => {
      const result = router.route("show me lessons");
      expect(result.intent).toBe(IntentType.LESSONS);
      expect(result.toolCall.toolName).toBe("memory_lessons");
    });

    test("should handle example from requirements: memory stats", () => {
      const result = router.route("how much memory is used?");
      expect(result.intent).toBe(IntentType.STATS);
      expect(result.toolCall.toolName).toBe("memory_stats");
    });
  });
});

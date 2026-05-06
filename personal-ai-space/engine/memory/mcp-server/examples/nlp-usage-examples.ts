/**
 * NLP Interface Usage Examples
 *
 * Practical examples of how to use the NLP router with pi-memory tools.
 */

import { NLPRouter, IntentType, ToolMap, ToolResult } from "../src/nlp-interface";

/**
 * Example 1: Basic NLP routing without tool execution
 */
async function example1_basicRouting() {
  console.log("=== Example 1: Basic NLP Routing ===\n");

  const router = new NLPRouter();

  // Route various user inputs
  const examples = [
    "remember I like TypeScript",
    "what do I know about databases?",
    "forget my old config",
    "show me lessons",
    "how much memory is used?",
  ];

  for (const input of examples) {
    const route = router.route(input);
    console.log(`Input: "${input}"`);
    console.log(`Intent: ${route.intent}`);
    console.log(`Tool: ${route.toolCall.toolName}`);
    console.log(`Explanation: ${route.explanation}`);
    console.log(`Confidence: ${(route.confidence * 100).toFixed(0)}%\n`);
  }
}

/**
 * Example 2: NLP with tool execution
 */
async function example2_withToolExecution() {
  console.log("=== Example 2: NLP with Tool Execution ===\n");

  const router = new NLPRouter();

  // Create mock tool handlers
  const mockTools: ToolMap = {
    memory_remember: async (params) => {
      console.log("Tool: memory_remember");
      console.log("Params:", params);
      return {
        success: true,
        data: {
          key: params.key,
          value: params.value,
          stored: true,
        },
      };
    },

    memory_search: async (params) => {
      console.log("Tool: memory_search");
      console.log("Query:", params.query);
      return {
        success: true,
        data: [
          { key: "pref.language", value: "TypeScript", confidence: 0.95 },
          { key: "tool.editor", value: "VSCode", confidence: 0.85 },
        ],
      };
    },

    memory_stats: async (params) => {
      console.log("Tool: memory_stats");
      return {
        success: true,
        data: {
          semantic: 42,
          lessons: 15,
          events: 250,
        },
      };
    },
  };

  // Execute NLP-routed commands
  const commands = [
    "remember I use Docker",
    "what do I know about testing?",
    "tell me my memory stats",
  ];

  for (const command of commands) {
    console.log(`\nExecuting: "${command}"`);
    const result = await router.handle(command, mockTools);
    console.log("Result:", JSON.stringify(result, null, 2));
  }
}

/**
 * Example 3: Conversational interface
 */
async function example3_conversational() {
  console.log("\n=== Example 3: Conversational Interface ===\n");

  const router = new NLPRouter();

  // Without tool execution - just get responses
  console.log("Mode: Confirmation mode (no tool execution)\n");

  const inputs = [
    "remember I like Python",
    "what about git workflows?",
    "show me lessons about security",
  ];

  for (const input of inputs) {
    const response = await router.conversational(input);
    console.log(`User: "${input}"`);
    console.log(`Router: ${response}\n`);
  }
}

/**
 * Example 4: Custom parameter extraction
 */
async function example4_parameterExtraction() {
  console.log("\n=== Example 4: Parameter Extraction ===\n");

  const router = new NLPRouter();

  // Examples showing how parameters are extracted
  const testCases = [
    {
      input: "i'm sure I like TypeScript",
      description: "High confidence",
    },
    {
      input: "remember my editor is vim",
      description: "Explicit key-value",
    },
    {
      input: "save that i prefer TDD approach",
      description: "Multi-word value",
    },
    {
      input: "remember project.myapp.language = Rust",
      description: "Explicit category prefix",
    },
    {
      input: "maybe I like Docker",
      description: "Low confidence modifier",
    },
  ];

  for (const test of testCases) {
    const route = router.route(test.input);
    console.log(`${test.description}`);
    console.log(`Input: "${test.input}"`);
    if (route.toolCall.toolName === "memory_remember") {
      console.log(`Extracted:`);
      console.log(`  Key: ${route.toolCall.params.key}`);
      console.log(`  Value: ${route.toolCall.params.value}`);
      console.log(
        `  Confidence: ${((route.toolCall.params.confidence as number) * 100).toFixed(0)}%`
      );
    }
    console.log("");
  }
}

/**
 * Example 5: System prompt generation for LLM
 */
async function example5_systemPrompt() {
  console.log("=== Example 5: System Prompt Generation ===\n");

  const router = new NLPRouter();

  // Generate base system prompt
  const basePrompt = router.generateSystemPrompt();
  console.log("Base system prompt length:", basePrompt.length, "characters");
  console.log("Contains extraction rules:", basePrompt.includes("Category Detection"));

  // Generate with custom examples
  const customPrompt = router.generateSystemPrompt([
    {
      input: "i'm definitely a fan of functional programming",
      output:
        '{"toolName": "memory_remember", "params": {"key": "pref.paradigm", "value": "functional programming", "confidence": 0.95}}',
    },
    {
      input: "search for commit message conventions",
      output:
        '{"toolName": "memory_search", "params": {"query": "commit message conventions"}}',
    },
  ]);

  console.log("Custom prompt length:", customPrompt.length, "characters");
  console.log("Contains custom examples:", customPrompt.includes("functional programming"));
}

/**
 * Example 6: Integration with pi-memory bootstrap
 */
async function example6_bootstrapIntegration() {
  console.log("\n=== Example 6: Integration with Bootstrap ===\n");

  // This example shows how to integrate with the existing bootstrap.ts
  // Note: This is pseudo-code since we don't have PiMemoryServer in scope

  const router = new NLPRouter();

  // Simulate tool handlers that match bootstrap.ts tools
  const piMemoryTools: ToolMap = {
    memory_search: async (params) => {
      // This would call server.handleMemorySearch in real usage
      return {
        success: true,
        data: [],
      };
    },

    memory_remember: async (params) => {
      // This would call server.handleMemoryRemember in real usage
      return {
        success: true,
        data: params,
      };
    },

    memory_forget: async (params) => {
      // This would call server.handleMemoryForget in real usage
      return {
        success: true,
        data: { deleted: params.key },
      };
    },

    memory_lessons: async (params) => {
      // This would call server.handleMemoryLessons in real usage
      return {
        success: true,
        data: [],
      };
    },

    memory_stats: async (params) => {
      // This would call server.handleMemoryStats in real usage
      return {
        success: true,
        data: { semantic: 0, lessons: 0, events: 0 },
      };
    },
  };

  // Now use NLP to route user queries to these tools
  const userQueries = [
    "remember that I prefer conventional commits",
    "what are my project notes?",
    "show me what I've learned",
  ];

  for (const query of userQueries) {
    console.log(`Query: "${query}"`);
    const result = await router.handle(query, piMemoryTools);
    console.log(`Success: ${result.success}`);
    if (result.data) {
      console.log(`Data keys: ${Object.keys(result.data as Record<string, unknown>).join(", ")}`);
    }
    console.log("");
  }
}

/**
 * Example 7: Error handling
 */
async function example7_errorHandling() {
  console.log("=== Example 7: Error Handling ===\n");

  const router = new NLPRouter();

  // Test with various error conditions
  const testCases = [
    { input: "", description: "Empty input" },
    { input: "xyz qwerty asdf", description: "Gibberish input" },
    { input: "   ", description: "Whitespace only" },
  ];

  for (const test of testCases) {
    console.log(`Test: ${test.description}`);
    console.log(`Input: "${test.input}"`);

    const route = router.route(test.input);
    console.log(`Intent: ${route.intent}`);
    console.log(`Confidence: ${route.confidence}`);
    console.log(`Explanation: ${route.explanation}\n`);
  }

  // Test with missing tools
  console.log("Test: Missing tool handler");
  const route = router.route("remember I like Rust");
  const missingTools: ToolMap = {}; // No tools defined

  const result = await router.handle("remember I like Rust", missingTools);
  console.log(`Success: ${result.success}`);
  console.log(`Error: ${result.error}\n`);
}

/**
 * Example 8: Real-world workflow
 */
async function example8_realWorldWorkflow() {
  console.log("=== Example 8: Real-world Workflow ===\n");

  const router = new NLPRouter();

  // Simulate a conversation workflow
  const userInteractions = [
    "Hi, remember I use TypeScript for my projects",
    "I'm definitely a fan of TDD",
    "I prefer vim as my editor",
    "What languages do I know?",
    "Show me lessons learned",
    "How much have I learned so far?",
  ];

  console.log("User Conversation Workflow:\n");

  for (const interaction of userInteractions) {
    const route = router.route(interaction);

    if (route.intent === IntentType.UNKNOWN) {
      console.log(`User: ${interaction}`);
      console.log("Router: I didn't understand that. Could you rephrase?\n");
    } else {
      console.log(`User: ${interaction}`);
      console.log(`Router: ${route.explanation}`);
      console.log(`[Would execute: ${route.toolCall.toolName}]\n`);
    }
  }
}

/**
 * Run all examples
 */
async function runAllExamples() {
  try {
    await example1_basicRouting();
    await example2_withToolExecution();
    await example3_conversational();
    await example4_parameterExtraction();
    await example5_systemPrompt();
    await example6_bootstrapIntegration();
    await example7_errorHandling();
    await example8_realWorldWorkflow();

    console.log("\n✅ All examples completed successfully!");
  } catch (error) {
    console.error("❌ Error running examples:", error);
  }
}

// Export for use in other files
export {
  example1_basicRouting,
  example2_withToolExecution,
  example3_conversational,
  example4_parameterExtraction,
  example5_systemPrompt,
  example6_bootstrapIntegration,
  example7_errorHandling,
  example8_realWorldWorkflow,
  runAllExamples,
};

// Run examples if this file is executed directly
if (require.main === module) {
  runAllExamples().catch(console.error);
}

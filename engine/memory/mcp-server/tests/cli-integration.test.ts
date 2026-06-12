import { MemoryStore } from "../src/store.js";
import { Injector } from "../src/injector.js";

/**
 * Test script for CLI functionality
 */
async function testCLI() {
  console.log("🧪 Testing CLI components...\n");

  // Test 1: Initialize MemoryStore
  console.log("Test 1: Initialize MemoryStore");
  const store = new MemoryStore();
  store.initialize({
    dbPath: ":memory:",
    logFn: (msg) => console.log(`  [STORE] ${msg}`),
  });
  console.log("✅ Store initialized\n");

  // Test 2: Initialize Injector
  console.log("Test 2: Initialize Injector");
  const injector = new Injector(store, {
    logFn: (msg) => console.log(`  [INJECTOR] ${msg}`),
  });
  console.log("✅ Injector initialized\n");

  // Test 3: Add facts
  console.log("Test 3: Add facts");
  store.addFact("TypeScript", "Statically typed superset of JavaScript", 0.95, "Languages", "test");
  store.addFact("React", "JavaScript library for building UIs with components", 0.92, "Libraries", "test");
  store.addFact("SQL", "Language for querying databases", 0.88, "Databases", "test");
  const facts = store.listFacts(undefined, 10);
  console.log(`✅ Added ${facts.length} facts\n`);

  // Test 4: Search facts
  console.log("Test 4: Search facts");
  const searchResults = injector.searchFacts("TypeScript", 5);
  console.log(`✅ Search returned ${searchResults.length} results`);
  searchResults.forEach((result) => {
    console.log(`   - ${result.entry.key}: relevance ${Math.round(result.relevance * 100)}%`);
  });
  console.log();

  // Test 5: Add lessons
  console.log("Test 5: Add lessons");
  store.addLesson("Always test before deployment", 0, "Best Practices", "test");
  store.addLesson("Never hardcode secrets", 1, "Security", "test");
  const lessons = store.listLessons(undefined, undefined, 10);
  console.log(`✅ Added ${lessons.length} lessons\n`);

  // Test 6: Get stats
  console.log("Test 6: Get stats");
  const stats = store.getStats();
  console.log(`✅ Stats:`);
  console.log(`   - Facts: ${stats.semantic}`);
  console.log(`   - Lessons: ${stats.lessons}`);
  console.log(`   - Events: ${stats.events}`);
  console.log();

  // Test 7: Get config
  console.log("Test 7: Get Injector config");
  const config = injector.getConfig();
  console.log(`✅ Config:`);
  console.log(`   - Context Budget: ${config.contextBudget}`);
  console.log(`   - Min Confidence: ${Math.round(config.minConfidence * 100)}%`);
  console.log(`   - Injection Mode: ${config.injectionMode}`);
  console.log();

  // Test 8: Format context block
  console.log("Test 8: Build context block");
  const contextBlock = injector.buildContextBlock({ query: "TypeScript", limit: 10 });
  console.log(`✅ Context block generated:`);
  console.log(`   - Semantic entries: ${contextBlock.stats.semanticCount}`);
  console.log(`   - Lessons: ${contextBlock.stats.lessonCount}`);
  console.log(`   - Total characters: ${contextBlock.stats.totalCharacters}`);
  console.log();

  // Test 9: Format memory prompt
  console.log("Test 9: Format memory prompt");
  const prompt = injector.formatMemoryPrompt("TypeScript");
  console.log(`✅ Memory prompt generated (${prompt.length} chars)`);
  console.log();

  console.log("🎉 All tests passed!\n");
}

// Run tests
testCLI().catch((error) => {
  console.error("❌ Test failed:", error);
  process.exit(1);
});

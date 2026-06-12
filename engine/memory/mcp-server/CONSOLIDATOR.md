# Consolidator Engine - API Reference

## Overview

The `Consolidator` class is the core engine for extracting, deduplicating, and storing learned knowledge from AI agent sessions. It provides intelligent memory consolidation using LLM-based extraction and pattern recognition.

## Key Features

✓ **LLM-based Knowledge Extraction** - Uses any LLM (Claude, OpenAI, etc) to extract structured knowledge  
✓ **Intelligent Deduplication** - Exact match + Jaccard similarity (≥0.7 threshold)  
✓ **Confidence Filtering** - Only stores facts with ≥0.8 confidence  
✓ **Flexible LLM Support** - Accepts any LLM client implementing ILMClient interface  
✓ **Graceful Error Handling** - Handles LLM failures, malformed JSON, and edge cases  
✓ **Category Prefixes** - Supports pref.*, project.*, tool.*, user.* patterns  
✓ **TypeScript Strict Mode** - Fully typed with zero implicit any  

## Installation & Setup

```typescript
import { Consolidator, MockLLMClient } from './src/consolidator';
import { MemoryStore } from './src/store';

// Initialize store
const store = new MemoryStore();
store.initialize({
  dbPath: '/path/to/memory.db',
  logFn: (msg) => console.log(msg)
});

// Create consolidator with LLM client
const llmClient = new YourLLMClient(); // Must implement ILMClient
const consolidator = new Consolidator(llmClient);
```

## Core API

### 1. Consolidate a Session

```typescript
const result = await consolidator.consolidateSession(store, {
  userMessages: ["What's the best way to deploy?"],
  assistantMessages: ["I recommend using git push with webhooks"],
  cwd: "/projects/myapp",
  sessionId: "session-123"
});

// Result:
{
  semanticAdded: 1,           // New facts stored
  lessonsAdded: 1,            // New lessons stored
  semanticDuplicated: 0,      // Exact duplicate facts
  lessonsDuplicated: 0,       // Duplicate lessons
  factsRejectedByConfidence: 1, // Low confidence facts
  errors: []                  // Any errors encountered
}
```

### 2. Extract Knowledge

```typescript
const extracted = await consolidator.extractKnowledge({
  userMessages: [...],
  assistantMessages: [...],
  cwd: "/projects/myapp"
});

// Result:
{
  facts: [
    { key: "pref.deploy_method", value: "git push + webhooks", confidence: 0.95 },
    ...
  ],
  lessons: [
    { rule: "Always use git webhooks for deployment", category: "devops", negative: false },
    ...
  ]
}
```

### 3. Deduplicate Facts

```typescript
const existingFacts = store.listFacts(undefined, 1000);
const uniqueFacts = consolidator.deduplicateFacts(newFacts, existingFacts);
```

### 4. Deduplicate Lessons

```typescript
const existingLessons = store.listLessons(undefined, undefined, 1000);
const uniqueLessons = consolidator.deduplicateLessons(newLessons, existingLessons);
```

### 5. Calculate Jaccard Similarity

```typescript
const similarity = consolidator.jaccardSimilarity(
  "Use sed to insert lines into files",
  "Never use echo >> for vault, use sed instead"
);
// Returns: 0.5 - 0.7 range (similar enough to deduplicate at 0.7 threshold)
```

### 6. Build Consolidation Prompt

```typescript
const prompt = consolidator.buildConsolidationPrompt({
  userMessages: [...],
  assistantMessages: [...],
  cwd: "/projects/myapp",
  sessionId: "session-123"
});

// Prompt structure:
// - Clear instructions on what to extract
// - Emphasis on confidence ≥0.8
// - Category prefix guidance
// - Session message history
// - JSON response format specification
```

### 7. Parse LLM Response

```typescript
const extracted = consolidator.parseConsolidationResponse(llmResponseText);

// Handles:
// - Raw JSON
// - Markdown code blocks (```json ... ```)
// - Malformed JSON (returns empty result)
// - Confidence normalization to [0, 1]
// - Missing optional fields
```

### 8. Apply Extracted Memory

```typescript
const result = consolidator.applyExtracted(store, extracted, "consolidation");

// Applies with:
// - Confidence filtering (≥0.8)
// - Exact deduplication
// - Similarity deduplication
// - Per-fact/lesson error handling
```

## Types & Interfaces

### ExtractedFact
```typescript
interface ExtractedFact {
  key: string;              // e.g. "pref.editor", "project.myapp.language"
  value: string;            // Preference or pattern value
  confidence: number;       // 0.0 - 1.0 (only stored if ≥0.8)
  category?: string;        // Optional grouping category
}
```

### ExtractedLesson
```typescript
interface ExtractedLesson {
  rule: string;             // The lesson/correction/validated approach
  category?: string;        // e.g. "vault", "git", "deployment"
  negative: boolean;        // true = "avoid", false = "validated"
}
```

### ConsolidationInput
```typescript
interface ConsolidationInput {
  userMessages: string[];       // Messages from user during session
  assistantMessages: string[];  // Messages from assistant
  cwd?: string;                 // Optional working directory context
  sessionId?: string;           // Optional session identifier
}
```

### ConsolidationResult
```typescript
interface ConsolidationResult {
  semanticAdded: number;              // New facts added
  lessonsAdded: number;               // New lessons added
  semanticDuplicated: number;         // Duplicate facts rejected
  lessonsDuplicated: number;          // Duplicate lessons rejected
  factsRejectedByConfidence: number;  // Low-confidence facts
  errors: string[];                   // Errors encountered
}
```

### ILMClient
```typescript
interface ILMClient {
  generateText(prompt: string): Promise<string>;
}
```

Implement this to use any LLM:
```typescript
class AnthropicClient implements ILMClient {
  async generateText(prompt: string): Promise<string> {
    const response = await anthropic.messages.create({
      model: "claude-3-5-sonnet-20241022",
      max_tokens: 2048,
      messages: [{role: "user", content: prompt}]
    });
    return response.content[0].type === 'text' ? response.content[0].text : '';
  }
}
```

## Configuration Constants

```typescript
export const DEDUP_CONFIG = {
  MIN_CONFIDENCE: 0.8,           // Minimum confidence to store a fact
  JACCARD_THRESHOLD: 0.7,        // Similarity threshold for lesson deduplication
};
```

## Algorithms

### Jaccard Similarity
Used to detect semantic duplicates in lessons:

```
Similarity = |intersection| / |union|
           = common_tokens / total_unique_tokens

Examples:
- "Use vim for editing" vs "Use vim for coding" = 0.67
- "Use sed for insert" vs "Use sed to insert"  = 0.86 (≥0.7 → duplicate)
```

### Confidence Filtering
Only facts with confidence ≥0.8 are stored to avoid noise:
```
Input: [{key, value, confidence: 0.75}, ...]
Output: [] (rejected - below threshold)
```

### Exact Deduplication
Fast O(1) lookup for duplicate detection:
```typescript
// Facts: O(1) by exact key match
existingKeys.has(fact.key)

// Lessons: O(n) case-insensitive text comparison
existing.some(l => l.text.toLowerCase() === lesson.rule.toLowerCase())
```

### Similarity Deduplication
O(n) Jaccard similarity check:
```typescript
existingLessons.some(l =>
  jaccardSimilarity(newLesson.rule, l.text) >= JACCARD_THRESHOLD
)
```

## Workflow Example

```typescript
// 1. During session, collect messages
const sessionMessages = {
  userMessages: ["How should I structure Go projects?"],
  assistantMessages: ["Go recommends flat package structure for simple apps"]
};

// 2. At session end, consolidate
const result = await consolidator.consolidateSession(store, sessionMessages);

// 3. Results are stored in database
// store.listFacts() → [{key: "project.go.structure", value: "flat", ...}]

// 4. Next session, facts are injected as context
// Agent remembers: "For Go projects, use flat package structure"
```

## Error Handling

All methods handle errors gracefully:

```typescript
// LLM unavailable → returns empty extraction
const extracted = await consolidator.extractKnowledge({...});
// extracted = { facts: [], lessons: [] }

// Malformed JSON → returns empty extraction
const parsed = consolidator.parseConsolidationResponse("not json");
// parsed = { facts: [], lessons: [] }

// Low confidence facts → included in result errors
const result = await consolidator.consolidateSession(store, input);
// result.factsRejectedByConfidence = count of low-conf facts
```

## Testing

Run the comprehensive test suite:
```bash
npm test -- tests/consolidator.test.ts
```

Manual verification:
```bash
npx tsx verify-consolidator.ts
```

## Best Practices

1. **Call only on meaningful sessions** (≥3 messages)
   ```typescript
   if (userMessages.length >= 3) {
     await consolidator.consolidateSession(store, input);
   }
   ```

2. **Provide working directory context**
   ```typescript
   const result = await consolidator.consolidateSession(store, {
     userMessages: [...],
     assistantMessages: [...],
     cwd: process.cwd(),  // Helps with project-specific patterns
     sessionId: generateId()
   });
   ```

3. **Monitor consolidation results**
   ```typescript
   if (result.errors.length > 0) {
     logger.warn("Consolidation errors:", result.errors);
   }
   console.log(`Added ${result.semanticAdded} facts, ${result.lessonsAdded} lessons`);
   ```

4. **Use appropriate confidence in LLM prompt**
   - The consolidation prompt explicitly requires ≥0.8 confidence
   - Let the LLM decide confidence, don't adjust manually
   - Trust high-confidence extractions (0.9+)

5. **Category organization**
   - Use `project.*` for project-specific patterns
   - Use `pref.*` for personal preferences
   - Use `tool.*` for tool configurations
   - Use `user.*` for user identity/metadata

## Performance Characteristics

- **Jaccard similarity**: O(n) per comparison
- **Exact dedup (facts)**: O(1) average
- **Exact dedup (lessons)**: O(n) for text comparison
- **Similarity dedup**: O(n²) worst case (all lessons vs all existing)
- **JSON parsing**: O(n) with markdown extraction
- **Full consolidation**: O(n*m) where n=new facts, m=existing facts

For typical sessions (10-100 facts, 1000s existing):
- Full consolidation: <100ms
- Store operations: <50ms
- LLM extraction: 1-5s (network bound)

## See Also

- `src/store.ts` - Memory persistence layer (SQLite)
- `src/injector.ts` - Context injection for agent prompts
- `tests/consolidator.test.ts` - Full test suite

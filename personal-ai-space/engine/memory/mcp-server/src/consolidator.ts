import { MemoryStore, SemanticEntry, LessonEntry } from "./store.js";

/**
 * Types and Interfaces for Consolidator
 */

/**
 * Extracted fact from LLM consolidation
 */
export interface ExtractedFact {
  key: string;
  value: string;
  confidence: number; // 0.0 - 1.0
  category?: string;
}

/**
 * Extracted lesson from LLM consolidation
 */
export interface ExtractedLesson {
  rule: string;
  category?: string;
  negative: boolean; // true = "avoid", false = "do"
}

/**
 * Complete knowledge extracted from a session
 */
export interface ExtractedMemory {
  facts: ExtractedFact[];
  lessons: ExtractedLesson[];
}

/**
 * Consolidation input: session messages to analyze
 */
export interface ConsolidationInput {
  userMessages: string[];
  assistantMessages: string[];
  cwd?: string;
  sessionId?: string;
}

/**
 * Result of applying extracted memory to store
 */
export interface ConsolidationResult {
  semanticAdded: number;
  lessonsAdded: number;
  semanticDuplicated: number;
  lessonsDuplicated: number;
  factsRejectedByConfidence: number;
  errors: string[];
}

/**
 * LLM client interface - supports any LLM (Claude, OpenAI, etc.)
 */
export interface ILMClient {
  generateText(prompt: string): Promise<string>;
}

/**
 * Deduplication thresholds
 */
export const DEDUP_CONFIG = {
  MIN_CONFIDENCE: 0.8, // Only store facts with ≥0.8 confidence
  JACCARD_THRESHOLD: 0.7, // Lessons are dupes if Jaccard similarity ≥0.7
};

/**
 * Consolidator: Main class for extracting and deduplicating knowledge
 *
 * Key features:
 * - Calls LLM to extract structured knowledge from session messages
 * - Deduplicates facts using exact match (fast path)
 * - Deduplicates lessons using Jaccard similarity
 * - Filters by confidence threshold (≥0.8)
 * - Graceful error handling with comprehensive logging
 */
export class Consolidator {
  private llmClient: ILMClient;
  private logFn: (msg: string) => void = () => {};

  constructor(llmClient: ILMClient, logFn?: (msg: string) => void) {
    this.llmClient = llmClient;
    if (logFn) this.logFn = logFn;
  }

  /**
   * Main consolidation workflow:
   * 1. Build LLM prompt from session messages
   * 2. Call LLM to extract facts and lessons
   * 3. Deduplicate against existing memory
   * 4. Apply to store with confidence filtering
   *
   * @returns ConsolidationResult with counts and errors
   */
  public async consolidateSession(
    store: MemoryStore,
    input: ConsolidationInput
  ): Promise<ConsolidationResult> {
    const result: ConsolidationResult = {
      semanticAdded: 0,
      lessonsAdded: 0,
      semanticDuplicated: 0,
      lessonsDuplicated: 0,
      factsRejectedByConfidence: 0,
      errors: [],
    };

    try {
      // Validate input
      if (input.userMessages.length === 0 && input.assistantMessages.length === 0) {
        this.log("Warning: No messages provided for consolidation");
        return result;
      }

      this.log(
        `Starting consolidation: ${input.userMessages.length} user + ${input.assistantMessages.length} assistant messages`
      );

      // Step 1: Build prompt
      const prompt = this.buildConsolidationPrompt(input);

      // Step 2: Call LLM
      this.log("Calling LLM for extraction...");
      const llmResponse = await this.callLLMForExtraction(prompt);

      // Step 3: Parse LLM response
      const extracted = this.parseConsolidationResponse(llmResponse);
      this.log(
        `LLM extracted: ${extracted.facts.length} facts, ${extracted.lessons.length} lessons`
      );

      // Step 4: Get existing memory for deduplication
      const existingFacts = store.listFacts(undefined, 10000);
      const existingLessons = store.listLessons(undefined, undefined, 10000);

      // Step 5: Deduplicate facts
      for (const fact of extracted.facts) {
        try {
          // Confidence check first
          if (fact.confidence < DEDUP_CONFIG.MIN_CONFIDENCE) {
            result.factsRejectedByConfidence++;
            this.log(
              `Fact rejected (low confidence): ${fact.key}=${fact.value} (${fact.confidence})`
            );
            continue;
          }

          // Exact match check
          const duplicate = this.findExactDuplicateFact(fact, existingFacts);
          if (duplicate) {
            result.semanticDuplicated++;
            this.log(`Fact is exact duplicate: ${fact.key}`);
            continue;
          }

          // Add to store
          store.addFact(
            fact.key,
            fact.value,
            fact.confidence,
            fact.category,
            "consolidation"
          );
          result.semanticAdded++;
          this.log(
            `Added fact: ${fact.key}=${fact.value} (confidence: ${fact.confidence})`
          );
        } catch (error) {
          const msg = error instanceof Error ? error.message : String(error);
          result.errors.push(`Error adding fact ${fact.key}: ${msg}`);
          this.log(`ERROR adding fact: ${msg}`);
        }
      }

      // Step 6: Deduplicate lessons
      for (const lesson of extracted.lessons) {
        try {
          // Exact match check
          const exactDuplicate = this.findExactDuplicateLesson(lesson, existingLessons);
          if (exactDuplicate) {
            result.lessonsDuplicated++;
            this.log(`Lesson is exact duplicate: ${lesson.rule.substring(0, 50)}...`);
            continue;
          }

          // Similarity check (Jaccard)
          const similarDuplicate = this.findSimilarDuplicateLesson(
            lesson,
            existingLessons
          );
          if (similarDuplicate) {
            result.lessonsDuplicated++;
            this.log(
              `Lesson is similar duplicate (Jaccard): ${lesson.rule.substring(0, 50)}...`
            );
            continue;
          }

          // Add to store
          store.addLesson(
            lesson.rule,
            lesson.negative ? 1 : 0,
            lesson.category,
            "consolidation"
          );
          result.lessonsAdded++;
          this.log(
            `Added lesson (negative=${lesson.negative}): ${lesson.rule.substring(0, 50)}...`
          );
        } catch (error) {
          const msg = error instanceof Error ? error.message : String(error);
          result.errors.push(`Error adding lesson: ${msg}`);
          this.log(`ERROR adding lesson: ${msg}`);
        }
      }

      this.log(
        `Consolidation complete: +${result.semanticAdded} facts, +${result.lessonsAdded} lessons, ${result.semanticDuplicated} fact dupes, ${result.lessonsDuplicated} lesson dupes`
      );

      return result;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      result.errors.push(`Consolidation failed: ${msg}`);
      this.log(`FATAL ERROR: ${msg}`);
      return result;
    }
  }

  /**
   * Build consolidation prompt for LLM
   *
   * Instructions to LLM:
   * - Extract ONLY high-confidence facts (≥0.8)
   * - Extract preferences (pref.*, tool.*, project.*)
   * - Extract learned corrections (lessons)
   * - Avoid extracting ephemeral data, code snippets, or paths
   */
  public buildConsolidationPrompt(input: ConsolidationInput): string {
    const userMsgsText = input.userMessages.map((m, i) => `[User ${i + 1}]: ${m}`).join("\n\n");

    const assistantMsgsText = input.assistantMessages
      .map((m, i) => `[Assistant ${i + 1}]: ${m}`)
      .join("\n\n");

    const cwdHint = input.cwd ? `\nWorking directory: ${input.cwd}` : "";
    const sessionIdHint = input.sessionId ? `\nSession ID: ${input.sessionId}` : "";

    const prompt = `Extract structured knowledge from this conversation session.

INSTRUCTIONS:
1. Extract ONLY facts with confidence ≥ 0.8
2. Use these key prefixes:
   - "pref.*" for user preferences
   - "project.*" for project-specific patterns
   - "tool.*" for tool preferences
   - "user.*" for user identity
3. Extract learned corrections as lessons
4. For lessons, mark "negative: true" for things to AVOID, "negative: false" for validated approaches
5. Focus on PATTERNS, not ephemeral data
6. Ignore code snippets, file paths, and session-specific details

DO EXTRACT:
- Preferences (commit style, testing approach, documentation habits)
- Project patterns (languages, frameworks, DI tools)
- Tool preferences (sed vs echo, vim vs nano)
- Corrections (things user corrected you on)
- Validated approaches (things user confirmed work)

DON'T EXTRACT:
- Code patterns or project structure
- Git history or blame info
- Exact commands (unless they encode a pattern)
- File contents or code snippets
- Ephemeral task details or in-progress work
- Activity summaries ("we worked on X today")

${cwdHint}${sessionIdHint}

CONVERSATION TO ANALYZE:

${userMsgsText}

${assistantMsgsText}

RESPOND WITH VALID JSON (no markdown, no extra text):
{
  "facts": [
    { "key": "string", "value": "string", "confidence": 0.8 to 1.0, "category": "string (optional)" }
  ],
  "lessons": [
    { "rule": "string (clear, actionable statement)", "category": "string (optional)", "negative": true or false }
  ]
}`;

    return prompt;
  }

  /**
   * Call LLM for extraction
   *
   * Wraps the LLM client call with error handling
   */
  private async callLLMForExtraction(prompt: string): Promise<string> {
    try {
      const response = await this.llmClient.generateText(prompt);
      return response;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`LLM extraction failed: ${msg}`);
    }
  }

  /**
   * Parse JSON response from LLM
   *
   * Handles:
   * - Markdown code blocks (```json ... ```)
   * - Raw JSON
   * - Malformed responses with fallback
   */
  public parseConsolidationResponse(jsonText: string): ExtractedMemory {
    try {
      // Extract JSON from markdown code blocks if present
      let cleanedText = jsonText;
      const codeBlockMatch = jsonText.match(/```(?:json)?\s*([\s\S]*?)```/);
      if (codeBlockMatch) {
        cleanedText = codeBlockMatch[1];
      }

      // Parse JSON
      const parsed = JSON.parse(cleanedText);

      // Validate and normalize response
      const facts: ExtractedFact[] = [];
      const lessons: ExtractedLesson[] = [];

      // Process facts
      if (Array.isArray(parsed.facts)) {
        for (const fact of parsed.facts) {
          if (fact && typeof fact === "object" && fact.key && fact.value) {
            facts.push({
              key: String(fact.key).trim(),
              value: String(fact.value).trim(),
              confidence: Math.min(1.0, Math.max(0.0, Number(fact.confidence) || 0.8)),
              category: fact.category ? String(fact.category).trim() : undefined,
            });
          }
        }
      }

      // Process lessons
      if (Array.isArray(parsed.lessons)) {
        for (const lesson of parsed.lessons) {
          if (lesson && typeof lesson === "object" && lesson.rule) {
            lessons.push({
              rule: String(lesson.rule).trim(),
              category: lesson.category ? String(lesson.category).trim() : undefined,
              negative: Boolean(lesson.negative),
            });
          }
        }
      }

      return { facts, lessons };
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR parsing LLM response: ${msg}`);
      this.log(`Response text: ${jsonText.substring(0, 200)}`);
      // Return empty result on parse error (graceful fallback)
      return { facts: [], lessons: [] };
    }
  }

  /**
   * Extract knowledge from session messages
   *
   * Convenience method that combines buildPrompt + callLLM + parse
   *
   * @returns ExtractedMemory or empty result on failure
   */
  public async extractKnowledge(input: ConsolidationInput): Promise<ExtractedMemory> {
    try {
      const prompt = this.buildConsolidationPrompt(input);
      const response = await this.callLLMForExtraction(prompt);
      return this.parseConsolidationResponse(response);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`Knowledge extraction failed: ${msg}`);
      return { facts: [], lessons: [] };
    }
  }

  /**
   * Deduplicate facts against existing facts
   *
   * Uses exact key matching (fast path)
   *
   * @returns Array of non-duplicate facts
   */
  public deduplicateFacts(
    newFacts: ExtractedFact[],
    existingFacts: SemanticEntry[]
  ): ExtractedFact[] {
    const existingKeys = new Set(existingFacts.map((f: SemanticEntry) => f.key));
    return newFacts.filter((fact: ExtractedFact) => !existingKeys.has(fact.key));
  }

  /**
   * Deduplicate lessons against existing lessons
   *
   * Two strategies:
   * 1. Exact text match (fast path)
   * 2. Jaccard similarity (≥0.7 threshold)
   *
   * @returns Array of non-duplicate lessons
   */
  public deduplicateLessons(
    newLessons: ExtractedLesson[],
    existingLessons: LessonEntry[]
  ): ExtractedLesson[] {
    const result: ExtractedLesson[] = [];

    for (const newLesson of newLessons) {
      // Check exact match
      const exactMatch = existingLessons.some(
        (existing: LessonEntry) => existing.text.toLowerCase() === newLesson.rule.toLowerCase()
      );
      if (exactMatch) {
        continue;
      }

      // Check Jaccard similarity
      const hasSimilar = existingLessons.some(
        (existing: LessonEntry) =>
          this.jaccardSimilarity(newLesson.rule, existing.text) >=
          DEDUP_CONFIG.JACCARD_THRESHOLD
      );
      if (hasSimilar) {
        continue;
      }

      result.push(newLesson);
    }

    return result;
  }

  /**
   * Apply extracted memory to store
   *
   * Handles:
   * - Confidence filtering (≥0.8)
   * - Exact deduplication
   * - Similarity deduplication
   * - Error handling per fact/lesson
   *
   * @returns ConsolidationResult with counts
   */
  public applyExtracted(
    store: MemoryStore,
    extracted: ExtractedMemory,
    source: string = "consolidation"
  ): ConsolidationResult {
    const result: ConsolidationResult = {
      semanticAdded: 0,
      lessonsAdded: 0,
      semanticDuplicated: 0,
      lessonsDuplicated: 0,
      factsRejectedByConfidence: 0,
      errors: [],
    };

    try {
      // Get existing facts and lessons
      const existingFacts = store.listFacts(undefined, 10000);
      const existingLessons = store.listLessons(undefined, undefined, 10000);

      // Apply facts
      for (const fact of extracted.facts) {
        try {
          // Confidence check
          if (fact.confidence < DEDUP_CONFIG.MIN_CONFIDENCE) {
            result.factsRejectedByConfidence++;
            continue;
          }

          // Exact duplicate check
          const isDuplicate = existingFacts.some((f) => f.key === fact.key);
          if (isDuplicate) {
            result.semanticDuplicated++;
            continue;
          }

          // Add to store
          store.addFact(
            fact.key,
            fact.value,
            fact.confidence,
            fact.category,
            source
          );
          result.semanticAdded++;
        } catch (error) {
          const msg = error instanceof Error ? error.message : String(error);
          result.errors.push(`Error adding fact: ${msg}`);
        }
      }

      // Apply lessons
      for (const lesson of extracted.lessons) {
        try {
          // Exact duplicate check
          const exactDuplicate = existingLessons.some(
            (l) => l.text.toLowerCase() === lesson.rule.toLowerCase()
          );
          if (exactDuplicate) {
            result.lessonsDuplicated++;
            continue;
          }

          // Similarity check
          const similarDuplicate = existingLessons.some(
            (l) =>
              this.jaccardSimilarity(lesson.rule, l.text) >=
              DEDUP_CONFIG.JACCARD_THRESHOLD
          );
          if (similarDuplicate) {
            result.lessonsDuplicated++;
            continue;
          }

          // Add to store
          store.addLesson(
            lesson.rule,
            lesson.negative ? 1 : 0,
            lesson.category,
            source
          );
          result.lessonsAdded++;
        } catch (error) {
          const msg = error instanceof Error ? error.message : String(error);
          result.errors.push(`Error adding lesson: ${msg}`);
        }
      }

      return result;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      result.errors.push(`Failed to apply extracted memory: ${msg}`);
      return result;
    }
  }

  /**
   * Jaccard Similarity: Measure of similarity between two strings
   *
   * Formula: |intersection| / |union|
   * where intersection and union are based on token sets
   *
   * Used for deduplicating lessons that express the same idea
   * with different wording.
   *
   * @returns Score from 0.0 (completely different) to 1.0 (identical)
   */
  public jaccardSimilarity(str1: string, str2: string): number {
    // Tokenize by splitting on whitespace and punctuation
    const tokens1 = new Set(
      str1
        .toLowerCase()
        .split(/\s+/)
        .filter((t) => t.length > 0)
    );

    const tokens2 = new Set(
      str2
        .toLowerCase()
        .split(/\s+/)
        .filter((t) => t.length > 0)
    );

    if (tokens1.size === 0 && tokens2.size === 0) {
      return 1.0; // Both empty, identical
    }

    if (tokens1.size === 0 || tokens2.size === 0) {
      return 0.0; // One empty, not similar
    }

    // Calculate intersection
    const intersection = Array.from(tokens1).filter((t) => tokens2.has(t)).length;

    // Calculate union
    const union = tokens1.size + tokens2.size - intersection;

    return intersection / union;
  }

  /**
   * Helper: Find exact duplicate fact by key
   */
  private findExactDuplicateFact(
    fact: ExtractedFact,
    existingFacts: SemanticEntry[]
  ): SemanticEntry | undefined {
    return existingFacts.find((f) => f.key === fact.key);
  }

  /**
   * Helper: Find exact duplicate lesson by text
   */
  private findExactDuplicateLesson(
    lesson: ExtractedLesson,
    existingLessons: LessonEntry[]
  ): LessonEntry | undefined {
    return existingLessons.find(
      (l) => l.text.toLowerCase() === lesson.rule.toLowerCase()
    );
  }

  /**
   * Helper: Find similar duplicate lesson by Jaccard similarity
   */
  private findSimilarDuplicateLesson(
    lesson: ExtractedLesson,
    existingLessons: LessonEntry[]
  ): LessonEntry | undefined {
    return existingLessons.find(
      (l) =>
        this.jaccardSimilarity(lesson.rule, l.text) >=
        DEDUP_CONFIG.JACCARD_THRESHOLD
    );
  }

  /**
   * Internal logging
   */
  private log(msg: string): void {
    this.logFn(`[Consolidator] ${msg}`);
  }
}

/**
 * Helper: Create a mock LLM client for testing
 *
 * Useful for development and testing before connecting real LLMs
 */
export class MockLLMClient implements ILMClient {
  async generateText(prompt: string): Promise<string> {
    // Return mock extraction result
    return JSON.stringify({
      facts: [
        {
          key: "pref.editor",
          value: "vim",
          confidence: 0.9,
          category: "tools",
        },
      ],
      lessons: [
        {
          rule: "Always use vim for editing, not nano",
          category: "tools",
          negative: false,
        },
      ],
    });
  }
}

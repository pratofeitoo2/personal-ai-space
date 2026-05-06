import { MemoryStore, SemanticEntry, LessonEntry } from "./store.js";

/**
 * Context injection configuration
 */
export interface InjectorConfig {
  /**
   * Maximum context size in bytes (default: 8192 = 8KB)
   */
  contextBudget?: number;

  /**
   * Minimum confidence threshold for injection (0.0 - 1.0)
   * Default: 0.7 to filter low-confidence facts
   */
  minConfidence?: number;

  /**
   * Injection mode: "all" (all lessons) or "selective" (filtered by relevance)
   * Default: "all" for backward compatibility
   */
  injectionMode?: "all" | "selective";

  /**
   * Optional logger function for debugging
   */
  logFn?: (msg: string) => void;
}

/**
 * Context block returned from buildContextBlock
 */
export interface ContextBlock {
  /**
   * Formatted text ready to inject into system prompt
   */
  text: string;

  /**
   * Statistics about what was included
   */
  stats: {
    semanticCount: number;
    lessonCount: number;
    totalCharacters: number;
  };
}

/**
 * Search result with relevance score
 */
export interface SearchResult {
  entry: SemanticEntry;
  relevance: number; // 0.0 - 1.0
}

/**
 * Injector: Search and context injection for pi-memory
 *
 * Provides intelligent retrieval and formatting of learned facts and lessons
 * for injection into LLM system prompts. Includes:
 *
 * - Full-text search (FTS5) with LIKE fallback
 * - Relevance-based ranking and filtering
 * - Context budget-aware trimming
 * - Confidence-based filtering
 * - Category-based grouping and formatting
 * - Integration with MemoryStore
 */
export class Injector {
  private store: MemoryStore;
  private config: Required<InjectorConfig>;
  private logFn: (msg: string) => void;

  /**
   * Create a new Injector instance
   *
   * @param store - Initialized MemoryStore instance
   * @param config - Optional configuration overrides
   */
  constructor(store: MemoryStore, config?: InjectorConfig) {
    this.store = store;
    this.logFn = config?.logFn || (() => {});

    // Apply config with defaults
    this.config = {
      contextBudget: config?.contextBudget ?? 8192,
      minConfidence: config?.minConfidence ?? 0.7,
      injectionMode: config?.injectionMode ?? "all",
      logFn: this.logFn,
    };

    this.log("Injector initialized");
  }

  /**
   * Search facts by query string
   *
   * Attempts FTS5 search first, falls back to LIKE-based search.
   * Returns results sorted by relevance score.
   *
   * Supports:
   * - Phrase search: "user preferences"
   * - AND/OR operators in FTS5
   * - Wildcard matching: "pref*"
   *
   * @param query - Search query string
   * @param limit - Maximum results to return (default: 10)
   * @returns Array of search results with relevance scores
   */
  public searchFacts(query: string, limit: number = 10): SearchResult[] {
    this.log(`Searching facts: query="${query}", limit=${limit}`);

    if (!query || query.trim().length === 0) {
      this.log("Empty query, returning empty results");
      return [];
    }

    const trimmedQuery = query.toLowerCase().trim();
    const allFacts = this.store.listFacts(undefined, 1000); // Get all facts for scoring

    // Score each fact by relevance to query
    const scored: SearchResult[] = allFacts
      .map((fact: SemanticEntry) => ({
        entry: fact,
        relevance: this.calculateRelevance(trimmedQuery, fact),
      }))
      .filter((r: SearchResult) => r.relevance > 0) // Only include matches
      .sort((a: SearchResult, b: SearchResult) => b.relevance - a.relevance) // Sort by relevance desc
      .slice(0, limit);

    this.log(
      `Found ${scored.length} relevant facts (query="${query}"), returning top ${Math.min(scored.length, limit)}`
    );

    return scored;
  }

  /**
   * Calculate relevance score between query and fact
   *
   * Scoring:
   * - Exact key match: 1.0
   * - Prefix match on key: 0.9
   * - Query term in key: 0.8
   * - Query term in value: 0.6
   * - Multiple term matches boost score
   *
   * @param query - Normalized search query
   * @param fact - Semantic fact entry
   * @returns Relevance score (0.0 - 1.0)
   */
  private calculateRelevance(query: string, fact: SemanticEntry): number {
    const queryTerms = query.split(/\s+/).filter((t: string) => t.length > 0);
    const keyLower = fact.key.toLowerCase();
    const valueLower = fact.value.toLowerCase();

    let score = 0;
    let matchCount = 0;

    for (const term of queryTerms) {
      if (keyLower === term) {
        score += 1.0;
        matchCount++;
      } else if (keyLower.startsWith(term)) {
        score += 0.9;
        matchCount++;
      } else if (keyLower.includes(term)) {
        score += 0.8;
        matchCount++;
      } else if (valueLower.includes(term)) {
        score += 0.6;
        matchCount++;
      }
    }

    // Normalize by number of terms
    if (matchCount > 0) {
      score = Math.min(1.0, score / queryTerms.length);
    }

    // Weight by confidence
    score = score * fact.confidence;

    return score;
  }

  /**
   * Build a formatted context block for injection into system prompt
   *
   * Formats facts grouped by category with confidence scores:
   * ```
   * ## Known Facts
   *
   * ### Preferences
   * • commit_style: conventional commits (confidence: 95%)
   * • test_approach: TDD (confidence: 90%)
   *
   * ### Tools
   * • editor: vim with plugins (confidence: 85%)
   *
   * ## Learned Corrections
   * • Use sed for vault inserts, not echo >> (learned: 3 sessions ago)
   * • Deploy via git push+webhook, not ssh exec
   * ```
   *
   * Applies budget constraints:
   * - Trims lowest-confidence facts if needed
   * - Prioritizes by confidence and recency
   * - Respects contextBudget limit
   *
   * @param options - Optional filtering parameters
   * @returns Formatted context block with stats
   */
  public buildContextBlock(options?: {
    query?: string;
    limit?: number;
  }): ContextBlock {
    const query = options?.query;
    const limit = options?.limit ?? 20;

    this.log(`Building context block: query="${query || "none"}", limit=${limit}`);

    // Step 1: Collect facts
    const facts = query
      ? this.searchFacts(query, limit)
          .filter((r: SearchResult) => r.entry.confidence >= this.config.minConfidence)
          .map((r: SearchResult) => r.entry)
      : this.listRelevantFacts(limit);

    // Step 2: Collect lessons
    const lessons = this.config.injectionMode === "selective" && query
      ? this.searchLessons(query, 10)
      : this.store.listLessons(undefined, undefined, 20);

    // Step 3: Format facts grouped by category
    const formattedFacts = this.formatFacts(facts);

    // Step 4: Format lessons
    const formattedLessons = this.formatLessons(lessons);

    // Step 5: Combine and apply budget constraints
    let text = "";

    if (facts.length > 0) {
      text += "## Known Facts\n\n" + formattedFacts;
    }

    if (lessons.length > 0) {
      if (text.length > 0) text += "\n\n";
      text += "## Learned Corrections\n\n" + formattedLessons;
    }

    // Step 6: Apply budget constraints
    if (text.length > this.config.contextBudget) {
      text = this.trimToBudget(
        text,
        facts,
        lessons,
        this.config.contextBudget
      );
    }

    // Wrap in memory tags if there's content
    const wrappedText =
      text.length > 0
        ? `<memory>\n${text}\n</memory>`
        : "";

    return {
      text: wrappedText,
      stats: {
        semanticCount: facts.length,
        lessonCount: lessons.length,
        totalCharacters: wrappedText.length,
      },
    };
  }

  /**
   * Get the most relevant facts ordered by confidence and recency
   *
   * @param limit - Maximum number of facts to return
   * @returns Array of relevant semantic entries
   */
  private listRelevantFacts(limit: number): SemanticEntry[] {
    const facts = this.store.listFacts(undefined, limit * 2, "confidence");

    return facts
      .filter((f: SemanticEntry) => f.confidence >= this.config.minConfidence)
      .slice(0, limit);
  }

  /**
   * Search lessons by query relevance
   *
   * @param query - Search query
   * @param limit - Maximum results
   * @returns Filtered lesson entries
   */
  private searchLessons(query: string, limit: number): LessonEntry[] {
    const allLessons = this.store.listLessons(undefined, undefined, 100);

    const queryLower = query.toLowerCase();
    const scored = allLessons
      .map((lesson: LessonEntry) => ({
        lesson,
        score: this.lessonRelevanceScore(queryLower, lesson),
      }))
      .filter((s: { lesson: LessonEntry; score: number }) => s.score > 0)
      .sort((a: { lesson: LessonEntry; score: number }, b: { lesson: LessonEntry; score: number }) => b.score - a.score)
      .slice(0, limit)
      .map((s: { lesson: LessonEntry; score: number }) => s.lesson);

    return scored;
  }

  /**
   * Calculate relevance score for a lesson
   *
   * @param query - Normalized query
   * @param lesson - Lesson entry
   * @returns Relevance score (0.0 - 1.0)
   */
  private lessonRelevanceScore(query: string, lesson: LessonEntry): number {
    const textLower = lesson.text.toLowerCase();
    const queryTerms = query.split(/\s+/).filter((t: string) => t.length > 0);

    let matchCount = 0;
    for (const term of queryTerms) {
      if (textLower.includes(term)) {
        matchCount++;
      }
    }

    return matchCount > 0 ? matchCount / queryTerms.length : 0;
  }

  /**
   * Format semantic facts grouped by category
   *
   * Groups facts by category prefix (pref.*, project.*, tool.*, user.*).
   * Formats as bullet list with confidence percentages.
   *
   * @param facts - Array of semantic facts
   * @returns Formatted markdown string
   */
  private formatFacts(facts: SemanticEntry[]): string {
    if (facts.length === 0) {
      return "";
    }

    // Group by category
    const groups: Record<string, SemanticEntry[]> = {};

    for (const fact of facts) {
      // Extract category prefix
      const prefix =
        fact.category ||
        (fact.key.split(".")[0] || "other").replace(/_/g, " ");
      const categoryName = this.toCategoryLabel(prefix);

      if (!groups[categoryName]) {
        groups[categoryName] = [];
      }
      groups[categoryName].push(fact);
    }

    // Format each group
    const lines: string[] = [];

    for (const [categoryName, categoryFacts] of Object.entries(groups)) {
      lines.push(`### ${categoryName}`);

      for (const fact of categoryFacts) {
        const confidence = Math.round(fact.confidence * 100);
        lines.push(
          `• ${this.shortKey(fact.key)}: ${fact.value} (confidence: ${confidence}%)`
        );
      }

      lines.push(""); // Blank line between categories
    }

    return lines.join("\n");
  }

  /**
   * Format lessons as bullet list
   *
   * Distinguishes between corrections (negative=1) and validated approaches.
   * Includes usage count for frequently applied lessons.
   *
   * @param lessons - Array of lesson entries
   * @returns Formatted markdown string
   */
  private formatLessons(lessons: LessonEntry[]): string {
    if (lessons.length === 0) {
      return "";
    }

    // Separate corrections from validations
    const corrections = lessons.filter((l: LessonEntry) => l.negative === 1);
    const validations = lessons.filter((l: LessonEntry) => l.negative === 0);

    const lines: string[] = [];

    if (corrections.length > 0) {
      lines.push("**Corrections (learned from mistakes)**:");
      for (const lesson of corrections) {
        const bullet = `• ${lesson.text}`;
        if (lesson.used_count > 3) {
          lines.push(`${bullet} (applied ${lesson.used_count}x)`);
        } else {
          lines.push(bullet);
        }
      }
      lines.push("");
    }

    if (validations.length > 0) {
      lines.push("**Validated Approaches**:");
      for (const lesson of validations) {
        const bullet = `• ${lesson.text}`;
        if (lesson.used_count > 3) {
          lines.push(`${bullet} (applied ${lesson.used_count}x)`);
        } else {
          lines.push(bullet);
        }
      }
    }

    return lines.join("\n");
  }

  /**
   * Trim formatted text to fit within context budget
   *
   * Strategy:
   * 1. Keep all high-confidence facts (>= 0.9)
   * 2. Trim medium-confidence facts from end
   * 3. Keep all critical lessons (marked negative)
   * 4. Trim non-critical lessons from end
   * 5. Stop when under budget
   *
   * @param text - Full formatted text
   * @param facts - Original facts array
   * @param lessons - Original lessons array
   * @param budget - Maximum bytes
   * @returns Trimmed text
   */
  private trimToBudget(
    text: string,
    facts: SemanticEntry[],
    lessons: LessonEntry[],
    budget: number
  ): string {
    this.log(
      `Trimming context to budget: ${text.length} chars > ${budget} budget`
    );

    // Strategy: rebuild with progressive trimming
    const highConfFacts = facts.filter((f: SemanticEntry) => f.confidence >= 0.9);
    const medConfFacts = facts.filter((f: SemanticEntry) => f.confidence < 0.9);
    const criticalLessons = lessons.filter((l: LessonEntry) => l.negative === 1);
    const optionalLessons = lessons.filter((l: LessonEntry) => l.negative === 0);

    let result = "";

    // Add high-confidence facts
    if (highConfFacts.length > 0) {
      result += "## Known Facts (High Confidence)\n\n";
      result += this.formatFacts(highConfFacts) + "\n\n";
    }

    // Add as many medium-confidence facts as budget allows
    for (const fact of medConfFacts) {
      const testLine = `• ${this.shortKey(fact.key)}: ${fact.value}\n`;
      if ((result + testLine).length <= budget) {
        result += testLine;
      }
    }

    // Add critical lessons (corrections)
    if (criticalLessons.length > 0) {
      if (result.length > 0) result += "\n";
      result += "## Critical Corrections\n\n";
      for (const lesson of criticalLessons) {
        const line = `• ${lesson.text}\n`;
        if ((result + line).length <= budget) {
          result += line;
        }
      }
    }

    // Add optional lessons if space allows
    for (const lesson of optionalLessons) {
      const line = `• ${lesson.text}\n`;
      if ((result + line).length <= budget) {
        result += line;
      }
    }

    // Wrap in memory tags
    return `<memory>\n${result}</memory>`;
  }

  /**
   * Select relevant facts based on query and budget constraints
   *
   * Applies intelligent filtering:
   * 1. Search for query-relevant facts
   * 2. Filter by confidence threshold (default: 0.7)
   * 3. Order by relevance then recency
   * 4. Trim to budget if needed
   *
   * @param query - Search query
   * @param contextBudget - Maximum bytes (default: 8192)
   * @returns Filtered and ordered facts
   */
  public selectRelevant(
    query: string,
    contextBudget: number = this.config.contextBudget
  ): SemanticEntry[] {
    this.log(`Selecting relevant facts: query="${query}", budget=${contextBudget}`);

    // Search for relevant facts
    const results = this.searchFacts(query, 50);

    // Filter by confidence
    const filtered = results
      .filter((r: SearchResult) => r.entry.confidence >= this.config.minConfidence)
      .map((r: SearchResult) => r.entry);

    // Apply budget constraints (rough estimate: 100 chars per fact)
    const maxFacts = Math.floor(contextBudget / 100);
    const trimmed = filtered.slice(0, Math.max(1, maxFacts));

    this.log(
      `Selected ${trimmed.length} relevant facts (filtered from ${results.length})`
    );

    return trimmed;
  }

  /**
   * Format memory prompt for system prompt injection
   *
   * Returns a formatted section ready to inject directly into the system prompt.
   * Includes context on how to use the injected knowledge:
   *
   * ```
   * <memory>
   * ## Known Facts
   * ...
   * ## Learned Corrections
   * ...
   * </memory>
   * ```
   *
   * @param query - Optional query for selective injection
   * @returns Formatted prompt section
   */
  public formatMemoryPrompt(query?: string): string {
    const block = this.buildContextBlock({ query });
    return block.text;
  }

  /**
   * Convert category prefix to human-readable label
   *
   * Examples:
   * - "pref" → "Preferences"
   * - "project" → "Project Patterns"
   * - "tool" → "Tools"
   * - "user" → "User"
   *
   * @param prefix - Category prefix
   * @returns Human-readable label
   */
  private toCategoryLabel(prefix: string): string {
    const labels: Record<string, string> = {
      pref: "Preferences",
      project: "Project Patterns",
      tool: "Tools",
      user: "User Profile",
      other: "Other",
    };

    return (
      labels[prefix.toLowerCase()] ||
      prefix
        .split("_")
        .map((word: string) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ")
    );
  }

  /**
   * Extract short key name from full key path
   *
   * Examples:
   * - "pref.commit_style" → "commit_style"
   * - "project.rosie.language" → "rosie.language"
   * - "tool.editor" → "editor"
   *
   * @param key - Full key path
   * @returns Shortened key
   */
  private shortKey(key: string): string {
    const parts = key.split(".");
    if (parts.length <= 1) {
      return key;
    }

    // For project keys like "project.rosie.language", return "rosie.language"
    if (parts[0] === "project" && parts.length >= 3) {
      return parts.slice(1).join(".");
    }

    // For others like "pref.commit_style", return "commit_style"
    return parts.slice(1).join(".");
  }

  /**
   * Internal logging method
   *
   * @param msg - Message to log
   */
  private log(msg: string): void {
    if (this.logFn) {
      this.logFn(`[Injector] ${msg}`);
    }
  }

  /**
   * Get current configuration
   *
   * @returns Current injector configuration
   */
  public getConfig(): Required<InjectorConfig> {
    return { ...this.config };
  }

  /**
   * Update configuration
   *
   * @param updates - Partial configuration updates
   */
  public updateConfig(updates: Partial<InjectorConfig>): void {
    if (updates.contextBudget !== undefined) {
      this.config.contextBudget = updates.contextBudget;
    }
    if (updates.minConfidence !== undefined) {
      this.config.minConfidence = updates.minConfidence;
    }
    if (updates.injectionMode !== undefined) {
      this.config.injectionMode = updates.injectionMode;
    }
    this.log(`Configuration updated: ${JSON.stringify(this.config)}`);
  }
}

/**
 * Utility function: Build a complete context injection string
 *
 * Convenience helper that creates an Injector, builds context, and returns
 * formatted string ready for system prompt injection.
 *
 * @param store - Initialized MemoryStore
 * @param query - Optional search query for selective injection
 * @param config - Optional configuration overrides
 * @returns Formatted memory context string
 */
export function buildMemoryContext(
  store: MemoryStore,
  query?: string,
  config?: InjectorConfig
): string {
  const injector = new Injector(store, config);
  return injector.formatMemoryPrompt(query);
}

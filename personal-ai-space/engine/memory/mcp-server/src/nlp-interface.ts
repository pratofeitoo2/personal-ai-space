/**
 * NLP Interface for pi-memory
 *
 * Natural language processing layer that interprets user intent and routes
 * to appropriate memory tools. Uses keyword/pattern matching for intent
 * detection and parameter extraction.
 *
 * Features:
 * - Intent detection (REMEMBER, SEARCH, FORGET, LESSONS, STATS)
 * - Parameter extraction (category, confidence, key/value pairs)
 * - Tool routing (converts NL to tool calls)
 * - Response formatting (conversational output)
 * - System prompt generation for optional LLM extraction
 */

/**
 * Supported intent types
 */
export enum IntentType {
  REMEMBER = "REMEMBER",
  SEARCH = "SEARCH",
  FORGET = "FORGET",
  LESSONS = "LESSONS",
  STATS = "STATS",
  UNKNOWN = "UNKNOWN",
}

/**
 * Tool call representation
 */
export interface ToolCall {
  toolName: string;
  params: Record<string, unknown>;
}

/**
 * Route result with intent and tool call
 */
export interface RouteResult {
  intent: IntentType;
  toolCall: ToolCall;
  confidence: number; // 0.0 - 1.0, confidence in the routing decision
  explanation: string; // Human-readable explanation of the routing
}

/**
 * Tool execution result
 */
export interface ToolResult {
  success: boolean;
  data?: unknown;
  error?: string;
}

/**
 * Map of tool handlers
 */
export type ToolMap = Record<
  string,
  (params: Record<string, unknown>) => Promise<ToolResult>
>;

/**
 * Confidence levels for parameter extraction
 */
export enum ConfidenceLevel {
  LOW = 0.6,
  MEDIUM = 0.75,
  HIGH = 0.85,
  VERY_HIGH = 0.95,
}

/**
 * Category prefixes recognized by the system
 */
const CATEGORY_PREFIXES = ["pref", "project", "tool", "user"];

/**
 * Keywords for intent detection
 */
const INTENT_KEYWORDS = {
  [IntentType.REMEMBER]: [
    "remember",
    "save",
    "note",
    "store",
    "i like",
    "i prefer",
    "i use",
    "my",
    "add",
    "mark as",
  ],
  [IntentType.SEARCH]: [
    "what",
    "find",
    "search",
    "tell me about",
    "show me what",
    "do you know",
    "what do i know",
    "look up",
    "lookup",
  ],
  [IntentType.FORGET]: [
    "forget",
    "delete",
    "remove",
    "clear",
    "erase",
    "unlearn",
  ],
  [IntentType.LESSONS]: [
    "show me lessons",
    "lessons learned",
    "lessons",
    "learned",
    "corrections",
    "what corrections",
  ],
  [IntentType.STATS]: [
    "stats",
    "statistics",
    "memory",
    "how much",
    "status",
    "tell me my memory",
  ],
};

/**
 * Confidence modifiers in user input
 */
const CONFIDENCE_MODIFIERS = {
  "i'm sure": ConfidenceLevel.VERY_HIGH,
  "i'm certain": ConfidenceLevel.VERY_HIGH,
  definitely: ConfidenceLevel.VERY_HIGH,
  certain: ConfidenceLevel.VERY_HIGH,
  sure: ConfidenceLevel.HIGH,
  confident: ConfidenceLevel.HIGH,
  pretty: ConfidenceLevel.HIGH,
  likely: ConfidenceLevel.MEDIUM,
  think: ConfidenceLevel.MEDIUM,
  guess: ConfidenceLevel.LOW,
  maybe: ConfidenceLevel.LOW,
  perhaps: ConfidenceLevel.LOW,
  uncertain: ConfidenceLevel.LOW,
};

/**
 * NLPRouter: Natural language processing router for pi-memory
 *
 * Converts natural language queries into tool calls and executes them.
 * Provides confidence scores and human-readable explanations for debugging.
 */
export class NLPRouter {
  /**
   * Route a natural language input to a tool call
   *
   * @param userInput - Natural language user input
   * @returns Route result with intent, tool call, and confidence
   */
  public route(userInput: string): RouteResult {
    if (!userInput || userInput.trim().length === 0) {
      return {
        intent: IntentType.UNKNOWN,
        toolCall: { toolName: "noop", params: {} },
        confidence: 0,
        explanation: "Empty input",
      };
    }

    const normalized = userInput.toLowerCase().trim();

    // Detect intent
    const intentResult = this.detectIntent(normalized);
    if (intentResult.intent === IntentType.UNKNOWN) {
      return {
        intent: IntentType.UNKNOWN,
        toolCall: { toolName: "noop", params: {} },
        confidence: 0,
        explanation: "Could not determine intent from input",
      };
    }

    // Extract parameters based on intent
    let toolCall: ToolCall;
    let explanation: string;

    switch (intentResult.intent) {
      case IntentType.REMEMBER: {
        const { key, value, confidence } = this.extractRememberParams(
          userInput,
          normalized
        );
        toolCall = {
          toolName: "memory_remember",
          params: {
            key: key || "unspecified",
            value: value || "unspecified",
            ...(confidence !== undefined && { confidence }),
          },
        };
        explanation = `Storing fact: ${key} = ${value}${confidence !== undefined ? ` (confidence: ${(confidence * 100).toFixed(0)}%)` : ""}`;
        break;
      }

      case IntentType.SEARCH: {
        const query = this.extractSearchQuery(userInput, normalized);
        toolCall = {
          toolName: "memory_search",
          params: { query: query || "general" },
        };
        explanation = `Searching for: "${query}"`;
        break;
      }

      case IntentType.FORGET: {
        const key = this.extractForgetKey(userInput, normalized);
        toolCall = {
          toolName: "memory_forget",
          params: { key: key || "unspecified" },
        };
        explanation = `Forgetting: ${key}`;
        break;
      }

      case IntentType.LESSONS: {
        const category = this.extractLessonsCategory(userInput, normalized);
        toolCall = {
          toolName: "memory_lessons",
          params: category ? { category } : {},
        };
        explanation = `Retrieving lessons${category ? ` for category: ${category}` : ""}`;
        break;
      }

      case IntentType.STATS: {
        toolCall = {
          toolName: "memory_stats",
          params: {},
        };
        explanation = "Getting memory statistics";
        break;
      }

      default: {
        return {
          intent: IntentType.UNKNOWN,
          toolCall: { toolName: "noop", params: {} },
          confidence: 0,
          explanation: "Invalid intent",
        };
      }
    }

    return {
      intent: intentResult.intent,
      toolCall,
      confidence: intentResult.confidence,
      explanation,
    };
  }

  /**
   * Execute a tool call and return the result
   *
   * @param userInput - Original user input
   * @param tools - Map of tool handlers
   * @returns Promise resolving to tool result
   */
  public async handle(
    userInput: string,
    tools: ToolMap
  ): Promise<ToolResult> {
    try {
      const route = this.route(userInput);

      if (route.intent === IntentType.UNKNOWN) {
        return {
          success: false,
          error: "Could not understand your request. Try: 'remember X', 'search Y', 'forget Z', 'show lessons', or 'stats'",
        };
      }

      const tool = tools[route.toolCall.toolName];
      if (!tool) {
        return {
          success: false,
          error: `Tool not found: ${route.toolCall.toolName}`,
        };
      }

      const result = await tool(route.toolCall.params);
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return {
        success: false,
        error: `Error executing tool: ${message}`,
      };
    }
  }

  /**
   * Conversational interface - provides friendly responses to user input
   *
   * @param userInput - User natural language input
   * @param context - Optional conversation context
   * @param tools - Optional tool handlers for execution
   * @returns Promise resolving to conversational response string
   */
  public async conversational(
    userInput: string,
    context?: string,
    tools?: ToolMap
  ): Promise<string> {
    if (!userInput || userInput.trim().length === 0) {
      return "I didn't hear anything. Try asking me something like: 'What do I know about databases?' or 'Remember I like TypeScript'";
    }

    const route = this.route(userInput);

    if (route.intent === IntentType.UNKNOWN) {
      return `I'm not sure what you mean. Could you rephrase? For example:
- "Remember I use Docker" (to store a preference)
- "What do I know about testing?" (to search)
- "Forget my old config" (to delete a fact)
- "Show me lessons" (to see learned corrections)
- "What's my memory usage?" (to get statistics)`;
    }

    // If tools are provided, execute the tool
    if (tools) {
      const result = await this.handle(userInput, tools);
      if (!result.success) {
        return `I encountered an error: ${result.error || "Unknown error"}`;
      }
      return this.formatToolResult(route.intent, result.data);
    }

    // Otherwise, provide a confirmation of what would happen
    return `I understood that you want to: ${route.explanation}. ${context ? `Context: ${context}` : ""}`;
  }

  /**
   * Generate a system prompt for LLM extraction (optional advanced mode)
   *
   * @param examples - Optional examples to include in the prompt
   * @returns System prompt string for LLM parameter extraction
   */
  public generateSystemPrompt(examples?: Array<{ input: string; output: string }>): string {
    let prompt = `You are a parameter extraction system for a memory management tool.

Your task is to extract structured parameters from natural language user inputs and convert them into JSON tool calls.

## Tool Definitions

### memory_remember
Stores a fact in semantic memory.
Example input: "Remember I like TypeScript"
Output: {"toolName": "memory_remember", "params": {"key": "pref.language", "value": "TypeScript", "confidence": 0.95}}

### memory_search
Searches for facts in memory.
Example input: "What do I know about databases?"
Output: {"toolName": "memory_search", "params": {"query": "databases"}}

### memory_forget
Forgets a fact from memory.
Example input: "Forget my old config"
Output: {"toolName": "memory_forget", "params": {"key": "config.*"}}

### memory_lessons
Retrieves learned corrections.
Example input: "Show me lessons"
Output: {"toolName": "memory_lessons", "params": {}}

### memory_stats
Gets memory statistics.
Example input: "How much memory is used?"
Output: {"toolName": "memory_stats", "params": {}}

## Extraction Rules

1. **Category Detection**: Look for prefixes like "pref.", "project.", "tool.", "user."
2. **Confidence Levels**: Detect certainty modifiers:
   - "I'm sure" → 0.95
   - "definitely" → 0.95
   - "sure" → 0.85
   - "think" → 0.75
   - "maybe" → 0.6
   - (default) → 0.8

3. **Key/Value Extraction**: For REMEMBER intent, extract:
   - Key: category + topic (e.g., "pref.language")
   - Value: the fact/preference (e.g., "TypeScript")

4. **Query Extraction**: For SEARCH intent, extract the main topic

5. **Pattern Matching**: For FORGET intent, support wildcards (e.g., "config.*")

## Examples`;

    if (examples && examples.length > 0) {
      prompt += "\n\n### Custom Examples:\n";
      examples.forEach((ex) => {
        prompt += `\nInput: "${ex.input}"\nOutput: ${ex.output}`;
      });
    }

    prompt += `

## Output Format

Always respond with valid JSON containing:
{
  "toolName": "memory_remember" | "memory_search" | "memory_forget" | "memory_lessons" | "memory_stats",
  "params": {
    // parameters specific to the tool
  },
  "confidence": 0.0-1.0,
  "explanation": "human-readable explanation"
}

If you cannot extract parameters with confidence, respond with:
{
  "error": "reason why extraction failed"
}`;

    return prompt;
  }

  /**
   * Detect intent from normalized input
   *
   * @private
   * @param normalized - Lowercased, trimmed input
   * @returns Intent detection result with confidence
   */
  private detectIntent(
    normalized: string
  ): { intent: IntentType; confidence: number } {
    let bestMatch: IntentType = IntentType.UNKNOWN;
    let bestScore = 0;

    for (const [intent, keywords] of Object.entries(INTENT_KEYWORDS)) {
      let score = 0;
      let matchCount = 0;

      for (const keyword of keywords) {
        if (normalized.includes(keyword)) {
          matchCount++;
          // Exact phrase match gets higher score
          if (
            normalized.startsWith(keyword) ||
            normalized.endsWith(keyword)
          ) {
            score += 2;
          } else {
            score += 1;
          }
        }
      }

      // Normalize score
      const normalizedScore = score / Math.max(keywords.length, 1);

      if (normalizedScore > bestScore && matchCount > 0) {
        bestScore = normalizedScore;
        bestMatch = intent as IntentType;
      }
    }

    // Convert score to confidence (0-1)
    const confidence = Math.min(bestScore / 2, 1.0);

    return {
      intent: bestMatch,
      confidence: bestMatch === IntentType.UNKNOWN ? 0 : Math.max(0.51, confidence),
    };
  }

  /**
   * Extract parameters for REMEMBER intent
   *
   * @private
   * @param originalInput - Original user input
   * @param normalized - Lowercased, trimmed input
   * @returns Extracted key, value, and confidence
   */
  private extractRememberParams(
    originalInput: string,
    normalized: string
  ): { key?: string; value?: string; confidence?: number } {
    // Extract confidence modifier
    let confidence: number | undefined;
    for (const [modifier, level] of Object.entries(CONFIDENCE_MODIFIERS)) {
      if (normalized.includes(modifier)) {
        confidence = level;
        break;
      }
    }
    if (confidence === undefined) {
      confidence = ConfidenceLevel.HIGH; // Default confidence for REMEMBER
    }

    // Extract category if present
    let category = "pref"; // Default category
    for (const prefix of CATEGORY_PREFIXES) {
      if (normalized.includes(`${prefix}.`)) {
        category = prefix;
        break;
      }
    }

    // Extract key/value using patterns
    // Pattern 1: "remember I like X" → key: pref.language, value: X
    const likeMatch = originalInput.match(
      /(?:remember|i like|i prefer|i use)\s+(?:that\s+)?(?:i\s+)?(?:like|prefer|use)\s+(.+?)(?:\.|,|$)/i
    );
    if (likeMatch) {
      const value = likeMatch[1].trim();
      const key = this.inferKeyFromValue(value, category);
      return { key, value, confidence };
    }

    // Pattern 2: "remember key = value"
    const eqMatch = originalInput.match(/remember\s+(.+?)\s*=\s*(.+?)(?:\.|,|$)/i);
    if (eqMatch) {
      let key = eqMatch[1].trim();
      const value = eqMatch[2].trim();
      // Add category if not already present
      if (!key.includes(".")) {
        key = `${category}.${key}`;
      }
      return { key, value, confidence };
    }

    // Pattern 3: "save/note/store X as Y"
    const asMatch = originalInput.match(
      /(?:save|note|store|add)\s+(.+?)\s+as\s+(.+?)(?:\.|,|$)/i
    );
    if (asMatch) {
      const value = asMatch[2].trim();
      const key = `${category}.${asMatch[1].trim()}`;
      return { key, value, confidence };
    }

    // Pattern 4: "remember X" (extract after the verb)
    const verbMatch = originalInput.match(
      /(?:remember|save|note|store|add)\s+(.+?)(?:\.|,|$)/i
    );
    if (verbMatch) {
      const value = verbMatch[1].trim();
      const key = this.inferKeyFromValue(value, category);
      return { key, value, confidence };
    }

    return { confidence };
  }

  /**
   * Infer a structured key from a value
   *
   * @private
   * @param value - The value to infer from
   * @param category - The category prefix
   * @returns Inferred key
   */
  private inferKeyFromValue(value: string, category: string): string {
    // Extract first significant word as key
    const words = value.split(/\s+/);
    const key = words[0].toLowerCase().replace(/[^a-z0-9_]/g, "");
    return key ? `${category}.${key}` : `${category}.item`;
  }

  /**
   * Extract search query from SEARCH intent
   *
   * @private
   * @param originalInput - Original user input
   * @param normalized - Lowercased, trimmed input
   * @returns Search query
   */
  private extractSearchQuery(
    originalInput: string,
    normalized: string
  ): string {
    // Remove question mark
    const cleaned = originalInput.replace(/\?$/, "").trim();

    // Pattern 1: "what do i know about X?"
    const knowMatch = cleaned.match(
      /(?:what do i know about|tell me about|show me|search for|find)\s+(.+?)(?:\?|$)/i
    );
    if (knowMatch) {
      return knowMatch[1].trim();
    }

    // Pattern 2: "find X"
    const findMatch = cleaned.match(/(?:find|search)\s+(.+?)(?:$|\?)/i);
    if (findMatch) {
      return findMatch[1].trim();
    }

    // Pattern 3: Extract everything after common verbs
    const verbs = ["what", "find", "search", "tell me about", "show me"];
    for (const verb of verbs) {
      if (normalized.startsWith(verb)) {
        const remainder = cleaned.substring(verb.length).trim();
        if (remainder.length > 0) {
          return remainder;
        }
      }
    }

    return cleaned;
  }

  /**
   * Extract key to forget
   *
   * @private
   * @param originalInput - Original user input
   * @param normalized - Lowercased, trimmed input
   * @returns Key pattern to forget
   */
  private extractForgetKey(
    originalInput: string,
    normalized: string
  ): string {
    // Pattern 1: "forget X" - extract after forget/delete/remove
    // Use greedy match to capture everything including dots
    const forgetMatch = originalInput.match(
      /(?:forget|delete|remove|clear|erase)\s+(?:my\s+)?([a-zA-Z0-9_\.\*\-\s]+?)(?:\s*$)/i
    );
    if (forgetMatch) {
      const extracted = forgetMatch[1].trim();
      
      // If it already contains a dot, preserve it as-is (it's a complete key)
      if (extracted.includes(".")) {
        return extracted;
      }
      
      // If it's multi-word like "my old config", take the last word as the key
      const words = extracted.split(/\s+/);
      const lastWord = words[words.length - 1];
      
      // If last word already has wildcard, return as-is
      if (lastWord.includes("*")) {
        return lastWord;
      }
      
      // If single word without dot, add wildcard
      if (words.length === 1) {
        return `${lastWord}.*`;
      }
      
      // Multi-word phrase - use the last word with wildcard
      return `${lastWord}.*`;
    }

    return "*";
  }

  /**
   * Extract category for LESSONS intent
   *
   * @private
   * @param originalInput - Original user input
   * @param normalized - Lowercased, trimmed input
   * @returns Category filter or undefined
   */
  private extractLessonsCategory(
    originalInput: string,
    normalized: string
  ): string | undefined {
    // Pattern: "lessons about X" or "corrections for X"
    const categoryMatch = originalInput.match(
      /(?:lessons|corrections)\s+(?:about|for|in)\s+(.+?)(?:\.|,|$)/i
    );
    if (categoryMatch) {
      return categoryMatch[1].trim();
    }

    // Pattern: "show me lessons about X"
    const showLessonsMatch = originalInput.match(
      /show\s+(?:me\s+)?lessons\s+(?:about|for|in)\s+(.+?)(?:\.|,|$)/i
    );
    if (showLessonsMatch) {
      return showLessonsMatch[1].trim();
    }

    // Check for known categories
    for (const category of CATEGORY_PREFIXES) {
      if (normalized.includes(category)) {
        return category;
      }
    }

    return undefined;
  }

  /**
   * Format tool result into conversational response
   *
   * @private
   * @param intent - The intent type
   * @param data - The tool result data
   * @returns Formatted response string
   */
  private formatToolResult(intent: IntentType, data?: unknown): string {
    if (!data) {
      return "Operation completed.";
    }

    switch (intent) {
      case IntentType.REMEMBER: {
        const result = data as Record<string, unknown>;
        return `✓ Stored: ${result.key || "fact"} = ${result.value || "value"}${
          result.confidence ? ` (confidence: ${((result.confidence as number) * 100).toFixed(0)}%)` : ""
        }`;
      }

      case IntentType.SEARCH: {
        const results = Array.isArray(data) ? data : [data];
        if (results.length === 0) {
          return "No matches found.";
        }
        let response = `Found ${results.length} match${results.length === 1 ? "" : "es"}:\n`;
        results.forEach((r: unknown, i: number) => {
          const result = r as Record<string, unknown>;
          response += `${i + 1}. ${result.key || "Unknown"}: ${result.value || "N/A"}`;
          if (result.confidence) {
            response += ` (${((result.confidence as number) * 100).toFixed(0)}%)`;
          }
          response += "\n";
        });
        return response;
      }

      case IntentType.FORGET: {
        const result = data as Record<string, unknown>;
        return `✓ Forgot: ${result.key || "fact"}`;
      }

      case IntentType.LESSONS: {
        const lessons = Array.isArray(data) ? data : [data];
        if (lessons.length === 0) {
          return "No lessons found.";
        }
        let response = `Found ${lessons.length} lesson${lessons.length === 1 ? "" : "s"}:\n`;
        lessons.forEach((l: unknown, i: number) => {
          const lesson = l as Record<string, unknown>;
          const type = lesson.negative ? "❌ Avoid" : "✓ Do";
          response += `${i + 1}. ${type}: ${lesson.text || "N/A"}`;
          if (lesson.category) {
            response += ` [${lesson.category}]`;
          }
          response += "\n";
        });
        return response;
      }

      case IntentType.STATS: {
        const stats = data as Record<string, unknown>;
        return `Memory Stats:
- Facts stored: ${stats.semantic || 0}
- Lessons learned: ${stats.lessons || 0}
- Events tracked: ${stats.events || 0}`;
      }

      default:
        return JSON.stringify(data);
    }
  }
}

/**
 * Export helper function for quick routing
 */
export function createNLPRouter(): NLPRouter {
  return new NLPRouter();
}

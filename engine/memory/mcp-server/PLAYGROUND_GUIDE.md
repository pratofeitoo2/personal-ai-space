# π Memory Clone - Playground & Demo Guide

## Overview

The pi-memory-clone playground provides interactive demonstrations and examples of natural language memory usage patterns. It showcases how developers can use pi-memory for context-aware assistance.

## Files Created

### 1. `src/playground.ts` (25KB)
Comprehensive demonstration platform with 10 realistic example workflows:

**Features:**
- ConsoleFormatter utility class for beautiful terminal output
- Playground orchestrator with configurable demo selection
- 10 complete demo scenarios covering all major features
- Performance metrics and detailed statistics
- Auto-cleanup of temporary databases

**10 Demo Scenarios:**
1. **Developer Preferences** - Store and retrieve tool preferences (editor, language, testing approach)
2. **Search and Context Injection** - Natural language queries with relevance scoring
3. **Extract and Store Lessons** - Record corrections (negative lessons) and validations (positive lessons)
4. **Memory Deduplication** - Handle and merge duplicate facts with confidence updates
5. **Confidence-Based Filtering** - Filter facts by confidence thresholds
6. **Tool Integration Patterns** - Store configurations for Prettier, ESLint, Jest, etc.
7. **Project-Specific Context** - Organize facts by project (API, frontend, DevOps)
8. **Multi-Session Memory** - Show how memory evolves across sessions
9. **Context Budget Management** - Intelligent trimming when context exceeds budget
10. **Real-World Workflow** - Complex multi-step developer scenario

### 2. `src/demo-cli.ts` (19KB)
Interactive command-line interface for manual exploration and testing:

**Features:**
- DemoCli class with comprehensive command system
- Interactive REPL mode for manual testing
- Playground runner with verbose logging option
- Export memory to JSON for backup/analysis
- Comparison tool for tool-calling vs natural language approaches

**Interactive Commands:**
```
add-fact <key> <value> [confidence] [category]    Add a semantic fact
search <query>                                     Search facts by query
list-facts [prefix]                               List all or filtered facts
get-fact <key>                                    Get specific fact
delete-fact <key>                                 Delete a fact
add-lesson <text> [negative] [category]           Add a lesson
list-lessons [category]                           List lessons
context [query]                                   Build context block
stats                                             Show memory statistics
export [path]                                     Export to JSON
compare-approaches <scenario>                     Compare approaches
help                                              Show commands
exit / quit                                       Exit interactive mode
```

### 3. Updated `package.json`
Added 4 new npm scripts:

```json
"demo": "tsx src/demo-cli.ts --playground"
"demo:verbose": "tsx src/demo-cli.ts --playground --verbose"
"playground": "tsx src/playground.ts"
"interactive": "tsx src/demo-cli.ts --interactive"
```

## Usage

### Run All Demos (Default)
```bash
npm run demo
npm run playground
```

Both run all 10 demonstrations with performance metrics and comprehensive output.

### Verbose Mode
```bash
npm run demo:verbose
```

Shows detailed logs from the MemoryStore and Injector during execution.

### Interactive Mode
```bash
npm run interactive
```

Launch an interactive REPL for manual testing:
```
π> add-fact pref.editor "VS Code" 0.95 "Preferences"
✓ Added fact: pref.editor
  Value: VS Code
  Confidence: 95%
  Category: Preferences

π> search editor
📊 Search results for: "editor"
  ◆ pref.editor
    Value: VS Code
    Relevance: 92% | Confidence: 95%
```

## Demo Output Examples

### Developer Preferences
Shows how to store and retrieve developer tool preferences with high confidence:
- Editor preferences (VS Code with vim)
- Commit style (Conventional commits)
- Testing approach (TDD)
- Language choice (TypeScript)
- Code review mindset

### Search and Context Injection
Demonstrates natural language queries with relevance scoring:
- Query: "How do I set up the API framework?"
- Returns: Ranked facts by relevance (22%, 19%, 18%, etc.)
- Includes: Context size, fact count, lesson count

### Real-World Workflow
Complex 5-step scenario:
1. Load project context (task, codebase facts)
2. Natural language query (JWT token refresh)
3. Build context for LLM system prompt
4. Record solution and lessons
5. Show updated memory state

## Key Features Demonstrated

### 1. Natural Language Query System
- Full-text search with relevance scoring
- Multi-term query support
- Confidence-weighted results
- Contextual ranking

### 2. Confidence Management
- Facts stored with confidence scores (0.0 - 1.0)
- Threshold-based filtering (configurable)
- Confidence evolution over sessions
- High-confidence facts prioritized in context

### 3. Lesson Learning System
- **Corrections** (negative=1): Learned from mistakes
- **Validations** (negative=0): Confirmed best practices
- Usage counting for frequently applied lessons
- Category organization

### 4. Context Injection
- Formatted memory blocks ready for LLM prompts
- Budget-aware trimming (respects context budget)
- Category-based grouping
- Confidence percentages displayed

### 5. Deduplication and Updates
- Duplicate detection by key
- Confidence score updates
- Maintains single authoritative entry
- Tracks update timestamps

### 6. Performance Metrics
- Per-demo timing (milliseconds)
- Total execution time
- Memory statistics (facts, lessons, events)
- Average performance per demo

## Architecture

### ConsoleFormatter (Utility Class)
Beautiful terminal formatting:
```typescript
ConsoleFormatter.section("Title")      // Large section header
ConsoleFormatter.subsection("Title")   // Subsection header
ConsoleFormatter.arrow("Label")        // Arrow point
ConsoleFormatter.success("Label", "value")
ConsoleFormatter.example("Label", "content")
ConsoleFormatter.result("content")
ConsoleFormatter.timing("operation", ms)
```

### Playground Class
Main orchestrator with:
- Store initialization
- Injector configuration
- Demo execution loop
- Result collection
- Summary generation

### DemoCli Class
Interactive interface with:
- Command parsing and execution
- REPL mode management
- Data export functionality
- Comparison analysis

## Performance Characteristics

From typical run:
```
Total time: ~26ms
Average per demo: ~2.5ms
Memory statistics:
  - 54 semantic facts
  - 11 lessons
  - 68 audit events
```

## Example Workflows

### Workflow 1: API Development
1. Store API framework preference (Express.js + TypeScript)
2. Store database choice (PostgreSQL with migrations)
3. Store testing approach (Jest with supertest)
4. Query: "What's my API setup?"
5. Context injected with all relevant facts

### Workflow 2: Learning from Mistakes
1. Record correction: "Use parameterized queries, not string concat"
2. Record validation: "Always use dependency injection"
3. Next session: Corrections included in context
4. Less likely to repeat mistakes

### Workflow 3: Multi-Project Context
1. Store project.api.* facts
2. Store project.frontend.* facts
3. Store project.devops.* facts
4. Query by project: "How do I set up the frontend?"
5. Relevant facts automatically ranked and injected

## Best Practices Demonstrated

1. **High Confidence for Certainties**
   - Store definite facts at 0.9+ confidence
   - Use lower confidence for tentative ideas

2. **Organize by Category**
   - pref.* for preferences
   - project.* for project-specific info
   - tool.* for tool configurations
   - user.* for user profile info

3. **Learn from Mistakes**
   - Record negative lessons when you go wrong
   - Include details for future reference
   - Track usage to identify repeat issues

4. **Search Effectively**
   - Use natural language queries
   - System finds relevant facts by similarity
   - Combine with category prefixes for precision

5. **Budget Management**
   - Respect context budget limits
   - High-confidence facts prioritized
   - Critical lessons always included

## Extension Points

The playground can be extended with:

### New Demo Scenarios
Add to the `demos` array in `Playground.runAll()`:
```typescript
{ name: "my-demo", fn: () => this.demoMyFeature() }
```

### New Interactive Commands
Add to `DemoCli.processCommand()`:
```typescript
case "my-command":
  await this.myCommand(args);
  break;
```

### Custom Formatters
Extend `ConsoleFormatter` class:
```typescript
static myFormat(label: string, value: string): void {
  console.log(`  ❯ ${label}: ${value}`);
}
```

## Troubleshooting

### "Database is not open" error
- Ensure store is initialized before operations
- Check database path is writable
- Verify cleanup() doesn't close unopened database

### Empty demo output
- Run with `--verbose` flag for detailed logs
- Check TypeScript compilation with `npm run build`
- Verify Node.js version supports ES modules

### Interactive mode not responding
- Use `Ctrl+C` to exit
- Each command should complete quickly
- Check for syntax errors in commands

## Integration with pi-memory Server

The playground demonstrates the API used by:
- `MemoryStore` - CRUD operations on semantic memory
- `Injector` - Search and context building
- `PiMemoryServer` - MCP server integration

These same APIs are used in production:
```typescript
// Production usage (same as playground)
const store = new MemoryStore();
store.initialize({ dbPath: "~/.pi/memory/memory.db" });

const injector = new Injector(store);
const context = injector.buildContextBlock({ query: "How do I X?" });

// Inject context into system prompt
const systemPrompt = `You have access to developer memory:\n${context.text}`;
```

## Next Steps

1. **Run the demo:** `npm run demo`
2. **Try interactive mode:** `npm run interactive`
3. **Explore the code:** Read `src/playground.ts` and `src/demo-cli.ts`
4. **Create custom scenarios:** Extend Playground class with your own demos
5. **Integrate with your workflow:** Use MemoryStore and Injector APIs

## Files Reference

- Main playground: `src/playground.ts`
- CLI interface: `src/demo-cli.ts`
- Memory store: `src/store.ts`
- Context injector: `src/injector.ts`
- Bootstrap server: `src/bootstrap.ts`
- Configuration: `package.json` (scripts section)


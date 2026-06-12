# Memory Assistant CLI Documentation

## Overview

The Memory Assistant CLI is an interactive command-line interface for the pi-memory-clone project. It provides natural language input support for managing semantic memory, learning lessons, and searching knowledge facts.

## Quick Start

### Run the CLI

```bash
# Run with persistent memory database
npm run cli

# Run in demo mode with sample data
npm run cli:demo

# Run compiled version directly
node dist/cli.js --demo
```

### First Time Setup

The CLI automatically creates a SQLite database at `data/memory.db` on first run. This stores:
- **Facts**: Key-value pairs with confidence scores
- **Lessons**: Learned rules and corrections
- **Events**: Audit log of all operations

## Features

### 🔍 Search Commands

Search through your stored knowledge using natural language:

```
search typescript
find React best practices
lookup database indexing
what is dependency injection
tell me about SQL optimization
```

**Output**: Formatted table with matching facts, confidence scores, and relevance rankings.

### 💾 Remember Commands (Save Facts)

Save important facts and knowledge:

```
remember TypeScript has strict typing
save React hooks must be called unconditionally
note SQL indexing improves query speed
i should use git rebase for clean history
remember Key: This is the value
```

**Format**: `key: value` automatically splits on the first colon. Without a colon, the entire text is saved as both key and value.

**Output**: Confirmation with the saved fact and confidence score (85% default).

### 💡 Lesson Commands (Learn Rules)

Record lessons and best practices:

```
lesson: Always write unit tests first
learned: Code review catches 90% of bugs
avoid: Never commit without testing
don't hardcode configuration values
never skip database backups
```

**Output**: Confirmation with the lesson type (Do/Avoid) and category.

### 📊 System Commands

#### `stats` or `statistics`
Display memory statistics with visual bar charts:
- Total facts stored
- Total lessons learned
- Total events tracked

#### `config` or `settings`
Show current configuration:
- Memory store status
- Injector settings
- Context budget
- Confidence thresholds
- Injection mode

#### `export` or `save`
Export all memory to a JSON file:
- Exports facts with metadata
- Exports lessons with categories
- Exports statistics
- File saved as `memory-export-[timestamp].json`

#### `clear` or `reset`
Delete all memory (requires confirmation):
- Clears all facts
- Clears all lessons
- Keeps event log for audit purposes
- Asks for confirmation before deletion

#### `help` or `?`
Display comprehensive help with examples:
- Search examples
- Remember examples
- Lesson examples
- System commands reference

#### `quit` or `exit`
Exit the application gracefully:
- Closes database connection
- Saves all changes
- Exits with code 0

## Demo Mode

Run with `--demo` flag to populate with sample data:

```bash
npm run cli:demo
```

**Sample Data Includes:**
- **5 Facts**: TypeScript, React Hooks, SQL Indexing, Git Rebase, Error Handling
- **4 Lessons**: Testing, Security, Configuration, Performance

Perfect for testing functionality without worrying about your real memory.

## Natural Language Processing

The CLI uses a simple NLP router to parse natural language inputs. It recognizes:

### Keywords for Each Command Type

**Search**: `search`, `find`, `lookup`, `what`, `tell me about`

**Remember**: `remember`, `save`, `note`, `i should`, `remember that`

**Lessons**: `lesson:`, `learned:`, `avoid:`, `don't`, `never`

**System**: `stats`, `config`, `export`, `clear`, `help`, `quit`, `exit`

## Output Formatting

### Search Results
```
📋 Search Results:
────────────────────────────────────────────────────────────────────────────────
1. TypeScript [Languages]
   Value: Statically typed superset of JavaScript with strict mode
   Confidence: 95% | Relevance: 95%
   Last accessed: 5/6/2024 10:30:45 AM
```

### Statistics
```
📊 Memory Statistics:
────────────────────────────────────────────────────────────────────────────────
Facts:    ██████████████████████████░░░░░░░░░░░░░░░░░░░░░░ 25
Lessons:  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 12
Events:   ██████████████████████████████████████████░░░░░░ 48
```

### Lessons
```
💡 Learned Lessons:
────────────────────────────────────────────────────────────────────────────────
1. ✅ Do: [Best Practices]
   Write clean, readable code (used 3x)
   Created: 5/6/2024 9:15:32 AM
```

## Architecture

### Components

1. **SimpleNLPRouter**: Parses natural language into structured commands
2. **OutputFormatter**: Formats results with tables, charts, and styled output
3. **MemoryAssistantCLI**: Main REPL loop and command handler
4. **MemoryStore**: SQLite backend for persistence
5. **Injector**: Search and context building

### Data Flow

```
User Input
    ↓
SimpleNLPRouter (Parse)
    ↓
MemoryAssistantCLI (Execute)
    ↓
MemoryStore (Persist) + Injector (Search)
    ↓
OutputFormatter (Format)
    ↓
Console Output
```

## Database Schema

### semantic table
```sql
CREATE TABLE semantic (
  id TEXT PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  value TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.8,
  category TEXT,
  source TEXT DEFAULT 'user',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  last_accessed TEXT
);
```

### lessons table
```sql
CREATE TABLE lessons (
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  category TEXT,
  negative INTEGER NOT NULL DEFAULT 0,
  source TEXT DEFAULT 'user',
  created_at TEXT NOT NULL,
  used_count INTEGER NOT NULL DEFAULT 0
);
```

### events table
```sql
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  action TEXT NOT NULL,
  details TEXT,
  timestamp TEXT NOT NULL
);
```

## Configuration

### Injector Settings

Located in `src/cli.ts` constructor:

```typescript
const injector = new Injector(store, {
  contextBudget: 8192,        // Max context size in bytes
  minConfidence: 0.7,         // 70% minimum confidence
  injectionMode: "all",       // "all" or "selective"
});
```

### Fact Confidence Scoring

- **Remember command**: 85% confidence by default
- **Search results**: Weighted by relevance and confidence
- **Minimum display**: 70% (configurable)

## Error Handling

The CLI provides clear error messages for:

- Invalid commands
- Missing parameters
- Database errors
- File I/O errors
- Type validation errors

All errors are prefixed with ❌ and show helpful context.

## Examples

### Complete Workflow

```
You: help
[Shows help page]

You: remember Kubernetes: Container orchestration platform
✅ Fact Saved

You: remember Docker: Containerization technology
✅ Fact Saved

You: search container
📋 Search Results:
[Shows both facts with relevance scores]

You: lesson: Always use resource limits in Kubernetes
💡 Lesson Recorded

You: stats
📊 Memory Statistics:
[Shows bar charts]

You: export
✅ Memory exported to: memory-export-1715001234567.json

You: quit
ℹ️ Goodbye! Memory saved.
```

## Performance Considerations

- **Search**: O(n) with relevance scoring on all facts
- **Storage**: SQLite with WAL mode for concurrent access
- **Memory**: All facts loaded for search (up to 1000 by default)
- **Export**: Synchronous file I/O, suitable for < 10MB exports

## Limitations

- Single-user local database
- No network distribution
- Piped input not fully supported (use `npm run cli:demo` for testing)
- Search limited to 10 results by default (configurable)

## Future Enhancements

- [ ] Multi-line input mode (until "done")
- [ ] Fuzzy matching for search
- [ ] Category filtering
- [ ] Confidence threshold customization
- [ ] Import from JSON
- [ ] Batch operations
- [ ] Search history
- [ ] Command shortcuts/aliases

## Troubleshooting

### CLI not starting

```bash
# Rebuild TypeScript
npm run build

# Check Node version (requires v20+)
node --version

# Check dependencies
npm install
```

### Database locked error

The CLI uses SQLite with WAL mode. This shouldn't happen in normal usage. Try:

```bash
# Remove the database and start fresh
rm data/memory.db data/memory.db-wal data/memory.db-shm

# Restart the CLI
npm run cli
```

### Commands not recognized

Make sure you're using the exact keywords. Try `help` for examples:

```
You: help
```

## Development

### Building from source

```bash
npm run build          # Compile TypeScript
npm run cli:demo       # Run with demo data
npm run test           # Run tests
```

### Adding new commands

1. Add command type to `ParsedCommand` type
2. Add keyword matching to `SimpleNLPRouter.parse()`
3. Add handler method to `MemoryAssistantCLI`
4. Add formatter method to `OutputFormatter`
5. Test with `npm run cli:demo`

### Running tests

```bash
npm run test

# Or run integration tests
npx tsx tests/cli-integration.test.ts
```

## License

See LICENSE file in repository.

## Support

For issues, questions, or suggestions, please create an issue in the repository.

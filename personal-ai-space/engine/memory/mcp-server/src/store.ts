import { randomUUID } from "node:crypto";
import { mkdirSync, existsSync } from "node:fs";
import { dirname } from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let DatabaseSync: any;

try {
  // Try to import DatabaseSync from node:sqlite (Node 22+)
  const sqlite = require("node:sqlite");
  DatabaseSync = sqlite.DatabaseSync;
} catch {
  // If that fails, the user must install better-sqlite3
  try {
    const BetterSqlite3 = require("better-sqlite3");
    DatabaseSync = BetterSqlite3;
  } catch {
    throw new Error(
      "Neither node:sqlite nor better-sqlite3 available. Requires Node 22+ for node:sqlite, or run: npm install better-sqlite3"
    );
  }
}

/**
 * Types and Interfaces for MemoryStore
 */

export interface SemanticEntry {
  id?: string;
  key: string;
  value: string;
  confidence: number; // 0.0 - 1.0
  category?: string;
  source?: string; // "user" | "consolidation" | "correction"
  created_at: string;
  updated_at: string;
  last_accessed?: string;
}

export interface LessonEntry {
  id: string;
  text: string;
  category?: string;
  negative: 0 | 1; // 1 = "avoid", 0 = "do"
  source?: string;
  created_at: string;
  used_count: number;
}

export interface EventEntry {
  id?: number;
  action: string; // "insert" | "update" | "delete" | "search"
  details?: string;
  timestamp: string;
}

export interface StoreStats {
  semantic: number;
  lessons: number;
  events: number;
}

export interface InitializeOptions {
  dbPath: string;
  logFn?: (msg: string) => void;
}

/**
 * MemoryStore: SQLite-backed CRUD layer for semantic memory
 *
 * Database Schema:
 * - semantic: id, key, value, confidence, category, source, created_at, updated_at, last_accessed
 * - lessons: id, text, category, negative, source, created_at, used_count
 * - events: id, action, details, timestamp
 *
 * Features:
 * - WAL mode for concurrent reads
 * - Foreign key constraints
 * - Busy timeout for lock contention
 * - Comprehensive error handling
 * - Logging support
 */
export class MemoryStore {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private db: any = null;
  private dbPath: string = "";
  private logFn: (msg: string) => void = () => {};
  private isInitialized: boolean = false;

  /**
   * Initialize the MemoryStore with a database file
   *
   * Creates:
   * - semantic table for facts/preferences
   * - lessons table for learned corrections
   * - events table for audit logging
   *
   * Sets up SQLite pragmas for performance:
   * - WAL mode for concurrent reads
   * - Foreign key constraints
   * - Busy timeout for lock handling
   */
  public initialize(options: InitializeOptions): void {
    if (this.isInitialized) {
      this.log("MemoryStore already initialized");
      return;
    }

    const { dbPath, logFn } = options;
    this.dbPath = dbPath;
    if (logFn) this.logFn = logFn;

    this.log(`Initializing MemoryStore at: ${dbPath}`);

    // Create directory if it doesn't exist
    const dir = dirname(dbPath);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
      this.log(`Created directory: ${dir}`);
    }

    try {
      // Open database connection
      this.db = new DatabaseSync(dbPath);
      this.log("Database connection opened");

      // Configure SQLite pragmas
      this.configurePragmas();

      // Create tables
      this.createTables();

      this.isInitialized = true;
      this.log("MemoryStore initialization complete");
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR during initialization: ${msg}`);
      throw new Error(`Failed to initialize MemoryStore: ${msg}`);
    }
  }

  /**
   * Configure SQLite pragmas for optimal performance
   */
  private configurePragmas(): void {
    if (!this.db) throw new Error("Database not initialized");

    try {
      // Use exec() for pragmas (compatible with node:sqlite)
      const pragmas = `
        PRAGMA journal_mode = WAL;
        PRAGMA busy_timeout = 5000;
        PRAGMA foreign_keys = ON;
        PRAGMA cache_size = -64000;
      `;

      this.db.exec(pragmas);
      this.log("Configured SQLite pragmas (WAL, busy_timeout, foreign_keys, cache_size)");
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR configuring pragmas: ${msg}`);
      throw error;
    }
  }

  /**
   * Create database tables if they don't exist
   */
  private createTables(): void {
    if (!this.db) throw new Error("Database not initialized");

    try {
      // Semantic facts table
      this.db.exec(`
        CREATE TABLE IF NOT EXISTS semantic (
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

        CREATE INDEX IF NOT EXISTS idx_semantic_key ON semantic(key);
        CREATE INDEX IF NOT EXISTS idx_semantic_updated ON semantic(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_semantic_category ON semantic(category);
        CREATE INDEX IF NOT EXISTS idx_semantic_confidence ON semantic(confidence DESC);
      `);
      this.log("Created semantic table and indexes");

      // Lessons table
      this.db.exec(`
        CREATE TABLE IF NOT EXISTS lessons (
          id TEXT PRIMARY KEY,
          text TEXT NOT NULL,
          category TEXT,
          negative INTEGER NOT NULL DEFAULT 0,
          source TEXT DEFAULT 'user',
          created_at TEXT NOT NULL,
          used_count INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_lessons_category ON lessons(category);
        CREATE INDEX IF NOT EXISTS idx_lessons_negative ON lessons(negative);
        CREATE INDEX IF NOT EXISTS idx_lessons_created ON lessons(created_at DESC);
      `);
      this.log("Created lessons table and indexes");

      // Events audit log table
      this.db.exec(`
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          action TEXT NOT NULL,
          details TEXT,
          timestamp TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_events_action ON events(action);
      `);
      this.log("Created events table and indexes");
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR creating tables: ${msg}`);
      throw error;
    }
  }

  /**
   * Add or update a semantic fact
   */
  public addFact(
    key: string,
    value: string,
    confidence: number = 0.8,
    category?: string,
    source: string = "user"
  ): void {
    if (!this.db) throw new Error("MemoryStore not initialized");

    if (confidence < 0.0 || confidence > 1.0) {
      throw new Error("Confidence must be between 0.0 and 1.0");
    }

    try {
      // Check existing value — only log event if something actually changed
      const existing = this.db.prepare(
        "SELECT value, confidence FROM semantic WHERE key = ?"
      ).get(key) as { value: string; confidence: number } | undefined;

      const sameValue = existing && existing.value === value && existing.confidence === confidence;

      const id = randomUUID();
      const now = new Date().toISOString();

      const stmt = this.db.prepare(
        `
        INSERT INTO semantic (id, key, value, confidence, category, source, created_at, updated_at, last_accessed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
          value = excluded.value,
          confidence = excluded.confidence,
          category = COALESCE(excluded.category, category),
          source = excluded.source,
          updated_at = excluded.updated_at
      `
      );

      stmt.run(
        id,
        key,
        value,
        confidence,
        category || null,
        source || "user",
        now,
        now,
        now
      );

      if (!sameValue) {
        this.logEvent("INSERT", `semantic:${key}`, `Added fact: ${key}`);
      }
      this.log(`Added fact: key=${key}, confidence=${confidence}`);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR adding fact: ${msg}`);
      throw error;
    }
  }

  /**
   * Retrieve a semantic fact by key
   */
  public getFact(key: string): SemanticEntry | null {
    if (!this.db) throw new Error("MemoryStore not initialized");

    try {
      const stmt = this.db.prepare(`SELECT * FROM semantic WHERE key = ?`);
      const result = stmt.get(key) as SemanticEntry | undefined;

      if (result) {
        // Update last_accessed timestamp
        const updateStmt = this.db.prepare(
          `UPDATE semantic SET last_accessed = ? WHERE key = ?`
        );
        updateStmt.run(new Date().toISOString(), key);

        this.log(`Retrieved fact: key=${key}`);
      }

      return result || null;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR retrieving fact: ${msg}`);
      throw error;
    }
  }

  /**
   * List all semantic facts with optional filtering
   */
  public listFacts(
    prefix?: string,
    limit: number = 100,
    orderBy: "updated" | "created" | "confidence" = "updated"
  ): SemanticEntry[] {
    if (!this.db) throw new Error("MemoryStore not initialized");

    try {
      let query = `SELECT * FROM semantic`;
      const params: unknown[] = [];

      if (prefix) {
        query += ` WHERE key LIKE ?`;
        params.push(`${prefix}%`);
      }

      // Order by
      if (orderBy === "updated") {
        query += ` ORDER BY updated_at DESC`;
      } else if (orderBy === "created") {
        query += ` ORDER BY created_at DESC`;
      } else if (orderBy === "confidence") {
        query += ` ORDER BY confidence DESC`;
      }

      query += ` LIMIT ?`;
      params.push(limit);

      const stmt = this.db.prepare(query);
      const results = stmt.all(...params) as SemanticEntry[];

      this.log(`Listed facts: found ${results.length}, prefix=${prefix || "none"}`);
      return results;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR listing facts: ${msg}`);
      throw error;
    }
  }

  /**
   * Delete a semantic fact by key
   */
  public deleteFact(key: string): boolean {
    if (!this.db) throw new Error("MemoryStore not initialized");

    try {
      const stmt = this.db.prepare(`DELETE FROM semantic WHERE key = ?`);
      const result = stmt.run(key);

      if ((result.changes ?? 0) > 0) {
        this.logEvent("DELETE", `semantic:${key}`, `Deleted fact: ${key}`);
        this.log(`Deleted fact: key=${key}`);
        return true;
      }

      return false;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR deleting fact: ${msg}`);
      throw error;
    }
  }

  /**
   * Add a lesson (learned correction or validated approach)
   */
  public addLesson(
    text: string,
    negative: 0 | 1 = 0,
    category?: string,
    source?: string
  ): void {
    if (!this.db) throw new Error("MemoryStore not initialized");

    try {
      const id = randomUUID();
      const now = new Date().toISOString();

      const stmt = this.db.prepare(
        `
        INSERT INTO lessons (id, text, category, negative, source, created_at, used_count)
        VALUES (?, ?, ?, ?, ?, ?, 0)
      `
      );

      stmt.run(
        id,
        text,
        category || null,
        negative,
        source || "user",
        now
      );

      this.logEvent(
        "INSERT",
        `lessons:${id}`,
        `Added lesson (negative=${negative}): ${text.substring(0, 100)}`
      );
      this.log(
        `Added lesson: id=${id}, negative=${negative}, category=${category || "none"}`
      );
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR adding lesson: ${msg}`);
      throw error;
    }
  }

  /**
   * Retrieve a lesson by ID
   */
  public getLesson(id: string): LessonEntry | null {
    if (!this.db) throw new Error("MemoryStore not initialized");

    try {
      const stmt = this.db.prepare(`SELECT * FROM lessons WHERE id = ?`);
      const result = stmt.get(id) as LessonEntry | undefined;

      if (result) {
        this.log(`Retrieved lesson: id=${id}`);
      }

      return result || null;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR retrieving lesson: ${msg}`);
      throw error;
    }
  }

  /**
   * List all lessons with optional filtering
   */
  public listLessons(
    category?: string,
    negative?: 0 | 1,
    limit: number = 100
  ): LessonEntry[] {
    if (!this.db) throw new Error("MemoryStore not initialized");

    try {
      let query = `SELECT * FROM lessons`;
      const params: unknown[] = [];

      const filters: string[] = [];
      if (category !== undefined) {
        filters.push(`category = ?`);
        params.push(category);
      }
      if (negative !== undefined) {
        filters.push(`negative = ?`);
        params.push(negative);
      }

      if (filters.length > 0) {
        query += ` WHERE ${filters.join(" AND ")}`;
      }

      query += ` ORDER BY created_at DESC LIMIT ?`;
      params.push(limit);

      const stmt = this.db.prepare(query);
      const results = stmt.all(...params) as LessonEntry[];

      this.log(
        `Listed lessons: found ${results.length}, category=${category || "none"}, negative=${negative !== undefined ? negative : "any"}`
      );
      return results;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR listing lessons: ${msg}`);
      throw error;
    }
  }

  /**
   * Delete a lesson by ID
   */
  public deleteLesson(id: string): boolean {
    if (!this.db) throw new Error("MemoryStore not initialized");

    try {
      const stmt = this.db.prepare(`DELETE FROM lessons WHERE id = ?`);
      const result = stmt.run(id);

      if ((result.changes ?? 0) > 0) {
        this.logEvent("DELETE", `lessons:${id}`, `Deleted lesson: ${id}`);
        this.log(`Deleted lesson: id=${id}`);
        return true;
      }

      return false;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR deleting lesson: ${msg}`);
      throw error;
    }
  }

  /**
   * Increment usage count for a lesson
   */
  public incrementLessonUsage(id: string): void {
    if (!this.db) throw new Error("MemoryStore not initialized");

    try {
      const stmt = this.db.prepare(
        `UPDATE lessons SET used_count = used_count + 1 WHERE id = ?`
      );
      stmt.run(id);

      this.log(`Incremented lesson usage: id=${id}`);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR incrementing lesson usage: ${msg}`);
      throw error;
    }
  }

  /**
   * Get recent events from the audit log
   */
  public getRecentEvents(limit: number = 100): EventEntry[] {
    if (!this.db) throw new Error("MemoryStore not initialized");

    try {
      const stmt = this.db.prepare(
        `SELECT id, action, details, timestamp FROM events ORDER BY timestamp DESC LIMIT ?`
      );
      const results = stmt.all(limit) as EventEntry[];

      this.log(`Retrieved recent events: found ${results.length}`);
      return results;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR retrieving events: ${msg}`);
      throw error;
    }
  }

  /**
   * Get database statistics
   */
  public getStats(): StoreStats {
    if (!this.db) throw new Error("MemoryStore not initialized");

    try {
      const semanticCount = (
        this.db.prepare(`SELECT COUNT(*) as count FROM semantic`).get() as {
          count: number;
        }
      ).count;

      const lessonsCount = (
        this.db.prepare(`SELECT COUNT(*) as count FROM lessons`).get() as {
          count: number;
        }
      ).count;

      const eventsCount = (
        this.db.prepare(`SELECT COUNT(*) as count FROM events`).get() as {
          count: number;
        }
      ).count;

      const stats: StoreStats = {
        semantic: semanticCount,
        lessons: lessonsCount,
        events: eventsCount,
      };

      this.log(
        `Stats: semantic=${semanticCount}, lessons=${lessonsCount}, events=${eventsCount}`
      );
      return stats;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR getting stats: ${msg}`);
      throw error;
    }
  }

  /**
   * Close the database connection
   */
  public close(): void {
    try {
      if (this.db) {
        this.db.close();
        this.isInitialized = false;
        this.log("Database connection closed");
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`ERROR closing database: ${msg}`);
      throw error;
    }
  }

  /**
   * Log an event to the events table
   */
  private logEvent(action: string, memory_key: string, details: string): void {
    if (!this.db) return;

    try {
      const stmt = this.db.prepare(
        `INSERT INTO events (action, details, timestamp) VALUES (?, ?, ?)`
      );

      stmt.run(action, `${memory_key}: ${details}`, new Date().toISOString());
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.log(`WARNING: Could not log event: ${msg}`);
    }
  }

  /**
   * Internal logging method
   */
  private log(msg: string): void {
    this.logFn(`[MemoryStore] ${msg}`);
  }

  /**
   * Check if store is initialized
   */
  public isReady(): boolean {
    return this.isInitialized && this.db !== null;
  }
}

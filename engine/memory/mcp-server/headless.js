#!/usr/bin/env node
/**
 * headless.js — Non-interactive JSON interface for the pi-memory MemoryStore.
 *
 * Called by the Python MCPMemoryBridge as a subprocess:
 *   node headless.js <operation> [args...]
 *
 * All output is newline-delimited JSON on stdout.
 * Errors are written to stderr; exit code 1 on failure.
 *
 * Operations (single):
 *   add-fact  <key> <value> [confidence] [category] [source]
 *   get-fact  <key>
 *   list-facts [prefix] [limit] [orderBy]
 *   delete-fact <key>
 *   add-lesson <text> [negative:0|1] [category] [source]
 *   list-lessons [category] [negative:0|1] [limit]
 *   delete-lesson <id>
 *   stats
 *
 * Operations (batch — reads JSON array from stdin):
 *   batch-add-facts   [{"key","value","confidence","category","source"}, ...]
 *   batch-add-lessons [{"text","negative","category","source"}, ...]
 */

import { createRequire } from "node:module";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, existsSync } from "node:fs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// DB lives in engine/db/ alongside all other project databases
const DB_PATH = resolve(__dirname, "..", "..", "db", "agent_memory.db");
const DB_DIR  = resolve(__dirname, "..", "..", "db");

if (!existsSync(DB_DIR)) mkdirSync(DB_DIR, { recursive: true });

const require = createRequire(import.meta.url);

// ── MemoryStore (inline to avoid TS compilation dependency) ──────────────────
// We import from the compiled dist/ so this stays pure JS at runtime.
let MemoryStore;
try {
  const mod = await import("./dist/store.js");
  MemoryStore = mod.MemoryStore;
} catch {
  process.stderr.write("ERROR: dist/store.js not found. Run: npm run build\n");
  process.exit(1);
}

const store = new MemoryStore();
store.initialize({ dbPath: DB_PATH, logFn: () => {} });

function ok(data) {
  process.stdout.write(JSON.stringify({ ok: true, ...data }) + "\n");
}

function fail(msg) {
  process.stderr.write(`ERROR: ${msg}\n`);
  process.stdout.write(JSON.stringify({ ok: false, error: msg }) + "\n");
  process.exit(1);
}

/** Read all of stdin as a single string. */
function readStdin() {
  return new Promise((resolve) => {
    if (process.stdin.isTTY) return resolve("");
    let data = "";
    process.stdin.setEncoding("utf-8");
    process.stdin.on("data", (chunk) => { data += chunk; });
    process.stdin.on("end", () => resolve(data));
  });
}

const [,, op, ...args] = process.argv;

switch (op) {
  case "add-fact": {
    const [key, value, confidence = "0.8", category, source = "engine"] = args;
    if (!key || !value) fail("add-fact requires <key> <value>");
    store.addFact(key, value, parseFloat(confidence), category || undefined, source);
    ok({ stored: true, key, value });
    break;
  }
  case "get-fact": {
    const [key] = args;
    if (!key) fail("get-fact requires <key>");
    const fact = store.getFact(key);
    if (fact) ok(fact);
    else ok({ found: false });
    break;
  }
  case "list-facts": {
    const [prefix, limit = "100", orderBy = "updated"] = args;
    const facts = store.listFacts(prefix || undefined, parseInt(limit), orderBy);
    ok({ facts, count: facts.length });
    break;
  }
  case "delete-fact": {
    const [key] = args;
    if (!key) fail("delete-fact requires <key>");
    const deleted = store.deleteFact(key);
    ok({ deleted });
    break;
  }
  case "add-lesson": {
    const [text, negative = "0", category, source = "engine"] = args;
    if (!text) fail("add-lesson requires <text>");
    store.addLesson(text, parseInt(negative) === 1 ? 1 : 0, category || undefined, source);
    ok({ stored: true });
    break;
  }
  case "list-lessons": {
    const [category, negative, limit = "100"] = args;
    const neg = negative !== undefined ? (parseInt(negative) === 1 ? 1 : 0) : undefined;
    const lessons = store.listLessons(category || undefined, neg, parseInt(limit));
    ok({ lessons, count: lessons.length });
    break;
  }
  case "delete-lesson": {
    const [id] = args;
    if (!id) fail("delete-lesson requires <id>");
    const deleted = store.deleteLesson(id);
    ok({ deleted });
    break;
  }
  case "stats": {
    const stats = store.getStats();
    ok(stats);
    break;
  }
  case "batch-add-facts": {
    const raw = await readStdin();
    if (!raw) fail("batch-add-facts requires JSON array on stdin");
    let facts;
    try { facts = JSON.parse(raw); } catch { fail("Invalid JSON on stdin"); }
    if (!Array.isArray(facts)) fail("Expected JSON array on stdin");
    let stored = 0;
    for (const f of facts) {
      if (!f.key || f.value === undefined) continue;
      store.addFact(f.key, String(f.value), parseFloat(f.confidence ?? "0.8"), f.category || undefined, f.source || "engine");
      stored++;
    }
    ok({ stored, total: facts.length });
    break;
  }
  case "batch-add-lessons": {
    const raw = await readStdin();
    if (!raw) fail("batch-add-lessons requires JSON array on stdin");
    let lessons;
    try { lessons = JSON.parse(raw); } catch { fail("Invalid JSON on stdin"); }
    if (!Array.isArray(lessons)) fail("Expected JSON array on stdin");
    let stored = 0;
    for (const l of lessons) {
      if (!l.text) continue;
      store.addLesson(l.text, (parseInt(l.negative ?? "0") === 1) ? 1 : 0, l.category || undefined, l.source || "engine");
      stored++;
    }
    ok({ stored, total: lessons.length });
    break;
  }
  default:
    fail(`Unknown operation: ${op}. Valid: add-fact, get-fact, list-facts, delete-fact, add-lesson, list-lessons, delete-lesson, stats, batch-add-facts, batch-add-lessons`);
}

store.close();

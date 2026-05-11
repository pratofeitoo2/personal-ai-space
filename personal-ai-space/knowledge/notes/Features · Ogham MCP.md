---
title: Features · Ogham MCP
type: note
created: 2026-05-11T19:47
updated: 2026-05-11T19:47
---

# Features · Ogham MCP

## Page 1

Ogham MCP Features Download Docs Benchmarks Compare Blog
Features
10 mins
Hybrid Search
Hybrid Search
Relationship Graph
Edge types
Graph traversal
Wiki Layer
Obsidian Export
Cognitive Scoring
Confidence
Novelty detection
Content signal scoring
Automatic condensing
Retrieval quality
How this compares
Retrieval R@10 (no
LLM in search loop)
Benchmark setup
Profiles
Memory expiration
Embedding Provider
Choice
Ogham runs two retrieval methods in the same query:
Workflow skills
Platform integrations
Semantic search via pgvector cosine similarity (understands meaning)
Slack
Keyword search via PostgreSQL `tsvector` full-text search (finds exact terms) Telegram
Coming soon
SSE transport
Vector Search
Embed Query
pgvector cosine
Cognitive Scoring
Reciprocal Rank
Query ACT-R + Confidence Ranked Results
Fusion
+ Graph Boost
Full-Text Search
tsvector
Click to expand
Results are merged with Reciprocal Rank Fusion (RRF). RRF is rank-based, so a document ranking
high in both systems surfaces first without score normalization. Runs on Supabase free tier.
↑
Relationship Graph
Ogham builds a relationship graph between memories, entirely inside PostgreSQL. No separate
graph database, no LLM to extract entities. Connections come from embedding similarity.
When you store a memory, Ogham compares its embedding against existing memories using HNSW
vector search. Any pair above a similarity threshold (default 0.85) gets a weighted edge in the
`memory_relationships` table. One HNSW scan, one insert, no LLM inference.
New Memory
Generate Embedding
HNSW Scan
Store in PostgreSQL
find similar memories
Similarity > 0.85?
Yes
Create weighted edge
No
in memory_relationships
Done
Click to expand
Edge types
Relationship What it means
`similar` Auto-created when embeddings are close (cosine similarity)
`supports` Created by `store_decision` — links a decision to the context that informed it
`contradicts` For conflicting information
`related` General-purpose link
`follows` Sequential relationship
`derived_from` One memory built on another
Graph traversal
Once edges exist, you can traverse them:
`explore_knowledge` runs a hybrid search to find seed memories, then walks relationship
edges via a recursive CTE to pull in connected context.
`find_related` starts from a known memory and traverses outward for impact analysis.
`link_unlinked` backfills edges for memories that predate auto-linking, in configurable
batches.
similar 0.91 Related Memory derived_from Source Memory
Seed Memory 1
Query Hybrid Search supports Decision
Seed Memory 2 similar 0.87 Related Memory
Click to expand
Both operations run as single SQL queries inside PostgreSQL.
Wiki Layer
Pull a tag’s worth of memories into a single synthesized markdown page. Compile once, cache,
recompile when sources change. Built on top of the relationship graph – not separate from it.
Four MCP tools cover the lifecycle:
Tool What it does
`compile_wiki` LLM synthesizes every memory carrying a tag into one markdown page. Hash-check
short-circuit makes repeat calls free until sources change.
`query_topic_summary` Read the cached page. No LLM cost.
`walk_knowledge` Direction-aware graph walk – outgoing, incoming, or both – along memory
relationships. Cycle-detected.
`lint_wiki` Health report: contradictions, orphans, stale lifecycle, stale summaries, summary
drift.
Synthesis works with any LLM. Run it locally on Ollama with `llama3.2`, on vLLM, or in the cloud
against Gemini, OpenAI, Anthropic, Mistral, Groq, or OpenRouter. The provider gets stamped into
each page’s frontmatter so you can re-compile the same topic against a different model and
compare.
Cached pages are auto-stale-marked when memories tagged with that topic change, so the next
read knows to recompile. A nightly sweep cleans up topics that haven’t been re-compiled in a while.
The wiki layer is opt-in cache – if you don’t `compile_wiki`, you don’t pay the LLM cost. Hybrid
search keeps working as before.
Obsidian Export
Snapshot your wiki layer to a folder of plain markdown files. One file per topic, with full YAML
frontmatter, auto-detected `[[wikilinks]]`, and a `README.md` index.
ogham export-obsidian /path/to/vault
Open the result in Obsidian – or any text editor. Edits stay in Obsidian; re-run the export to refresh.
Read-only by design: this is a portable snapshot, not a sync target.
Why it matters: your memory is yours. A vault of plain `.md` files is the most portable thing you can
have. No proprietary format, no API, no lock-in. If Ogham disappears tomorrow your memory is still
readable in any text editor. Obsidian’s graph view turns wiki cross-references into an interactive
map you can explore.
Full guide and frontmatter reference.
Cognitive Scoring
Search results are ranked by `relevance`, not raw vector similarity. Ogham tracks access
frequency, recency, and graph connectivity, then applies an ACT-R base-level activation formula at
query time:
relevance = rrf_score × softplus(ACT-R) × confidence × graph_boost
Where:
ageDays
ACT-R = ln(n + 1) − 0.5 ⋅ ln!
( n + 1 )
graph_boost = 1 + (relationship_strength) × 0.2
∑
`n` = access count, `ageDays` = time since last access
`rrf_score` is the Reciprocal Rank Fusion score from hybrid retrieval
`confidence` is a Bayesian trust score (0 to 1, default 0.5)
`graph_boost` counts relationship edges. An isolated memory scores 1.0 (no change). A
memory with five strong links gets up to 2x
A memory accessed ten times this week ranks higher than one accessed once two years ago, even
if both have similar embeddings. A memory linked to five others outranks an identical one with no
connections. New memories with zero access get a neutral score. All of this runs in PostgreSQL, no
extra compute.
Confidence
Each memory has a confidence score. Call `reinforce_memory` when something checks out,
`contradict_memory` when it’s wrong. Low-confidence memories rank lower but aren’t deleted, so
they’re still findable if you go looking.
Novelty detection
When you store a memory, Ogham checks how similar it is to what you already have. If you’re
storing something you’ve already captured, the new memory starts quieter in search results. It’s still
there, it just won’t push out content that’s more useful.
Runs on every `store_memory` call. Nothing to configure.
Content signal scoring
A decision about your database architecture matters more than a note about a meeting. Ogham
scores content at store time by looking for signals in the text: decision keywords, error messages,
architecture references, code blocks, file paths. Each signal bumps the score. Higher-scoring
memories rank above lower ones in search.
No LLM in the loop. Regex pattern matching, runs in microseconds.
Automatic condensing
Old memories that nobody accesses gradually shrink. Full text becomes a summary of key
sentences (about 30% of the original), then a one-line description with tags. The original is always
preserved, so if a condensed memory becomes relevant again you can restore it.
Memories that matter resist condensing. If something has high signal scores, gets accessed
frequently, or has high confidence, it stays at full text regardless of age. A decision you made six
months ago that you still reference stays intact. A passing observation from three months ago that
nobody looked at gets condensed to its key sentences.
Run `compress_old_memories` manually or on a schedule.
Retrieval quality
Tested against the LongMemEval benchmark (Wu et al., ICLR 2025) – 500 questions across 5
memory abilities, 124,342 memories ingested.
No LLM in the retrieval pipeline. No neural rerankers, no knowledge graph enrichment, no query
expansion. One PostgreSQL query: hybrid search combining pgvector cosine similarity and tsvector
keyword matching via Reciprocal Rank Fusion (position-based, score-agnostic). Optional
FlashRank cross-encoder reranking available for self-hosters.
Category What it tests R@10 MRR Questions
single-session-assistant Finding assistant’s previous answers 100% 100% 56
knowledge-update Tracking changed facts 100% 97.4% 78
single-session-user Recalling user statements 98.6% 89.8% 70
multi-session Connecting facts across conversations 97.3% 90.2% 133
single-session-preference Remembering user preferences 96.7% 87.5% 30
temporal-reasoning Time-based queries (“when”, “how long ago”) 93.5% 85.9% 133
Overall 97.2% 91.1% 500
Temporal reasoning (93.5%) is the weakest category. Time-based queries like “how long ago” need
more than similarity matching – we use entity-centric bridge retrieval and Gaussian decay re-
ranking to close the gap, but some multi-hop temporal questions remain hard without an LLM in the
loop.
How this compares
Most memory systems report end-to-end QA accuracy (retrieval + LLM reads and answers). That’s
a different metric from retrieval R@10 – QA accuracy tests the whole pipeline, R@10 tests whether
the right memories were found.
Published QA accuracy on LongMemEval:
System Accuracy Architecture
OMEGA 95.4% Classification + extraction pipeline
Observational Memory (Mastra) 94.9% Observation extraction + GPT-5-mini
Hindsight (Vectorize) 91.4% 4 memory types + Gemini-3
Zep (Graphiti) 71.2% Temporal knowledge graph + GPT-4o
Mem0 49.0% RAG-based
Ogham’s 97.2% is retrieval R@10 – did the correct session appear in the top 10 results, with no LLM
interpreting the content. The LongMemEval paper reports 78.4% as their best retrieval baseline.
Ogham reaches 97.2% with one Postgres query.
Retrieval R@10 (no LLM in search loop)
Benchmark setup
Embedding: Voyage AI voyage-4-lite at 512 dimensions
Index: halfvec HNSW (float16 compression, roughly half the size of float32)
Database: PostgreSQL 17 with pgvector 0.8.2
Cache hit ratio during benchmark: 97.5%
CPU usage: under 4%
Zero errors across all 500 questions
Profiles
Borrowed from Severance: each profile is a separate memory partition. In “work” mode, personal
memories don’t exist. Switch to personal, and work memories vanish.
> "Switch to my work profile"
> "Remember that the prod database is on us-east-1"
> "Switch to personal profile"
> "Search for database" <-- returns nothing, work memories are invisible
The default profile is `default`. Profiles are created automatically when you store a memory.
Switching is instant and lasts for the session only.
Memory expiration
Set a TTL on any profile so memories automatically expire:
““Set a 90-day TTL on my work profile””
Expired memories are automatically filtered from all searches and listings. Run
`cleanup_expired()` to permanently delete them and reclaim storage.
Embedding Provider Choice
Ogham supports four embedding providers. Pick whichever fits your setup and budget.
Provider Model Default Dimensions Configurable
OpenAI text-embedding-3-small 1024 Any up to 1536
Mistral mistral-embed 1024 Any up to 1024
Voyage AI voyage-4-lite 1024 256, 512, 1024, 2048
Ollama embeddinggemma (default) 512 128, 256, 512, 768 via Matryoshka truncation
The database schema ships with 512-dimensional vectors. OpenAI, Voyage, and Ollama all support
512. Mistral is the exception: `mistral-embed` only produces 1024-dim vectors, so Mistral users
need to run a dimension migration after setup. We tested 512 against 1024 on a 4,300-memory
database and saw no search quality difference, with faster indexing and less storage at the smaller
size. Other Ollama models have fixed dimensions; swap via `OLLAMA_EMBED_MODEL`. Set
`EMBEDDING_DIM` to override.
Voyage AI includes 200M free tokens. Ollama runs on your machine with no API calls. Mistral and
OpenAI charge per token.
Switching providers means re-embedding existing memories. The `re_embed_all` tool does this —
it re-generates every vector in the active profile with the new provider. The embedding cache skips
any text that’s already been embedded, so you don’t pay twice.
EMBEDDING_PROVIDER=voyage
VOYAGE_API_KEY=pa-...
VOYAGE_EMBED_MODEL=voyage-4-lite
Change the config, run `re_embed_all`, and search picks up the new vectors.
Workflow skills
You don’t have to call MCP tools by hand. Ogham ships with three skills that wire up common
workflows.
Skill What it does
ogham-research Memory capture – dedup checks, auto-tagging, structured decisions
ogham-recall Retrieval – chained search, graph traversal, session bootstrapping
ogham-maintain Admin – health checks, stats, cleanup, re-embedding, profile management
Install with `npx skills add ogham-mcp/ogham-mcp`. See the skills docs for details.
You can also add a `CLAUDE.md` instruction telling the AI to save learnings as it works, or use
Claude Code hooks to trigger capture after git commits.
Platform integrations
Talk to your memories from Slack or Telegram. No context switching – just ask a question where
you’re already working.
Slack
Add the Ogham bot to your workspace via OAuth. Three ways to use it:
@mention in any channel – the bot replies in a thread with search results
/ogham slash command – private search, only you see the response
Direct message – one-on-one queries
Results are formatted as native Slack markup. Daily and monthly usage caps keep your bill
predictable – the bot warns you when you’re running low instead of silently cutting off.
Telegram
Connect your own bot (create one via @BotFather) to Ogham Cloud. It responds to DMs and the
/ogham command. Same search, different window.
Coming soon
Discord is next.
All integrations require Pro plan or above. BYOK users get unlimited queries – counters still track for
analytics but never block.
SSE transport
For users running multiple agents or MCP clients at the same time, SSE mode runs Ogham as a
persistent background server. All clients connect to one process instead of each spawning their
own.
ogham serve --transport sse --port 8742
One server, one database pool, one embedding cache. Clients connect via URL:
{"mcpServers": {"ogham": {"url": "http://127.0.0.1:8742/sse"}}}
Health check at `/health` on the same port (cached, sub-10ms). See the SSE transport docs for
client configs and Docker setup.
Download →
Ogham MCP
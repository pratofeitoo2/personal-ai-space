# personal-ai-space/engine/extractors/

## Responsibility
Data extraction extension point. Currently a placeholder package with only `__init__.py`. Designed for modular extractors that pull structured data from various sources (files, APIs, documents) for ingestion into the knowledge base and memory systems.

## Files
- `__init__.py` — Package marker, empty

## Integration Points
- **Consumed by**: `comprehensive_extractor.py` (future integration)
- **Pattern**: Each extractor is expected to implement a consistent `extract(source) -> dict` interface

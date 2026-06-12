# personal-ai-space/engine/tests/

## Responsibility
Pytest test suite for engine core components — covers base agent, database manager, engine orchestration, GitHub integration, and LLM bridge.

## Test Infrastructure
- Framework: pytest
- Fixtures: `conftest.py` provides shared test fixtures (temp databases, mock agents, config overrides)
- Run command: `python -m pytest tests/ -v --tb=short`

## Test Catalog

| Test File | Component Tested | Key Test Cases |
|-----------|-----------------|---------------|
| `test_base_agent.py` | BaseAgent | Agent initialization, execute cycle, capability reporting, metadata |
| `test_db_manager.py` | DatabaseManager | Connection pooling, CRUD operations, schema creation, transaction rollback |
| `test_engine.py` | Engine orchestrator | Agent loading, message routing, scheduled task execution, shutdown |
| `test_github_config.py` | GitHub configuration | Config parsing, credential validation, endpoint resolution |
| `test_github_discovery.py` | GitHub discovery | Repository search, file listing, content fetching |
| `test_github_git_ops.py` | GitHub git operations | Clone, commit, push, branch management |
| `test_llm_bridge.py` | LlmBridge | Prompt construction, response parsing, error handling, token management |

## Integration
- Tests use in-memory SQLite databases where possible to avoid side effects
- External calls (GitHub API, LLM endpoints) use mocking via `unittest.mock`
- Engine tests instantiate `Engine` with test configuration overrides

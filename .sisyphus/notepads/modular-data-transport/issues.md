## 2026-05-14 Foundation Issues
- mcp_transport.py: ImportError for MCPClientFactory (not in base_client.py).
- event_bus.py: delivered count logic is broken (requires handler to return non-None).
- test_transport.py: Missing mock import for DataHub tests.
- config.py: Pydantic singleton issue (fixed by Atlas, but needs verification).

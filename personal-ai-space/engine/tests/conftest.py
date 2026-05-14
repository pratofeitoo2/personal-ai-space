import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def setup_logging():
    """Silence logging during tests."""
    import logging
    logging.getLogger("engine").setLevel(logging.CRITICAL)
    yield


@pytest.fixture
def temp_db_dir():
    """Create a temporary DB directory for actual DB files, keeping schema access intact."""
    import db_manager
    with tempfile.TemporaryDirectory() as tmpdir:
        orig_paths = db_manager.DB_PATHS.copy()
        for name in db_manager.DB_PATHS:
            db_manager.DB_PATHS[name] = Path(tmpdir) / f"{name}.db"
        yield tmpdir
        db_manager.clear_pool()
        db_manager.DB_PATHS.clear()
        db_manager.DB_PATHS.update(orig_paths)


@pytest.fixture
def init_test_db(temp_db_dir):
    """Initialize all databases with schemas."""
    import db_manager as db
    db.init_all()
    return db

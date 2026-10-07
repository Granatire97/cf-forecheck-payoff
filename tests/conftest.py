import sys
from pathlib import Path

# The project is not an installed package, so import it from the repo root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import duckdb
import pytest

from pipeline.config import DB_PATH
from pipeline.pipeline import pipeline


@pytest.fixture(scope="session")
def con():
    """Build the warehouse once if needed, then share a read-only connection."""
    if not DB_PATH.exists():
        pipeline()
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    yield connection
    connection.close()

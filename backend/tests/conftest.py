"""Shared pytest setup for backend tests."""

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{(BACKEND_ROOT / 'data' / 'sentiment.db').as_posix()}",
)


@pytest.fixture(autouse=True)
def isolate_rate_limit_buckets():
    """Keep request-rate tests isolated inside one pytest process."""
    import app.main as main_module

    main_module._RATE_LIMIT_BUCKETS.clear()
    yield
    main_module._RATE_LIMIT_BUCKETS.clear()

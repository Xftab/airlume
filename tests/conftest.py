import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from airlume.pipeline.registry import Registry


@pytest.fixture(scope="session")
def registry() -> Registry:
    return Registry.load()

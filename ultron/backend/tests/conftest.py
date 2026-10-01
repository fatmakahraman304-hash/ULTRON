import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

@pytest.fixture(autouse=True)
def release_managed_database_connections():
    yield
    from app.core.database import close_all
    close_all()

# tests/conftest.py

import os
import sys

# Ensure the backend root (the directory that contains 'app') is on sys.path
CURRENT_DIR = os.path.dirname(__file__)              # .../backend/tests
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)          # .../backend

if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from fastapi.testclient import TestClient
from app.main import app


import pytest


@pytest.fixture
def client():
    """
    Fresh TestClient for each test.
    """
    return TestClient(app)
"""
conftest.py - pytest configuration and shared fixtures.

This file defines common fixtures and hooks for the test suite.
"""

import sys
from pathlib import Path

# Ensure project root (the directory containing the 'dictsqlite' package) is on sys.path
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

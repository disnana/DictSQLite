"""
Pytest configuration for auto-sync tests.
"""

import sys
import os

# Add parent directory to path for imports
test_dir = os.path.dirname(os.path.abspath(__file__))
auto_sync_dir = os.path.dirname(test_dir)
sys.path.insert(0, auto_sync_dir)

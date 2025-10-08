"""
Quick test to reproduce the test_safe_pickle_forbidden_objects scenario
"""
import sys
import pickle
import tempfile
import os

sys.path.insert(0, r'c:\Users\msi-z\Downloads\新しいフォルダー\プロジェクトCode\DictSQLite\others\beta-versions\dictsqlite_v4.2')

# Import the wrapper
from __init__ import DictSQLiteV4

# Create temp db
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
    db_path = f.name

try:
    print(f"Creating DictSQLiteV4 with enable_safe_pickle=True at {db_path}")
    db = DictSQLiteV4(db_path, enable_safe_pickle=True)
    
    print(f"db._enable_safe_pickle = {db._enable_safe_pickle}")
    print(f"db._safe_pickle_allowed_modules = {db._safe_pickle_allowed_modules}")
    
    # Try to store dangerous pickle (same as test)
    dangerous = pickle.dumps(__import__)
    print(f"\nAttempting to store pickled __import__ (len={len(dangerous)} bytes)...")
    
    try:
        db["dangerous"] = dangerous
        print("ERROR: No exception was raised!")
        sys.exit(1)
    except Exception as e:
        print(f"SUCCESS: Exception raised: {type(e).__name__}: {e}")
        sys.exit(0)
        
finally:
    try:
        os.unlink(db_path)
    except:
        pass

"""
Pytest configuration and shared utilities for dictsqlite_v4.2 tests
"""
import os
import sys
import time
import tempfile
from contextlib import contextmanager


def cleanup_db_files(db_path):
    """
    データベースファイルとWALファイルをクリーンアップ
    Windows対応: リトライロジック付き
    
    This function handles Windows file locking issues by:
    1. Adding a small delay to allow file handles to be released
    2. Retrying cleanup operations with exponential backoff
    3. Gracefully handling PermissionError on Windows
    
    Args:
        db_path: Path to the database file to clean up
    """
    # Only add delay on Windows to avoid performance impact on other platforms
    if sys.platform == 'win32':
        time.sleep(0.1)
    
    for attempt in range(3):
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
            # WALファイルもクリーンアップ
            for ext in ['-wal', '-shm']:
                wal_file = db_path + ext
                if os.path.exists(wal_file):
                    os.unlink(wal_file)
            break
        except PermissionError:
            if attempt < 2:
                # Only sleep on Windows during retries
                if sys.platform == 'win32':
                    time.sleep(0.2)  # 200ms待機してリトライ
            # 最後の試行でも失敗した場合は無視
        except Exception:
            # その他のエラーは無視
            break


@contextmanager
def windows_safe_temp_db(suffix=".db"):
    """
    Context manager for creating temporary database files with Windows-safe cleanup.
    
    This handles the common pattern of:
    1. Creating a temporary database file
    2. Running tests
    3. Cleaning up with proper Windows file handle handling
    
    Yields:
        str: Path to the temporary database file
    """
    fd, db_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    
    try:
        yield db_path
    finally:
        cleanup_db_files(db_path)


@contextmanager  
def windows_safe_temp_dir():
    """
    Context manager for creating temporary directories with Windows-safe cleanup.
    
    For use with tempfile.TemporaryDirectory() when database files are involved.
    Ensures proper cleanup even on Windows where file handles may be held.
    
    Yields:
        str: Path to the temporary directory
    """
    tmpdir = tempfile.mkdtemp()
    
    try:
        yield tmpdir
    finally:
        # Clean up database files first with proper Windows handling
        if sys.platform == 'win32':
            time.sleep(0.1)  # Allow file handles to be released
        
        # Try to remove the directory with retry logic
        for attempt in range(3):
            try:
                # Remove all database-related files first
                if os.path.exists(tmpdir):
                    for filename in os.listdir(tmpdir):
                        filepath = os.path.join(tmpdir, filename)
                        if os.path.isfile(filepath):
                            os.unlink(filepath)
                    os.rmdir(tmpdir)
                break
            except (PermissionError, OSError):
                if attempt < 2 and sys.platform == 'win32':
                    time.sleep(0.2)
                # Silently ignore on last attempt
            except Exception:
                break

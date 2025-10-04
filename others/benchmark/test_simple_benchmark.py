#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DictSQLite 簡易ベンチマーク - デバッグ版
"""

import sys
import os
import time
import tempfile
from pathlib import Path

# モジュールパスの設定
BASE_DIR = Path(__file__).parent
REPO_ROOT = BASE_DIR.parent.parent  # /others/benchmark から / へ
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'dictsqlite-fastest'))
sys.path.insert(0, str(REPO_ROOT / 'dictsqlite-fastest' / 'beta'))

# インポート
from dictsqlite.main import DictSQLite
from dictsqlite_fastest.main import DictSQLiteFastest
from dictsqlite_fastest_beta import DictSQLiteFastestBeta

def test_simple():
    """簡単なテスト"""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_"))
    
    print("="*80)
    print("簡易テスト開始")
    print("="*80)
    
    # Original版
    print("\n[DictSQLite オリジナル版]")
    try:
        db_path = temp_dir / "original.db"
        with DictSQLite(str(db_path)) as db:
            start = time.perf_counter()
            for i in range(100):
                db[f'key_{i}'] = f'value_{i}'
            duration = time.perf_counter() - start
            print(f"  100件書き込み: {duration:.4f}秒")
    except Exception as e:
        print(f"  エラー: {e}")
    
    # Fastest版
    print("\n[DictSQLite-Fastest APSW版]")
    try:
        db_path = temp_dir / "fastest.db"
        print(f"  DBパス: {db_path}")
        db = DictSQLiteFastest(str(db_path))
        print("  初期化完了")
        start = time.perf_counter()
        for i in range(100):
            db[f'key_{i}'] = f'value_{i}'
        duration = time.perf_counter() - start
        print(f"  100件書き込み: {duration:.4f}秒")
        db.close()
    except Exception as e:
        print(f"  エラー: {e}")
        import traceback
        traceback.print_exc()
    
    # Beta版
    print("\n[DictSQLite-Fastest Beta版]")
    try:
        db_path = temp_dir / "beta.db"
        db = DictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
        start = time.perf_counter()
        for i in range(100):
            db[f'key_{i}'] = f'value_{i}'
        duration = time.perf_counter() - start
        print(f"  100件書き込み: {duration:.4f}秒")
        db.close()
    except Exception as e:
        print(f"  エラー: {e}")
        import traceback
        traceback.print_exc()
    
    # クリーンアップ
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print("\nテスト完了")

if __name__ == '__main__':
    test_simple()

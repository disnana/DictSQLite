"""Beta版v2の最小テスト - 同期版のみ"""

import sys
import os
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "others" / "beta-versions" / "dictsqlite-fastest" / "beta"))

from dictsqlite_fastest_beta_v2 import DictSQLiteFastestBeta


def cleanup_db(db_path):
    """テスト用DBを削除"""
    for attempt in range(3):
        try:
            for ext in ['', '-wal', '-shm']:
                try:
                    os.remove(db_path + ext)
                except FileNotFoundError:
                    pass
            break
        except PermissionError:
            if attempt < 2:
                time.sleep(0.3)


def test_sync_only():
    """同期版のみのテスト"""
    print("="*80)
    print("Beta版v2 - 同期版テスト")
    print("="*80)
    
    db_path = "test_sync_simple.db"
    cleanup_db(db_path)
    
    db = None
    try:
        print("\n[1/4] データベース作成...")
        db = DictSQLiteFastestBeta(
            db_name=db_path,
            cache_capacity=100,
            write_buffer_size=50
        )
        print("   OK")
        
        print("\n[2/4] 書き込みテスト（100件）...")
        start = time.perf_counter()
        for i in range(100):
            db[f'key_{i}'] = f'value_{i}'
        db._flush_write_buffer()
        elapsed = time.perf_counter() - start
        print(f"   OK: {elapsed:.3f}秒")
        
        print("\n[3/4] 読み取りテスト（100件）...")
        start = time.perf_counter()
        for i in range(100):
            value = db[f'key_{i}']
            assert value == f'value_{i}', f"Expected 'value_{i}', got '{value}'"
        elapsed = time.perf_counter() - start
        print(f"   OK: {elapsed:.3f}秒")
        
        print("\n[4/4] 統計情報...")
        stats = db.get_stats()
        print(f"   - キャッシュヒット: {stats['cache_hits']}")
        print(f"   - キャッシュミス: {stats['cache_misses']}")
        print(f"   - ヒット率: {stats['cache']['hit_rate']:.1f}%")
        
        print("\n" + "="*80)
        print("[SUCCESS] 同期版テスト成功！")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if db is not None:
            try:
                db.close()
                print("\n[INFO] データベース閉じました")
            except Exception as e:
                print(f"\n[WARN] close時のエラー: {e}")
        
        time.sleep(0.5)
        cleanup_db(db_path)
        print("[INFO] クリーンアップ完了")


if __name__ == "__main__":
    test_sync_only()

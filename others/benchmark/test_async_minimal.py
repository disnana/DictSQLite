"""Beta版v2の非同期版最小テスト"""

import asyncio
import sys
import os
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "others" / "beta-versions" / "dictsqlite-fastest" / "beta"))

from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta


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


async def test_async_minimal():
    """非同期版の最小テスト"""
    print("="*80)
    print("Beta版v2 - 非同期版最小テスト")
    print("="*80)
    
    db_path = "test_async_simple.db"
    cleanup_db(db_path)
    
    db = None
    try:
        print("\n[1/5] データベース作成（バックグラウンドタスク無効）...")
        db = AsyncDictSQLiteFastestBeta(
            db_name=db_path,
            cache_capacity=100,
            async_batch_size=50,
            async_commit_interval=0  # バックグラウンドタスク無効
        )
        print("   OK")
        
        print("\n[2/5] 初期化...")
        await db._ensure_initialized()
        print("   OK")
        
        print("\n[3/5] 書き込みテスト（100件）...")
        start = time.perf_counter()
        for i in range(100):
            await db.aset(f'key_{i}', f'value_{i}')
        await db._flush_write_buffer()
        elapsed = time.perf_counter() - start
        print(f"   OK: {elapsed:.3f}秒")
        
        print("\n[4/5] 読み取りテスト（100件）...")
        start = time.perf_counter()
        for i in range(100):
            value = await db.aget(f'key_{i}')
            assert value == f'value_{i}', f"Expected 'value_{i}', got '{value}'"
        elapsed = time.perf_counter() - start
        print(f"   OK: {elapsed:.3f}秒")
        
        print("\n[5/5] 統計情報...")
        stats = db.get_stats()
        print(f"   - バッチ書き込み: {stats['batch_writes']}")
        print(f"   - キャッシュヒット: {stats['cache_hits']}")
        print(f"   - キャッシュミス: {stats['cache_misses']}")
        print(f"   - ヒット率: {stats['cache']['hit_rate']:.1f}%")
        
        print("\n" + "="*80)
        print("[SUCCESS] 非同期版テスト成功！")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if db is not None:
            try:
                print("\n[INFO] データベースを閉じています...")
                await db.aclose()
                print("[INFO] データベース閉じました")
            except Exception as e:
                print(f"\n[WARN] close時のエラー: {e}")
                import traceback
                traceback.print_exc()
        
        await asyncio.sleep(0.5)
        cleanup_db(db_path)
        print("[INFO] クリーンアップ完了")


if __name__ == "__main__":
    print("[INFO] テスト開始...")
    asyncio.run(test_async_minimal())
    print("[INFO] テスト終了")

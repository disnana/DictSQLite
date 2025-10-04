#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""並行操作のデッドロック修正テスト"""

import sys
import asyncio
import tempfile
import time
from pathlib import Path

# パスの設定
sys.path.insert(0, str(Path(__file__).parent / 'dictsqlite-fastest'))
sys.path.insert(0, str(Path(__file__).parent / 'dictsqlite-fastest' / 'beta'))

from dictsqlite_fastest.main import AsyncDictSQLiteFastest
from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta


async def test_concurrent_writes_fastest(db_path: str, num_tasks: int, items_per_task: int):
    """Fastest版の並行書き込みテスト"""
    async with AsyncDictSQLiteFastest(db_path, table_name='test') as db:
        async def write_task(task_id: int):
            for i in range(items_per_task):
                key = f"task{task_id}_item{i}"
                value = {"task": task_id, "item": i, "data": "x" * 100}
                await db.aset(key, value)
        
        # 並行実行
        start = time.perf_counter()
        tasks = [write_task(i) for i in range(num_tasks)]
        await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start
        
        # 統計
        total_items = num_tasks * items_per_task
        throughput = total_items / elapsed if elapsed > 0 else 0
        
        return {
            'elapsed': elapsed,
            'throughput': throughput,
            'total_items': total_items
        }


async def test_concurrent_writes_beta(db_path: str, num_tasks: int, items_per_task: int):
    """Beta版の並行書き込みテスト"""
    async with AsyncDictSQLiteFastestBeta(db_path, table_name='test') as db:
        async def write_task(task_id: int):
            for i in range(items_per_task):
                key = f"task{task_id}_item{i}"
                value = {"task": task_id, "item": i, "data": "x" * 100}
                await db.aset(key, value)
        
        # 並行実行
        start = time.perf_counter()
        tasks = [write_task(i) for i in range(num_tasks)]
        await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start
        
        # 統計
        total_items = num_tasks * items_per_task
        throughput = total_items / elapsed if elapsed > 0 else 0
        
        return {
            'elapsed': elapsed,
            'throughput': throughput,
            'total_items': total_items
        }


async def main():
    print("🚀 並行操作デッドロック修正テスト\n")
    
    # テストケース
    test_cases = [
        {"num_tasks": 10, "items_per_task": 50},   # 500件, 並行度10
        {"num_tasks": 20, "items_per_task": 50},   # 1000件, 並行度20
        {"num_tasks": 50, "items_per_task": 40},   # 2000件, 並行度50
    ]
    
    for case in test_cases:
        num_tasks = case['num_tasks']
        items_per_task = case['items_per_task']
        total = num_tasks * items_per_task
        
        print("=" * 80)
        print(f"テストケース: {total}件, 並行度{num_tasks}")
        print("=" * 80)
        
        # Fastest版
        print("\n[AsyncDictSQLiteFastest]")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        try:
            result = await test_concurrent_writes_fastest(db_path, num_tasks, items_per_task)
            print(f"  ✅ 成功")
            print(f"  時間: {result['elapsed']:.3f}s")
            print(f"  スループット: {result['throughput']:,.0f} ops/sec")
        except Exception as e:
            print(f"  ❌ 失敗: {e}")
        finally:
            Path(db_path).unlink(missing_ok=True)
        
        # Beta版
        print("\n[AsyncDictSQLiteFastestBeta]")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        try:
            result = await test_concurrent_writes_beta(db_path, num_tasks, items_per_task)
            print(f"  ✅ 成功")
            print(f"  時間: {result['elapsed']:.3f}s")
            print(f"  スループット: {result['throughput']:,.0f} ops/sec")
        except Exception as e:
            print(f"  ❌ 失敗: {e}")
        finally:
            Path(db_path).unlink(missing_ok=True)
        
        print()
    
    print("=" * 80)
    print("✅ すべてのテスト完了！")
    print("=" * 80)


if __name__ == '__main__':
    asyncio.run(main())

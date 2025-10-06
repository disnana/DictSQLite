#!/usr/bin/env python
"""簡単なベンチマーク実行スクリプト"""

import sys
import os
import tempfile
from pathlib import Path

# パスの設定
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'beta'))

from dictsqlite_v2.core import DictSQLiteV2
from dictsqlite_v2.benchmarks import run_benchmark, PerformanceBaseline, PerformanceHistory
from dictsqlite_v2.utils import format_ops


def main():
    """ベンチマークのメイン実行"""
    print("=" * 70)
    print("DictSQLite-v2.0 ベンチマーク")
    print("=" * 70)
    
    # 一時ファイル
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # ベンチマーク実行
        print("\n[1/3] ベンチマーク実行中...")
        results = run_benchmark(DictSQLiteV2, db_path, num_items=1000)
        
        print(f"\n結果:")
        print(f"  書き込み速度: {format_ops(results['write_ops'])}")
        print(f"  読み込み速度: {format_ops(results['read_ops'])}")
        print(f"  バルク書き込み: {format_ops(results['bulk_write_ops'])}")
        
        # ベースライン保存
        print("\n[2/3] ベースライン保存...")
        reports_dir = Path(__file__).parent / 'reports'
        baseline = PerformanceBaseline(reports_dir / 'current_baseline.json')
        baseline.save_baseline(results)
        print(f"  ✓ ベースライン保存: {baseline.baseline_file}")
        
        # 履歴追加
        print("\n[3/3] 履歴追加...")
        history = PerformanceHistory(reports_dir / 'performance_history.json')
        history.add_entry(results, metadata={'version': '2.0.0', 'test': 'initial'})
        print(f"  ✓ 履歴追加: {history.history_file}")
        
        print("\n" + "=" * 70)
        print("✅ ベンチマーク完了!")
        print("=" * 70)
        
    finally:
        # クリーンアップ
        for ext in ['', '-wal', '-shm']:
            file_path = Path(db_path + ext)
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass


if __name__ == '__main__':
    main()

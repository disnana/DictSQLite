"""
包括的パフォーマンス比較ベンチマーク

以下のバージョンを比較:
- dictsqlite v1 (main.py)
- dictsqlite v2.0 (dictsqlite-fastest/dictsqlite_v2)
- dictsqlite-fastest (dictsqlite-fastest/dictsqlite_fastest)
- dictsqlite-fastest beta v2, v3, v4

測定内容:
1. 単発書き込み (single write)
2. 単発読み込み (single read)
3. バルク書き込み (bulk write)
4. バルク読み込み (bulk read)
5. 更新処理 (update)
6. 削除処理 (delete)
7. イテレーション (iteration)
"""

import sys
import os
import time
import statistics
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
import tempfile
import shutil

# パスの追加
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'dictsqlite'))
sys.path.insert(0, str(Path(__file__).parent / 'dictsqlite-fastest'))
sys.path.insert(0, str(Path(__file__).parent / 'dictsqlite-fastest' / 'dictsqlite_v2'))
sys.path.insert(0, str(Path(__file__).parent / 'dictsqlite-fastest' / 'dictsqlite_fastest'))


class BenchmarkRunner:
    """ベンチマーク実行クラス"""
    
    def __init__(self, warmup_runs: int = 2, test_runs: int = 5):
        self.warmup_runs = warmup_runs
        self.test_runs = test_runs
        self.results = {}
        self.temp_dirs = []
    
    def create_temp_db(self) -> str:
        """一時的なDBディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        return os.path.join(temp_dir, "test.db")
    
    def cleanup(self):
        """一時ディレクトリをクリーンアップ"""
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to cleanup {temp_dir}: {e}")
    
    def measure_time(self, func, *args, **kwargs) -> float:
        """関数の実行時間を測定"""
        start = time.perf_counter()
        func(*args, **kwargs)
        end = time.perf_counter()
        return end - start
    
    def benchmark_single_write(self, db_class, db_path: str, num_items: int = 1000) -> float:
        """単発書き込みのベンチマーク"""
        db = db_class(db_path)
        
        def write_items():
            for i in range(num_items):
                db[f"key_{i}"] = f"value_{i}"
        
        elapsed = self.measure_time(write_items)
        
        try:
            if hasattr(db, 'close'):
                db.close()
        except:
            pass
        
        return num_items / elapsed if elapsed > 0 else 0
    
    def benchmark_bulk_write(self, db_class, db_path: str, num_items: int = 1000) -> float:
        """バルク書き込みのベンチマーク"""
        db = db_class(db_path)
        
        # バルク書き込みメソッドがあるかチェック
        if hasattr(db, 'bulk_insert'):
            data = {f"key_{i}": f"value_{i}" for i in range(num_items)}
            elapsed = self.measure_time(db.bulk_insert, data)
        elif hasattr(db, 'update'):
            data = {f"key_{i}": f"value_{i}" for i in range(num_items)}
            elapsed = self.measure_time(db.update, data)
        else:
            # フォールバック: 通常の書き込み
            def write_items():
                for i in range(num_items):
                    db[f"key_{i}"] = f"value_{i}"
            elapsed = self.measure_time(write_items)
        
        try:
            if hasattr(db, 'close'):
                db.close()
        except:
            pass
        
        return num_items / elapsed if elapsed > 0 else 0
    
    def benchmark_single_read(self, db_class, db_path: str, num_items: int = 1000) -> float:
        """単発読み込みのベンチマーク"""
        db = db_class(db_path)
        
        # まずデータを準備
        for i in range(num_items):
            db[f"key_{i}"] = f"value_{i}"
        
        def read_items():
            for i in range(num_items):
                _ = db[f"key_{i}"]
        
        elapsed = self.measure_time(read_items)
        
        try:
            if hasattr(db, 'close'):
                db.close()
        except:
            pass
        
        return num_items / elapsed if elapsed > 0 else 0
    
    def benchmark_update(self, db_class, db_path: str, num_items: int = 1000) -> float:
        """更新処理のベンチマーク"""
        db = db_class(db_path)
        
        # まずデータを準備
        for i in range(num_items):
            db[f"key_{i}"] = f"value_{i}"
        
        def update_items():
            for i in range(num_items):
                db[f"key_{i}"] = f"updated_value_{i}"
        
        elapsed = self.measure_time(update_items)
        
        try:
            if hasattr(db, 'close'):
                db.close()
        except:
            pass
        
        return num_items / elapsed if elapsed > 0 else 0
    
    def benchmark_delete(self, db_class, db_path: str, num_items: int = 1000) -> float:
        """削除処理のベンチマーク"""
        db = db_class(db_path)
        
        # まずデータを準備
        for i in range(num_items):
            db[f"key_{i}"] = f"value_{i}"
        
        def delete_items():
            for i in range(num_items):
                del db[f"key_{i}"]
        
        elapsed = self.measure_time(delete_items)
        
        try:
            if hasattr(db, 'close'):
                db.close()
        except:
            pass
        
        return num_items / elapsed if elapsed > 0 else 0
    
    def run_benchmark_suite(self, name: str, db_class, num_items: int = 1000):
        """特定のDBクラスに対してベンチマークスイートを実行"""
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"{'='*60}")
        
        results = {
            'name': name,
            'single_write': [],
            'bulk_write': [],
            'single_read': [],
            'update': [],
            'delete': []
        }
        
        benchmarks = [
            ('single_write', self.benchmark_single_write),
            ('bulk_write', self.benchmark_bulk_write),
            ('single_read', self.benchmark_single_read),
            ('update', self.benchmark_update),
            ('delete', self.benchmark_delete),
        ]
        
        for bench_name, bench_func in benchmarks:
            print(f"  Running {bench_name}...", end=' ', flush=True)
            
            # ウォームアップ
            for _ in range(self.warmup_runs):
                db_path = self.create_temp_db()
                try:
                    bench_func(db_class, db_path, num_items)
                except Exception as e:
                    print(f"\n    Warning during warmup: {e}")
            
            # 実測定
            ops_per_sec_list = []
            for _ in range(self.test_runs):
                db_path = self.create_temp_db()
                try:
                    ops_per_sec = bench_func(db_class, db_path, num_items)
                    ops_per_sec_list.append(ops_per_sec)
                except Exception as e:
                    print(f"\n    Error: {e}")
                    break
            
            if ops_per_sec_list:
                avg_ops = statistics.mean(ops_per_sec_list)
                results[bench_name] = ops_per_sec_list
                print(f"{avg_ops:,.0f} ops/sec")
            else:
                print("FAILED")
        
        self.results[name] = results
        return results


def main():
    """メイン関数"""
    print("=" * 80)
    print("DictSQLite 包括的パフォーマンス比較ベンチマーク")
    print("=" * 80)
    
    runner = BenchmarkRunner(warmup_runs=2, test_runs=5)
    
    # テスト項目数
    num_items = 1000
    
    try:
        # 1. dictsqlite v1
        try:
            from dictsqlite.main import DictSQLite as DictSQLiteV1
            runner.run_benchmark_suite("DictSQLite v1", DictSQLiteV1, num_items)
        except Exception as e:
            print(f"\nSkipping DictSQLite v1: {e}")
        
        # 2. dictsqlite v2.0
        try:
            from dictsqlite_v2.core import DictSQLiteV2
            runner.run_benchmark_suite("DictSQLite v2.0", DictSQLiteV2, num_items)
        except Exception as e:
            print(f"\nSkipping DictSQLite v2.0: {e}")
        
        # 3. dictsqlite-fastest
        try:
            from dictsqlite_fastest.main import DictSQLiteFastest
            runner.run_benchmark_suite("DictSQLite-Fastest", DictSQLiteFastest, num_items)
        except Exception as e:
            print(f"\nSkipping DictSQLite-Fastest: {e}")
        
        # 4. dictsqlite-fastest beta v2
        try:
            sys.path.insert(0, str(Path(__file__).parent / 'dictsqlite-fastest' / 'beta'))
            from dictsqlite_fastest_beta_v2 import DictSQLiteFastest as DictSQLiteFastestBetaV2
            runner.run_benchmark_suite("DictSQLite-Fastest Beta v2", DictSQLiteFastestBetaV2, num_items)
        except Exception as e:
            print(f"\nSkipping DictSQLite-Fastest Beta v2: {e}")
        
        # 5. dictsqlite-fastest beta v3
        try:
            from dictsqlite_fastest_beta_v3_alpha import DictSQLiteFastest as DictSQLiteFastestBetaV3
            runner.run_benchmark_suite("DictSQLite-Fastest Beta v3", DictSQLiteFastestBetaV3, num_items)
        except Exception as e:
            print(f"\nSkipping DictSQLite-Fastest Beta v3: {e}")
        
        # 6. dictsqlite-fastest beta v4
        try:
            from dictsqlite_fastest_beta_v4 import DictSQLiteFastestBeta as DictSQLiteFastestBetaV4
            runner.run_benchmark_suite("DictSQLite-Fastest Beta v4", DictSQLiteFastestBetaV4, num_items)
        except Exception as e:
            print(f"\nSkipping DictSQLite-Fastest Beta v4: {e}")
        
        # 結果のサマリを表示
        print("\n" + "=" * 80)
        print("ベンチマーク結果サマリ")
        print("=" * 80)
        
        # 結果を表形式で表示
        print(f"\n{'Version':<30} {'Single Write':<15} {'Bulk Write':<15} {'Single Read':<15} {'Update':<15} {'Delete':<15}")
        print("-" * 110)
        
        for name, results in runner.results.items():
            single_write = statistics.mean(results['single_write']) if results['single_write'] else 0
            bulk_write = statistics.mean(results['bulk_write']) if results['bulk_write'] else 0
            single_read = statistics.mean(results['single_read']) if results['single_read'] else 0
            update = statistics.mean(results['update']) if results['update'] else 0
            delete = statistics.mean(results['delete']) if results['delete'] else 0
            
            print(f"{name:<30} {single_write:>13,.0f}  {bulk_write:>13,.0f}  {single_read:>13,.0f}  {update:>13,.0f}  {delete:>13,.0f}")
        
        # 結果をJSONファイルに保存
        output_file = "benchmark_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(runner.results, f, indent=2, ensure_ascii=False)
        print(f"\n詳細な結果を {output_file} に保存しました。")
        
    finally:
        # クリーンアップ
        runner.cleanup()


if __name__ == "__main__":
    main()

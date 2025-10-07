#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DictSQLite 高速包括ベンチマーク v2

包括的テストを高速化：
- データ量を最適化（10分の1程度に削減）
- 重複テストを削減
- 並列実行可能な構造
- エラー検出に重点

約2-3分で完了する包括的テスト。
"""

import sys
import os
import time
import asyncio
import tempfile
import statistics
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor

# モジュールパスの設定
BASE_DIR = Path(__file__).parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest'))
sys.path.insert(0, str(REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest' / 'beta'))

# インポート
from dictsqlite.main import DictSQLite
from dictsqlite_fastest.main import DictSQLiteFastest, AsyncDictSQLiteFastest
from dictsqlite_fastest_beta import DictSQLiteFastestBeta, AsyncDictSQLiteFastestBeta


# =====================================================================
# 設定
# =====================================================================

# 高速化のためのデータサイズ（従来の1/10）
TEST_SIZES = {
    'tiny': 50,      # エッジケース用
    'small': 100,    # 基本動作確認
    'medium': 500,   # 標準的な使用
    'large': 2000,   # 大量データ（従来は10000）
}

# テスト設定
CONFIG = {
    'iterations': 2,  # 測定回数（従来は3）
    'thread_count': 3,  # スレッド数（従来は5）
    'verbose': True,
}


# =====================================================================
# ユーティリティ
# =====================================================================

def format_time(seconds: float) -> str:
    """時間をフォーマット"""
    if seconds < 0.001:
        return f"{seconds*1_000_000:.2f}μs"
    elif seconds < 1:
        return f"{seconds*1_000:.2f}ms"
    else:
        return f"{seconds:.3f}s"


def format_ops(ops: float) -> str:
    """OPSをフォーマット"""
    if ops >= 1_000_000:
        return f"{ops/1_000_000:.2f}M ops/s"
    elif ops >= 1_000:
        return f"{ops/1_000:.2f}K ops/s"
    else:
        return f"{ops:.2f} ops/s"


class TestResult:
    """テスト結果を保持"""
    def __init__(self, name: str):
        self.name = name
        self.success = 0
        self.failure = 0
        self.errors = []
        self.times = []
        self.details = {}
    
    def add_success(self, duration: float):
        self.success += 1
        self.times.append(duration)
    
    def add_failure(self, error: str):
        self.failure += 1
        self.errors.append(error)
    
    @property
    def total(self):
        return self.success + self.failure
    
    @property
    def success_rate(self):
        if self.total == 0:
            return 0
        return (self.success / self.total) * 100
    
    @property
    def avg_time(self):
        return statistics.mean(self.times) if self.times else 0
    
    def summary(self):
        return {
            'name': self.name,
            'success': self.success,
            'failure': self.failure,
            'total': self.total,
            'success_rate': self.success_rate,
            'avg_time': self.avg_time,
            'errors': self.errors[:5]  # 最初の5個のみ
        }


# =====================================================================
# ベンチマーククラス
# =====================================================================

class FastComprehensiveBenchmark:
    """高速包括ベンチマーク"""
    
    def __init__(self):
        self.results = {
            'original': {},
            'fastest': {},
            'beta': {}
        }
        self.start_time = time.time()
    
    def log(self, message: str, level: str = 'INFO'):
        """ログ出力"""
        if CONFIG['verbose']:
            elapsed = time.time() - self.start_time
            print(f"[{elapsed:6.2f}s] {message}")
    
    def test_sync_basic_write(self, db_class, count: int) -> TestResult:
        """基本書き込みテスト"""
        result = TestResult(f"基本書き込み ({count}件)")
        
        for iteration in range(CONFIG['iterations']):
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                db_path = tmp.name
            
            try:
                start = time.perf_counter()
                db = db_class(db_path)
                try:
                    for i in range(count):
                        db[f'key_{i}'] = f'value_{i}'
                finally:
                    db.close()
                duration = time.perf_counter() - start
                result.add_success(duration)
            except Exception as e:
                result.add_failure(f"{type(e).__name__}: {str(e)}")
            finally:
                try:
                    os.unlink(db_path)
                except:
                    pass
        
        return result
    
    def test_sync_basic_read(self, db_class, count: int) -> TestResult:
        """基本読み込みテスト"""
        result = TestResult(f"基本読み込み ({count}件)")
        
        # データ準備
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        db = db_class(db_path)
        try:
            for i in range(count):
                db[f'key_{i}'] = f'value_{i}'
        finally:
            db.close()
        
        # 読み込みテスト
        for iteration in range(CONFIG['iterations']):
            try:
                start = time.perf_counter()
                db = db_class(db_path)
                try:
                    for i in range(count):
                        _ = db[f'key_{i}']
                finally:
                    db.close()
                duration = time.perf_counter() - start
                result.add_success(duration)
            except Exception as e:
                result.add_failure(f"{type(e).__name__}: {str(e)}")
        
        try:
            os.unlink(db_path)
        except:
            pass
        
        return result
    
    def test_sync_bulk_insert(self, db_class, count: int) -> TestResult:
        """バルク挿入テスト"""
        result = TestResult(f"バルク挿入 ({count}件)")
        
        # bulk_insertがないクラスはスキップ
        if not hasattr(db_class, '__name__') or 'Fastest' not in db_class.__name__:
            result.add_failure("bulk_insert not supported")
            return result
        
        for iteration in range(CONFIG['iterations']):
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                db_path = tmp.name
            
            try:
                start = time.perf_counter()
                db = db_class(db_path)
                try:
                    data = {f'key_{i}': f'value_{i}' for i in range(count)}
                    db.bulk_insert(data)
                finally:
                    db.close()
                duration = time.perf_counter() - start
                result.add_success(duration)
            except Exception as e:
                result.add_failure(f"{type(e).__name__}: {str(e)}")
            finally:
                try:
                    os.unlink(db_path)
                except:
                    pass
        
        return result
    
    def test_sync_complex_data(self, db_class, count: int) -> TestResult:
        """複雑データテスト"""
        result = TestResult(f"複雑データ ({count}件)")
        
        for iteration in range(CONFIG['iterations']):
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                db_path = tmp.name
            
            try:
                start = time.perf_counter()
                db = db_class(db_path)
                try:
                    for i in range(count):
                        db[f'user_{i}'] = {
                            'id': i,
                            'name': f'User {i}',
                            'tags': [f'tag{j}' for j in range(5)],
                            'metadata': {'score': i * 1.5, 'active': i % 2 == 0}
                        }
                finally:
                    db.close()
                duration = time.perf_counter() - start
                result.add_success(duration)
            except Exception as e:
                result.add_failure(f"{type(e).__name__}: {str(e)}")
            finally:
                try:
                    os.unlink(db_path)
                except:
                    pass
        
        return result
    
    def test_sync_update(self, db_class, count: int) -> TestResult:
        """更新テスト"""
        result = TestResult(f"更新操作 ({count}件)")
        
        # データ準備
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        db = db_class(db_path)
        try:
            for i in range(count):
                db[f'key_{i}'] = f'value_{i}'
        finally:
            db.close()
        
        # 更新テスト
        for iteration in range(CONFIG['iterations']):
            try:
                start = time.perf_counter()
                db = db_class(db_path)
                try:
                    for i in range(count):
                        db[f'key_{i}'] = f'updated_{i}'
                finally:
                    db.close()
                duration = time.perf_counter() - start
                result.add_success(duration)
            except Exception as e:
                result.add_failure(f"{type(e).__name__}: {str(e)}")
        
        try:
            os.unlink(db_path)
        except:
            pass
        
        return result
    
    def test_sync_mixed(self, db_class, count: int) -> TestResult:
        """混合操作テスト（get()メソッドを含む）"""
        result = TestResult(f"混合操作 ({count}件)")
        
        for iteration in range(CONFIG['iterations']):
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                db_path = tmp.name
            
            try:
                start = time.perf_counter()
                db = db_class(db_path)
                try:
                    for i in range(count):
                        # 書き込み
                        db[f'key_{i}'] = f'value_{i}'
                        
                        # 読み込み（get使用）
                        if i % 2 == 0 and i > 0:
                            if hasattr(db, 'get'):
                                _ = db.get(f'key_{i//2}', None)
                            else:
                                try:
                                    _ = db[f'key_{i//2}']
                                except KeyError:
                                    pass
                        
                        # 更新
                        if i % 3 == 0 and i > 0:
                            db[f'key_{i//3}'] = f'updated_{i}'
                        
                        # 削除
                        if i % 5 == 0 and i > 0:
                            try:
                                del db[f'key_{i//5}']
                            except KeyError:
                                pass
                finally:
                    db.close()
                duration = time.perf_counter() - start
                result.add_success(duration)
            except Exception as e:
                result.add_failure(f"{type(e).__name__}: {str(e)}")
            finally:
                try:
                    os.unlink(db_path)
                except:
                    pass
        
        return result
    
    def test_multithreaded(self, db_class, count: int) -> TestResult:
        """マルチスレッドテスト"""
        result = TestResult(f"マルチスレッド ({count}件 x {CONFIG['thread_count']}スレッド)")
        
        def worker(thread_id: int, db_path: str):
            """ワーカースレッド"""
            db = db_class(db_path)
            try:
                for i in range(count):
                    db[f'thread{thread_id}_key{i}'] = f'value_{i}'
            finally:
                db.close()
        
        for iteration in range(CONFIG['iterations']):
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                db_path = tmp.name
            
            try:
                start = time.perf_counter()
                with ThreadPoolExecutor(max_workers=CONFIG['thread_count']) as executor:
                    futures = [
                        executor.submit(worker, tid, db_path)
                        for tid in range(CONFIG['thread_count'])
                    ]
                    for future in futures:
                        future.result()
                duration = time.perf_counter() - start
                result.add_success(duration)
            except Exception as e:
                result.add_failure(f"{type(e).__name__}: {str(e)}")
            finally:
                try:
                    os.unlink(db_path)
                except:
                    pass
        
        return result
    
    async def test_async_basic(self, db_class_async, count: int) -> TestResult:
        """非同期基本テスト"""
        result = TestResult(f"非同期基本 ({count}件)")
        
        for iteration in range(CONFIG['iterations']):
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                db_path = tmp.name
            
            try:
                start = time.perf_counter()
                db = db_class_async(db_path)
                try:
                    for i in range(count):
                        # 非同期版は aset() を使用
                        await db.aset(f'key_{i}', f'value_{i}')
                finally:
                    # 非同期版は aclose() を使用
                    await db.aclose()
                duration = time.perf_counter() - start
                result.add_success(duration)
            except Exception as e:
                result.add_failure(f"{type(e).__name__}: {str(e)}")
            finally:
                try:
                    os.unlink(db_path)
                except:
                    pass
        
        return result
    
    def run_version_tests(self, version_name: str, db_class, db_class_async=None):
        """バージョン別テスト実行"""
        self.log(f"\n{'='*70}")
        self.log(f"  {version_name} テスト開始")
        self.log(f"{'='*70}")
        
        results = {}
        
        # 同期テスト
        self.log(f"\n[同期操作]")
        
        # 小規模（エッジケース検出）
        self.log("  小規模テスト (100件)...")
        results['write_small'] = self.test_sync_basic_write(db_class, TEST_SIZES['small'])
        results['read_small'] = self.test_sync_basic_read(db_class, TEST_SIZES['small'])
        
        # 中規模（標準的な使用）
        self.log("  中規模テスト (500件)...")
        results['write_medium'] = self.test_sync_basic_write(db_class, TEST_SIZES['medium'])
        results['bulk_insert_medium'] = self.test_sync_bulk_insert(db_class, TEST_SIZES['medium'])
        results['complex_medium'] = self.test_sync_complex_data(db_class, TEST_SIZES['medium'])
        
        # 大規模（パフォーマンステスト）
        self.log("  大規模テスト (2000件)...")
        results['bulk_insert_large'] = self.test_sync_bulk_insert(db_class, TEST_SIZES['large'])
        results['update_large'] = self.test_sync_update(db_class, TEST_SIZES['large'])
        
        # 混合・マルチスレッド
        self.log("  特殊テスト...")
        results['mixed'] = self.test_sync_mixed(db_class, TEST_SIZES['medium'])
        results['multithreaded'] = self.test_multithreaded(db_class, TEST_SIZES['small'])
        
        # 非同期テスト
        if db_class_async:
            self.log(f"\n[非同期操作]")
            results['async_basic'] = asyncio.run(
                self.test_async_basic(db_class_async, TEST_SIZES['medium'])
            )
        
        self.results[version_name.lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '')] = results
        return results
    
    def print_summary(self):
        """サマリー表示"""
        print("\n" + "="*70)
        print("  📊 テスト結果サマリー")
        print("="*70)
        
        for version_key, tests in self.results.items():
            version_name = version_key.replace('_', ' ').title()
            print(f"\n{version_name}:")
            print("-" * 70)
            
            total_success = 0
            total_tests = 0
            total_errors = []
            
            for test_name, result in tests.items():
                total_success += result.success
                total_tests += result.total
                total_errors.extend(result.errors)
                
                status = "✅" if result.failure == 0 else "❌"
                time_str = format_time(result.avg_time) if result.times else "N/A"
                
                print(f"  {status} {result.name:30s}: {result.success}/{result.total} "
                      f"({result.success_rate:5.1f}%) - {time_str}")
            
            success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0
            print(f"\n  総合成功率: {total_success}/{total_tests} ({success_rate:.1f}%)")
            
            if total_errors:
                print(f"  ⚠️  エラー数: {len(total_errors)}")
                print(f"  最初のエラー: {total_errors[0][:100]}")
        
        print("\n" + "="*70)
        print(f"  ⏱️  総実行時間: {format_time(time.time() - self.start_time)}")
        print("="*70)
    
    def save_results(self, filepath: str = None):
        """結果をJSONで保存"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"fast_benchmark_results_{timestamp}.json"
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'config': CONFIG,
            'test_sizes': TEST_SIZES,
            'total_time': time.time() - self.start_time,
            'results': {}
        }
        
        for version_key, tests in self.results.items():
            output['results'][version_key] = {
                test_name: result.summary()
                for test_name, result in tests.items()
            }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 結果を保存しました: {filepath}")


# =====================================================================
# メイン処理
# =====================================================================

def main():
    """メイン処理"""
    print("="*70)
    print("  🚀 DictSQLite 高速包括ベンチマーク v2")
    print("="*70)
    print("\n  従来の包括テストを高速化（約2-3分で完了）")
    print("  - データ量: 最適化（50〜2000件）")
    print("  - 測定回数: 2回")
    print("  - 包括性: 維持（エッジケース検出重視）")
    print()
    
    benchmark = FastComprehensiveBenchmark()
    
    try:
        # オリジナル版
        benchmark.run_version_tests(
            "Original",
            DictSQLite
        )
        
        # APSW版
        benchmark.run_version_tests(
            "Fastest (APSW)",
            DictSQLiteFastest,
            AsyncDictSQLiteFastest
        )
        
        # Beta版
        benchmark.run_version_tests(
            "Beta",
            DictSQLiteFastestBeta,
            AsyncDictSQLiteFastestBeta
        )
        
        # サマリー表示
        benchmark.print_summary()
        
        # 結果保存
        output_path = BASE_DIR / "results" / f"fast_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path.parent.mkdir(exist_ok=True)
        benchmark.save_results(str(output_path))
        
        print("\n🎉 すべてのテストが完了しました！")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  テストが中断されました")
        benchmark.print_summary()
    except Exception as e:
        print(f"\n\n❌ エラーが発生しました: {e}")
        traceback.print_exc()
        benchmark.print_summary()


if __name__ == '__main__':
    main()

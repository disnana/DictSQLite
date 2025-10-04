#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DictSQLite 包括的ベンチマークツール

3つのバージョンを徹底的に比較:
- DictSQLite (オリジナル版)
- DictSQLite-Fastest (APSW版)
- DictSQLite-Fastest Beta (メモリ最適化版)

同期・非同期操作、バルク処理、複雑なデータ構造など、
あらゆるシナリオでパフォーマンスを詳細に測定します。
"""

import sys
import os
import time
import asyncio
import tempfile
import shutil
import statistics
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Callable, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import traceback

# モジュールパスの設定
BASE_DIR = Path(__file__).parent
REPO_ROOT = BASE_DIR.parent.parent  # /others/benchmark から / へ
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'dictsqlite-fastest'))
sys.path.insert(0, str(REPO_ROOT / 'dictsqlite-fastest' / 'beta'))

# インポート
from dictsqlite.main import DictSQLite
from dictsqlite_fastest.main import DictSQLiteFastest, AsyncDictSQLiteFastest
from dictsqlite_fastest_beta import DictSQLiteFastestBeta, AsyncDictSQLiteFastestBeta


# =====================================================================
# ユーティリティ関数
# =====================================================================

def format_number(num: float) -> str:
    """数値を読みやすくフォーマット"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{num/1_000:.2f}K"
    else:
        return f"{num:.2f}"


def format_ops(ops: float) -> str:
    """OPS値を読みやすくフォーマット"""
    return f"{format_number(ops)} ops/sec"


def format_time(seconds: float) -> str:
    """時間を読みやすくフォーマット"""
    if seconds < 0.001:
        return f"{seconds*1_000_000:.2f}μs"
    elif seconds < 1:
        return f"{seconds*1_000:.2f}ms"
    else:
        return f"{seconds:.3f}s"


def calculate_stats(times: List[float]) -> Dict[str, float]:
    """統計情報を計算"""
    if not times:
        return {'mean': 0, 'median': 0, 'stdev': 0, 'min': 0, 'max': 0}
    return {
        'mean': statistics.mean(times),
        'median': statistics.median(times),
        'stdev': statistics.stdev(times) if len(times) > 1 else 0,
        'min': min(times),
        'max': max(times)
    }


# =====================================================================
# ベンチマーククラス
# =====================================================================

class ComprehensiveBenchmark:
    """包括的ベンチマークマネージャー"""
    
    def __init__(self, output_dir: str = None):
        """
        Args:
            output_dir: 結果を保存するディレクトリ（デフォルト: /others/benchmark/results）
        """
        if output_dir is None:
            output_dir = str(BASE_DIR / "results")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 結果保存用
        self.results = []
        self.async_results = []
        
        # タイムスタンプ
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # ログファイル
        self.log_file = self.output_dir / f"benchmark_{self.timestamp}.log"
        self.csv_file = self.output_dir / f"benchmark_{self.timestamp}.csv"
        self.json_file = self.output_dir / f"benchmark_{self.timestamp}.json"
        self.summary_file = self.output_dir / f"summary_{self.timestamp}.md"
        
    def log(self, message: str, print_console: bool = True):
        """ログメッセージを出力"""
        if print_console:
            try:
                print(message)
            except UnicodeEncodeError:
                # Windows環境でのエンコードエラーを回避
                print(message.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    
    def measure_sync_operation(
        self,
        name: str,
        func: Callable,
        iterations: int = 3,
        warmup: int = 1
    ) -> Dict[str, Any]:
        """同期操作のベンチマーク測定
        
        Args:
            name: 操作名
            func: 測定する関数
            iterations: 測定回数
            warmup: ウォームアップ回数
            
        Returns:
            測定結果の辞書
        """
        # ウォームアップ
        for _ in range(warmup):
            try:
                func()
            except Exception:
                pass
        
        # 測定
        times = []
        errors = []
        
        for i in range(iterations):
            try:
                start = time.perf_counter()
                result = func()
                duration = time.perf_counter() - start
                times.append(duration)
            except Exception as e:
                errors.append(str(e))
                self.log(f"  エラー (試行 {i+1}): {e}", print_console=False)
        
        if not times:
            return {
                'name': name,
                'success': False,
                'error': errors[0] if errors else 'Unknown error',
                'times': [],
                'stats': {}
            }
        
        stats = calculate_stats(times)
        
        return {
            'name': name,
            'success': True,
            'times': times,
            'stats': stats,
            'iterations': len(times)
        }
    
    async def measure_async_operation(
        self,
        name: str,
        func: Callable,
        iterations: int = 3,
        warmup: int = 1
    ) -> Dict[str, Any]:
        """非同期操作のベンチマーク測定
        
        Args:
            name: 操作名
            func: 測定する非同期関数
            iterations: 測定回数
            warmup: ウォームアップ回数
            
        Returns:
            測定結果の辞書
        """
        # ウォームアップ
        for _ in range(warmup):
            try:
                await func()
            except Exception:
                pass
        
        # 測定
        times = []
        errors = []
        
        for i in range(iterations):
            try:
                start = time.perf_counter()
                await func()
                duration = time.perf_counter() - start
                times.append(duration)
            except Exception as e:
                errors.append(str(e))
                self.log(f"  エラー (試行 {i+1}): {e}", print_console=False)
        
        if not times:
            return {
                'name': name,
                'success': False,
                'error': errors[0] if errors else 'Unknown error',
                'times': [],
                'stats': {}
            }
        
        stats = calculate_stats(times)
        
        return {
            'name': name,
            'success': True,
            'times': times,
            'stats': stats,
            'iterations': len(times)
        }
    
    def compare_sync_versions(
        self,
        test_name: str,
        original_func: Callable,
        fastest_func: Callable,
        beta_func: Callable,
        operation_count: int,
        iterations: int = 3
    ):
        """3バージョンの同期操作を比較
        
        Args:
            test_name: テスト名
            original_func: オリジナル版の関数
            fastest_func: Fastest版の関数
            beta_func: Beta版の関数
            operation_count: 操作数
            iterations: 測定回数
        """
        self.log(f"\n{'='*80}")
        self.log(f"テスト: {test_name}")
        self.log(f"操作数: {operation_count:,}")
        self.log(f"{'='*80}")
        
        # 各バージョンを測定
        results = {}
        
        # オリジナル版
        self.log("\n[DictSQLite オリジナル版]")
        original_result = self.measure_sync_operation(
            f"{test_name} (Original)",
            original_func,
            iterations
        )
        if original_result['success']:
            orig_time = original_result['stats']['mean']
            orig_ops = operation_count / orig_time
            self.log(f"  平均時間: {format_time(orig_time)}")
            self.log(f"  スループット: {format_ops(orig_ops)}")
            results['original'] = {
                'time': orig_time,
                'ops': orig_ops,
                'stats': original_result['stats']
            }
        else:
            self.log(f"  失敗: {original_result.get('error', 'Unknown')}")
            results['original'] = None
        
        # Fastest版
        self.log("\n[DictSQLite-Fastest APSW版]")
        fastest_result = self.measure_sync_operation(
            f"{test_name} (Fastest)",
            fastest_func,
            iterations
        )
        if fastest_result['success']:
            fastest_time = fastest_result['stats']['mean']
            fastest_ops = operation_count / fastest_time
            self.log(f"  平均時間: {format_time(fastest_time)}")
            self.log(f"  スループット: {format_ops(fastest_ops)}")
            results['fastest'] = {
                'time': fastest_time,
                'ops': fastest_ops,
                'stats': fastest_result['stats']
            }
        else:
            self.log(f"  失敗: {fastest_result.get('error', 'Unknown')}")
            results['fastest'] = None
        
        # Beta版
        self.log("\n[DictSQLite-Fastest Beta版]")
        beta_result = self.measure_sync_operation(
            f"{test_name} (Beta)",
            beta_func,
            iterations
        )
        if beta_result['success']:
            beta_time = beta_result['stats']['mean']
            beta_ops = operation_count / beta_time
            self.log(f"  平均時間: {format_time(beta_time)}")
            self.log(f"  スループット: {format_ops(beta_ops)}")
            results['beta'] = {
                'time': beta_time,
                'ops': beta_ops,
                'stats': beta_result['stats']
            }
        else:
            self.log(f"  失敗: {beta_result.get('error', 'Unknown')}")
            results['beta'] = None
        
        # 比較結果
        self.log("\n[比較結果]")
        if results['original'] and results['fastest']:
            speedup_fastest = results['original']['time'] / results['fastest']['time']
            self.log(f"  Fastest vs Original: {speedup_fastest:.2f}x 高速")
        
        if results['original'] and results['beta']:
            speedup_beta = results['original']['time'] / results['beta']['time']
            self.log(f"  Beta vs Original: {speedup_beta:.2f}x 高速")
        
        if results['fastest'] and results['beta']:
            speedup_beta_fastest = results['fastest']['time'] / results['beta']['time']
            self.log(f"  Beta vs Fastest: {speedup_beta_fastest:.2f}x 高速")
        
        # 最速を判定
        valid_results = {k: v for k, v in results.items() if v is not None}
        if valid_results:
            fastest_version = min(valid_results.items(), key=lambda x: x[1]['time'])
            self.log(f"\n  [最速] {fastest_version[0].upper()}")
        
        # 結果を保存
        self.results.append({
            'test_name': test_name,
            'operation_count': operation_count,
            'results': results
        })
    
    async def compare_async_versions(
        self,
        test_name: str,
        fastest_func: Callable,
        beta_func: Callable,
        operation_count: int,
        iterations: int = 3
    ):
        """2バージョンの非同期操作を比較
        
        Args:
            test_name: テスト名
            fastest_func: Fastest版の非同期関数
            beta_func: Beta版の非同期関数
            operation_count: 操作数
            iterations: 測定回数
        """
        self.log(f"\n{'='*80}")
        self.log(f"非同期テスト: {test_name}")
        self.log(f"操作数: {operation_count:,}")
        self.log(f"{'='*80}")
        
        results = {}
        
        # Fastest版
        self.log("\n[AsyncDictSQLiteFastest]")
        fastest_result = await self.measure_async_operation(
            f"{test_name} (Async Fastest)",
            fastest_func,
            iterations
        )
        if fastest_result['success']:
            fastest_time = fastest_result['stats']['mean']
            fastest_ops = operation_count / fastest_time
            self.log(f"  平均時間: {format_time(fastest_time)}")
            self.log(f"  スループット: {format_ops(fastest_ops)}")
            results['fastest'] = {
                'time': fastest_time,
                'ops': fastest_ops,
                'stats': fastest_result['stats']
            }
        else:
            self.log(f"  失敗: {fastest_result.get('error', 'Unknown')}")
            results['fastest'] = None
        
        # Beta版
        self.log("\n[AsyncDictSQLiteFastestBeta]")
        beta_result = await self.measure_async_operation(
            f"{test_name} (Async Beta)",
            beta_func,
            iterations
        )
        if beta_result['success']:
            beta_time = beta_result['stats']['mean']
            beta_ops = operation_count / beta_time
            self.log(f"  平均時間: {format_time(beta_time)}")
            self.log(f"  スループット: {format_ops(beta_ops)}")
            results['beta'] = {
                'time': beta_time,
                'ops': beta_ops,
                'stats': beta_result['stats']
            }
        else:
            self.log(f"  失敗: {beta_result.get('error', 'Unknown')}")
            results['beta'] = None
        
        # 比較結果
        self.log("\n[比較結果]")
        if results['fastest'] and results['beta']:
            speedup = results['fastest']['time'] / results['beta']['time']
            if speedup > 1:
                self.log(f"  Beta vs Fastest: {speedup:.2f}x 高速")
                self.log(f"  [最速] BETA")
            else:
                self.log(f"  Fastest vs Beta: {1/speedup:.2f}x 高速")
                self.log(f"  [最速] FASTEST")
        
        # 結果を保存
        self.async_results.append({
            'test_name': test_name,
            'operation_count': operation_count,
            'results': results
        })


# =====================================================================
# テストシナリオ
# =====================================================================

class BenchmarkScenarios:
    """ベンチマークテストシナリオ集"""
    
    def __init__(self, benchmark: ComprehensiveBenchmark):
        self.benchmark = benchmark
        self.temp_dir = Path(tempfile.mkdtemp(prefix="dictsqlite_bench_"))
    
    def cleanup(self):
        """一時ディレクトリをクリーンアップ"""
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"クリーンアップエラー: {e}")
    
    # -----------------------------------------------------------------
    # 基本操作テスト
    # -----------------------------------------------------------------
    
    def test_basic_write(self, count: int = 1000):
        """基本的な書き込み操作"""
        test_name = f"基本書き込み ({count}件)"
        
        def original():
            db_path = self.temp_dir / f"original_write_{count}.db"
            if db_path.exists():
                db_path.unlink()
            with DictSQLite(str(db_path)) as db:
                for i in range(count):
                    db[f'key_{i}'] = f'value_{i}'
        
        def fastest():
            db_path = self.temp_dir / f"fastest_write_{count}.db"
            if db_path.exists():
                db_path.unlink()
            # コンテキストマネージャーを使用
            db = DictSQLiteFastest(str(db_path))
            try:
                for i in range(count):
                    db[f'key_{i}'] = f'value_{i}'
            finally:
                db.close()
        
        def beta():
            db_path = self.temp_dir / f"beta_write_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            try:
                for i in range(count):
                    db[f'key_{i}'] = f'value_{i}'
            finally:
                db.close()
        
        self.benchmark.compare_sync_versions(
            test_name, original, fastest, beta, count
        )
    
    def test_basic_read(self, count: int = 1000):
        """基本的な読み込み操作"""
        test_name = f"基本読み込み ({count}件)"
        
        # データ準備
        original_db_path = self.temp_dir / f"original_read_{count}.db"
        fastest_db_path = self.temp_dir / f"fastest_read_{count}.db"
        beta_db_path = self.temp_dir / f"beta_read_{count}.db"
        
        # データ作成
        with DictSQLite(str(original_db_path)) as db:
            for i in range(count):
                db[f'key_{i}'] = f'value_{i}'
        
        db_fastest = DictSQLiteFastest(str(fastest_db_path))
        try:
            for i in range(count):
                db_fastest[f'key_{i}'] = f'value_{i}'
        finally:
            db_fastest.close()
        
        db_beta = DictSQLiteFastestBeta(str(beta_db_path), memory_budget_mb=100)
        try:
            for i in range(count):
                db_beta[f'key_{i}'] = f'value_{i}'
        finally:
            db_beta.close()
        
        def original():
            with DictSQLite(str(original_db_path)) as db:
                for i in range(count):
                    _ = db[f'key_{i}']
        
        def fastest():
            db = DictSQLiteFastest(str(fastest_db_path))
            try:
                for i in range(count):
                    _ = db[f'key_{i}']
            finally:
                db.close()
        
        def beta():
            db = DictSQLiteFastestBeta(str(beta_db_path), memory_budget_mb=100)
            try:
                for i in range(count):
                    _ = db[f'key_{i}']
            finally:
                db.close()
        
        self.benchmark.compare_sync_versions(
            test_name, original, fastest, beta, count
        )
    
    # -----------------------------------------------------------------
    # バルク操作テスト
    # -----------------------------------------------------------------
    
    def test_bulk_insert(self, count: int = 5000):
        """バルク挿入操作"""
        test_name = f"バルク挿入 ({count}件)"
        
        data = {f'key_{i}': f'value_{i}' * 10 for i in range(count)}
        
        def original():
            db_path = self.temp_dir / f"original_bulk_insert_{count}.db"
            if db_path.exists():
                db_path.unlink()
            with DictSQLite(str(db_path)) as db:
                # オリジナル版は1件ずつ挿入
                for key, value in data.items():
                    db[key] = value
        
        def fastest():
            db_path = self.temp_dir / f"fastest_bulk_insert_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastest(str(db_path))
            try:
                db.bulk_insert(data)
            finally:
                db.close()
        
        def beta():
            db_path = self.temp_dir / f"beta_bulk_insert_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            try:
                db.bulk_insert(data)
            finally:
                db.close()
        
        self.benchmark.compare_sync_versions(
            test_name, original, fastest, beta, count
        )
    
    def test_bulk_read(self, count: int = 5000):
        """バルク読み込み操作"""
        test_name = f"バルク読み込み ({count}件)"
        
        # データ準備
        data = {f'key_{i}': f'value_{i}' * 10 for i in range(count)}
        keys = list(data.keys())
        
        original_db_path = self.temp_dir / f"original_bulk_read_{count}.db"
        fastest_db_path = self.temp_dir / f"fastest_bulk_read_{count}.db"
        beta_db_path = self.temp_dir / f"beta_bulk_read_{count}.db"
        
        with DictSQLite(str(original_db_path)) as db:
            for key, value in data.items():
                db[key] = value
        
        db_fastest = DictSQLiteFastest(str(fastest_db_path))
        try:
            db_fastest.bulk_insert(data)
        finally:
            db_fastest.close()
        
        db_beta = DictSQLiteFastestBeta(str(beta_db_path), memory_budget_mb=100)
        try:
            db_beta.bulk_insert(data)
        finally:
            db_beta.close()
        
        def original():
            with DictSQLite(str(original_db_path)) as db:
                for key in keys:
                    _ = db[key]
        
        def fastest():
            db = DictSQLiteFastest(str(fastest_db_path))
            try:
                _ = db.bulk_get(keys)
            finally:
                db.close()
        
        def beta():
            db = DictSQLiteFastestBeta(str(beta_db_path), memory_budget_mb=100)
            try:
                _ = db.bulk_get(keys)
            finally:
                db.close()
        
        self.benchmark.compare_sync_versions(
            test_name, original, fastest, beta, count
        )
    
    # -----------------------------------------------------------------
    # 複雑なデータ構造テスト
    # -----------------------------------------------------------------
    
    def test_complex_data(self, count: int = 500):
        """複雑なデータ構造の処理"""
        test_name = f"複雑データ構造 ({count}件)"
        
        # 複雑なデータを生成
        complex_data = {}
        for i in range(count):
            complex_data[f'item_{i}'] = {
                'id': i,
                'name': f'アイテム_{i}',
                'metadata': {
                    'tags': ['tag1', 'tag2', f'tag_{i}'],
                    'scores': [1.0, 2.5, 3.7] * 10,
                    'nested': {
                        'level1': {
                            'level2': {
                                'data': [i] * 50
                            }
                        }
                    }
                },
                'history': [{'timestamp': j, 'value': j * i} for j in range(20)]
            }
        
        def original():
            db_path = self.temp_dir / f"original_complex_{count}.db"
            if db_path.exists():
                db_path.unlink()
            with DictSQLite(str(db_path)) as db:
                for key, value in complex_data.items():
                    db[key] = value
        
        def fastest():
            db_path = self.temp_dir / f"fastest_complex_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastest(str(db_path))
            try:
                db.bulk_insert(complex_data)
            finally:
                db.close()
        
        def beta():
            db_path = self.temp_dir / f"beta_complex_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            try:
                db.bulk_insert(complex_data)
            finally:
                db.close()
        
        self.benchmark.compare_sync_versions(
            test_name, original, fastest, beta, count
        )
    
    # -----------------------------------------------------------------
    # 更新・削除テスト
    # -----------------------------------------------------------------
    
    def test_update_operations(self, count: int = 1000):
        """更新操作"""
        test_name = f"更新操作 ({count}件)"
        
        # データ準備
        initial_data = {f'key_{i}': f'initial_{i}' for i in range(count)}
        update_data = {f'key_{i}': f'updated_{i}' for i in range(count)}
        
        def original():
            db_path = self.temp_dir / f"original_update_{count}.db"
            if db_path.exists():
                db_path.unlink()
            with DictSQLite(str(db_path)) as db:
                for key, value in initial_data.items():
                    db[key] = value
                for key, value in update_data.items():
                    db[key] = value
        
        def fastest():
            db_path = self.temp_dir / f"fastest_update_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastest(str(db_path))
            try:
                db.bulk_insert(initial_data)
                db.bulk_insert(update_data)
            finally:
                db.close()
        
        def beta():
            db_path = self.temp_dir / f"beta_update_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            try:
                db.bulk_insert(initial_data)
                db.bulk_insert(update_data)
            finally:
                db.close()
        
        self.benchmark.compare_sync_versions(
            test_name, original, fastest, beta, count
        )
    
    def test_delete_operations(self, count: int = 1000):
        """削除操作"""
        test_name = f"削除操作 ({count}件)"
        
        data = {f'key_{i}': f'value_{i}' for i in range(count)}
        
        def original():
            db_path = self.temp_dir / f"original_delete_{count}.db"
            if db_path.exists():
                db_path.unlink()
            with DictSQLite(str(db_path)) as db:
                for key, value in data.items():
                    db[key] = value
                for i in range(count):
                    del db[f'key_{i}']
        
        def fastest():
            db_path = self.temp_dir / f"fastest_delete_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastest(str(db_path))
            try:
                db.bulk_insert(data)
                for i in range(count):
                    del db[f'key_{i}']
            finally:
                db.close()
        
        def beta():
            db_path = self.temp_dir / f"beta_delete_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            try:
                db.bulk_insert(data)
                for i in range(count):
                    del db[f'key_{i}']
            finally:
                db.close()
        
        self.benchmark.compare_sync_versions(
            test_name, original, fastest, beta, count
        )
    
    # -----------------------------------------------------------------
    # 混合操作テスト
    # -----------------------------------------------------------------
    
    def test_mixed_operations(self, count: int = 1000):
        """読み書き混合操作"""
        test_name = f"混合操作 ({count}件)"
        
        def original():
            db_path = self.temp_dir / f"original_mixed_{count}.db"
            if db_path.exists():
                db_path.unlink()
            with DictSQLite(str(db_path)) as db:
                for i in range(count):
                    db[f'key_{i}'] = f'value_{i}'
                    if i % 2 == 0:
                        # オリジナル版用：get()メソッドがあれば使用、なければtry/except
                        if hasattr(db, 'get'):
                            _ = db.get(f'key_{i//2}', None)
                        else:
                            try:
                                _ = db[f'key_{i//2}']
                            except KeyError:
                                pass
                    if i % 3 == 0 and i > 0:
                        db[f'key_{i//3}'] = f'updated_{i}'
        
        def fastest():
            db_path = self.temp_dir / f"fastest_mixed_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastest(str(db_path))
            try:
                for i in range(count):
                    db[f'key_{i}'] = f'value_{i}'
                    if i % 2 == 0:
                        _ = db.get(f'key_{i//2}', None)
                    if i % 3 == 0 and i > 0:
                        db[f'key_{i//3}'] = f'updated_{i}'
            finally:
                db.close()
        
        def beta():
            db_path = self.temp_dir / f"beta_mixed_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            try:
                for i in range(count):
                    db[f'key_{i}'] = f'value_{i}'
                    if i % 2 == 0:
                        _ = db.get(f'key_{i//2}', None)
                    if i % 3 == 0 and i > 0:
                        db[f'key_{i//3}'] = f'updated_{i}'
            finally:
                db.close()
        
        self.benchmark.compare_sync_versions(
            test_name, original, fastest, beta, count
        )
    
    # -----------------------------------------------------------------
    # 非同期操作テスト
    # -----------------------------------------------------------------
    
    async def test_async_write(self, count: int = 1000):
        """非同期書き込み"""
        test_name = f"非同期書き込み ({count}件)"
        
        async def fastest():
            db_path = self.temp_dir / f"async_fastest_write_{count}.db"
            if db_path.exists():
                db_path.unlink()
            async with AsyncDictSQLiteFastest(str(db_path)) as db:
                for i in range(count):
                    await db.aset(f'key_{i}', f'value_{i}')
        
        async def beta():
            db_path = self.temp_dir / f"async_beta_write_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = AsyncDictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            for i in range(count):
                await db.aset(f'key_{i}', f'value_{i}')
            await db.aclose()
        
        await self.benchmark.compare_async_versions(
            test_name, fastest, beta, count
        )
    
    async def test_async_bulk_insert(self, count: int = 5000):
        """非同期バルク挿入"""
        test_name = f"非同期バルク挿入 ({count}件)"
        
        data = {f'key_{i}': f'value_{i}' * 10 for i in range(count)}
        
        async def fastest():
            db_path = self.temp_dir / f"async_fastest_bulk_{count}.db"
            if db_path.exists():
                db_path.unlink()
            async with AsyncDictSQLiteFastest(str(db_path)) as db:
                await db.abulk_insert(data)
        
        async def beta():
            db_path = self.temp_dir / f"async_beta_bulk_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = AsyncDictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            await db.abulk_insert(data)
            await db.aclose()
        
        await self.benchmark.compare_async_versions(
            test_name, fastest, beta, count
        )
    
    async def test_async_concurrent_operations(self, count: int = 100, concurrency: int = 10):
        """非同期並行操作"""
        test_name = f"非同期並行操作 ({count}件, 並行度{concurrency})"
        
        async def fastest():
            db_path = self.temp_dir / f"async_fastest_concurrent_{count}.db"
            if db_path.exists():
                db_path.unlink()
            async with AsyncDictSQLiteFastest(str(db_path)) as db:
                tasks = []
                for i in range(count):
                    tasks.append(db.aset(f'key_{i}', f'value_{i}'))
                    if len(tasks) >= concurrency:
                        await asyncio.gather(*tasks)
                        tasks = []
                if tasks:
                    await asyncio.gather(*tasks)
        
        async def beta():
            db_path = self.temp_dir / f"async_beta_concurrent_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = AsyncDictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            tasks = []
            for i in range(count):
                tasks.append(db.aset(f'key_{i}', f'value_{i}'))
                if len(tasks) >= concurrency:
                    await asyncio.gather(*tasks)
                    tasks = []
            if tasks:
                await asyncio.gather(*tasks)
            await db.aclose()
        
        await self.benchmark.compare_async_versions(
            test_name, fastest, beta, count
        )


# =====================================================================
# レポート生成
# =====================================================================

class ReportGenerator:
    """ベンチマーク結果レポート生成"""
    
    def __init__(self, benchmark: ComprehensiveBenchmark):
        self.benchmark = benchmark
    
    def generate_csv(self):
        """CSV形式でレポート生成"""
        with open(self.benchmark.csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # ヘッダー
            writer.writerow([
                'Test Name',
                'Operation Count',
                'Original Time (s)',
                'Original OPS',
                'Fastest Time (s)',
                'Fastest OPS',
                'Beta Time (s)',
                'Beta OPS',
                'Speedup (Fastest/Original)',
                'Speedup (Beta/Original)',
                'Speedup (Beta/Fastest)'
            ])
            
            # データ
            for result in self.benchmark.results:
                row = [result['test_name'], result['operation_count']]
                
                orig = result['results'].get('original')
                fastest = result['results'].get('fastest')
                beta = result['results'].get('beta')
                
                row.extend([
                    orig['time'] if orig else 'N/A',
                    orig['ops'] if orig else 'N/A',
                    fastest['time'] if fastest else 'N/A',
                    fastest['ops'] if fastest else 'N/A',
                    beta['time'] if beta else 'N/A',
                    beta['ops'] if beta else 'N/A',
                ])
                
                # スピードアップ計算
                if orig and fastest:
                    row.append(orig['time'] / fastest['time'])
                else:
                    row.append('N/A')
                
                if orig and beta:
                    row.append(orig['time'] / beta['time'])
                else:
                    row.append('N/A')
                
                if fastest and beta:
                    row.append(fastest['time'] / beta['time'])
                else:
                    row.append('N/A')
                
                writer.writerow(row)
        
        print(f"\n✓ CSV レポート生成完了: {self.benchmark.csv_file}")
    
    def generate_json(self):
        """JSON形式でレポート生成"""
        report = {
            'timestamp': self.benchmark.timestamp,
            'sync_tests': self.benchmark.results,
            'async_tests': self.benchmark.async_results
        }
        
        with open(self.benchmark.json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✓ JSON レポート生成完了: {self.benchmark.json_file}")
    
    def generate_markdown_summary(self):
        """Markdown形式でサマリー生成"""
        lines = []
        lines.append(f"# DictSQLite 包括的ベンチマーク結果")
        lines.append(f"\n**実行日時:** {self.benchmark.timestamp}")
        lines.append(f"\n## 概要\n")
        lines.append("3つのバージョンを徹底比較:")
        lines.append("- **DictSQLite (オリジナル版)**: sqlite3ベース")
        lines.append("- **DictSQLite-Fastest (APSW版)**: APSWベース、高速化")
        lines.append("- **DictSQLite-Fastest Beta版**: メモリ最適化、LRUキャッシュ\n")
        
        # 同期テスト結果
        lines.append("## 同期操作ベンチマーク\n")
        lines.append("| テスト名 | 操作数 | Original | Fastest | Beta | Fastest倍率 | Beta倍率 | 最速 |")
        lines.append("|---------|--------|----------|---------|------|------------|----------|------|")
        
        for result in self.benchmark.results:
            test_name = result['test_name']
            op_count = result['operation_count']
            orig = result['results'].get('original')
            fastest = result['results'].get('fastest')
            beta = result['results'].get('beta')
            
            orig_time = f"{orig['time']:.4f}s" if orig else "N/A"
            fastest_time = f"{fastest['time']:.4f}s" if fastest else "N/A"
            beta_time = f"{beta['time']:.4f}s" if beta else "N/A"
            
            # スピードアップ
            if orig and fastest:
                speedup_fastest = f"{orig['time']/fastest['time']:.2f}x"
            else:
                speedup_fastest = "N/A"
            
            if orig and beta:
                speedup_beta = f"{orig['time']/beta['time']:.2f}x"
            else:
                speedup_beta = "N/A"
            
            # 最速判定
            valid_times = {}
            if orig:
                valid_times['Original'] = orig['time']
            if fastest:
                valid_times['Fastest'] = fastest['time']
            if beta:
                valid_times['Beta'] = beta['time']
            
            if valid_times:
                winner = min(valid_times.items(), key=lambda x: x[1])[0]
            else:
                winner = "N/A"
            
            lines.append(f"| {test_name} | {op_count:,} | {orig_time} | {fastest_time} | {beta_time} | {speedup_fastest} | {speedup_beta} | **{winner}** |")
        
        # 非同期テスト結果
        if self.benchmark.async_results:
            lines.append("\n## 非同期操作ベンチマーク\n")
            lines.append("| テスト名 | 操作数 | Fastest | Beta | Beta倍率 | 最速 |")
            lines.append("|---------|--------|---------|------|----------|------|")
            
            for result in self.benchmark.async_results:
                test_name = result['test_name']
                op_count = result['operation_count']
                fastest = result['results'].get('fastest')
                beta = result['results'].get('beta')
                
                fastest_time = f"{fastest['time']:.4f}s" if fastest else "N/A"
                beta_time = f"{beta['time']:.4f}s" if beta else "N/A"
                
                if fastest and beta:
                    speedup = f"{fastest['time']/beta['time']:.2f}x"
                    winner = "Beta" if beta['time'] < fastest['time'] else "Fastest"
                else:
                    speedup = "N/A"
                    winner = "N/A"
                
                lines.append(f"| {test_name} | {op_count:,} | {fastest_time} | {beta_time} | {speedup} | **{winner}** |")
        
        # 総合評価
        lines.append("\n## 総合評価\n")
        
        # 同期テストの統計
        fastest_wins = 0
        beta_wins = 0
        original_wins = 0
        
        for result in self.benchmark.results:
            times = {}
            if result['results'].get('original'):
                times['original'] = result['results']['original']['time']
            if result['results'].get('fastest'):
                times['fastest'] = result['results']['fastest']['time']
            if result['results'].get('beta'):
                times['beta'] = result['results']['beta']['time']
            
            if times:
                winner = min(times.items(), key=lambda x: x[1])[0]
                if winner == 'fastest':
                    fastest_wins += 1
                elif winner == 'beta':
                    beta_wins += 1
                else:
                    original_wins += 1
        
        total_tests = len(self.benchmark.results)
        lines.append(f"### 同期操作での勝率")
        lines.append(f"- **Beta版**: {beta_wins}/{total_tests} ({beta_wins/total_tests*100:.1f}%)")
        lines.append(f"- **Fastest版**: {fastest_wins}/{total_tests} ({fastest_wins/total_tests*100:.1f}%)")
        lines.append(f"- **Original版**: {original_wins}/{total_tests} ({original_wins/total_tests*100:.1f}%)")
        
        # 推奨事項
        lines.append("\n## 推奨事項\n")
        if beta_wins > fastest_wins:
            lines.append("[推奨] **DictSQLite-Fastest Beta版**")
            lines.append("\nメモリ最適化とLRUキャッシュにより、ほとんどのシナリオで最高のパフォーマンスを発揮します。")
        else:
            lines.append("[推奨] **DictSQLite-Fastest (APSW版)**")
            lines.append("\nAPSWベースの実装により、安定した高パフォーマンスを提供します。")
        
        # ファイル出力
        with open(self.benchmark.summary_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        # BENCHMARK_SUMMARY.mdとしても保存（GitHub Actions用）
        benchmark_summary = self.benchmark.output_dir / "BENCHMARK_SUMMARY.md"
        with open(benchmark_summary, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"✓ Markdown サマリー生成完了: {self.benchmark.summary_file}")
        print(f"✓ BENCHMARK_SUMMARY.md 生成完了: {benchmark_summary}")
        
        # コンソールにも出力
        print("\n" + "="*80)
        print('\n'.join(lines))


# =====================================================================
# メイン実行
# =====================================================================

def main():
    """メイン実行関数"""
    print("="*80)
    print("DictSQLite 包括的ベンチマークツール")
    print("="*80)
    print("\n3つのバージョンを徹底比較:")
    print("  1. DictSQLite (オリジナル版)")
    print("  2. DictSQLite-Fastest (APSW版)")
    print("  3. DictSQLite-Fastest Beta版 (メモリ最適化)")
    print("\n同期・非同期操作、バルク処理、複雑データを網羅的にテストします。\n")
    
    # ベンチマーク初期化
    benchmark = ComprehensiveBenchmark()
    scenarios = BenchmarkScenarios(benchmark)
    
    try:
        # ===== 同期操作テスト =====
        print("\n" + "="*80)
        print("同期操作テスト開始")
        print("="*80)
        
        # 基本操作
        scenarios.test_basic_write(count=1000)
        scenarios.test_basic_write(count=5000)
        scenarios.test_basic_read(count=1000)
        scenarios.test_basic_read(count=5000)
        
        # バルク操作
        scenarios.test_bulk_insert(count=1000)
        scenarios.test_bulk_insert(count=5000)
        scenarios.test_bulk_insert(count=10000)
        scenarios.test_bulk_read(count=1000)
        scenarios.test_bulk_read(count=5000)
        scenarios.test_bulk_read(count=10000)
        
        # 複雑データ
        scenarios.test_complex_data(count=100)
        scenarios.test_complex_data(count=500)
        scenarios.test_complex_data(count=1000)
        
        # 更新・削除
        scenarios.test_update_operations(count=1000)
        scenarios.test_update_operations(count=5000)
        scenarios.test_delete_operations(count=1000)
        scenarios.test_delete_operations(count=5000)
        
        # 混合操作
        scenarios.test_mixed_operations(count=1000)
        scenarios.test_mixed_operations(count=5000)
        
        # ===== 非同期操作テスト =====
        print("\n" + "="*80)
        print("非同期操作テスト開始")
        print("="*80)
        
        async def run_async_tests():
            await scenarios.test_async_write(count=1000)
            await scenarios.test_async_write(count=5000)
            await scenarios.test_async_bulk_insert(count=1000)
            await scenarios.test_async_bulk_insert(count=5000)
            await scenarios.test_async_bulk_insert(count=10000)
            await scenarios.test_async_concurrent_operations(count=500, concurrency=10)
            await scenarios.test_async_concurrent_operations(count=1000, concurrency=20)
            await scenarios.test_async_concurrent_operations(count=2000, concurrency=50)
        
        asyncio.run(run_async_tests())
        
        # ===== レポート生成 =====
        print("\n" + "="*80)
        print("レポート生成中...")
        print("="*80)
        
        reporter = ReportGenerator(benchmark)
        reporter.generate_csv()
        reporter.generate_json()
        reporter.generate_markdown_summary()
        
        # ===== グラフ生成 =====
        print("\n" + "="*80)
        print("グラフ生成中...")
        print("="*80)
        
        try:
            from visualize_benchmark import BenchmarkGraphGenerator
            generator = BenchmarkGraphGenerator(str(benchmark.csv_file))
            generator.generate_all_graphs()
            print(f"✓ グラフ生成完了: {generator.output_dir}")
        except ImportError as e:
            print(f"⚠ グラフ生成をスキップ: {e}")
            print("  matplotlib, seaborn, plotlyをインストールしてください:")
            print("  pip install matplotlib seaborn plotly")
        except Exception as e:
            print(f"⚠ グラフ生成中にエラーが発生: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*80)
        print("ベンチマーク完了!")
        print("="*80)
        print(f"\n結果ディレクトリ: {benchmark.output_dir}")
        print(f"  - ログ: {benchmark.log_file.name}")
        print(f"  - CSV: {benchmark.csv_file.name}")
        print(f"  - JSON: {benchmark.json_file.name}")
        print(f"  - サマリー: {benchmark.summary_file.name}")
        
        # グラフディレクトリの情報も表示
        graph_dir = benchmark.output_dir / "graphs"
        if graph_dir.exists():
            graph_files = list(graph_dir.glob('*.png'))
            if graph_files:
                print(f"  - グラフ: {len(graph_files)}個 ({graph_dir.name}/)")
            else:
                print(f"  - グラフ: なし")
        
    except KeyboardInterrupt:
        print("\n\nベンチマーク中断されました。")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        traceback.print_exc()
    finally:
        # クリーンアップ
        scenarios.cleanup()
        print("\nクリーンアップ完了。")


if __name__ == '__main__':
    main()

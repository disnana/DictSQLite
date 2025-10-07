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
import gc  # ガベージコレクション
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Callable, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import traceback

# tqdmのインポート (利用可能な場合のみ)
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # tqdmがない場合のダミー実装
    class tqdm:
        def __init__(self, iterable=None, **kwargs):
            self.iterable = iterable
        def __iter__(self):
            return iter(self.iterable) if self.iterable else iter([])
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def update(self, n=1):
            pass
        def set_description(self, desc):
            pass

# モジュールパスの設定
BASE_DIR = Path(__file__).parent
REPO_ROOT = BASE_DIR.parent.parent  # /others/benchmark から / へ
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest'))
sys.path.insert(0, str(REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest' / 'beta'))

# インポート
from dictsqlite.main import DictSQLite
from dictsqlite_fastest.main import DictSQLiteFastest, AsyncDictSQLiteFastest
from dictsqlite_fastest_beta import DictSQLiteFastestBeta, AsyncDictSQLiteFastestBeta

# バージョン管理システムのインポート
try:
    from version_manager import VersionManager
    VERSION_MANAGER_AVAILABLE = True
except ImportError:
    VERSION_MANAGER_AVAILABLE = False
    print("⚠ version_manager.pyが見つかりません。バージョン管理機能は無効化されます。")


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
    
    def __init__(self, output_dir: str = None, use_version_manager: bool = True):
        """
        Args:
            output_dir: 結果を保存するディレクトリ（デフォルト: /others/benchmark/results）
            use_version_manager: バージョン管理システムを使用するか
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
        
        # Beta版のバージョンを環境変数から取得
        beta_version = os.getenv('BETA_VERSION', None)
        
        # バージョン管理システム
        self.use_version_manager = use_version_manager and VERSION_MANAGER_AVAILABLE
        if self.use_version_manager:
            self.version_manager = VersionManager(self.output_dir, beta_version=beta_version)
            self.version_string = self.version_manager.get_version_string()
            print(f"✓ バージョン管理システム有効: {self.version_string}")
        else:
            self.version_manager = None
            self.version_string = None
        
        # ログファイル（タイムスタンプ付き - 一時ファイル）
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
        
        # tqdmは5回以上の測定でのみ使用（オーバーヘッド最小化）
        iterator = range(iterations)
        use_tqdm = TQDM_AVAILABLE and iterations >= 5
        if use_tqdm:
            iterator = tqdm(iterator, desc=f"  測定中", leave=False, ncols=80, disable=False)
        
        for i in iterator:
            try:
                start = time.perf_counter()
                result = func()
                duration = time.perf_counter() - start
                times.append(duration)
                
                # 経過時間を表示（tqdm使用時のみ）
                if use_tqdm and hasattr(iterator, 'set_description'):
                    iterator.set_description(f"  測定中 ({format_time(duration)})")
                    
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
        warmup: int = 1,
        timeout: float = 120.0  # デフォルト120秒のタイムアウト
    ) -> Dict[str, Any]:
        """非同期操作のベンチマーク測定
        
        Args:
            name: 操作名
            func: 測定する非同期関数
            iterations: 測定回数
            warmup: ウォームアップ回数
            timeout: 各イテレーションのタイムアウト（秒）
            
        Returns:
            測定結果の辞書
        """
        # ウォームアップ
        for _ in range(warmup):
            try:
                await asyncio.wait_for(func(), timeout=timeout)
            except (Exception, asyncio.TimeoutError):
                pass
        
        # 測定
        times = []
        errors = []
        
        # tqdmは5回以上の測定でのみ使用（オーバーヘッド最小化）
        iterator = range(iterations)
        use_tqdm = TQDM_AVAILABLE and iterations >= 5
        if use_tqdm:
            iterator = tqdm(iterator, desc=f"  測定中", leave=False, ncols=80, disable=False)
        
        for i in iterator:
            try:
                start = time.perf_counter()
                await asyncio.wait_for(func(), timeout=timeout)
                duration = time.perf_counter() - start
                times.append(duration)
                
                # 経過時間を表示（tqdm使用時のみ）
                if use_tqdm and hasattr(iterator, 'set_description'):
                    iterator.set_description(f"  測定中 ({format_time(duration)})")
                    
            except asyncio.TimeoutError:
                errors.append(f'Timeout after {timeout}s')
                self.log(f"  タイムアウト (試行 {i+1}): {timeout}秒経過", print_console=False)
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
        test_start_time = time.perf_counter()
        
        # オリジナル版
        self.log("\n[DictSQLite オリジナル版]")
        version_start = time.perf_counter()
        original_result = self.measure_sync_operation(
            f"{test_name} (Original)",
            original_func,
            iterations
        )
        version_elapsed = time.perf_counter() - version_start
        
        if original_result['success']:
            orig_time = original_result['stats']['mean']
            orig_ops = operation_count / orig_time
            self.log(f"  平均時間: {format_time(orig_time)} (実測: {format_time(version_elapsed)})")
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
        version_start = time.perf_counter()
        fastest_result = self.measure_sync_operation(
            f"{test_name} (Fastest)",
            fastest_func,
            iterations
        )
        version_elapsed = time.perf_counter() - version_start
        
        if fastest_result['success']:
            fastest_time = fastest_result['stats']['mean']
            fastest_ops = operation_count / fastest_time
            self.log(f"  平均時間: {format_time(fastest_time)} (実測: {format_time(version_elapsed)})")
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
        version_start = time.perf_counter()
        beta_result = self.measure_sync_operation(
            f"{test_name} (Beta)",
            beta_func,
            iterations
        )
        version_elapsed = time.perf_counter() - version_start
        
        if beta_result['success']:
            beta_time = beta_result['stats']['mean']
            beta_ops = operation_count / beta_time
            self.log(f"  平均時間: {format_time(beta_time)} (実測: {format_time(version_elapsed)})")
            self.log(f"  スループット: {format_ops(beta_ops)}")
            results['beta'] = {
                'time': beta_time,
                'ops': beta_ops,
                'stats': beta_result['stats']
            }
        else:
            self.log(f"  失敗: {beta_result.get('error', 'Unknown')}")
            results['beta'] = None
        
        # テスト全体の経過時間を表示
        total_elapsed = time.perf_counter() - test_start_time
        self.log(f"\n[テスト全体の実測時間: {format_time(total_elapsed)}]")
        
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
        
        # メモリ解放
        gc.collect()
    
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
        test_start_time = time.perf_counter()
        
        # Fastest版
        self.log("\n[AsyncDictSQLiteFastest]")
        version_start = time.perf_counter()
        fastest_result = await self.measure_async_operation(
            f"{test_name} (Async Fastest)",
            fastest_func,
            iterations
        )
        version_elapsed = time.perf_counter() - version_start
        
        if fastest_result['success']:
            fastest_time = fastest_result['stats']['mean']
            fastest_ops = operation_count / fastest_time
            self.log(f"  平均時間: {format_time(fastest_time)} (実測: {format_time(version_elapsed)})")
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
        version_start = time.perf_counter()
        beta_result = await self.measure_async_operation(
            f"{test_name} (Async Beta)",
            beta_func,
            iterations
        )
        version_elapsed = time.perf_counter() - version_start
        
        if beta_result['success']:
            beta_time = beta_result['stats']['mean']
            beta_ops = operation_count / beta_time
            self.log(f"  平均時間: {format_time(beta_time)} (実測: {format_time(version_elapsed)})")
            self.log(f"  スループット: {format_ops(beta_ops)}")
            results['beta'] = {
                'time': beta_time,
                'ops': beta_ops,
                'stats': beta_result['stats']
            }
        else:
            self.log(f"  失敗: {beta_result.get('error', 'Unknown')}")
            results['beta'] = None
        
        # テスト全体の経過時間を表示
        total_elapsed = time.perf_counter() - test_start_time
        self.log(f"\n[テスト全体の実測時間: {format_time(total_elapsed)}]")
        
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
        
        # メモリ解放
        gc.collect()
    
    def save_to_version_manager(self):
        """バージョン管理システムを使用して結果を保存"""
        if not self.use_version_manager or not self.version_manager:
            print("⚠ バージョン管理システムが有効化されていません")
            return
        
        print("\n" + "=" * 80)
        print("バージョン管理システムを使用して結果を保存中...")
        print("=" * 80)
        
        # CSV内容を読み込み
        csv_content = None
        if self.csv_file.exists():
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                csv_content = f.read()
        
        # JSON内容を読み込み
        json_content = None
        if self.json_file.exists():
            with open(self.json_file, 'r', encoding='utf-8') as f:
                json_content = json.load(f)
        
        # サマリー内容を読み込み
        summary_content = None
        if self.summary_file.exists():
            with open(self.summary_file, 'r', encoding='utf-8') as f:
                summary_content = f.read()
        
        # ログ内容を読み込み
        log_content = None
        if self.log_file.exists():
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
        
        # バージョン管理システムに保存
        saved_files = self.version_manager.save_benchmark_result(
            csv_content=csv_content,
            json_content=json_content,
            summary_content=summary_content,
            log_content=log_content,
            version_string=self.version_string
        )
        
        # グラフディレクトリが存在する場合はコピー
        graphs_dir = self.output_dir / "graphs"
        if graphs_dir.exists():
            self.version_manager.copy_graphs_to_version(
                graphs_dir,
                version_string=self.version_string
            )
        
        print(f"\n✓ バージョン {self.version_string} の結果を保存しました")
        print(f"  保存先: {self.version_manager.version_results_dir / self.version_string}")
        
        return saved_files


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
            db = DictSQLiteFastest(str(db_path))
            try:
                for i in range(count):
                    db[f'key_{i}'] = f'value_{i}'
            finally:
                db.close()
                del db  # 明示的に削除
        
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
                del db  # 明示的に削除
        
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
        
        # データ作成 - 必ず閉じる
        with DictSQLite(str(original_db_path)) as db:
            for i in range(count):
                db[f'key_{i}'] = f'value_{i}'
        # with文を抜けた時点でDBは閉じられている
        
        db_fastest = DictSQLiteFastest(str(fastest_db_path))
        try:
            for i in range(count):
                db_fastest[f'key_{i}'] = f'value_{i}'
        finally:
            db_fastest.close()
        # 閉じた後、明示的にNoneに設定
        db_fastest = None
        
        db_beta = DictSQLiteFastestBeta(str(beta_db_path), memory_budget_mb=100)
        try:
            for i in range(count):
                db_beta[f'key_{i}'] = f'value_{i}'
        finally:
            db_beta.close()
        # 閉じた後、明示的にNoneに設定
        db_beta = None
        
        # ガベージコレクション実行でファイルハンドルを確実に開放
        gc.collect()
        
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
                del db
        
        def beta():
            db = DictSQLiteFastestBeta(str(beta_db_path), memory_budget_mb=100)
            try:
                for i in range(count):
                    _ = db[f'key_{i}']
            finally:
                db.close()
                del db
        
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
                del db
        
        def beta():
            db_path = self.temp_dir / f"beta_bulk_insert_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            try:
                db.bulk_insert(data)
            finally:
                db.close()
                del db
        
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
        
        # データ作成 - 必ず閉じる
        with DictSQLite(str(original_db_path)) as db:
            for key, value in data.items():
                db[key] = value
        # with文を抜けた時点でDBは閉じられている
        
        db_fastest = DictSQLiteFastest(str(fastest_db_path))
        try:
            db_fastest.bulk_insert(data)
        finally:
            db_fastest.close()
        db_fastest = None
        
        db_beta = DictSQLiteFastestBeta(str(beta_db_path), memory_budget_mb=100)
        try:
            db_beta.bulk_insert(data)
        finally:
            db_beta.close()
        db_beta = None
        
        # ガベージコレクション実行でファイルハンドルを確実に開放
        gc.collect()
        
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
                del db
        
        def beta():
            db = DictSQLiteFastestBeta(str(beta_db_path), memory_budget_mb=100)
            try:
                _ = db.bulk_get(keys)
            finally:
                db.close()
                del db
        
        self.benchmark.compare_sync_versions(
            test_name, original, fastest, beta, count
        )
    
    # -----------------------------------------------------------------
    # 複雑なデータ構造テスト
    # -----------------------------------------------------------------
    
    def test_complex_data(self, count: int = 500):
        """複雑なデータ構造の処理"""
        test_name = f"複雑データ構造 ({count}件)"
        
        # プログレス表示
        print(f"\n[準備] {test_name} - 複雑データ生成中...")
        
        # 複雑なデータを生成（最適化版）
        complex_data = {}
        # データサイズを若干縮小して処理時間を短縮
        for i in range(count):
            complex_data[f'item_{i}'] = {
                'id': i,
                'name': f'アイテム_{i}',
                'metadata': {
                    'tags': ['tag1', 'tag2', f'tag_{i}'],
                    'scores': [1.0, 2.5, 3.7] * 5,  # 10 → 5 に縮小
                    'nested': {
                        'level1': {
                            'level2': {
                                'data': [i] * 25  # 50 → 25 に縮小
                            }
                        }
                    }
                },
                'history': [{'timestamp': j, 'value': j * i} for j in range(10)]  # 20 → 10 に縮小
            }
        
        print(f"[準備完了] データ生成完了 ({len(complex_data)}件)")
        
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

                del db
        
        def beta():
            db_path = self.temp_dir / f"beta_complex_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            try:
                db.bulk_insert(complex_data)
            finally:
                db.close()

                del db
        
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

                del db
        
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

                del db
        
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

                del db
        
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

                del db
        
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
                        # get()メソッドがない場合はKeyErrorをキャッチ
                        try:
                            _ = db[f'key_{i//2}']
                        except KeyError:
                            pass
                    if i % 3 == 0 and i > 0:
                        db[f'key_{i//3}'] = f'updated_{i}'
            finally:
                db.close()

                del db
        
        def beta():
            db_path = self.temp_dir / f"beta_mixed_{count}.db"
            if db_path.exists():
                db_path.unlink()
            db = DictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            try:
                for i in range(count):
                    db[f'key_{i}'] = f'value_{i}'
                    if i % 2 == 0:
                        # get()メソッドがない場合はKeyErrorをキャッチ
                        try:
                            _ = db[f'key_{i//2}']
                        except KeyError:
                            pass
                    if i % 3 == 0 and i > 0:
                        db[f'key_{i//3}'] = f'updated_{i}'
            finally:
                db.close()

                del db
        
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
            try:
                for i in range(count):
                    await db.aset(f'key_{i}', f'value_{i}')
            finally:
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
            try:
                await db.abulk_insert(data)
            finally:
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
            try:
                tasks = []
                for i in range(count):
                    tasks.append(db.aset(f'key_{i}', f'value_{i}'))
                    if len(tasks) >= concurrency:
                        await asyncio.gather(*tasks)
                        tasks = []
                if tasks:
                    await asyncio.gather(*tasks)
            finally:
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
    print("\n同期・非同期操作、バルク処理、複雑データを網羅的にテストします。")
    
    # tqdmの利用可否を表示
    if TQDM_AVAILABLE:
        print("✓ tqdmを使用してプログレスバーを表示します\n")
    else:
        print("⚠ tqdm未インストール（プログレスバーなし）\n")
    
    # ベンチマーク初期化
    benchmark = ComprehensiveBenchmark()
    scenarios = BenchmarkScenarios(benchmark)
    
    # 全体の開始時間を記録
    overall_start = time.perf_counter()
    
    try:
        # ===== 同期操作テスト =====
        print("\n" + "="*80)
        print("同期操作テスト開始")
        print("="*80)
        sync_start = time.perf_counter()
        
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
        
        sync_elapsed = time.perf_counter() - sync_start
        print(f"\n✓ 同期操作テスト完了 (所要時間: {format_time(sync_elapsed)})")
        
        # ===== 非同期操作テスト =====
        print("\n" + "="*80)
        print("非同期操作テスト開始")
        print("="*80)
        async_start = time.perf_counter()
        
        async def run_async_tests():
            """非同期テストを順次実行"""
            try:
                await scenarios.test_async_write(count=1000)
                await scenarios.test_async_write(count=5000)
                await scenarios.test_async_bulk_insert(count=1000)
                await scenarios.test_async_bulk_insert(count=5000)
                await scenarios.test_async_bulk_insert(count=10000)
                await scenarios.test_async_concurrent_operations(count=500, concurrency=10)
                await scenarios.test_async_concurrent_operations(count=1000, concurrency=20)
                await scenarios.test_async_concurrent_operations(count=2000, concurrency=50)
            except Exception as e:
                print(f"\n⚠ 非同期テスト中にエラーが発生: {e}")
                traceback.print_exc()
                raise
        
        try:
            asyncio.run(run_async_tests())
        except KeyboardInterrupt:
            print("\n非同期テストが中断されました")
            raise
        except Exception as e:
            print(f"\n⚠ 非同期テスト実行中にエラー: {e}")
            # 続行可能な場合は続ける
        finally:
            # asyncioのイベントループをクリーンアップ
            # 残っているタスクをキャンセル
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.stop()
            except RuntimeError:
                # イベントループが既に閉じている場合は無視
                pass
            
            # ガベージコレクション実行
            gc.collect()
        
        async_elapsed = time.perf_counter() - async_start
        print(f"\n✓ 非同期操作テスト完了 (所要時間: {format_time(async_elapsed)})")
        
        # ===== レポート生成 =====
        print("\n" + "="*80)
        print("レポート生成中...")
        print("="*80)
        report_start = time.perf_counter()
        
        reporter = ReportGenerator(benchmark)
        reporter.generate_csv()
        reporter.generate_json()
        reporter.generate_markdown_summary()
        
        report_elapsed = time.perf_counter() - report_start
        print(f"\n✓ レポート生成完了 (所要時間: {format_time(report_elapsed)})")
        
        # ===== 古いファイルのクリーンアップ =====
        # ===== 古いファイルのクリーンアップ =====
        print("\n" + "="*80)
        print("古いファイルのクリーンアップ中...")
        print("="*80)
        
        # 古いログファイルを削除（最新5個を保持）
        log_files = sorted(benchmark.output_dir.glob('benchmark_*.log'), 
                          key=lambda f: f.stat().st_mtime, reverse=True)
        csv_files = sorted(benchmark.output_dir.glob('benchmark_*.csv'), 
                          key=lambda f: f.stat().st_mtime, reverse=True)
        json_files = sorted(benchmark.output_dir.glob('benchmark_*.json'), 
                           key=lambda f: f.stat().st_mtime, reverse=True)
        summary_files = sorted(benchmark.output_dir.glob('summary_*.md'), 
                              key=lambda f: f.stat().st_mtime, reverse=True)
        
        old_logs_count = 0
        old_logs_size_kb = 0
        
        # 最新5個以外を削除
        for old_file in log_files[5:] + csv_files[5:] + json_files[5:] + summary_files[5:]:
            try:
                old_logs_size_kb += old_file.stat().st_size / 1024
                old_file.unlink()
                old_logs_count += 1
            except Exception:
                pass
        
        if old_logs_count > 0:
            print(f"✓ 古いログ/CSV/JSON削除: {old_logs_count}個 ({old_logs_size_kb:.1f} KB)")
        else:
            print("✓ クリーンアップ不要（古いファイルなし）")
        
        # ===== グラフ生成 =====
        # GitHub Actionsではデフォルトでスキップ（CI環境判定）
        is_ci = os.getenv('CI', 'false').lower() == 'true' or os.getenv('GITHUB_ACTIONS', 'false').lower() == 'true'
        skip_graphs_env = os.getenv('SKIP_BENCHMARK_GRAPHS', '').lower()
        
        # CI環境ではデフォルトでスキップ、環境変数で明示的に有効化可能
        if skip_graphs_env == 'true' or (is_ci and skip_graphs_env != 'false'):
            print("\n" + "="*80)
            if is_ci:
                print("グラフ生成をスキップ (GitHub Actions環境を検出)")
            else:
                print("グラフ生成をスキップ (SKIP_BENCHMARK_GRAPHS=true)")
            print("="*80)
            print("⚠ グラフ生成は環境変数により無効化されています")
            print("  有効化するには: export SKIP_BENCHMARK_GRAPHS=false")
            graph_generation_success = False
            graph_elapsed = 0
        else:
            print("\n" + "="*80)
            print("グラフ生成中...")
            print("="*80)
            graph_start = time.perf_counter()
            
            graph_generation_success = False
            try:
                print(f"CSVファイル: {benchmark.csv_file}")
                print(f"CSVファイル存在確認: {benchmark.csv_file.exists()}")
                if benchmark.csv_file.exists():
                    print(f"CSVファイルサイズ: {benchmark.csv_file.stat().st_size} bytes")
                
                from visualize_benchmark import BenchmarkGraphGenerator
                print("✓ BenchmarkGraphGeneratorインポート成功")
                
                generator = BenchmarkGraphGenerator(str(benchmark.csv_file))
                print(f"✓ ジェネレーター初期化完了")
                print(f"  出力ディレクトリ: {generator.output_dir}")
                
                generator.generate_all_graphs()
                
                graph_elapsed = time.perf_counter() - graph_start
                print(f"✓ グラフ生成完了: {generator.output_dir} (所要時間: {format_time(graph_elapsed)})")
                graph_generation_success = True
                
            except ImportError as e:
                print(f"⚠ グラフ生成をスキップ (ImportError): {e}")
                print("  必要なパッケージをインストールしてください:")
                print("  pip install matplotlib seaborn pandas numpy")
            except FileNotFoundError as e:
                print(f"⚠ グラフ生成をスキップ (FileNotFoundError): {e}")
                print(f"  CSVファイルが見つかりません: {benchmark.csv_file}")
            except Exception as e:
                print(f"⚠ グラフ生成中にエラーが発生: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
        
        # ===== バージョン管理システムへの保存 =====
        if benchmark.use_version_manager:
            try:
                benchmark.save_to_version_manager()
            except Exception as e:
                print(f"⚠ バージョン管理システムへの保存中にエラーが発生: {e}")
                import traceback
                traceback.print_exc()
        
        # ===== 結果表示 =====
        print("\n" + "="*80)
        print("ベンチマーク完了!")
        print("="*80)
        print(f"\n結果ディレクトリ: {benchmark.output_dir}")
        print(f"  - ログ: {benchmark.log_file.name}")
        print(f"  - CSV: {benchmark.csv_file.name}")
        print(f"  - JSON: {benchmark.json_file.name}")
        print(f"  - サマリー: {benchmark.summary_file.name}")
        
        # バージョン管理情報を表示
        if benchmark.use_version_manager:
            print(f"\nバージョン管理システム:")
            print(f"  - バージョン: {benchmark.version_string}")
            version_dir = benchmark.version_manager.version_results_dir / benchmark.version_string
            print(f"  - 保存先: {version_dir.relative_to(benchmark.output_dir.parent)}/")
        
        # グラフディレクトリの情報を簡潔に表示
        graph_dir = benchmark.output_dir / "graphs"
        if graph_generation_success and graph_dir.exists():
            graph_files = list(graph_dir.glob('*.png'))
            if graph_files:
                total_size_kb = sum(gf.stat().st_size for gf in graph_files) / 1024
                print(f"  - グラフ: {len(graph_files)}個生成 ({graph_dir.name}/) - 合計 {total_size_kb:.1f} KB")
            else:
                print(f"  - グラフ: ディレクトリは存在するがファイルなし")
        elif graph_generation_success:
            print(f"  - グラフ: ディレクトリが作成されませんでした")
        else:
            print(f"  - グラフ: 生成スキップ")
        
        # 全体の所要時間を表示
        overall_elapsed = time.perf_counter() - overall_start
        print(f"\n{'='*80}")
        print(f"全ベンチマーク完了! 総所要時間: {format_time(overall_elapsed)}")
        print(f"  - 同期テスト: {format_time(sync_elapsed)}")
        print(f"  - 非同期テスト: {format_time(async_elapsed)}")
        print(f"  - レポート生成: {format_time(report_elapsed)}")
        if graph_generation_success:
            print(f"  - グラフ生成: {format_time(graph_elapsed)}")
        print(f"{'='*80}")
        
    except KeyboardInterrupt:
        print("\n\nベンチマーク中断されました。")
        sys.exit(1)
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        # クリーンアップ
        scenarios.cleanup()
        print("\nクリーンアップ完了。")
        
        # 明示的にガベージコレクション実行
        gc.collect()
        
        # 正常終了
        sys.exit(0)


if __name__ == '__main__':
    main()

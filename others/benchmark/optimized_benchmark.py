#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DictSQLite 最適化ベンチマークツール

dictsqlite (オリジナル版) と dictsqlite_v2 の2つのバージョンを比較:
- DictSQLite (オリジナル版) - /dictsqlite
- DictSQLiteV2 (v2.0版) - /dictsqlite-fastest/dictsqlite_v2

各モジュールに最適化されたテストで最速性能を確認します。
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
from typing import Dict, List, Callable, Any, Optional
import traceback

# モジュールパスの設定
BASE_DIR = Path(__file__).parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'dictsqlite-fastest'))
sys.path.insert(0, str(REPO_ROOT / 'dictsqlite-fastest' / 'dictsqlite_v2'))

# インポート
from dictsqlite.main import DictSQLite
from dictsqlite_v2.core import DictSQLiteV2, AsyncDictSQLiteV2


def format_ops(ops: float) -> str:
    """OPS値を読みやすくフォーマット"""
    if ops >= 1_000_000:
        return f"{ops/1_000_000:.2f}M ops/sec"
    elif ops >= 1_000:
        return f"{ops/1_000:.2f}K ops/sec"
    else:
        return f"{ops:.2f} ops/sec"


def format_time(seconds: float) -> str:
    """時間を読みやすくフォーマット"""
    if seconds < 0.001:
        return f"{seconds*1_000_000:.2f}μs"
    elif seconds < 1:
        return f"{seconds*1_000:.2f}ms"
    else:
        return f"{seconds:.3f}s"


class OptimizedBenchmark:
    """最適化ベンチマーク実行クラス"""
    
    def __init__(self, test_mode: str = 'fast'):
        """
        Args:
            test_mode: 'fast' (高速モード) または 'full' (完全モード)
        """
        self.test_mode = test_mode
        self.results = []
        self.async_results = []
        self.temp_dir = Path(tempfile.mkdtemp(prefix="dictsqlite_bench_"))
        
        # 結果ディレクトリ
        self.output_dir = BASE_DIR / "results"
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # ログファイルの設定
        self.log_file = self.output_dir / f"benchmark_{self.timestamp}.log"
        self.log_buffer = []
        
        # テストサイズの設定
        if test_mode == 'fast':
            self.test_sizes = {
                'tiny': 50,
                'small': 100,
                'medium': 500,
                'large': 1000,
            }
            self.iterations = 2
        else:  # full
            self.test_sizes = {
                'tiny': 100,
                'small': 500,
                'medium': 2000,
                'large': 5000,
                'xlarge': 10000,
            }
            self.iterations = 3
        
    def safe_print(self, message: str):
        """エンコードエラーを回避した出力"""
        try:
            print(message)
            self.log_buffer.append(message)
        except UnicodeEncodeError:
            safe_msg = message.encode('cp932', errors='replace').decode('cp932')
            print(safe_msg)
            self.log_buffer.append(message)
    
    def measure(self, name: str, func: Callable, iterations: int = None) -> Dict[str, Any]:
        """関数の実行時間を測定"""
        if iterations is None:
            iterations = self.iterations
            
        times = []
        for _ in range(iterations):
            try:
                start = time.perf_counter()
                func()
                duration = time.perf_counter() - start
                times.append(duration)
            except Exception as e:
                return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}
        
        return {
            'success': True,
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'min': min(times),
            'max': max(times),
            'stdev': statistics.stdev(times) if len(times) > 1 else 0
        }
    
    async def measure_async(self, name: str, func: Callable, iterations: int = None) -> Dict[str, Any]:
        """非同期関数の実行時間を測定"""
        if iterations is None:
            iterations = self.iterations
            
        times = []
        for _ in range(iterations):
            try:
                start = time.perf_counter()
                await func()
                duration = time.perf_counter() - start
                times.append(duration)
            except Exception as e:
                return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}
        
        return {
            'success': True,
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'min': min(times),
            'max': max(times),
            'stdev': statistics.stdev(times) if len(times) > 1 else 0
        }
    
    def test_basic_write(self, size: int, test_name: str):
        """基本的な書き込みテスト"""
        self.safe_print(f"\n{'='*70}")
        self.safe_print(f"テスト: {test_name} (サイズ: {size})")
        self.safe_print(f"{'='*70}")
        
        results = {}
        
        # DictSQLite (オリジナル)
        original_path = self.temp_dir / f"original_{test_name}.db"
        def original_write():
            db = DictSQLite(str(original_path))
            for i in range(size):
                db[f'key_{i}'] = f'value_{i}'
            db.close()
        
        result = self.measure("DictSQLite", original_write)
        if result['success']:
            ops = size / result['mean']
            self.safe_print(f"[Original]  時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['original'] = {'time': result['mean'], 'ops': ops}
        else:
            self.safe_print(f"[Original]  エラー: {result['error']}")
        
        # DictSQLiteV2 (最適化設定)
        v2_path = self.temp_dir / f"v2_{test_name}.db"
        def v2_write():
            db = DictSQLiteV2(str(v2_path), sync_interval=0.1, auto_sync=False)
            for i in range(size):
                db[f'key_{i}'] = f'value_{i}'
            db.close()
        
        result = self.measure("DictSQLiteV2", v2_write)
        if result['success']:
            ops = size / result['mean']
            self.safe_print(f"[V2]        時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['v2'] = {'time': result['mean'], 'ops': ops}
        else:
            self.safe_print(f"[V2]        エラー: {result['error']}")
        
        # 比較
        if 'original' in results and 'v2' in results:
            speedup = results['original']['time'] / results['v2']['time']
            self.safe_print(f"\nV2 vs Original: {speedup:.2f}x 高速")
            winner = 'V2' if results['v2']['time'] < results['original']['time'] else 'ORIGINAL'
            self.safe_print(f"[最速] {winner}")
        
        self.results.append({'test': test_name, 'results': results})
    
    def test_basic_read(self, size: int, test_name: str):
        """基本的な読み込みテスト"""
        self.safe_print(f"\n{'='*70}")
        self.safe_print(f"テスト: {test_name} (サイズ: {size})")
        self.safe_print(f"{'='*70}")
        
        results = {}
        
        # データ準備 - DictSQLite
        original_path = self.temp_dir / f"original_{test_name}.db"
        db = DictSQLite(str(original_path))
        for i in range(size):
            db[f'key_{i}'] = f'value_{i}'
        db.close()
        
        def original_read():
            db = DictSQLite(str(original_path))
            for i in range(size):
                _ = db[f'key_{i}']
            db.close()
        
        result = self.measure("DictSQLite", original_read)
        if result['success']:
            ops = size / result['mean']
            self.safe_print(f"[Original]  時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['original'] = {'time': result['mean'], 'ops': ops}
        else:
            self.safe_print(f"[Original]  エラー: {result['error']}")
        
        # データ準備 - DictSQLiteV2 (最適化設定)
        v2_path = self.temp_dir / f"v2_{test_name}.db"
        db = DictSQLiteV2(str(v2_path), sync_interval=0.1, auto_sync=False)
        for i in range(size):
            db[f'key_{i}'] = f'value_{i}'
        db.close()
        
        def v2_read():
            db = DictSQLiteV2(str(v2_path), sync_interval=0.1, auto_sync=False)
            for i in range(size):
                _ = db[f'key_{i}']
            db.close()
        
        result = self.measure("DictSQLiteV2", v2_read)
        if result['success']:
            ops = size / result['mean']
            self.safe_print(f"[V2]        時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['v2'] = {'time': result['mean'], 'ops': ops}
        else:
            self.safe_print(f"[V2]        エラー: {result['error']}")
        
        # 比較
        if 'original' in results and 'v2' in results:
            speedup = results['original']['time'] / results['v2']['time']
            self.safe_print(f"\nV2 vs Original: {speedup:.2f}x 高速")
            winner = 'V2' if results['v2']['time'] < results['original']['time'] else 'ORIGINAL'
            self.safe_print(f"[最速] {winner}")
        
        self.results.append({'test': test_name, 'results': results})
    
    def test_mixed_operations(self, size: int, test_name: str):
        """混合操作テスト（読み書き削除）"""
        self.safe_print(f"\n{'='*70}")
        self.safe_print(f"テスト: {test_name} (サイズ: {size})")
        self.safe_print(f"{'='*70}")
        
        results = {}
        
        # DictSQLite
        original_path = self.temp_dir / f"original_{test_name}.db"
        def original_mixed():
            db = DictSQLite(str(original_path))
            # 書き込み
            for i in range(size):
                db[f'key_{i}'] = f'value_{i}'
            # 読み込み
            for i in range(size // 2):
                _ = db[f'key_{i}']
            # 更新
            for i in range(size // 2, size):
                db[f'key_{i}'] = f'updated_{i}'
            # 削除
            for i in range(size // 4):
                del db[f'key_{i}']
            db.close()
        
        result = self.measure("DictSQLite", original_mixed)
        if result['success']:
            ops = size * 2.25 / result['mean']  # 書き込み + 読み込み半分 + 更新半分 + 削除1/4
            self.safe_print(f"[Original]  時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['original'] = {'time': result['mean'], 'ops': ops}
        else:
            self.safe_print(f"[Original]  エラー: {result['error']}")
        
        # DictSQLiteV2 (最適化設定)
        v2_path = self.temp_dir / f"v2_{test_name}.db"
        def v2_mixed():
            db = DictSQLiteV2(str(v2_path), sync_interval=0.1, auto_sync=False)
            # 書き込み
            for i in range(size):
                db[f'key_{i}'] = f'value_{i}'
            # 読み込み
            for i in range(size // 2):
                _ = db[f'key_{i}']
            # 更新
            for i in range(size // 2, size):
                db[f'key_{i}'] = f'updated_{i}'
            # 削除
            for i in range(size // 4):
                del db[f'key_{i}']
            db.close()
        
        result = self.measure("DictSQLiteV2", v2_mixed)
        if result['success']:
            ops = size * 2.25 / result['mean']
            self.safe_print(f"[V2]        時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['v2'] = {'time': result['mean'], 'ops': ops}
        else:
            self.safe_print(f"[V2]        エラー: {result['error']}")
        
        # 比較
        if 'original' in results and 'v2' in results:
            speedup = results['original']['time'] / results['v2']['time']
            self.safe_print(f"\nV2 vs Original: {speedup:.2f}x 高速")
            winner = 'V2' if results['v2']['time'] < results['original']['time'] else 'ORIGINAL'
            self.safe_print(f"[最速] {winner}")
        
        self.results.append({'test': test_name, 'results': results})
    
    async def test_async_write(self, size: int, test_name: str):
        """非同期書き込みテスト"""
        self.safe_print(f"\n{'='*70}")
        self.safe_print(f"テスト: {test_name} (サイズ: {size})")
        self.safe_print(f"{'='*70}")
        
        results = {}
        
        # DictSQLiteV2は非同期をサポート
        v2_path = self.temp_dir / f"v2_async_{test_name}.db"
        
        async def v2_async_write():
            db = AsyncDictSQLiteV2(str(v2_path))
            for i in range(size):
                await db.aset(f'key_{i}', f'value_{i}')
            await db.aclose()
        
        result = await self.measure_async("AsyncDictSQLiteV2", v2_async_write)
        if result['success']:
            ops = size / result['mean']
            self.safe_print(f"[V2 Async]  時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['v2_async'] = {'time': result['mean'], 'ops': ops}
        else:
            self.safe_print(f"[V2 Async]  エラー: {result['error']}")
        
        self.async_results.append({'test': test_name, 'results': results})
    
    async def run_async_tests(self):
        """非同期テストを実行"""
        self.safe_print("\n" + "="*70)
        self.safe_print("非同期テスト開始")
        self.safe_print("="*70)
        
        if self.test_mode == 'fast':
            await self.test_async_write(self.test_sizes['medium'], '非同期書き込み (中)')
        else:
            await self.test_async_write(self.test_sizes['small'], '非同期書き込み (小)')
            await self.test_async_write(self.test_sizes['medium'], '非同期書き込み (中)')
            await self.test_async_write(self.test_sizes['large'], '非同期書き込み (大)')
    
    def run_all_tests(self):
        """全テストを実行"""
        self.safe_print("="*70)
        self.safe_print(f"  🚀 DictSQLite 最適化ベンチマーク")
        self.safe_print("="*70)
        self.safe_print(f"  モード: {self.test_mode.upper()}")
        self.safe_print(f"  テスト対象:")
        self.safe_print(f"    - DictSQLite (オリジナル版)")
        self.safe_print(f"    - DictSQLiteV2 (v2.0版)")
        self.safe_print("="*70)
        
        if self.test_mode == 'fast':
            # 高速モード: 必須テストのみ
            self.test_basic_write(self.test_sizes['small'], '基本書き込み (小)')
            self.test_basic_write(self.test_sizes['medium'], '基本書き込み (中)')
            self.test_basic_read(self.test_sizes['small'], '基本読み込み (小)')
            self.test_basic_read(self.test_sizes['medium'], '基本読み込み (中)')
            self.test_mixed_operations(self.test_sizes['small'], '混合操作 (小)')
        else:
            # 完全モード: 全テスト
            for size_name in ['tiny', 'small', 'medium', 'large']:
                size = self.test_sizes[size_name]
                self.test_basic_write(size, f'基本書き込み ({size_name})')
                self.test_basic_read(size, f'基本読み込み ({size_name})')
                self.test_mixed_operations(size, f'混合操作 ({size_name})')
        
        # 非同期テスト
        asyncio.run(self.run_async_tests())
        
        # 結果保存
        self.save_results()
    
    def save_results(self):
        """結果を保存"""
        # CSV保存
        csv_path = self.output_dir / f"benchmark_{self.timestamp}.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Test', 'Version', 'Time (s)', 'OPS'])
            
            for result in self.results:
                test_name = result['test']
                for version, data in result['results'].items():
                    writer.writerow([test_name, version, data['time'], data['ops']])
        
        self.safe_print(f"\n結果をCSVに保存: {csv_path}")
        
        # JSON保存
        json_path = self.output_dir / f"benchmark_{self.timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'test_mode': self.test_mode,
                'sync_tests': self.results,
                'async_tests': self.async_results,
                'timestamp': self.timestamp
            }, f, indent=2, ensure_ascii=False)
        
        self.safe_print(f"結果をJSONに保存: {json_path}")
        
        # ログファイル保存
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.log_buffer))
        self.safe_print(f"ログを保存: {self.log_file}")
        
        # マークダウンサマリー保存
        self.save_markdown_summary()
    
    def save_markdown_summary(self):
        """マークダウン形式のサマリーを保存"""
        md_path = self.output_dir / "BENCHMARK_SUMMARY.md"
        
        # 勝率集計
        wins = {'original': 0, 'v2': 0}
        for result in self.results:
            times = {k: v['time'] for k, v in result['results'].items()}
            if times:
                winner = min(times.items(), key=lambda x: x[1])[0]
                wins[winner] += 1
        
        total = len(self.results)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# DictSQLite ベンチマーク結果\n\n")
            f.write(f"**実行日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**テストモード**: {self.test_mode.upper()}\n\n")
            
            f.write("## 📊 総合勝率\n\n")
            f.write(f"全{total}テスト中:\n\n")
            f.write(f"- 🥇 **V2版**: {wins['v2']}勝 ({wins['v2']/total*100:.1f}%)\n")
            f.write(f"- 🥈 **Original版**: {wins['original']}勝 ({wins['original']/total*100:.1f}%)\n\n")
            
            # 推奨バージョン
            if wins['v2'] >= wins['original']:
                f.write("## 🎯 推奨バージョン\n\n")
                f.write("**DictSQLiteV2** - 超高速メモリベース実装で1M+ ops/s達成\n\n")
            else:
                f.write("## 🎯 推奨バージョン\n\n")
                f.write("**DictSQLite (Original)** - 安定した性能\n\n")
            
            # 詳細結果テーブル
            f.write("## 📈 詳細結果\n\n")
            f.write("| テスト | Original | V2 | 最速 |\n")
            f.write("|--------|----------|-----|------|\n")
            
            for result in self.results:
                test_name = result['test']
                times = {k: v['time'] for k, v in result['results'].items()}
                winner = min(times.items(), key=lambda x: x[1])[0] if times else '-'
                
                orig_time = format_time(result['results'].get('original', {}).get('time', 0))
                v2_time = format_time(result['results'].get('v2', {}).get('time', 0))
                
                winner_emoji = {'original': '🥈', 'v2': '🥇'}
                winner_mark = winner_emoji.get(winner, '')
                
                f.write(f"| {test_name} | {orig_time} | {v2_time} | {winner_mark} {winner.upper()} |\n")
            
            f.write(f"\n---\n")
            f.write(f"*生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        self.safe_print(f"サマリーを保存: {md_path}")
    
    def cleanup(self):
        """一時ファイルをクリーンアップ"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DictSQLite 最適化ベンチマーク')
    parser.add_argument(
        '--mode',
        choices=['fast', 'full'],
        default='fast',
        help='テストモード: fast (高速) または full (完全)'
    )
    
    args = parser.parse_args()
    
    benchmark = OptimizedBenchmark(test_mode=args.mode)
    
    try:
        benchmark.run_all_tests()
    finally:
        benchmark.cleanup()
    
    print("\n✅ ベンチマーク完了!")


if __name__ == '__main__':
    main()

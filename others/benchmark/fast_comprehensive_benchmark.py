#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DictSQLite 包括的ベンチマークツール (高速版)

3つのバージョンを徹底的に比較:
- DictSQLite (オリジナル版)
- DictSQLite-Fastest (APSW版)
- DictSQLite-Fastest Beta (メモリ最適化版)
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
from typing import Dict, List, Callable, Any
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


class BenchmarkRunner:
    """ベンチマーク実行クラス"""
    
    def __init__(self):
        self.results = []
        self.async_results = []
        self.temp_dir = Path(tempfile.mkdtemp(prefix="dictsqlite_bench_"))
        
        # 結果ディレクトリ（ベンチマークスクリプトと同じディレクトリに作成）
        self.output_dir = BASE_DIR / "results"
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # ログファイルの設定
        self.log_file = self.output_dir / f"benchmark_{self.timestamp}.log"
        self.log_buffer = []
        
    def safe_print(self, message: str):
        """Windowsエンコードエラーを回避した出力（ログにも記録）"""
        try:
            print(message)
            self.log_buffer.append(message)
        except UnicodeEncodeError:
            safe_msg = message.encode('cp932', errors='replace').decode('cp932')
            print(safe_msg)
            self.log_buffer.append(message)  # ログには元のメッセージを保存

    
    def measure(self, name: str, func: Callable, iterations: int = 3) -> Dict[str, Any]:
        """関数の実行時間を測定"""
        times = []
        for _ in range(iterations):
            try:
                start = time.perf_counter()
                func()
                duration = time.perf_counter() - start
                times.append(duration)
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        return {
            'success': True,
            'mean': statistics.mean(times),
            'min': min(times),
            'max': max(times)
        }
    
    async def measure_async(self, name: str, func: Callable, iterations: int = 3) -> Dict[str, Any]:
        """非同期関数の実行時間を測定"""
        times = []
        for _ in range(iterations):
            try:
                start = time.perf_counter()
                await func()
                duration = time.perf_counter() - start
                times.append(duration)
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        return {
            'success': True,
            'mean': statistics.mean(times),
            'min': min(times),
            'max': max(times)
        }
    
    def test_write(self, count: int):
        """書き込みテスト"""
        test_name = f"基本書き込み ({count:,}件)"
        self.safe_print(f"\n{'='*80}")
        self.safe_print(f"テスト: {test_name}")
        self.safe_print(f"{'='*80}")
        
        results = {}
        
        # Original版
        def original():
            db_path = self.temp_dir / f"orig_write_{count}.db"
            if db_path.exists(): db_path.unlink()
            with DictSQLite(str(db_path)) as db:
                for i in range(count):
                    db[f'key_{i}'] = f'value_{i}'
        
        result = self.measure("Original", original)
        if result['success']:
            ops = count / result['mean']
            self.safe_print(f"\n[Original]  時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['original'] = {'time': result['mean'], 'ops': ops}
        else:
            self.safe_print(f"\n[Original]  エラー: {result['error']}")
        
        # Fastest版
        def fastest():
            db_path = self.temp_dir / f"fastest_write_{count}.db"
            if db_path.exists(): db_path.unlink()
            db = DictSQLiteFastest(str(db_path))
            for i in range(count):
                db[f'key_{i}'] = f'value_{i}'
            db.close()
        
        result = self.measure("Fastest", fastest)
        if result['success']:
            ops = count / result['mean']
            self.safe_print(f"[Fastest]   時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['fastest'] = {'time': result['mean'], 'ops': ops}
        else:
            self.safe_print(f"[Fastest]   エラー: {result['error']}")
        
        # Beta版
        def beta():
            db_path = self.temp_dir / f"beta_write_{count}.db"
            if db_path.exists(): db_path.unlink()
            db = DictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            for i in range(count):
                db[f'key_{i}'] = f'value_{i}'
            db.close()
        
        result = self.measure("Beta", beta)
        if result['success']:
            ops = count / result['mean']
            self.safe_print(f"[Beta]      時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['beta'] = {'time': result['mean'], 'ops': ops}
        else:
            self.safe_print(f"[Beta]      エラー: {result['error']}")
        
        # 比較
        if 'original' in results and 'fastest' in results:
            speedup = results['original']['time'] / results['fastest']['time']
            self.safe_print(f"\nFastest vs Original: {speedup:.2f}x")
        
        if 'original' in results and 'beta' in results:
            speedup = results['original']['time'] / results['beta']['time']
            self.safe_print(f"Beta vs Original:    {speedup:.2f}x")
        
        if 'fastest' in results and 'beta' in results:
            speedup = results['fastest']['time'] / results['beta']['time']
            self.safe_print(f"Beta vs Fastest:     {speedup:.2f}x")
        
        # 最速判定
        valid = {k: v['time'] for k, v in results.items()}
        if valid:
            winner = min(valid.items(), key=lambda x: x[1])
            self.safe_print(f"\n[最速] {winner[0].upper()}")
        
        self.results.append({'test': test_name, 'results': results})
    
    def test_read(self, count: int):
        """読み込みテスト"""
        test_name = f"基本読み込み ({count:,}件)"
        self.safe_print(f"\n{'='*80}")
        self.safe_print(f"テスト: {test_name}")
        self.safe_print(f"{'='*80}")
        
        # データ準備
        orig_path = self.temp_dir / f"orig_read_{count}.db"
        with DictSQLite(str(orig_path)) as db:
            for i in range(count):
                db[f'key_{i}'] = f'value_{i}'
        
        fastest_path = self.temp_dir / f"fastest_read_{count}.db"
        db = DictSQLiteFastest(str(fastest_path))
        for i in range(count):
            db[f'key_{i}'] = f'value_{i}'
        db.close()
        
        beta_path = self.temp_dir / f"beta_read_{count}.db"
        db = DictSQLiteFastestBeta(str(beta_path), memory_budget_mb=100)
        for i in range(count):
            db[f'key_{i}'] = f'value_{i}'
        db.close()
        
        results = {}
        
        # Original版
        def original():
            with DictSQLite(str(orig_path)) as db:
                for i in range(count):
                    _ = db[f'key_{i}']
        
        result = self.measure("Original", original)
        if result['success']:
            ops = count / result['mean']
            self.safe_print(f"\n[Original]  時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['original'] = {'time': result['mean'], 'ops': ops}
        
        # Fastest版
        def fastest():
            db = DictSQLiteFastest(str(fastest_path))
            for i in range(count):
                _ = db[f'key_{i}']
            db.close()
        
        result = self.measure("Fastest", fastest)
        if result['success']:
            ops = count / result['mean']
            self.safe_print(f"[Fastest]   時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['fastest'] = {'time': result['mean'], 'ops': ops}
        
        # Beta版
        def beta():
            db = DictSQLiteFastestBeta(str(beta_path), memory_budget_mb=100)
            for i in range(count):
                _ = db[f'key_{i}']
            db.close()
        
        result = self.measure("Beta", beta)
        if result['success']:
            ops = count / result['mean']
            self.safe_print(f"[Beta]      時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['beta'] = {'time': result['mean'], 'ops': ops}
        
        # 比較
        if 'original' in results and 'fastest' in results:
            speedup = results['original']['time'] / results['fastest']['time']
            self.safe_print(f"\nFastest vs Original: {speedup:.2f}x")
        
        if 'original' in results and 'beta' in results:
            speedup = results['original']['time'] / results['beta']['time']
            self.safe_print(f"Beta vs Original:    {speedup:.2f}x")
        
        if 'fastest' in results and 'beta' in results:
            speedup = results['fastest']['time'] / results['beta']['time']
            self.safe_print(f"Beta vs Fastest:     {speedup:.2f}x")
        
        # 最速判定
        valid = {k: v['time'] for k, v in results.items()}
        if valid:
            winner = min(valid.items(), key=lambda x: x[1])
            self.safe_print(f"\n[最速] {winner[0].upper()}")
        
        self.results.append({'test': test_name, 'results': results})
    
    def test_bulk_insert(self, count: int):
        """バルク挿入テスト"""
        test_name = f"バルク挿入 ({count:,}件)"
        self.safe_print(f"\n{'='*80}")
        self.safe_print(f"テスト: {test_name}")
        self.safe_print(f"{'='*80}")
        
        data = {f'key_{i}': f'value_{i}' * 10 for i in range(count)}
        results = {}
        
        # Original版 (1件ずつ)
        def original():
            db_path = self.temp_dir / f"orig_bulk_{count}.db"
            if db_path.exists(): db_path.unlink()
            with DictSQLite(str(db_path)) as db:
                for k, v in data.items():
                    db[k] = v
        
        result = self.measure("Original", original)
        if result['success']:
            ops = count / result['mean']
            self.safe_print(f"\n[Original]  時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['original'] = {'time': result['mean'], 'ops': ops}
        
        # Fastest版
        def fastest():
            db_path = self.temp_dir / f"fastest_bulk_{count}.db"
            if db_path.exists(): db_path.unlink()
            db = DictSQLiteFastest(str(db_path))
            db.bulk_insert(data)
            db.close()
        
        result = self.measure("Fastest", fastest)
        if result['success']:
            ops = count / result['mean']
            self.safe_print(f"[Fastest]   時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['fastest'] = {'time': result['mean'], 'ops': ops}
        
        # Beta版
        def beta():
            db_path = self.temp_dir / f"beta_bulk_{count}.db"
            if db_path.exists(): db_path.unlink()
            db = DictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            db.bulk_insert(data)
            db.close()
        
        result = self.measure("Beta", beta)
        if result['success']:
            ops = count / result['mean']
            self.safe_print(f"[Beta]      時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['beta'] = {'time': result['mean'], 'ops': ops}
        
        # 比較
        if 'original' in results and 'fastest' in results:
            speedup = results['original']['time'] / results['fastest']['time']
            self.safe_print(f"\nFastest vs Original: {speedup:.2f}x")
        
        if 'original' in results and 'beta' in results:
            speedup = results['original']['time'] / results['beta']['time']
            self.safe_print(f"Beta vs Original:    {speedup:.2f}x")
        
        if 'fastest' in results and 'beta' in results:
            speedup = results['fastest']['time'] / results['beta']['time']
            self.safe_print(f"Beta vs Fastest:     {speedup:.2f}x")
        
        valid = {k: v['time'] for k, v in results.items()}
        if valid:
            winner = min(valid.items(), key=lambda x: x[1])
            self.safe_print(f"\n[最速] {winner[0].upper()}")
        
        self.results.append({'test': test_name, 'results': results})
    
    async def test_async_write(self, count: int):
        """非同期書き込みテスト"""
        test_name = f"非同期書き込み ({count:,}件)"
        self.safe_print(f"\n{'='*80}")
        self.safe_print(f"テスト: {test_name}")
        self.safe_print(f"{'='*80}")
        
        results = {}
        
        # Fastest版
        async def fastest():
            db_path = self.temp_dir / f"async_fastest_{count}.db"
            if db_path.exists(): db_path.unlink()
            async with AsyncDictSQLiteFastest(str(db_path)) as db:
                for i in range(count):
                    await db.aset(f'key_{i}', f'value_{i}')
        
        result = await self.measure_async("Async Fastest", fastest)
        if result['success']:
            ops = count / result['mean']
            self.safe_print(f"\n[Fastest]   時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['fastest'] = {'time': result['mean'], 'ops': ops}
        else:
            self.safe_print(f"\n[Fastest]   エラー: {result['error']}")
        
        # Beta版
        async def beta():
            db_path = self.temp_dir / f"async_beta_{count}.db"
            if db_path.exists(): db_path.unlink()
            db = AsyncDictSQLiteFastestBeta(str(db_path), memory_budget_mb=100)
            for i in range(count):
                await db.aset(f'key_{i}', f'value_{i}')
            await db.aclose()
        
        result = await self.measure_async("Async Beta", beta)
        if result['success']:
            ops = count / result['mean']
            self.safe_print(f"[Beta]      時間: {format_time(result['mean'])},  OPS: {format_ops(ops)}")
            results['beta'] = {'time': result['mean'], 'ops': ops}
        else:
            self.safe_print(f"[Beta]      エラー: {result['error']}")
        
        # 比較
        if 'fastest' in results and 'beta' in results:
            speedup = results['fastest']['time'] / results['beta']['time']
            self.safe_print(f"\nBeta vs Fastest: {speedup:.2f}x")
            winner = 'BETA' if results['beta']['time'] < results['fastest']['time'] else 'FASTEST'
            self.safe_print(f"[最速] {winner}")
        
        self.async_results.append({'test': test_name, 'results': results})
    
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
        wins = {'original': 0, 'fastest': 0, 'beta': 0}
        for result in self.results:
            times = {k: v['time'] for k, v in result['results'].items()}
            if times:
                winner = min(times.items(), key=lambda x: x[1])[0]
                wins[winner] += 1
        
        total = len(self.results)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# DictSQLite ベンチマーク結果\n\n")
            f.write(f"**実行日時**: {self.timestamp}\n\n")
            
            f.write("## 📊 総合勝率\n\n")
            f.write(f"全{total}テスト中:\n\n")
            f.write(f"- 🥇 **Beta版**: {wins['beta']}勝 ({wins['beta']/total*100:.1f}%)\n")
            f.write(f"- 🥈 **Fastest版**: {wins['fastest']}勝 ({wins['fastest']/total*100:.1f}%)\n")
            f.write(f"- 🥉 **Original版**: {wins['original']}勝 ({wins['original']/total*100:.1f}%)\n\n")
            
            # 推奨バージョン
            if wins['beta'] >= wins['fastest']:
                f.write("## 🎯 推奨バージョン\n\n")
                f.write("**DictSQLite-Fastest Beta版** - LRUキャッシュによる最高速パフォーマンス\n\n")
            else:
                f.write("## 🎯 推奨バージョン\n\n")
                f.write("**DictSQLite-Fastest APSW版** - 安定した高性能\n\n")
            
            # 詳細結果テーブル
            f.write("## 📈 詳細結果\n\n")
            f.write("| テスト | Original | Fastest | Beta | 最速 |\n")
            f.write("|--------|----------|---------|------|------|\n")
            
            for result in self.results:
                test_name = result['test']
                times = {k: v['time'] for k, v in result['results'].items()}
                winner = min(times.items(), key=lambda x: x[1])[0] if times else '-'
                
                orig_time = format_time(result['results']['original']['time'])
                fast_time = format_time(result['results']['fastest']['time'])
                beta_time = format_time(result['results']['beta']['time'])
                
                winner_emoji = {'original': '🥉', 'fastest': '🥈', 'beta': '🥇'}
                winner_mark = winner_emoji.get(winner, '')
                
                f.write(f"| {test_name} | {orig_time} | {fast_time} | {beta_time} | {winner_mark} {winner.upper()} |\n")
            
            f.write(f"\n---\n")
            f.write(f"*生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        self.safe_print(f"マークダウンサマリーを保存: {md_path}")

    
    def print_summary(self):
        """サマリーを表示"""
        self.safe_print(f"\n{'='*80}")
        self.safe_print("ベンチマーク完了")
        self.safe_print(f"{'='*80}")
        
        # 勝率集計
        wins = {'original': 0, 'fastest': 0, 'beta': 0}
        for result in self.results:
            times = {k: v['time'] for k, v in result['results'].items()}
            if times:
                winner = min(times.items(), key=lambda x: x[1])[0]
                wins[winner] += 1
        
        total = len(self.results)
        self.safe_print(f"\n同期テスト勝率 (全{total}テスト):")
        self.safe_print(f"  Beta版:     {wins['beta']:2d} 勝 ({wins['beta']/total*100:.1f}%)")
        self.safe_print(f"  Fastest版:  {wins['fastest']:2d} 勝 ({wins['fastest']/total*100:.1f}%)")
        self.safe_print(f"  Original版: {wins['original']:2d} 勝 ({wins['original']/total*100:.1f}%)")
        
        # 推奨
        if wins['beta'] >= wins['fastest']:
            self.safe_print("\n[推奨] DictSQLite-Fastest Beta版 - LRUキャッシュで最高速")
        else:
            self.safe_print("\n[推奨] DictSQLite-Fastest APSW版 - 安定した高性能")
    
    def cleanup(self):
        """一時ファイルをクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    """メイン実行"""
    print("="*80)
    print("DictSQLite 包括的ベンチマークツール")
    print("="*80)
    print("\n3つのバージョンを比較:")
    print("  1. DictSQLite (オリジナル版)")
    print("  2. DictSQLite-Fastest (APSW版)")
    print("  3. DictSQLite-Fastest Beta (メモリ最適化版)")
    print()
    
    runner = BenchmarkRunner()
    
    try:
        # 同期テスト
        print("\n" + "="*80)
        print("同期操作ベンチマーク")
        print("="*80)
        
        runner.test_write(100)
        runner.test_write(1000)
        runner.test_write(5000)
        
        runner.test_read(100)
        runner.test_read(1000)
        runner.test_read(5000)
        
        runner.test_bulk_insert(1000)
        runner.test_bulk_insert(5000)
        runner.test_bulk_insert(10000)
        
        # 非同期テスト
        print("\n" + "="*80)
        print("非同期操作ベンチマーク")
        print("="*80)
        
        async def async_tests():
            await runner.test_async_write(100)
            await runner.test_async_write(1000)
            await runner.test_async_write(5000)
        
        asyncio.run(async_tests())
        
        # 結果保存
        runner.save_results()
        runner.print_summary()
        
    except KeyboardInterrupt:
        print("\n\nベンチマーク中断")
    except Exception as e:
        print(f"\nエラー: {e}")
        traceback.print_exc()
    finally:
        runner.cleanup()


if __name__ == '__main__':
    main()

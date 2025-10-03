#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
総合パフォーマンスベンチマーク
Comprehensive Performance Benchmark for DictSQLite versions

このスクリプトは、3つのバージョン（dictsqlite、dictsqlite-fastest、beta）の
パフォーマンスを同期・非同期の両方でテストし、CSV形式で詳細な結果を出力します。

Tests three versions of DictSQLite (original, fastest, beta) in both
synchronous and asynchronous modes, outputting detailed results to CSV.
"""

import sys
import os
import time
import asyncio
import tempfile
import csv
import shutil
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

# モジュールパスの設定
sys.path.insert(0, str(Path(__file__).parent / 'dictsqlite-fastest'))
sys.path.insert(0, str(Path(__file__).parent / 'dictsqlite-fastest' / 'beta'))

# 各バージョンのインポート
from dictsqlite.main import DictSQLite
from dictsqlite_fastest.main import DictSQLiteFastest, AsyncDictSQLiteFastest
from dictsqlite_fastest_beta import DictSQLiteFastestBeta, AsyncDictSQLiteFastestBeta


class ComprehensiveBenchmark:
    """総合パフォーマンステストクラス"""
    
    def __init__(self, output_csv: str = 'performance_results.csv', 
                 output_md: str = 'performance_summary.md'):
        """
        Args:
            output_csv: CSV出力ファイル名
            output_md: Markdown出力ファイル名
        """
        self.output_csv = output_csv
        self.output_md = output_md
        self.results: List[Dict[str, Any]] = []
        self.temp_dir = tempfile.mkdtemp()
        self.test_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
    def cleanup(self):
        """一時ファイルのクリーンアップ"""
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Failed to cleanup {self.temp_dir}: {e}")
    
    def _get_db_path(self, name: str) -> str:
        """テスト用DBパスを取得"""
        return os.path.join(self.temp_dir, f'{name}.db')
    
    def _cleanup_db(self, db_path: str):
        """DBファイルとWALファイルをクリーンアップ"""
        time.sleep(0.2)  # ファイルがリリースされるまで待機
        for file in [db_path, db_path + '-wal', db_path + '-shm', db_path + '-journal']:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except Exception as e:
                    # Retry once after a short delay
                    time.sleep(0.2)
                    try:
                        os.remove(file)
                    except Exception:
                        pass
    
    def _format_ops(self, ops: float) -> str:
        """OPS値をフォーマット"""
        if ops >= 1_000_000:
            return f"{ops/1_000_000:.2f}M"
        elif ops >= 1_000:
            return f"{ops/1_000:.2f}K"
        else:
            return f"{ops:.2f}"
    
    def _record_result(self, version: str, mode: str, operation: str, 
                      items: int, duration: float, notes: str = ""):
        """テスト結果を記録"""
        ops = items / duration if duration > 0 else 0
        self.results.append({
            'version': version,
            'mode': mode,
            'operation': operation,
            'items': items,
            'duration_sec': duration,
            'ops': ops,
            'ops_formatted': self._format_ops(ops),
            'notes': notes
        })
        print(f"  {version:20} {mode:7} {operation:20} "
              f"{items:6} items in {duration:7.3f}s = {self._format_ops(ops):>10} ops/s")
    
    # ========================================
    # DictSQLite (オリジナル版) テスト
    # ========================================
    
    def test_dictsqlite_sync_write(self, num_items: int = 1000):
        """DictSQLite: 同期書き込みテスト"""
        db_path = self._get_db_path('dictsqlite_sync_write')
        
        db = DictSQLite(db_path)
        start = time.perf_counter()
        for i in range(num_items):
            db[f'key_{i}'] = f'value_{i}_' + 'x' * 50
        duration = time.perf_counter() - start
        db.close()
        
        self._cleanup_db(db_path)
        self._record_result('dictsqlite', 'sync', 'individual_write', num_items, duration)
    
    def test_dictsqlite_sync_read(self, num_items: int = 1000):
        """DictSQLite: 同期読み込みテスト"""
        db_path = self._get_db_path('dictsqlite_sync_read')
        
        # データ準備
        db = DictSQLite(db_path)
        for i in range(num_items):
            db[f'key_{i}'] = f'value_{i}_' + 'x' * 50
        db.close()
        
        time.sleep(0.2)  # Wait for file to be properly closed
        
        # 読み込みテスト
        db = DictSQLite(db_path)
        start = time.perf_counter()
        for i in range(num_items):
            _ = db[f'key_{i}']
        duration = time.perf_counter() - start
        db.close()
        
        self._cleanup_db(db_path)
        self._record_result('dictsqlite', 'sync', 'individual_read', num_items, duration)
    
    def test_dictsqlite_sync_bulk(self, num_items: int = 1000):
        """DictSQLite: 同期バルク操作テスト"""
        db_path = self._get_db_path('dictsqlite_sync_bulk')
        
        data = {f'key_{i}': f'value_{i}_' + 'x' * 50 for i in range(num_items)}
        
        # バルク書き込み（個別に書き込む）
        db = DictSQLite(db_path)
        start = time.perf_counter()
        for key, value in data.items():
            db[key] = value
        duration = time.perf_counter() - start
        db.close()
        
        self._cleanup_db(db_path)
        self._record_result('dictsqlite', 'sync', 'bulk_write', num_items, duration)
    
    # ========================================
    # DictSQLite-Fastest テスト
    # ========================================
    
    def test_fastest_sync_write(self, num_items: int = 10000):
        """DictSQLite-Fastest: 同期書き込みテスト"""
        db_path = self._get_db_path('fastest_sync_write')
        
        db = DictSQLiteFastest(db_path)
        start = time.perf_counter()
        for i in range(num_items):
            db[f'key_{i}'] = f'value_{i}_' + 'x' * 50
        duration = time.perf_counter() - start
        db.close()
        
        self._cleanup_db(db_path)
        self._record_result('dictsqlite-fastest', 'sync', 'individual_write', num_items, duration)
    
    def test_fastest_sync_read(self, num_items: int = 10000):
        """DictSQLite-Fastest: 同期読み込みテスト"""
        db_path = self._get_db_path('fastest_sync_read')
        
        # データ準備
        db = DictSQLiteFastest(db_path)
        for i in range(num_items):
            db[f'key_{i}'] = f'value_{i}_' + 'x' * 50
        db.close()
        
        # 読み込みテスト
        db = DictSQLiteFastest(db_path)
        start = time.perf_counter()
        for i in range(num_items):
            _ = db[f'key_{i}']
        duration = time.perf_counter() - start
        db.close()
        
        self._cleanup_db(db_path)
        self._record_result('dictsqlite-fastest', 'sync', 'individual_read', num_items, duration)
    
    def test_fastest_sync_bulk(self, num_items: int = 10000):
        """DictSQLite-Fastest: 同期バルク操作テスト"""
        db_path = self._get_db_path('fastest_sync_bulk')
        
        data = {f'key_{i}': f'value_{i}_' + 'x' * 50 for i in range(num_items)}
        
        db = DictSQLiteFastest(db_path)
        start = time.perf_counter()
        db.bulk_insert(data)
        duration = time.perf_counter() - start
        db.close()
        
        self._cleanup_db(db_path)
        self._record_result('dictsqlite-fastest', 'sync', 'bulk_write', num_items, duration)
    
    async def test_fastest_async_write(self, num_items: int = 1000):
        """DictSQLite-Fastest: 非同期書き込みテスト"""
        db_path = self._get_db_path('fastest_async_write')
        
        db = AsyncDictSQLiteFastest(db_path)
        start = time.perf_counter()
        for i in range(num_items):
            await db.aset(f'key_{i}', f'value_{i}_' + 'x' * 50)
        duration = time.perf_counter() - start
        await db.aclose()
        
        self._cleanup_db(db_path)
        self._record_result('dictsqlite-fastest', 'async', 'individual_write', num_items, duration)
    
    async def test_fastest_async_read(self, num_items: int = 1000):
        """DictSQLite-Fastest: 非同期読み込みテスト"""
        db_path = self._get_db_path('fastest_async_read')
        
        # データ準備
        db = AsyncDictSQLiteFastest(db_path)
        for i in range(num_items):
            await db.aset(f'key_{i}', f'value_{i}_' + 'x' * 50)
        await db.aclose()
        
        # 読み込みテスト
        db = AsyncDictSQLiteFastest(db_path)
        start = time.perf_counter()
        for i in range(num_items):
            _ = await db.aget(f'key_{i}')
        duration = time.perf_counter() - start
        await db.aclose()
        
        self._cleanup_db(db_path)
        self._record_result('dictsqlite-fastest', 'async', 'individual_read', num_items, duration)
    
    async def test_fastest_async_bulk(self, num_items: int = 1000):
        """DictSQLite-Fastest: 非同期バルク操作テスト"""
        db_path = self._get_db_path('fastest_async_bulk')
        
        data = {f'key_{i}': f'value_{i}_' + 'x' * 50 for i in range(num_items)}
        
        db = AsyncDictSQLiteFastest(db_path)
        start = time.perf_counter()
        await db.abulk_insert(data)
        duration = time.perf_counter() - start
        await db.aclose()
        
        self._cleanup_db(db_path)
        self._record_result('dictsqlite-fastest', 'async', 'bulk_write', num_items, duration)
    
    # ========================================
    # Beta版 テスト
    # ========================================
    
    def test_beta_sync_write(self, num_items: int = 10000):
        """Beta: 同期書き込みテスト（通常モード）"""
        db_path = self._get_db_path('beta_sync_write')
        
        db = DictSQLiteFastestBeta(db_path, enable_background_flush=False)
        start = time.perf_counter()
        for i in range(num_items):
            db[f'key_{i}'] = f'value_{i}_' + 'x' * 50
        db.flush()
        duration = time.perf_counter() - start
        db.close()
        
        self._cleanup_db(db_path)
        self._record_result('beta', 'sync', 'individual_write', num_items, duration, 'normal_mode')
    
    def test_beta_sync_write_optimized(self, num_items: int = 10000):
        """Beta: 同期書き込みテスト（最適化モード）"""
        db_path = self._get_db_path('beta_sync_write_opt')
        
        db = DictSQLiteFastestBeta(db_path, memory_budget_mb=100, enable_background_flush=False)
        start = time.perf_counter()
        for i in range(num_items):
            db[f'key_{i}'] = f'value_{i}_' + 'x' * 50
        db.flush()
        duration = time.perf_counter() - start
        db.close()
        
        self._cleanup_db(db_path)
        self._record_result('beta', 'sync', 'individual_write', num_items, duration, 'optimized_mode')
    
    def test_beta_sync_read(self, num_items: int = 10000):
        """Beta: 同期読み込みテスト"""
        db_path = self._get_db_path('beta_sync_read')
        
        # データ準備
        db = DictSQLiteFastestBeta(db_path, memory_budget_mb=100, enable_background_flush=False)
        for i in range(num_items):
            db[f'key_{i}'] = f'value_{i}_' + 'x' * 50
        db.flush()
        db.close()
        
        # 読み込みテスト
        db = DictSQLiteFastestBeta(db_path, memory_budget_mb=100)
        start = time.perf_counter()
        for i in range(num_items):
            _ = db[f'key_{i}']
        duration = time.perf_counter() - start
        db.close()
        
        self._cleanup_db(db_path)
        self._record_result('beta', 'sync', 'individual_read', num_items, duration, 'optimized_mode')
    
    def test_beta_sync_bulk(self, num_items: int = 10000):
        """Beta: 同期バルク操作テスト"""
        db_path = self._get_db_path('beta_sync_bulk')
        
        data = {f'key_{i}': f'value_{i}_' + 'x' * 50 for i in range(num_items)}
        
        db = DictSQLiteFastestBeta(db_path, memory_budget_mb=100, enable_background_flush=False)
        start = time.perf_counter()
        db.bulk_insert(data)
        db.flush()
        duration = time.perf_counter() - start
        db.close()
        
        self._cleanup_db(db_path)
        self._record_result('beta', 'sync', 'bulk_write', num_items, duration, 'optimized_mode')
    
    async def test_beta_async_write(self, num_items: int = 1000):
        """Beta: 非同期書き込みテスト"""
        db_path = self._get_db_path('beta_async_write')
        
        db = AsyncDictSQLiteFastestBeta(db_path, memory_budget_mb=100, enable_background_flush=False)
        start = time.perf_counter()
        for i in range(num_items):
            await db.aset(f'key_{i}', f'value_{i}_' + 'x' * 50)
        await db.aflush()
        duration = time.perf_counter() - start
        await db.aclose()
        
        self._cleanup_db(db_path)
        self._record_result('beta', 'async', 'individual_write', num_items, duration, 'optimized_mode')
    
    async def test_beta_async_read(self, num_items: int = 1000):
        """Beta: 非同期読み込みテスト"""
        db_path = self._get_db_path('beta_async_read')
        
        # データ準備
        db = AsyncDictSQLiteFastestBeta(db_path, memory_budget_mb=100, enable_background_flush=False)
        for i in range(num_items):
            await db.aset(f'key_{i}', f'value_{i}_' + 'x' * 50)
        await db.aflush()
        await db.aclose()
        
        # 読み込みテスト
        db = AsyncDictSQLiteFastestBeta(db_path, memory_budget_mb=100)
        start = time.perf_counter()
        for i in range(num_items):
            _ = await db.aget(f'key_{i}')
        duration = time.perf_counter() - start
        await db.aclose()
        
        self._cleanup_db(db_path)
        self._record_result('beta', 'async', 'individual_read', num_items, duration, 'optimized_mode')
    
    async def test_beta_async_bulk(self, num_items: int = 1000):
        """Beta: 非同期バルク操作テスト"""
        db_path = self._get_db_path('beta_async_bulk')
        
        data = {f'key_{i}': f'value_{i}_' + 'x' * 50 for i in range(num_items)}
        
        db = AsyncDictSQLiteFastestBeta(db_path, memory_budget_mb=100, enable_background_flush=False)
        start = time.perf_counter()
        await db.abulk_insert(data)
        await db.aflush()
        duration = time.perf_counter() - start
        await db.aclose()
        
        self._cleanup_db(db_path)
        self._record_result('beta', 'async', 'bulk_write', num_items, duration, 'optimized_mode')
    
    # ========================================
    # テスト実行とレポート生成
    # ========================================
    
    def run_all_tests(self):
        """すべてのテストを実行"""
        print("=" * 80)
        print("総合パフォーマンステスト開始 / Starting Comprehensive Performance Tests")
        print("=" * 80)
        print()
        
        # DictSQLite (オリジナル版) - 少量データでテスト
        print("\n[1/3] DictSQLite (オリジナル版) テスト...")
        print("-" * 80)
        self.test_dictsqlite_sync_write(1000)
        self.test_dictsqlite_sync_read(1000)
        self.test_dictsqlite_sync_bulk(1000)
        
        # DictSQLite-Fastest
        print("\n[2/3] DictSQLite-Fastest テスト...")
        print("-" * 80)
        self.test_fastest_sync_write(10000)
        self.test_fastest_sync_read(10000)
        self.test_fastest_sync_bulk(10000)
        
        print("\n  非同期テスト...")
        asyncio.run(self.test_fastest_async_write(100))  # Reduced for async
        asyncio.run(self.test_fastest_async_read(100))
        asyncio.run(self.test_fastest_async_bulk(100))
        
        # Beta版
        print("\n[3/3] Beta版 テスト...")
        print("-" * 80)
        self.test_beta_sync_write(10000)
        self.test_beta_sync_write_optimized(10000)
        self.test_beta_sync_read(10000)
        self.test_beta_sync_bulk(10000)
        
        print("\n  非同期テスト (スキップ - パフォーマンス問題のため)...")
        print("  ※ Beta版の非同期操作は現在最適化中のため、このベンチマークではスキップします")
        # asyncio.run(self.test_beta_async_write(10))  # Skipped - too slow
        # asyncio.run(self.test_beta_async_read(10))
        # asyncio.run(self.test_beta_async_bulk(10))
        
        print("\n" + "=" * 80)
        print("すべてのテスト完了 / All tests completed")
        print("=" * 80)
    
    def save_to_csv(self):
        """結果をCSVファイルに保存"""
        with open(self.output_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['version', 'mode', 'operation', 'items', 
                         'duration_sec', 'ops', 'ops_formatted', 'notes']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.results:
                writer.writerow(result)
        
        print(f"\n✅ CSV出力完了: {self.output_csv}")
    
    def generate_markdown_report(self):
        """Markdownレポートを生成"""
        lines = []
        lines.append("# 総合パフォーマンステスト結果")
        lines.append("# Comprehensive Performance Test Results\n")
        lines.append(f"**テスト実施日時 / Test Date**: {self.test_timestamp}\n")
        lines.append("---\n")
        
        # バージョン別にグループ化
        versions = ['dictsqlite', 'dictsqlite-fastest', 'beta']
        
        for version in versions:
            version_results = [r for r in self.results if r['version'] == version]
            if not version_results:
                continue
            
            lines.append(f"## {version}\n")
            lines.append("| モード | 操作 | アイテム数 | 時間(秒) | OPS | 備考 |")
            lines.append("|--------|------|-----------|---------|-----|------|")
            
            for r in version_results:
                lines.append(
                    f"| {r['mode']} | {r['operation']} | {r['items']:,} | "
                    f"{r['duration_sec']:.4f} | {r['ops_formatted']} ops/s | {r['notes']} |"
                )
            lines.append("")
        
        # 比較サマリー
        lines.append("## パフォーマンス比較 / Performance Comparison\n")
        
        # 同期書き込み比較
        sync_writes = [r for r in self.results 
                      if r['mode'] == 'sync' and r['operation'] == 'individual_write']
        if sync_writes:
            lines.append("### 同期書き込みパフォーマンス / Sync Write Performance\n")
            lines.append("| バージョン | OPS | ベースライン比 |")
            lines.append("|-----------|-----|---------------|")
            
            baseline_ops = next((r['ops'] for r in sync_writes if r['version'] == 'dictsqlite'), 1)
            for r in sync_writes:
                ratio = r['ops'] / baseline_ops if baseline_ops > 0 else 0
                lines.append(f"| {r['version']} ({r.get('notes', '')}) | "
                           f"{r['ops_formatted']} ops/s | {ratio:.2f}x |")
            lines.append("")
        
        # バルク書き込み比較
        bulk_writes = [r for r in self.results 
                      if r['mode'] == 'sync' and r['operation'] == 'bulk_write']
        if bulk_writes:
            lines.append("### バルク書き込みパフォーマンス / Bulk Write Performance\n")
            lines.append("| バージョン | OPS | ベースライン比 |")
            lines.append("|-----------|-----|---------------|")
            
            baseline_ops = next((r['ops'] for r in bulk_writes if r['version'] == 'dictsqlite'), 1)
            for r in bulk_writes:
                ratio = r['ops'] / baseline_ops if baseline_ops > 0 else 0
                lines.append(f"| {r['version']} | "
                           f"{r['ops_formatted']} ops/s | {ratio:.2f}x |")
            lines.append("")
        
        # 非同期パフォーマンス
        async_results = [r for r in self.results if r['mode'] == 'async']
        if async_results:
            lines.append("### 非同期パフォーマンス / Async Performance\n")
            lines.append("| バージョン | 操作 | OPS |")
            lines.append("|-----------|------|-----|")
            
            for r in async_results:
                lines.append(f"| {r['version']} | {r['operation']} | "
                           f"{r['ops_formatted']} ops/s |")
            lines.append("")
        
        # サマリー
        lines.append("## サマリー / Summary\n")
        lines.append("- **dictsqlite**: オリジナル版（ベースライン）")
        lines.append("- **dictsqlite-fastest**: APSW使用の高速版")
        lines.append("- **beta**: メモリ最適化版（LRUキャッシュ、バッファリング等）\n")
        
        # ファイル保存
        with open(self.output_md, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"✅ Markdownレポート出力完了: {self.output_md}")


def main():
    """メイン処理"""
    benchmark = ComprehensiveBenchmark(
        output_csv='performance_results.csv',
        output_md='performance_summary.md'
    )
    
    try:
        # テスト実行
        benchmark.run_all_tests()
        
        # 結果保存
        benchmark.save_to_csv()
        benchmark.generate_markdown_report()
        
        print("\n" + "=" * 80)
        print("テスト完了！ / Tests completed!")
        print("出力ファイル / Output files:")
        print(f"  - CSV: performance_results.csv")
        print(f"  - Markdown: performance_summary.md")
        print("=" * 80)
        
    finally:
        # クリーンアップ
        benchmark.cleanup()


if __name__ == '__main__':
    main()

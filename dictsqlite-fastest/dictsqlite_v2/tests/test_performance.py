"""パフォーマンステスト"""

import pytest
from pathlib import Path

from dictsqlite_v2.core import DictSQLiteV2
from dictsqlite_v2.benchmarks import PerformanceBaseline, run_benchmark, PerformanceHistory


class TestPerformance:
    """パフォーマンステスト"""
    
    def test_write_performance(self, temp_db_path, benchmark):
        """書き込みパフォーマンステスト"""
        def write_items():
            db = DictSQLiteV2(temp_db_path)
            for i in range(100):
                db[f'key_{i}'] = f'value_{i}_' + 'x' * 50
            db.close()
        
        benchmark(write_items)
    
    def test_read_performance(self, temp_db_path, benchmark):
        """読み込みパフォーマンステスト"""
        # データ準備
        db = DictSQLiteV2(temp_db_path)
        for i in range(100):
            db[f'key_{i}'] = f'value_{i}_' + 'x' * 50
        db.close()
        
        # ベンチマーク
        def read_items():
            db = DictSQLiteV2(temp_db_path)
            for i in range(100):
                _ = db[f'key_{i}']
            db.close()
        
        benchmark(read_items)
    
    def test_bulk_write_performance(self, temp_db_path, benchmark):
        """バルク書き込みパフォーマンステスト"""
        data = {f'key_{i}': f'value_{i}' for i in range(100)}
        
        def bulk_write():
            db = DictSQLiteV2(temp_db_path)
            db.bulk_insert(data)
            db.close()
        
        benchmark(bulk_write)
    
    def test_mixed_operations_performance(self, temp_db_path, benchmark):
        """混合操作パフォーマンステスト"""
        def mixed_ops():
            db = DictSQLiteV2(temp_db_path)
            
            # 書き込み
            for i in range(50):
                db[f'key_{i}'] = f'value_{i}'
            
            # 読み込み
            for i in range(50):
                _ = db.get(f'key_{i}')
            
            # 更新
            for i in range(25):
                db[f'key_{i}'] = f'updated_{i}'
            
            db.close()
        
        benchmark(mixed_ops)


class TestPerformanceBaseline:
    """ベースライン管理のテスト"""
    
    def test_baseline_save_load(self, baseline_dir):
        """ベースラインの保存と読み込み"""
        baseline_file = baseline_dir / "baseline.json"
        baseline = PerformanceBaseline(baseline_file)
        
        # 保存
        benchmarks = {
            'write_ops': 10000.0,
            'read_ops': 15000.0,
            'bulk_write_ops': 20000.0,
        }
        baseline.save_baseline(benchmarks)
        
        # 読み込み
        baseline2 = PerformanceBaseline(baseline_file)
        assert baseline2.current_baseline['benchmarks'] == benchmarks
    
    def test_baseline_comparison(self, baseline_dir):
        """ベースライン比較のテスト"""
        baseline_file = baseline_dir / "baseline.json"
        baseline = PerformanceBaseline(baseline_file)
        
        # 初期ベースライン
        old_benchmarks = {
            'write_ops': 10000.0,
            'read_ops': 15000.0,
        }
        baseline.save_baseline(old_benchmarks)
        
        # 改善したケース
        new_benchmarks_improved = {
            'write_ops': 11000.0,  # 10%改善
            'read_ops': 16500.0,   # 10%改善
        }
        result = baseline.compare(new_benchmarks_improved, threshold=0.01)
        
        assert len(result['improvements']) == 2
        assert len(result['regressions']) == 0
        assert not result['has_regression']
        
        # 悪化したケース
        new_benchmarks_regressed = {
            'write_ops': 9000.0,   # 10%悪化
            'read_ops': 13500.0,   # 10%悪化
        }
        result = baseline.compare(new_benchmarks_regressed, threshold=0.01)
        
        assert len(result['regressions']) == 2
        assert len(result['improvements']) == 0
        assert result['has_regression']
        
        # 変化なし
        new_benchmarks_same = {
            'write_ops': 10050.0,  # 0.5%改善（閾値内）
            'read_ops': 14950.0,   # 0.33%悪化（閾値内）
        }
        result = baseline.compare(new_benchmarks_same, threshold=0.01)
        
        assert len(result['unchanged']) == 2
        assert not result['has_regression']


class TestPerformanceHistory:
    """パフォーマンス履歴のテスト"""
    
    def test_history_add_and_load(self, baseline_dir):
        """履歴の追加と読み込み"""
        history_file = baseline_dir / "history.json"
        history = PerformanceHistory(history_file)
        
        # エントリ追加
        benchmarks1 = {'write_ops': 10000.0, 'read_ops': 15000.0}
        history.add_entry(benchmarks1, metadata={'commit': 'abc123'})
        
        benchmarks2 = {'write_ops': 11000.0, 'read_ops': 16000.0}
        history.add_entry(benchmarks2, metadata={'commit': 'def456'})
        
        # 読み込み確認
        history2 = PerformanceHistory(history_file)
        assert len(history2.history) == 2
        assert history2.history[0]['benchmarks'] == benchmarks1
        assert history2.history[1]['benchmarks'] == benchmarks2
    
    def test_history_max_entries(self, baseline_dir):
        """履歴の最大件数制限"""
        history_file = baseline_dir / "history.json"
        history = PerformanceHistory(history_file)
        
        # 150件追加
        for i in range(150):
            benchmarks = {'write_ops': 10000.0 + i}
            history.add_entry(benchmarks)
        
        # 最新100件のみ保持されることを確認
        history2 = PerformanceHistory(history_file)
        assert len(history2.history) == 100
        assert history2.history[-1]['benchmarks']['write_ops'] == 10149.0


class TestRegressionDetection:
    """回帰検出のテスト"""
    
    def test_no_regression(self, temp_db_path, baseline_dir):
        """回帰なしのケース"""
        baseline_file = baseline_dir / "baseline.json"
        baseline = PerformanceBaseline(baseline_file)
        
        # ベースライン確立
        old_results = run_benchmark(DictSQLiteV2, temp_db_path, num_items=100)
        baseline.save_baseline(old_results)
        
        # クリーンアップ
        for ext in ['', '-wal', '-shm']:
            file_path = Path(temp_db_path + ext)
            if file_path.exists():
                file_path.unlink()
        
        # 再実行
        new_results = run_benchmark(DictSQLiteV2, temp_db_path, num_items=100)
        
        # 比較（多少の変動は許容）
        comparison = baseline.compare(new_results, threshold=0.20)  # 20%の変動を許容
        
        # 大幅な悪化がないことを確認
        for regression in comparison['regressions']:
            assert regression['ratio'] > 0.5, f"Major regression detected: {regression}"

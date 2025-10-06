"""ベンチマークとパフォーマンスベースライン管理"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PerformanceBaseline:
    """パフォーマンスベースラインの管理
    
    現在のパフォーマンスを記録し、過去のベースラインと比較する。
    1%以上の悪化を検出する。
    """
    
    def __init__(self, baseline_file: Path):
        """
        Args:
            baseline_file: ベースラインを保存するJSONファイルのパス
        """
        self.baseline_file = baseline_file
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        self.current_baseline = self.load_baseline()
    
    def load_baseline(self) -> Dict[str, Any]:
        """既存のベースラインを読み込み
        
        Returns:
            ベースライン情報の辞書
        """
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load baseline: {e}")
        
        return {
            'version': '2.0.0',
            'created_at': datetime.now().isoformat(),
            'benchmarks': {}
        }
    
    def save_baseline(self, benchmarks: Dict[str, float]) -> None:
        """新しいベースラインを保存
        
        Args:
            benchmarks: ベンチマーク結果の辞書（キー: ベンチマーク名, 値: ops/sec）
        """
        self.current_baseline['benchmarks'] = benchmarks
        self.current_baseline['updated_at'] = datetime.now().isoformat()
        
        with open(self.baseline_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_baseline, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Baseline saved to {self.baseline_file}")
    
    def compare(self, new_benchmarks: Dict[str, float], threshold: float = 0.01) -> Dict[str, Any]:
        """現在のパフォーマンスとベースラインを比較
        
        Args:
            new_benchmarks: 新しいベンチマーク結果
            threshold: 悪化許容率（デフォルト1% = 0.01）
            
        Returns:
            比較結果の辞書 {
                'regressions': [...],  # 悪化したベンチマーク
                'improvements': [...],  # 改善したベンチマーク
                'unchanged': [...],     # 変化なし
                'has_regression': bool
            }
        """
        baseline_benchmarks = self.current_baseline.get('benchmarks', {})
        
        regressions = []
        improvements = []
        unchanged = []
        
        for name, new_value in new_benchmarks.items():
            if name not in baseline_benchmarks:
                # 新しいベンチマーク
                continue
            
            old_value = baseline_benchmarks[name]
            ratio = new_value / old_value if old_value > 0 else 1.0
            change_pct = (ratio - 1.0) * 100
            
            if ratio < (1.0 - threshold):
                # 悪化
                regressions.append({
                    'name': name,
                    'old': old_value,
                    'new': new_value,
                    'ratio': ratio,
                    'change_pct': change_pct
                })
            elif ratio > (1.0 + threshold):
                # 改善
                improvements.append({
                    'name': name,
                    'old': old_value,
                    'new': new_value,
                    'ratio': ratio,
                    'change_pct': change_pct
                })
            else:
                # ほぼ同等
                unchanged.append({
                    'name': name,
                    'old': old_value,
                    'new': new_value,
                    'ratio': ratio,
                    'change_pct': change_pct
                })
        
        return {
            'regressions': regressions,
            'improvements': improvements,
            'unchanged': unchanged,
            'has_regression': len(regressions) > 0
        }


def run_benchmark(db_class, db_path: str, num_items: int = 1000) -> Dict[str, float]:
    """ベンチマークを実行
    
    Args:
        db_class: テスト対象のDBクラス
        db_path: DBファイルパス
        num_items: テスト項目数
        
    Returns:
        ベンチマーク結果（ops/sec）
    """
    results = {}
    
    # 書き込みベンチマーク
    db = db_class(db_path)
    start = time.perf_counter()
    for i in range(num_items):
        db[f'key_{i}'] = f'value_{i}_' + 'x' * 50
    write_time = time.perf_counter() - start
    results['write_ops'] = num_items / write_time if write_time > 0 else 0
    db.close()
    
    # 読み込みベンチマーク
    db = db_class(db_path)
    start = time.perf_counter()
    for i in range(num_items):
        _ = db[f'key_{i}']
    read_time = time.perf_counter() - start
    results['read_ops'] = num_items / read_time if read_time > 0 else 0
    db.close()
    
    # バルク書き込みベンチマーク
    bulk_data = {f'bulk_{i}': f'value_{i}' for i in range(num_items)}
    db = db_class(db_path)
    start = time.perf_counter()
    db.bulk_insert(bulk_data)
    bulk_time = time.perf_counter() - start
    results['bulk_write_ops'] = num_items / bulk_time if bulk_time > 0 else 0
    db.close()
    
    return results


class PerformanceHistory:
    """パフォーマンス履歴の管理"""
    
    def __init__(self, history_file: Path):
        """
        Args:
            history_file: 履歴を保存するJSONファイルのパス
        """
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history = self.load_history()
    
    def load_history(self) -> List[Dict[str, Any]]:
        """履歴を読み込み"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load history: {e}")
        
        return []
    
    def add_entry(self, benchmarks: Dict[str, float], metadata: Dict[str, Any] = None) -> None:
        """履歴にエントリを追加
        
        Args:
            benchmarks: ベンチマーク結果
            metadata: 追加のメタデータ
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'benchmarks': benchmarks,
        }
        
        if metadata:
            entry['metadata'] = metadata
        
        self.history.append(entry)
        
        # 最新100件のみ保持
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

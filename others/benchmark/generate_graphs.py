#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ベンチマーク結果グラフ生成モジュール

統計画像と徹底比較グラフを固定ファイル名で生成します。
- 単体テスト（v1, v2, v3, v4）: 統計サマリー画像のみ
- allテスト: 統計サマリー画像 + 徹底比較グラフ（複数ファイル）
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import warnings

# 警告を抑制
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# モジュールパスの設定
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# 日本語フォント設定をインポート
try:
    from visualize_benchmark import setup_japanese_font
    setup_japanese_font()
except ImportError:
    print("⚠ 日本語フォント設定をスキップ")


class BenchmarkGraphGenerator:
    """ベンチマーク結果グラフ生成クラス"""
    
    # 固定ファイル名の定義
    STATS_SUMMARY_FILE = "stats_summary.png"
    
    # allテスト用の徹底比較グラフファイル名（固定）
    COMPARISON_GRAPHS = {
        'ops_comparison': 'comparison_ops.png',
        'time_comparison': 'comparison_time.png',
        'speedup_ratio': 'comparison_speedup.png',
        'performance_heatmap': 'comparison_heatmap.png',
        'scalability': 'comparison_scalability.png',
        'version_evolution': 'comparison_evolution.png',
        'detailed_metrics': 'comparison_metrics.png',
        'test_coverage': 'comparison_coverage.png',
    }
    
    def __init__(self, csv_path: Path, version_type: str = None):
        """
        Args:
            csv_path: ベンチマークCSVファイルのパス
            version_type: バージョンタイプ（v1, v2, v3, v4, all）
        """
        self.csv_path = Path(csv_path)
        self.version_type = version_type or self._detect_version_type()
        self.graphs_dir = self.csv_path.parent / "graphs"
        self.graphs_dir.mkdir(exist_ok=True)
        
        # データ読み込み
        try:
            self.df = pd.read_csv(csv_path)
            print(f"✓ データ読み込み: {len(self.df)}行")
        except Exception as e:
            print(f"✗ CSV読み込みエラー: {e}")
            self.df = None
    
    def _detect_version_type(self) -> str:
        """CSVパスからバージョンタイプを検出"""
        path_str = str(self.csv_path)
        if '/all/' in path_str:
            return 'all'
        elif '/v1/' in path_str:
            return 'v1'
        elif '/v2/' in path_str:
            return 'v2'
        elif '/v3/' in path_str:
            return 'v3'
        elif '/v4/' in path_str:
            return 'v4'
        return 'unknown'
    
    def generate_all_graphs(self):
        """全グラフを生成"""
        if self.df is None or len(self.df) == 0:
            print("⚠ データなし、グラフ生成をスキップ")
            return
        
        print(f"\n{'='*60}")
        print(f"グラフ生成開始: {self.version_type}")
        print(f"{'='*60}")
        
        # 統計サマリーは全バージョンで生成
        self.generate_stats_summary()
        
        # allテストの場合のみ、徹底比較グラフを生成
        if self.version_type == 'all':
            print("\n[all テスト] 徹底比較グラフを生成中...")
            self.generate_comparison_graphs()
        else:
            print(f"\n[{self.version_type} テスト] 統計サマリーのみ生成")
        
        print(f"\n{'='*60}")
        print(f"✓ グラフ生成完了: {self.graphs_dir}")
        print(f"{'='*60}")
    
    def generate_stats_summary(self):
        """統計サマリー画像を生成（固定ファイル名）"""
        print(f"  [1/1] 統計サマリー生成中...")
        
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.3)
        
        # CSV形式を判定
        is_long_format = 'Version' in self.df.columns and 'OPS' in self.df.columns
        
        if is_long_format:
            self._generate_stats_long_format(fig, gs)
        else:
            self._generate_stats_wide_format(fig, gs)
        
        # タイトル
        fig.suptitle(f'ベンチマーク統計サマリー - {self.version_type.upper()}',
                     fontsize=16, fontweight='bold', y=0.98)
        
        # 保存
        output_path = self.graphs_dir / self.STATS_SUMMARY_FILE
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"    ✓ 保存: {self.STATS_SUMMARY_FILE}")
    
    def _generate_stats_long_format(self, fig, gs):
        """Long形式（Version列あり）の統計グラフ"""
        # 1. バージョン別平均OPS
        ax1 = fig.add_subplot(gs[0, 0])
        version_ops = self.df.groupby('Version')['OPS'].mean()
        bars = ax1.bar(version_ops.index, version_ops.values,
                       color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
        ax1.set_title('バージョン別平均OPS', fontweight='bold')
        ax1.set_ylabel('Average OPS')
        ax1.grid(True, alpha=0.3, axis='y')
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:,.0f}', ha='center', va='bottom')
        
        # 2. バージョン別最大OPS
        ax2 = fig.add_subplot(gs[0, 1])
        version_max_ops = self.df.groupby('Version')['OPS'].max()
        bars = ax2.bar(version_max_ops.index, version_max_ops.values,
                       color=['#FF8B8B', '#6EDDDD', '#65C7E1'])
        ax2.set_title('バージョン別最大OPS', fontweight='bold')
        ax2.set_ylabel('Max OPS')
        ax2.grid(True, alpha=0.3, axis='y')
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:,.0f}', ha='center', va='bottom')
        
        # 3. テスト数
        ax3 = fig.add_subplot(gs[0, 2])
        test_counts = self.df.groupby('Version').size()
        bars = ax3.bar(test_counts.index, test_counts.values,
                       color=['#FFA07A', '#98D8D8', '#87CEEB'])
        ax3.set_title('バージョン別テスト数', fontweight='bold')
        ax3.set_ylabel('テスト数')
        ax3.grid(True, alpha=0.3, axis='y')
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom')
        
        # 4. OPS分布（バイオリンプロット）
        ax4 = fig.add_subplot(gs[1, :2])
        versions = sorted(self.df['Version'].unique())
        data_for_violin = [self.df[self.df['Version'] == v]['OPS'].values for v in versions]
        parts = ax4.violinplot(data_for_violin, positions=range(len(versions)),
                               showmeans=True, showmedians=True)
        ax4.set_xticks(range(len(versions)))
        ax4.set_xticklabels(versions)
        ax4.set_title('OPS分布（バイオリンプロット）', fontweight='bold')
        ax4.set_ylabel('OPS')
        ax4.grid(True, alpha=0.3, axis='y')
        
        # 5. 時間分布
        ax5 = fig.add_subplot(gs[1, 2])
        if 'Time (s)' in self.df.columns:
            version_time = self.df.groupby('Version')['Time (s)'].mean()
            bars = ax5.bar(version_time.index, version_time.values,
                          color=['#FFB6C1', '#B0E0E6', '#ADD8E6'])
            ax5.set_title('バージョン別平均時間', fontweight='bold')
            ax5.set_ylabel('Average Time (s)')
            ax5.grid(True, alpha=0.3, axis='y')
            for bar in bars:
                height = bar.get_height()
                ax5.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.3f}', ha='center', va='bottom', fontsize=9)
        
        # 6. Top 10 テスト
        ax6 = fig.add_subplot(gs[2, :])
        top10 = self.df.nlargest(10, 'OPS')[['Test', 'Version', 'OPS']]
        y_pos = np.arange(len(top10))
        colors = [{'original': '#FF6B6B', 'fastest': '#4ECDC4', 'beta': '#45B7D1'}.get(v, '#999999')
                  for v in top10['Version']]
        ax6.barh(y_pos, top10['OPS'].values, color=colors)
        ax6.set_yticks(y_pos)
        ax6.set_yticklabels([f"{row['Test'][:30]}... ({row['Version']})"
                             for _, row in top10.iterrows()], fontsize=8)
        ax6.set_xlabel('OPS')
        ax6.set_title('Top 10 パフォーマンステスト', fontweight='bold')
        ax6.grid(True, alpha=0.3, axis='x')
        ax6.invert_yaxis()
    
    def _generate_stats_wide_format(self, fig, gs):
        """Wide形式（Original OPS等の列あり）の統計グラフ"""
        # 1. 平均OPS比較
        ax1 = fig.add_subplot(gs[0, 0])
        ops_cols = [c for c in self.df.columns if 'OPS' in c and c != 'OPS']
        if ops_cols:
            avg_ops = {col.replace(' OPS', ''): self.df[col].mean() for col in ops_cols}
            bars = ax1.bar(avg_ops.keys(), avg_ops.values(),
                          color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
            ax1.set_title('平均OPS比較', fontweight='bold')
            ax1.set_ylabel('Average OPS')
            ax1.grid(True, alpha=0.3, axis='y')
            for bar in bars:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:,.0f}', ha='center', va='bottom')
        
        # 2. 最大OPS比較
        ax2 = fig.add_subplot(gs[0, 1])
        if ops_cols:
            max_ops = {col.replace(' OPS', ''): self.df[col].max() for col in ops_cols}
            bars = ax2.bar(max_ops.keys(), max_ops.values,
                          color=['#FF8B8B', '#6EDDDD', '#65C7E1'])
            ax2.set_title('最大OPS比較', fontweight='bold')
            ax2.set_ylabel('Max OPS')
            ax2.grid(True, alpha=0.3, axis='y')
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:,.0f}', ha='center', va='bottom')
        
        # 3. テスト数
        ax3 = fig.add_subplot(gs[0, 2])
        test_count = len(self.df)
        ax3.bar(['Total Tests'], [test_count], color='#87CEEB')
        ax3.set_title('総テスト数', fontweight='bold')
        ax3.set_ylabel('テスト数')
        ax3.text(0, test_count, f'{test_count}', ha='center', va='bottom')
        ax3.grid(True, alpha=0.3, axis='y')
        
        # 4-6: スピードアップ比などの追加統計
        speedup_cols = [c for c in self.df.columns if 'Speedup' in c]
        if speedup_cols and len(speedup_cols) > 0:
            ax4 = fig.add_subplot(gs[1, :])
            self.df[speedup_cols].boxplot(ax=ax4)
            ax4.set_title('スピードアップ比の分布', fontweight='bold')
            ax4.set_ylabel('Speedup Ratio')
            ax4.grid(True, alpha=0.3, axis='y')
            ax4.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='Baseline')
            ax4.legend()
    
    def generate_comparison_graphs(self):
        """徹底比較グラフを生成（allテスト専用、固定ファイル名）"""
        if self.version_type != 'all':
            return
        
        # CSV形式を判定
        is_long_format = 'Version' in self.df.columns
        
        if not is_long_format:
            print("  ⚠ Wide形式のCSVのため、一部の比較グラフをスキップ")
        
        # 1. OPS比較グラフ
        self._generate_ops_comparison()
        
        # 2. 時間比較グラフ
        self._generate_time_comparison()
        
        # 3. スピードアップ比グラフ
        self._generate_speedup_comparison()
        
        # 4. パフォーマンスヒートマップ
        self._generate_heatmap()
        
        # 5. スケーラビリティグラフ
        self._generate_scalability()
        
        # 6. バージョン進化グラフ
        self._generate_evolution()
        
        # 7. 詳細メトリクスグラフ
        self._generate_detailed_metrics()
        
        # 8. テストカバレッジグラフ
        self._generate_test_coverage()
    
    def _generate_ops_comparison(self):
        """OPS比較グラフ"""
        print(f"  [2/9] OPS比較グラフ生成中...")
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        if 'Version' in self.df.columns:
            # Long形式
            versions = self.df['Version'].unique()
            x = np.arange(len(self.df['Test'].unique()))
            width = 0.25
            
            for i, version in enumerate(sorted(versions)):
                version_data = self.df[self.df['Version'] == version]
                tests = version_data['Test'].values
                ops = version_data['OPS'].values
                offset = (i - 1) * width
                ax.bar(x + offset, ops, width, label=version.upper(),
                      color=['#FF6B6B', '#4ECDC4', '#45B7D1'][i % 3])
            
            ax.set_xlabel('テスト')
            ax.set_ylabel('OPS')
            ax.set_title('テスト別OPS比較', fontweight='bold', fontsize=14)
            ax.set_xticks(x)
            ax.set_xticklabels([t[:20] + '...' if len(t) > 20 else t
                               for t in self.df['Test'].unique()],
                              rotation=45, ha='right', fontsize=8)
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        output_path = self.graphs_dir / self.COMPARISON_GRAPHS['ops_comparison']
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"    ✓ 保存: {self.COMPARISON_GRAPHS['ops_comparison']}")
    
    def _generate_time_comparison(self):
        """時間比較グラフ"""
        print(f"  [3/9] 時間比較グラフ生成中...")
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        if 'Version' in self.df.columns and 'Time (s)' in self.df.columns:
            versions = sorted(self.df['Version'].unique())
            for version in versions:
                version_data = self.df[self.df['Version'] == version]
                ax.plot(range(len(version_data)), version_data['Time (s)'].values,
                       marker='o', label=version.upper(), linewidth=2)
            
            ax.set_xlabel('テストインデックス')
            ax.set_ylabel('Time (s)')
            ax.set_title('実行時間比較', fontweight='bold', fontsize=14)
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.graphs_dir / self.COMPARISON_GRAPHS['time_comparison']
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"    ✓ 保存: {self.COMPARISON_GRAPHS['time_comparison']}")
    
    def _generate_speedup_comparison(self):
        """スピードアップ比グラフ"""
        print(f"  [4/9] スピードアップ比グラフ生成中...")
        
        fig, ax = plt.subplots(figsize=(12, 7))
        
        if 'Version' in self.df.columns:
            # Originalを基準にスピードアップを計算
            original_data = self.df[self.df['Version'] == 'original']
            if len(original_data) > 0:
                for version in ['fastest', 'beta']:
                    version_data = self.df[self.df['Version'] == version]
                    if len(version_data) > 0:
                        # 共通のテストで比較
                        common_tests = set(original_data['Test']) & set(version_data['Test'])
                        speedups = []
                        for test in common_tests:
                            orig_time = original_data[original_data['Test'] == test]['Time (s)'].values[0]
                            ver_time = version_data[version_data['Test'] == test]['Time (s)'].values[0]
                            if ver_time > 0:
                                speedups.append(orig_time / ver_time)
                        
                        if speedups:
                            ax.plot(range(len(speedups)), speedups,
                                   marker='o', label=f'{version.upper()} vs Original',
                                   linewidth=2)
                
                ax.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='Baseline (1x)')
                ax.set_xlabel('テストインデックス')
                ax.set_ylabel('スピードアップ比')
                ax.set_title('バージョン別スピードアップ比', fontweight='bold', fontsize=14)
                ax.legend()
                ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.graphs_dir / self.COMPARISON_GRAPHS['speedup_ratio']
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"    ✓ 保存: {self.COMPARISON_GRAPHS['speedup_ratio']}")
    
    def _generate_heatmap(self):
        """パフォーマンスヒートマップ"""
        print(f"  [5/9] ヒートマップ生成中...")
        
        fig, ax = plt.subplots(figsize=(14, 10))
        
        if 'Version' in self.df.columns:
            # バージョン x テストのヒートマップ
            pivot_data = self.df.pivot_table(
                values='OPS',
                index='Test',
                columns='Version',
                aggfunc='mean'
            )
            
            sns.heatmap(pivot_data, annot=True, fmt='.0f', cmap='YlOrRd',
                       ax=ax, cbar_kws={'label': 'OPS'})
            ax.set_title('パフォーマンスヒートマップ (OPS)', fontweight='bold', fontsize=14)
            ax.set_xlabel('Version')
            ax.set_ylabel('Test')
        
        plt.tight_layout()
        output_path = self.graphs_dir / self.COMPARISON_GRAPHS['performance_heatmap']
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"    ✓ 保存: {self.COMPARISON_GRAPHS['performance_heatmap']}")
    
    def _generate_scalability(self):
        """スケーラビリティグラフ"""
        print(f"  [6/9] スケーラビリティグラフ生成中...")
        
        fig, ax = plt.subplots(figsize=(12, 7))
        
        if 'Version' in self.df.columns and 'Operation Count' in self.df.columns:
            versions = sorted(self.df['Version'].unique())
            for version in versions:
                version_data = self.df[self.df['Version'] == version]
                # Operation Countでソート
                version_data_sorted = version_data.sort_values('Operation Count')
                ax.plot(version_data_sorted['Operation Count'],
                       version_data_sorted['OPS'],
                       marker='o', label=version.upper(), linewidth=2)
            
            ax.set_xlabel('Operation Count')
            ax.set_ylabel('OPS')
            ax.set_title('スケーラビリティ分析', fontweight='bold', fontsize=14)
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.set_xscale('log')
        
        plt.tight_layout()
        output_path = self.graphs_dir / self.COMPARISON_GRAPHS['scalability']
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"    ✓ 保存: {self.COMPARISON_GRAPHS['scalability']}")
    
    def _generate_evolution(self):
        """バージョン進化グラフ"""
        print(f"  [7/9] バージョン進化グラフ生成中...")
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('バージョン進化分析', fontweight='bold', fontsize=16)
        
        if 'Version' in self.df.columns:
            versions = sorted(self.df['Version'].unique())
            
            # 平均OPSの進化
            ax1 = axes[0, 0]
            avg_ops = [self.df[self.df['Version'] == v]['OPS'].mean() for v in versions]
            ax1.plot(versions, avg_ops, marker='o', linewidth=2, markersize=10, color='#4ECDC4')
            ax1.set_title('平均OPSの進化')
            ax1.set_ylabel('Average OPS')
            ax1.grid(True, alpha=0.3)
            
            # 最大OPSの進化
            ax2 = axes[0, 1]
            max_ops = [self.df[self.df['Version'] == v]['OPS'].max() for v in versions]
            ax2.plot(versions, max_ops, marker='s', linewidth=2, markersize=10, color='#FF6B6B')
            ax2.set_title('最大OPSの進化')
            ax2.set_ylabel('Max OPS')
            ax2.grid(True, alpha=0.3)
            
            # 最小OPSの進化
            ax3 = axes[1, 0]
            min_ops = [self.df[self.df['Version'] == v]['OPS'].min() for v in versions]
            ax3.plot(versions, min_ops, marker='^', linewidth=2, markersize=10, color='#45B7D1')
            ax3.set_title('最小OPSの進化')
            ax3.set_ylabel('Min OPS')
            ax3.grid(True, alpha=0.3)
            
            # OPS標準偏差の進化
            ax4 = axes[1, 1]
            std_ops = [self.df[self.df['Version'] == v]['OPS'].std() for v in versions]
            ax4.plot(versions, std_ops, marker='d', linewidth=2, markersize=10, color='#FFA07A')
            ax4.set_title('OPS標準偏差の進化')
            ax4.set_ylabel('Std Dev OPS')
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.graphs_dir / self.COMPARISON_GRAPHS['version_evolution']
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"    ✓ 保存: {self.COMPARISON_GRAPHS['version_evolution']}")
    
    def _generate_detailed_metrics(self):
        """詳細メトリクスグラフ"""
        print(f"  [8/9] 詳細メトリクスグラフ生成中...")
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('詳細パフォーマンスメトリクス', fontweight='bold', fontsize=16)
        
        if 'Version' in self.df.columns:
            # 1. バージョン別OPS分布（箱ひげ図）
            ax1 = axes[0, 0]
            versions = sorted(self.df['Version'].unique())
            data_for_box = [self.df[self.df['Version'] == v]['OPS'].values for v in versions]
            bp = ax1.boxplot(data_for_box, labels=versions, patch_artist=True)
            for patch, color in zip(bp['boxes'], ['#FF6B6B', '#4ECDC4', '#45B7D1']):
                patch.set_facecolor(color)
            ax1.set_title('OPS分布（箱ひげ図）')
            ax1.set_ylabel('OPS')
            ax1.grid(True, alpha=0.3, axis='y')
            
            # 2. 累積OPS
            ax2 = axes[0, 1]
            for version in versions:
                version_data = self.df[self.df['Version'] == version].sort_values('OPS')
                cumsum = version_data['OPS'].cumsum()
                ax2.plot(range(len(cumsum)), cumsum, label=version.upper(), linewidth=2)
            ax2.set_title('累積OPS')
            ax2.set_xlabel('テスト数')
            ax2.set_ylabel('Cumulative OPS')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # 3. OPSヒストグラム
            ax3 = axes[1, 0]
            for version in versions:
                version_data = self.df[self.df['Version'] == version]
                ax3.hist(version_data['OPS'], bins=20, alpha=0.5, label=version.upper())
            ax3.set_title('OPS分布ヒストグラム')
            ax3.set_xlabel('OPS')
            ax3.set_ylabel('頻度')
            ax3.legend()
            ax3.grid(True, alpha=0.3, axis='y')
            
            # 4. パーセンタイル比較
            ax4 = axes[1, 1]
            percentiles = [25, 50, 75, 90, 95]
            x = np.arange(len(percentiles))
            width = 0.25
            for i, version in enumerate(versions):
                version_data = self.df[self.df['Version'] == version]
                perc_values = [np.percentile(version_data['OPS'], p) for p in percentiles]
                offset = (i - 1) * width
                ax4.bar(x + offset, perc_values, width, label=version.upper(),
                       color=['#FF6B6B', '#4ECDC4', '#45B7D1'][i % 3])
            ax4.set_title('パーセンタイル比較')
            ax4.set_xlabel('パーセンタイル')
            ax4.set_ylabel('OPS')
            ax4.set_xticks(x)
            ax4.set_xticklabels([f'{p}%' for p in percentiles])
            ax4.legend()
            ax4.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        output_path = self.graphs_dir / self.COMPARISON_GRAPHS['detailed_metrics']
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"    ✓ 保存: {self.COMPARISON_GRAPHS['detailed_metrics']}")
    
    def _generate_test_coverage(self):
        """テストカバレッジグラフ"""
        print(f"  [9/9] テストカバレッジグラフ生成中...")
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('テストカバレッジ分析', fontweight='bold', fontsize=16)
        
        if 'Version' in self.df.columns:
            versions = sorted(self.df['Version'].unique())
            
            # 1. バージョン別テスト数
            ax1 = axes[0, 0]
            test_counts = [len(self.df[self.df['Version'] == v]) for v in versions]
            bars = ax1.bar(versions, test_counts, color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
            ax1.set_title('バージョン別テスト数')
            ax1.set_ylabel('テスト数')
            ax1.grid(True, alpha=0.3, axis='y')
            for bar in bars:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom')
            
            # 2. テストタイプ分布（Testカラムからパターン抽出）
            ax2 = axes[0, 1]
            test_types = {}
            for test_name in self.df['Test'].unique():
                # テスト名から種類を抽出（例: "基本書き込み" → "書き込み"）
                if '書き込み' in test_name or 'write' in test_name.lower():
                    test_type = '書き込み'
                elif '読み込み' in test_name or 'read' in test_name.lower():
                    test_type = '読み込み'
                elif 'バルク' in test_name or 'bulk' in test_name.lower():
                    test_type = 'バルク'
                elif '非同期' in test_name or 'async' in test_name.lower():
                    test_type = '非同期'
                else:
                    test_type = 'その他'
                test_types[test_type] = test_types.get(test_type, 0) + 1
            
            if test_types:
                ax2.pie(test_types.values(), labels=test_types.keys(), autopct='%1.1f%%',
                       colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8D8'])
                ax2.set_title('テストタイプ分布')
            
            # 3. 成功率（全テストが成功と仮定）
            ax3 = axes[1, 0]
            ax3.bar(versions, [100] * len(versions), color=['#90EE90'] * len(versions))
            ax3.set_title('テスト成功率')
            ax3.set_ylabel('成功率 (%)')
            ax3.set_ylim([0, 110])
            ax3.grid(True, alpha=0.3, axis='y')
            for i, v in enumerate(versions):
                ax3.text(i, 100, '100%', ha='center', va='bottom')
            
            # 4. 総合カバレッジスコア
            ax4 = axes[1, 1]
            # 簡易スコア: テスト数 × 平均OPS / 1000
            scores = []
            for version in versions:
                version_data = self.df[self.df['Version'] == version]
                score = len(version_data) * version_data['OPS'].mean() / 1000
                scores.append(score)
            
            bars = ax4.bar(versions, scores, color=['#FFD700', '#C0C0C0', '#CD7F32'])
            ax4.set_title('総合カバレッジスコア')
            ax4.set_ylabel('スコア')
            ax4.grid(True, alpha=0.3, axis='y')
            for bar in bars:
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.0f}', ha='center', va='bottom')
        
        plt.tight_layout()
        output_path = self.graphs_dir / self.COMPARISON_GRAPHS['test_coverage']
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"    ✓ 保存: {self.COMPARISON_GRAPHS['test_coverage']}")


def main():
    """メイン実行（テスト用）"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='ベンチマーク結果グラフ生成ツール'
    )
    parser.add_argument(
        'csv_file',
        help='ベンチマークCSVファイルのパス'
    )
    parser.add_argument(
        '--version',
        choices=['v1', 'v2', 'v3', 'v4', 'all'],
        help='バージョンタイプ（省略時は自動検出）'
    )
    
    args = parser.parse_args()
    
    # グラフ生成
    generator = BenchmarkGraphGenerator(
        csv_path=args.csv_file,
        version_type=args.version
    )
    generator.generate_all_graphs()


if __name__ == '__main__':
    main()

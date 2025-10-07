#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バージョン間比較ツール

複数バージョンのベンチマーク結果を比較し、
進化の過程を可視化します。
"""

import sys
from pathlib import Path
import warnings

# 警告を抑制
warnings.filterwarnings('ignore', category=FutureWarning, module='seaborn')
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

# モジュールパスの設定
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# 日本語フォント設定を最初に実行（matplotlibインポート前）
try:
    from visualize_benchmark import setup_japanese_font
    setup_japanese_font()
except ImportError:
    print("⚠ visualize_benchmark.pyが見つかりません。日本語フォント設定をスキップします。")

# matplotlibとseabornはフォント設定後にインポート
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
from typing import List, Dict

from version_manager import VersionManager

# マイナス記号の文字化け防止（フォント設定後に再適用）
plt.rcParams['axes.unicode_minus'] = False


class VersionComparator:
    """バージョン間比較クラス"""
    
    def __init__(self, version_manager: VersionManager = None):
        """
        Args:
            version_manager: VersionManagerインスタンス（Noneの場合は新規作成）
        """
        if version_manager is None:
            version_manager = VersionManager()
        
        self.version_manager = version_manager
        self.versions = self.version_manager.list_available_versions()
        self.comparison_dir = self.version_manager.comparison_dir
        self.comparison_dir.mkdir(exist_ok=True)
        
        # データを読み込み
        self.version_data = {}
        self._load_all_versions()
    
    def _load_all_versions(self):
        """全バージョンのデータを読み込み"""
        print(f"\n利用可能なバージョン: {len(self.versions)}個")
        
        for version in self.versions:
            paths = self.version_manager.get_version_paths(version)
            
            if paths['csv'].exists():
                try:
                    df = pd.read_csv(paths['csv'])
                    self.version_data[version] = {
                        'df': df,
                        'csv_path': paths['csv'],
                        'graphs_dir': paths['graphs_dir']
                    }
                    print(f"  ✓ {version}: {len(df)}件のテスト結果")
                except Exception as e:
                    print(f"  ⚠ {version}: CSV読み込みエラー - {e}")
            else:
                print(f"  ⚠ {version}: CSVファイルなし")
    
    def generate_version_timeline(self):
        """バージョン間のタイムライン比較グラフを生成"""
        if not self.version_data:
            print("⚠ 比較可能なバージョンデータがありません")
            return
        
        print("\n[1/4] バージョンタイムライン比較グラフを生成中...")
        
        # 各バージョンの平均パフォーマンスを計算
        version_stats = []
        
        for version, data in self.version_data.items():
            df = data['df']
            
            # CSV形式を判定
            if 'Version' in df.columns and 'OPS' in df.columns:
                # Long形式（fast_comprehensive_benchmark.py）
                for v in ['original', 'fastest', 'beta']:
                    v_df = df[df['Version'] == v]
                    if not v_df.empty:
                        version_stats.append({
                            'version': version,
                            'implementation': v,
                            'avg_ops': v_df['OPS'].mean(),
                            'max_ops': v_df['OPS'].max(),
                            'min_ops': v_df['OPS'].min()
                        })
            elif 'Original OPS' in df.columns:
                # Wide形式（comprehensive_benchmark.py）
                version_stats.append({
                    'version': version,
                    'implementation': 'original',
                    'avg_ops': df['Original OPS'].mean(),
                    'max_ops': df['Original OPS'].max(),
                    'min_ops': df['Original OPS'].min()
                })
                version_stats.append({
                    'version': version,
                    'implementation': 'fastest',
                    'avg_ops': df['Fastest OPS'].mean(),
                    'max_ops': df['Fastest OPS'].max(),
                    'min_ops': df['Fastest OPS'].min()
                })
                version_stats.append({
                    'version': version,
                    'implementation': 'beta',
                    'avg_ops': df['Beta OPS'].mean(),
                    'max_ops': df['Beta OPS'].max(),
                    'min_ops': df['Beta OPS'].min()
                })
        
        if not version_stats:
            print("⚠ 統計データの計算に失敗しました")
            return
        
        stats_df = pd.DataFrame(version_stats)
        
        # グラフ生成
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('バージョン間パフォーマンス比較', fontsize=16, fontweight='bold')
        
        # 1. 実装別平均OPS
        ax = axes[0, 0]
        pivot = stats_df.pivot_table(values='avg_ops', index='version', columns='implementation')
        pivot.plot(kind='bar', ax=ax)
        ax.set_title('実装別平均OPS', fontsize=12, fontweight='bold')
        ax.set_ylabel('Average OPS')
        ax.set_xlabel('Version')
        ax.legend(title='Implementation')
        ax.grid(True, alpha=0.3)
        
        # 2. 最大OPS比較
        ax = axes[0, 1]
        pivot = stats_df.pivot_table(values='max_ops', index='version', columns='implementation')
        pivot.plot(kind='bar', ax=ax)
        ax.set_title('実装別最大OPS', fontsize=12, fontweight='bold')
        ax.set_ylabel('Max OPS')
        ax.set_xlabel('Version')
        ax.legend(title='Implementation')
        ax.grid(True, alpha=0.3)
        
        # 3. Beta版の進化
        ax = axes[1, 0]
        beta_stats = stats_df[stats_df['implementation'] == 'beta']
        if not beta_stats.empty:
            beta_stats.plot(x='version', y='avg_ops', kind='line', ax=ax, marker='o', color='#45B7D1')
            ax.set_title('Beta版の進化（平均OPS）', fontsize=12, fontweight='bold')
            ax.set_ylabel('Average OPS')
            ax.set_xlabel('Version')
            ax.grid(True, alpha=0.3)
        
        # 4. 実装間のスピードアップ比
        ax = axes[1, 1]
        speedup_data = []
        for version in stats_df['version'].unique():
            v_df = stats_df[stats_df['version'] == version]
            original_ops = v_df[v_df['implementation'] == 'original']['avg_ops'].values
            beta_ops = v_df[v_df['implementation'] == 'beta']['avg_ops'].values
            
            if len(original_ops) > 0 and len(beta_ops) > 0:
                speedup = beta_ops[0] / original_ops[0]
                speedup_data.append({'version': version, 'speedup': speedup})
        
        if speedup_data:
            speedup_df = pd.DataFrame(speedup_data)
            speedup_df.plot(x='version', y='speedup', kind='bar', ax=ax, color='#FF6B6B')
            ax.set_title('Beta版 vs Original版 スピードアップ比', fontsize=12, fontweight='bold')
            ax.set_ylabel('Speedup (Beta/Original)')
            ax.set_xlabel('Version')
            ax.axhline(y=1.0, color='black', linestyle='--', alpha=0.5)
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.comparison_dir / f"version_comparison_{timestamp}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ 保存: {output_path}")
        return output_path
    
    def generate_comparison_report(self):
        """バージョン比較レポートを生成"""
        print("\n[2/4] バージョン比較レポートを生成中...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.comparison_dir / f"comparison_report_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# ベンチマーク バージョン比較レポート\n\n")
            f.write(f"**作成日時:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**比較バージョン数:** {len(self.versions)}\n\n")
            
            f.write("## 比較対象バージョン\n\n")
            for i, version in enumerate(self.versions, 1):
                f.write(f"{i}. **{version}**\n")
                if version in self.version_data:
                    df = self.version_data[version]['df']
                    f.write(f"   - テスト数: {len(df)}件\n")
                    
                    # 平均OPSを計算
                    if 'OPS' in df.columns:
                        f.write(f"   - 平均OPS: {df['OPS'].mean():,.2f}\n")
                    elif 'Beta OPS' in df.columns:
                        f.write(f"   - Beta平均OPS: {df['Beta OPS'].mean():,.2f}\n")
                
                metadata = self.version_manager.get_version_metadata(version)
                if metadata:
                    latest_run = metadata[-1] if metadata else None
                    if latest_run:
                        f.write(f"   - 最終実行: {latest_run['timestamp']}\n")
                f.write("\n")
            
            f.write("## ファイル場所\n\n")
            for version in self.versions:
                paths = self.version_manager.get_version_paths(version)
                f.write(f"### {version}\n\n")
                f.write(f"- CSV: `{paths['csv'].relative_to(self.version_manager.results_dir.parent)}`\n")
                f.write(f"- JSON: `{paths['json'].relative_to(self.version_manager.results_dir.parent)}`\n")
                f.write(f"- グラフ: `{paths['graphs_dir'].relative_to(self.version_manager.results_dir.parent)}/`\n")
                f.write("\n")
            
            f.write("## 比較グラフ\n\n")
            f.write(f"バージョン間比較グラフは `{self.comparison_dir.relative_to(self.version_manager.results_dir.parent)}/` に保存されています。\n\n")
        
        print(f"  ✓ 保存: {report_path}")
        return report_path
    
    def create_version_index(self):
        """バージョン一覧インデックスを生成"""
        print("\n[3/4] バージョンインデックスを生成中...")
        
        index_path = self.version_manager.results_dir / "VERSION_INDEX.md"
        
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("# ベンチマーク結果 バージョンインデックス\n\n")
            f.write(f"**最終更新:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**総バージョン数:** {len(self.versions)}\n\n")
            
            f.write("## バージョン一覧\n\n")
            f.write("| バージョン | テスト数 | 最終実行日時 | ファイル |\n")
            f.write("|------------|----------|--------------|----------|\n")
            
            for version in sorted(self.versions, reverse=True):
                test_count = "N/A"
                last_run = "N/A"
                
                if version in self.version_data:
                    test_count = str(len(self.version_data[version]['df']))
                
                metadata = self.version_manager.get_version_metadata(version)
                if metadata:
                    latest = metadata[-1] if metadata else None
                    if latest:
                        last_run = latest['timestamp'][:10]  # 日付部分のみ
                
                paths = self.version_manager.get_version_paths(version)
                rel_path = paths['dir'].relative_to(self.version_manager.results_dir.parent)
                
                f.write(f"| `{version}` | {test_count} | {last_run} | `{rel_path}/` |\n")
            
            f.write("\n## 比較レポート\n\n")
            comparison_files = sorted(self.comparison_dir.glob('comparison_report_*.md'))
            if comparison_files:
                latest_comparison = comparison_files[-1]
                rel_path = latest_comparison.relative_to(self.version_manager.results_dir.parent)
                f.write(f"最新の比較レポート: `{rel_path}`\n\n")
            else:
                f.write("比較レポートはまだ生成されていません。\n\n")
        
        print(f"  ✓ 保存: {index_path}")
        return index_path
    
    def generate_all_comparisons(self):
        """すべての比較レポートとグラフを生成"""
        print("\n" + "=" * 80)
        print("バージョン間比較ツール")
        print("=" * 80)
        
        if not self.version_data:
            print("\n⚠ 比較可能なバージョンデータがありません")
            print("   バージョン間比較を生成するには、少なくとも2つのバージョンのベンチマーク結果が必要です。")
            print("   ベンチマークを複数回実行してから、再度このツールを実行してください。")
            return
        
        if len(self.version_data) < 2:
            print(f"\n⚠ バージョン間比較には少なくとも2つのバージョンが必要です（現在: {len(self.version_data)}個）")
            print("   別のバージョンでベンチマークを実行してから、再度このツールを実行してください。")
            return
        
        print(f"\n{len(self.version_data)}個のバージョンを比較します")
        
        # グラフ生成
        graph_path = self.generate_version_timeline()
        
        # レポート生成
        report_path = self.generate_comparison_report()
        
        # インデックス生成
        index_path = self.create_version_index()
        
        print("\n[4/4] 完了サマリー")
        print(f"  - 比較グラフ: {graph_path}")
        print(f"  - 比較レポート: {report_path}")
        print(f"  - バージョンインデックス: {index_path}")
        
        print("\n" + "=" * 80)
        print("バージョン比較完了!")
        print("=" * 80)


def main():
    """メイン実行"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='DictSQLite ベンチマーク バージョン間比較ツール'
    )
    parser.add_argument(
        '--versions',
        nargs='*',
        help='比較するバージョンのリスト（指定しない場合は全バージョン）'
    )
    
    args = parser.parse_args()
    
    # バージョンマネージャー初期化
    version_manager = VersionManager()
    
    # 比較ツール初期化
    comparator = VersionComparator(version_manager)
    
    # すべての比較を生成
    comparator.generate_all_comparisons()


if __name__ == '__main__':
    main()

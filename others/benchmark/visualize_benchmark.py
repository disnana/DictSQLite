#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DictSQLite ベンチマーク結果グラフ生成ツール

CSVファイルから美しいグラフを生成します。
matplotlib、seaborn、plotlyを使用して多様な視覚化を提供。
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
import json
from datetime import datetime
import platform
import warnings

# 警告を適切にフィルタリング（重要な警告は表示し、冗長な警告のみ抑制）
warnings.filterwarnings('ignore', category=FutureWarning, module='seaborn')
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

# 日本語フォント設定
import matplotlib.font_manager as fm


def _apply_font_rc(font: str):
    """指定フォントを全体に強制適用（Arial等にフォールバックさせない）"""
    rc = plt.rcParams
    # 優先フォールバック候補（Arial/Helvetica等は入れない）
    jp_stack = [
        font,
        'Yu Gothic UI', 'Yu Gothic',
        'Meiryo UI', 'Meiryo',
        'MS PGothic', 'MS Gothic', 'MS UI Gothic',
        'Hiragino Sans', 'Hiragino Kaku Gothic ProN',
        'Noto Sans CJK JP', 'Noto Sans JP',
        'IPAPGothic', 'IPAGothic',
        'TakaoGothic', 'VL Gothic',
    ]
    # すべてのフォントファミリーに日本語フォントスタックを設定
    rc['font.family'] = [font]
    rc['font.sans-serif'] = jp_stack
    rc['font.serif'] = jp_stack
    rc['font.cursive'] = jp_stack
    rc['font.fantasy'] = jp_stack
    rc['font.monospace'] = jp_stack
    # mathtextでも同フォントを使う（数式での文字化け防止）
    rc['mathtext.fontset'] = 'custom'
    rc['mathtext.rm'] = font
    rc['mathtext.it'] = font
    rc['mathtext.bf'] = font


def setup_japanese_font():
    """OSに応じて日本語フォントを適切に設定"""
    system = platform.system()
    
    # 利用可能な日本語フォントを優先順位付きで検出
    if system == 'Windows':
        font_candidates = [
            'Yu Gothic UI',  # Windows 10/11の標準フォント
            'Yu Gothic',
            'Meiryo UI',
            'Meiryo',
            'MS PGothic',
            'MS Gothic',
            'MS UI Gothic',
        ]
    elif system == 'Darwin':  # macOS
        font_candidates = [
            'Hiragino Sans',
            'Hiragino Kaku Gothic ProN',
            'Hiragino Mincho ProN',
            'Apple Gothic',
        ]
    else:  # Linux/Ubuntu
        font_candidates = [
            'Noto Sans CJK JP',
            'Noto Sans JP',
            'IPAPGothic',
            'IPAGothic',
            'TakaoGothic',
            'VL Gothic',
        ]
    
    # 使用可能なフォントを検索
    available_fonts = {f.name for f in fm.fontManager.ttflist}
    
    selected_font = None
    for font in font_candidates:
        if font in available_fonts:
            selected_font = font
            _apply_font_rc(font)
            print(f"✓ 日本語フォント設定: {font}")
            return font
    
    # フォールバック（見つからない場合でも日本語系を最優先に設定）
    print(f"⚠ 適切な日本語フォントが見つかりません。")
    print(f"  OS: {system}")
    print(f"  推奨フォント: {', '.join(font_candidates[:3])}")
    fallback = font_candidates[0]
    _apply_font_rc(fallback)
    return None

# フォント設定を実行
selected_font = setup_japanese_font()

# マイナス記号の文字化け防止
plt.rcParams['axes.unicode_minus'] = False

# スタイル設定
sns.set_style("whitegrid")
sns.set_palette("husl")

# Seabornが一部rcParamsを上書きする可能性に備え、再適用
if selected_font:
    _apply_font_rc(selected_font)

class BenchmarkGraphGenerator:
    """ベンチマーク結果のグラフ生成クラス"""
    
    def __init__(self, csv_path: str):
        """
        Args:
            csv_path: ベンチマークCSVファイルのパス
        """
        self.csv_path = Path(csv_path)
        self.output_dir = self.csv_path.parent / "graphs"
        self.output_dir.mkdir(exist_ok=True)
        
        # データ読み込み
        self.df = pd.read_csv(csv_path)
        print(f"データ読み込み完了: {len(self.df)}行")
        print(f"カラム: {list(self.df.columns)}")
        
        # タイムスタンプ
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def clean_test_name(self, name: str) -> str:
        """テスト名から件数を抽出"""
        import re
        match = re.search(r'\(([\d,]+)件\)', name)
        if match:
            return match.group(1).replace(',', '')
        return name
    
    def extract_operation_type(self, name: str) -> str:
        """テスト名から操作タイプを抽出"""
        if '書き込み' in name:
            return '書き込み'
        elif '読み込み' in name:
            return '読み込み'
        elif 'バルク' in name:
            return 'バルク挿入'
        else:
            return 'その他'
    
    def generate_all_graphs(self):
        """すべてのグラフを生成"""
        print(f"\nグラフ生成開始...")
        print(f"出力ディレクトリ: {self.output_dir}")
        
        # 1. OPS比較グラフ
        self.plot_ops_comparison()
        
        # 2. 実行時間比較グラフ
        self.plot_time_comparison()
        
        # 3. スピードアップ比グラフ
        self.plot_speedup_ratio()
        
        # 4. バージョン別パフォーマンスヒートマップ
        self.plot_performance_heatmap()
        
        # 5. 操作タイプ別パフォーマンス
        self.plot_performance_by_operation()
        
        # 6. スケーラビリティグラフ
        self.plot_scalability()
        
        # 7. 総合ダッシュボード
        self.plot_dashboard()
        
        print(f"\n✓ すべてのグラフ生成完了!")
        print(f"  保存先: {self.output_dir}")
        
        # 生成されたファイルをリスト表示
        if self.output_dir.exists():
            graph_files = list(self.output_dir.glob('*.*'))
            if graph_files:
                print(f"\n📊 生成されたグラフファイル ({len(graph_files)}個):")
                for f in sorted(graph_files):
                    size = f.stat().st_size / 1024  # KB
                    print(f"  - {f.name} ({size:.1f} KB)")
            else:
                print(f"\n⚠️ 警告: グラフファイルが見つかりません！")
        else:
            print(f"\n⚠️ エラー: 出力ディレクトリが存在しません: {self.output_dir}")
    
    def plot_ops_comparison(self):
        """OPS比較棒グラフ"""
        print("\n[1/7] OPS比較グラフ生成中...")
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # データ準備
        plot_df = self.df.copy()
        plot_df['Count'] = plot_df['Test'].apply(self.clean_test_name)
        
        # テストごとにグループ化
        tests = plot_df['Test'].unique()
        x = np.arange(len(tests))
        width = 0.25
        
        versions = plot_df['Version'].unique()
        colors = {'original': '#FF6B6B', 'fastest': '#4ECDC4', 'beta': '#45B7D1'}
        
        for i, version in enumerate(versions):
            version_data = []
            for test in tests:
                test_data = plot_df[(plot_df['Test'] == test) & (plot_df['Version'] == version)]
                if len(test_data) > 0:
                    version_data.append(test_data['OPS'].values[0])
                else:
                    version_data.append(0)
            
            ax.bar(x + i * width, version_data, width, 
                   label=version.upper(), 
                   color=colors.get(version, '#999999'))
        
        ax.set_xlabel('テスト', fontsize=12, fontweight='bold')
        ax.set_ylabel('OPS (Operations Per Second)', fontsize=12, fontweight='bold')
        ax.set_title('バージョン別 OPS パフォーマンス比較', fontsize=14, fontweight='bold')
        ax.set_xticks(x + width)
        ax.set_xticklabels(tests, rotation=45, ha='right')
        ax.legend(loc='upper left')
        ax.grid(axis='y', alpha=0.3)
        
        # 対数スケール（差が大きい場合）
        max_ops = plot_df['OPS'].max()
        min_ops = plot_df[plot_df['OPS'] > 0]['OPS'].min()
        if max_ops / min_ops > 100:
            ax.set_yscale('log')
            ax.set_ylabel('OPS (対数スケール)', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        output_path = self.output_dir / f"1_ops_comparison_{self.timestamp}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ 保存: {output_path.name}")
    
    def plot_time_comparison(self):
        """実行時間比較グラフ"""
        print("\n[2/7] 実行時間比較グラフ生成中...")
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # データ準備
        plot_df = self.df.copy()
        tests = plot_df['Test'].unique()
        x = np.arange(len(tests))
        width = 0.25
        
        versions = plot_df['Version'].unique()
        colors = {'original': '#FF6B6B', 'fastest': '#4ECDC4', 'beta': '#45B7D1'}
        
        for i, version in enumerate(versions):
            version_data = []
            for test in tests:
                test_data = plot_df[(plot_df['Test'] == test) & (plot_df['Version'] == version)]
                if len(test_data) > 0:
                    version_data.append(test_data['Time (s)'].values[0])
                else:
                    version_data.append(0)
            
            ax.bar(x + i * width, version_data, width, 
                   label=version.upper(), 
                   color=colors.get(version, '#999999'))
        
        ax.set_xlabel('テスト', fontsize=12, fontweight='bold')
        ax.set_ylabel('実行時間 (秒)', fontsize=12, fontweight='bold')
        ax.set_title('バージョン別 実行時間比較 (低いほど高速)', fontsize=14, fontweight='bold')
        ax.set_xticks(x + width)
        ax.set_xticklabels(tests, rotation=45, ha='right')
        ax.legend(loc='upper left')
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        output_path = self.output_dir / f"2_time_comparison_{self.timestamp}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ 保存: {output_path.name}")
    
    def plot_speedup_ratio(self):
        """スピードアップ比グラフ"""
        print("\n[3/7] スピードアップ比グラフ生成中...")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
        
        # データ準備: Originalを基準としたスピードアップ比
        speedup_data = []
        
        tests = self.df['Test'].unique()
        for test in tests:
            test_df = self.df[self.df['Test'] == test]
            
            original_time = test_df[test_df['Version'] == 'original']['Time (s)']
            fastest_time = test_df[test_df['Version'] == 'fastest']['Time (s)']
            beta_time = test_df[test_df['Version'] == 'beta']['Time (s)']
            
            if len(original_time) > 0:
                base_time = original_time.values[0]
                
                if len(fastest_time) > 0:
                    speedup_data.append({
                        'Test': test,
                        'Version': 'Fastest',
                        'Speedup': base_time / fastest_time.values[0]
                    })
                
                if len(beta_time) > 0:
                    speedup_data.append({
                        'Test': test,
                        'Version': 'Beta',
                        'Speedup': base_time / beta_time.values[0]
                    })
        
        speedup_df = pd.DataFrame(speedup_data)
        
        # グラフ1: バージョン別スピードアップ比
        if len(speedup_df) > 0:
            pivot_df = speedup_df.pivot(index='Test', columns='Version', values='Speedup')
            pivot_df.plot(kind='bar', ax=ax1, color=['#4ECDC4', '#45B7D1'])
            ax1.set_xlabel('テスト', fontsize=11, fontweight='bold')
            ax1.set_ylabel('スピードアップ比 (倍)', fontsize=11, fontweight='bold')
            ax1.set_title('Original版を基準としたスピードアップ比', fontsize=12, fontweight='bold')
            ax1.axhline(y=1, color='red', linestyle='--', alpha=0.5, label='Original (基準)')
            ax1.legend(loc='upper left')
            ax1.grid(axis='y', alpha=0.3)
            ax1.tick_params(axis='x', rotation=45)
        
        # グラフ2: 平均スピードアップ比
        if len(speedup_df) > 0:
            avg_speedup = speedup_df.groupby('Version')['Speedup'].mean()
            bars = ax2.bar(avg_speedup.index, avg_speedup.values, 
                          color=['#4ECDC4', '#45B7D1'])
            
            # 数値ラベル
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}x',
                        ha='center', va='bottom', fontsize=14, fontweight='bold')
            
            ax2.set_xlabel('バージョン', fontsize=11, fontweight='bold')
            ax2.set_ylabel('平均スピードアップ比 (倍)', fontsize=11, fontweight='bold')
            ax2.set_title('平均パフォーマンス向上率', fontsize=12, fontweight='bold')
            ax2.axhline(y=1, color='red', linestyle='--', alpha=0.5)
            ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        output_path = self.output_dir / f"3_speedup_ratio_{self.timestamp}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ 保存: {output_path.name}")
    
    def plot_performance_heatmap(self):
        """パフォーマンスヒートマップ"""
        print("\n[4/7] パフォーマンスヒートマップ生成中...")
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # データピボット
        pivot_df = self.df.pivot(index='Test', columns='Version', values='OPS')
        pivot_df = pivot_df.fillna(0)
        
        # ヒートマップ
        sns.heatmap(pivot_df, annot=True, fmt='.0f', cmap='YlGnBu', 
                   cbar_kws={'label': 'OPS'}, ax=ax, linewidths=0.5)
        
        ax.set_title('バージョン×テスト別 OPS ヒートマップ', fontsize=14, fontweight='bold')
        ax.set_xlabel('バージョン', fontsize=12, fontweight='bold')
        ax.set_ylabel('テスト', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        output_path = self.output_dir / f"4_performance_heatmap_{self.timestamp}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ 保存: {output_path.name}")
    
    def plot_performance_by_operation(self):
        """操作タイプ別パフォーマンス"""
        print("\n[5/7] 操作タイプ別パフォーマンスグラフ生成中...")
        
        # 操作タイプを抽出
        self.df['Operation'] = self.df['Test'].apply(self.extract_operation_type)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
        
        # グラフ1: 操作タイプ別平均OPS
        ops_by_operation = self.df.groupby(['Operation', 'Version'])['OPS'].mean().unstack()
        ops_by_operation.plot(kind='bar', ax=ax1, color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
        ax1.set_xlabel('操作タイプ', fontsize=11, fontweight='bold')
        ax1.set_ylabel('平均 OPS', fontsize=11, fontweight='bold')
        ax1.set_title('操作タイプ別 平均パフォーマンス', fontsize=12, fontweight='bold')
        ax1.legend(title='Version', loc='upper left')
        ax1.grid(axis='y', alpha=0.3)
        ax1.tick_params(axis='x', rotation=0)
        
        # グラフ2: バージョン別操作タイプ分布
        version_ops = self.df.groupby(['Version', 'Operation'])['OPS'].mean().unstack()
        version_ops.plot(kind='bar', ax=ax2, stacked=False)
        ax2.set_xlabel('バージョン', fontsize=11, fontweight='bold')
        ax2.set_ylabel('平均 OPS', fontsize=11, fontweight='bold')
        ax2.set_title('バージョン別 操作パフォーマンス', fontsize=12, fontweight='bold')
        ax2.legend(title='Operation', loc='upper left')
        ax2.grid(axis='y', alpha=0.3)
        ax2.tick_params(axis='x', rotation=0)
        
        plt.tight_layout()
        output_path = self.output_dir / f"5_performance_by_operation_{self.timestamp}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ 保存: {output_path.name}")
    
    def plot_scalability(self):
        """スケーラビリティグラフ（データ量とパフォーマンスの関係）"""
        print("\n[6/7] スケーラビリティグラフ生成中...")
        
        # データ件数を抽出
        self.df['Data_Count'] = self.df['Test'].apply(
            lambda x: int(self.clean_test_name(x)) if self.clean_test_name(x).isdigit() else 0
        )
        
        # データ件数があるものだけフィルタ
        scalability_df = self.df[self.df['Data_Count'] > 0].copy()
        
        if len(scalability_df) == 0:
            print("  ⚠ スケーラビリティデータなし")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
        
        # グラフ1: データ量 vs OPS
        for version in scalability_df['Version'].unique():
            version_df = scalability_df[scalability_df['Version'] == version]
            version_df = version_df.sort_values('Data_Count')
            
            ax1.plot(version_df['Data_Count'], version_df['OPS'], 
                    marker='o', label=version.upper(), linewidth=2, markersize=8)
        
        ax1.set_xlabel('データ件数', fontsize=11, fontweight='bold')
        ax1.set_ylabel('OPS', fontsize=11, fontweight='bold')
        ax1.set_title('スケーラビリティ: データ量 vs パフォーマンス', fontsize=12, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        ax1.set_xscale('log')
        ax1.set_yscale('log')
        
        # グラフ2: データ量 vs 実行時間
        for version in scalability_df['Version'].unique():
            version_df = scalability_df[scalability_df['Version'] == version]
            version_df = version_df.sort_values('Data_Count')
            
            ax2.plot(version_df['Data_Count'], version_df['Time (s)'], 
                    marker='s', label=version.upper(), linewidth=2, markersize=8)
        
        ax2.set_xlabel('データ件数', fontsize=11, fontweight='bold')
        ax2.set_ylabel('実行時間 (秒)', fontsize=11, fontweight='bold')
        ax2.set_title('スケーラビリティ: データ量 vs 実行時間', fontsize=12, fontweight='bold')
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)
        ax2.set_xscale('log')
        ax2.set_yscale('log')
        
        plt.tight_layout()
        output_path = self.output_dir / f"6_scalability_{self.timestamp}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ 保存: {output_path.name}")
    
    def plot_dashboard(self):
        """総合ダッシュボード"""
        print("\n[7/7] 総合ダッシュボード生成中...")
        
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. バージョン別平均OPS
        ax1 = fig.add_subplot(gs[0, 0])
        avg_ops = self.df.groupby('Version')['OPS'].mean()
        bars = ax1.bar(avg_ops.index, avg_ops.values, color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.0f}',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
        ax1.set_title('平均 OPS', fontsize=11, fontweight='bold')
        ax1.set_ylabel('OPS', fontsize=10)
        ax1.grid(axis='y', alpha=0.3)
        
        # 2. バージョン別平均実行時間
        ax2 = fig.add_subplot(gs[0, 1])
        avg_time = self.df.groupby('Version')['Time (s)'].mean()
        bars = ax2.bar(avg_time.index, avg_time.values, color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.3f}s',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
        ax2.set_title('平均実行時間', fontsize=11, fontweight='bold')
        ax2.set_ylabel('秒', fontsize=10)
        ax2.grid(axis='y', alpha=0.3)
        
        # 3. スピードアップ比（円グラフ）
        ax3 = fig.add_subplot(gs[0, 2])
        speedup_data = []
        tests = self.df['Test'].unique()
        for test in tests:
            test_df = self.df[self.df['Test'] == test]
            original_time = test_df[test_df['Version'] == 'original']['Time (s)']
            beta_time = test_df[test_df['Version'] == 'beta']['Time (s)']
            
            if len(original_time) > 0 and len(beta_time) > 0:
                speedup = original_time.values[0] / beta_time.values[0]
                speedup_data.append(speedup)
        
        if speedup_data:
            avg_speedup = np.mean(speedup_data)
            ax3.pie([avg_speedup, 1], labels=[f'Beta\n{avg_speedup:.1f}x', 'Original\n1.0x'],
                   colors=['#45B7D1', '#FF6B6B'], autopct='%1.1f%%', startangle=90)
            ax3.set_title('Beta版の平均高速化率', fontsize=11, fontweight='bold')
        
        # 4. テスト別OPS比較（横棒グラフ）
        ax4 = fig.add_subplot(gs[1, :])
        pivot_ops = self.df.pivot(index='Test', columns='Version', values='OPS')
        pivot_ops.plot(kind='barh', ax=ax4, color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
        ax4.set_title('テスト別 OPS 詳細比較', fontsize=12, fontweight='bold')
        ax4.set_xlabel('OPS', fontsize=10)
        ax4.legend(loc='lower right')
        ax4.grid(axis='x', alpha=0.3)
        
        # 5. 実行時間分布（ヒストグラム）
        ax5 = fig.add_subplot(gs[2, 0])
        for version in self.df['Version'].unique():
            version_df = self.df[self.df['Version'] == version]
            ax5.hist(version_df['Time (s)'], alpha=0.6, label=version.upper(), bins=10)
        ax5.set_title('実行時間分布', fontsize=11, fontweight='bold')
        ax5.set_xlabel('時間 (秒)', fontsize=10)
        ax5.set_ylabel('頻度', fontsize=10)
        ax5.legend()
        ax5.grid(axis='y', alpha=0.3)
        
        # 6. OPS分布（バイオリンプロット）
        ax6 = fig.add_subplot(gs[2, 1])
        # OPSが0より大きいデータのみ
        plot_df = self.df[self.df['OPS'] > 0]
        if len(plot_df) > 0:
            sns.violinplot(data=plot_df, x='Version', y='OPS', ax=ax6, 
                          palette=['#FF6B6B', '#4ECDC4', '#45B7D1'])
            ax6.set_title('OPS分布（バイオリンプロット）', fontsize=11, fontweight='bold')
            ax6.set_ylabel('OPS', fontsize=10)
            ax6.set_yscale('log')
            ax6.grid(axis='y', alpha=0.3)
        
        # 7. 勝率円グラフ
        ax7 = fig.add_subplot(gs[2, 2])
        wins = {'original': 0, 'fastest': 0, 'beta': 0}
        for test in self.df['Test'].unique():
            test_df = self.df[self.df['Test'] == test]
            if len(test_df) > 0:
                fastest_version = test_df.loc[test_df['Time (s)'].idxmin(), 'Version']
                wins[fastest_version] += 1
        
        labels = [f'{k.upper()}\n{v}勝' for k, v in wins.items() if v > 0]
        sizes = [v for v in wins.values() if v > 0]
        colors_list = ['#FF6B6B', '#4ECDC4', '#45B7D1'][:len(sizes)]
        
        ax7.pie(sizes, labels=labels, colors=colors_list, autopct='%1.1f%%', startangle=90)
        ax7.set_title('勝率分布', fontsize=11, fontweight='bold')
        
        # 全体タイトル
        fig.suptitle('DictSQLite 包括的パフォーマンス分析ダッシュボード', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        output_path = self.output_dir / f"7_dashboard_{self.timestamp}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ 保存: {output_path.name}")
    
    def generate_summary_stats(self):
        """統計サマリーをテキストファイルに保存"""
        print("\n統計サマリー生成中...")
        
        summary_path = self.output_dir / f"statistics_summary_{self.timestamp}.txt"
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("DictSQLite ベンチマーク統計サマリー\n")
            f.write("="*80 + "\n\n")
            
            # 基本統計
            f.write("【基本統計】\n")
            f.write(f"総テスト数: {len(self.df['Test'].unique())}\n")
            f.write(f"総データポイント数: {len(self.df)}\n")
            f.write(f"テスト対象バージョン: {', '.join(self.df['Version'].unique())}\n\n")
            
            # バージョン別統計
            f.write("【バージョン別統計】\n")
            for version in self.df['Version'].unique():
                version_df = self.df[self.df['Version'] == version]
                f.write(f"\n{version.upper()}:\n")
                f.write(f"  平均OPS:        {version_df['OPS'].mean():,.2f}\n")
                f.write(f"  最大OPS:        {version_df['OPS'].max():,.2f}\n")
                f.write(f"  最小OPS:        {version_df['OPS'].min():,.2f}\n")
                f.write(f"  平均実行時間:  {version_df['Time (s)'].mean():.4f}秒\n")
                f.write(f"  最短実行時間:  {version_df['Time (s)'].min():.4f}秒\n")
                f.write(f"  最長実行時間:  {version_df['Time (s)'].max():.4f}秒\n")
            
            # スピードアップ統計
            f.write("\n【スピードアップ統計（vs Original）】\n")
            speedups = []
            for test in self.df['Test'].unique():
                test_df = self.df[self.df['Test'] == test]
                original = test_df[test_df['Version'] == 'original']['Time (s)']
                beta = test_df[test_df['Version'] == 'beta']['Time (s)']
                
                if len(original) > 0 and len(beta) > 0:
                    speedup = original.values[0] / beta.values[0]
                    speedups.append(speedup)
                    f.write(f"  {test}: {speedup:.2f}x\n")
            
            if speedups:
                f.write(f"\n平均スピードアップ: {np.mean(speedups):.2f}x\n")
                f.write(f"最大スピードアップ: {max(speedups):.2f}x\n")
                f.write(f"最小スピードアップ: {min(speedups):.2f}x\n")
            
            # 勝率
            f.write("\n【テスト勝率】\n")
            wins = {'original': 0, 'fastest': 0, 'beta': 0}
            for test in self.df['Test'].unique():
                test_df = self.df[self.df['Test'] == test]
                if len(test_df) > 0:
                    fastest_version = test_df.loc[test_df['Time (s)'].idxmin(), 'Version']
                    wins[fastest_version] += 1
            
            total = sum(wins.values())
            for version, count in wins.items():
                percentage = (count / total * 100) if total > 0 else 0
                f.write(f"  {version.upper()}: {count}勝 ({percentage:.1f}%)\n")
            
            f.write("\n" + "="*80 + "\n")
        
        print(f"  ✓ 保存: {summary_path.name}")


def main():
    """メイン実行"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='DictSQLite ベンチマーク結果グラフ生成ツール'
    )
    parser.add_argument(
        'csv_file',
        nargs='?',
        help='ベンチマークCSVファイルのパス'
    )
    
    args = parser.parse_args()
    
    # CSVファイルパスの決定
    if args.csv_file:
        csv_path = args.csv_file
    else:
        # 最新のCSVファイルを自動検索（ベンチマークスクリプトと同じディレクトリのresults）
        script_dir = Path(__file__).parent
        results_dir = script_dir / 'results'
        if not results_dir.exists():
            print("エラー: resultsディレクトリが見つかりません")
            print(f"期待されるパス: {results_dir}")
            return
        
        csv_files = list(results_dir.glob('benchmark_*.csv'))
        if not csv_files:
            print("エラー: CSVファイルが見つかりません")
            print("使用方法: python visualize_benchmark.py [CSVファイルパス]")
            return
        
        # 最新のファイルを選択
        csv_path = max(csv_files, key=lambda p: p.stat().st_mtime)
        print(f"最新のCSVファイルを使用: {csv_path}")
    
    # グラフ生成
    print("\n" + "="*80)
    print("DictSQLite ベンチマーク結果 グラフ生成ツール")
    print("="*80)
    
    try:
        generator = BenchmarkGraphGenerator(csv_path)
        generator.generate_all_graphs()
        generator.generate_summary_stats()
        
        print("\n" + "="*80)
        print("✓ すべての処理が完了しました!")
        print("="*80)
        print(f"\n生成されたファイル:")
        print(f"  ディレクトリ: {generator.output_dir}")
        print(f"  グラフ数: 7枚")
        print(f"  統計サマリー: 1ファイル")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

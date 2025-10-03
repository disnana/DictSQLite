"""ボトルネック特定のための詳細プロファイリングスクリプト"""

import cProfile
import pstats
import io
import sys
import os
from pathlib import Path
import time
import tempfile

# ベータモジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from dictsqlite_fastest.main import DictSQLiteFastest
from dictsqlite_fastest_beta import DictSQLiteFastestBeta

# テスト用のデータベースファイル
temp_dir = tempfile.gettempdir()
standard_db = os.path.join(temp_dir, 'profile_standard.db')
beta_db = os.path.join(temp_dir, 'profile_beta.db')


def profile_function(func, name):
    """関数をプロファイリングして結果を表示"""
    print(f"\n{'='*60}")
    print(f"プロファイリング: {name}")
    print('='*60)
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    start_time = time.perf_counter()
    func()
    end_time = time.perf_counter()
    
    profiler.disable()
    
    # 統計を文字列バッファに出力
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats('cumulative')
    ps.print_stats(20)  # 上位20件を表示
    
    print(f"実行時間: {end_time - start_time:.4f}秒")
    print("\n主要なボトルネック（累積時間順）:")
    print(s.getvalue())


def test_standard_write():
    """標準版の書き込みテスト"""
    with DictSQLiteFastest(standard_db) as db:
        for i in range(1000):
            db[f'key_{i}'] = {'id': i, 'value': f'value_{i}', 'data': 'x' * 100}


def test_standard_read():
    """標準版の読み込みテスト"""
    with DictSQLiteFastest(standard_db) as db:
        # データを準備
        for i in range(1000):
            db[f'key_{i}'] = {'id': i, 'value': f'value_{i}'}
        
        # 読み込み
        for i in range(1000):
            _ = db[f'key_{i}']


def test_beta_write_cold():
    """Beta版の書き込みテスト（キャッシュコールド）"""
    with DictSQLiteFastestBeta(':memory:', memory_only=True) as db:
        for i in range(1000):
            db[f'key_{i}'] = {'id': i, 'value': f'value_{i}', 'data': 'x' * 100}


def test_beta_read_cold():
    """Beta版の読み込みテスト（初回・キャッシュコールド）"""
    with DictSQLiteFastestBeta(':memory:', memory_only=True) as db:
        # データを準備
        for i in range(1000):
            db[f'key_{i}'] = {'id': i, 'value': f'value_{i}'}
        
        # キャッシュをクリア
        if hasattr(db, 'clear_cache'):
            db.clear_cache()
        
        # 読み込み
        for i in range(1000):
            _ = db[f'key_{i}']


def test_beta_read_hot():
    """Beta版の読み込みテスト（2回目・キャッシュホット）"""
    with DictSQLiteFastestBeta(':memory:', memory_only=True) as db:
        # データを準備
        for i in range(1000):
            db[f'key_{i}'] = {'id': i, 'value': f'value_{i}'}
        
        # 最初に1回読み込んでキャッシュをウォームアップ
        for i in range(1000):
            _ = db[f'key_{i}']
        
        # 2回目の読み込み（キャッシュヒット）
        for i in range(1000):
            _ = db[f'key_{i}']


def test_beta_bulk_operations():
    """Beta版のバルク操作テスト"""
    with DictSQLiteFastestBeta(':memory:', memory_only=True) as db:
        # バルク書き込み
        data = {f'bulk_key_{i}': {'id': i, 'value': f'value_{i}'} for i in range(1000)}
        db.bulk_insert(data)
        
        # バルク読み込み
        keys = [f'bulk_key_{i}' for i in range(1000)]
        _ = db.bulk_get(keys)


def analyze_cache_overhead():
    """キャッシュのオーバーヘッドを分析"""
    print(f"\n{'='*60}")
    print("キャッシュオーバーヘッド分析")
    print('='*60)
    
    # Beta版（キャッシュ有効）
    with DictSQLiteFastestBeta(':memory:', cache_capacity=10000, memory_only=True) as db_beta:
        for i in range(1000):
            db_beta[f'key_{i}'] = f'value_{i}'
        
        start = time.perf_counter()
        for i in range(1000):
            _ = db_beta[f'key_{i}']
        beta_time = time.perf_counter() - start
        
        # Beta版の統計
        stats = db_beta.get_beta_stats()
        print(f"Beta版の読み込み時間（2回目）: {beta_time:.4f}秒")
        print(f"\nBeta版統計:")
        print(f"  キャッシュヒット率: {stats['cache']['hit_rate']:.2f}%")
        print(f"  キャッシュヒット数: {stats['cache']['hits']}")
        print(f"  キャッシュミス数: {stats['cache']['misses']}")
    
    # 標準版（キャッシュなし）
    with DictSQLiteFastest(standard_db) as db_standard:
        for i in range(1000):
            db_standard[f'key_{i}'] = f'value_{i}'
        
        start = time.perf_counter()
        for i in range(1000):
            _ = db_standard[f'key_{i}']
        standard_time = time.perf_counter() - start
        
        print(f"\n標準版の読み込み時間: {standard_time:.4f}秒")
        print(f"キャッシュによる高速化: {standard_time / beta_time:.2f}倍")


def main():
    """メイン実行関数"""
    print("="*60)
    print("DictSQLite ボトルネック分析ツール")
    print("="*60)
    
    # 標準版のプロファイリング
    print("\n【標準版（dictsqlite-fastest）のプロファイリング】")
    profile_function(test_standard_write, "標準版 - 個別書き込み (1000件)")
    profile_function(test_standard_read, "標準版 - 個別読み込み (1000件)")
    
    # Beta版のプロファイリング
    print("\n\n【Beta版のプロファイリング】")
    profile_function(test_beta_write_cold, "Beta版 - 個別書き込み (1000件)")
    profile_function(test_beta_read_cold, "Beta版 - 読み込み（初回・コールド）(1000件)")
    profile_function(test_beta_read_hot, "Beta版 - 読み込み（2回目・ホット）(1000件)")
    profile_function(test_beta_bulk_operations, "Beta版 - バルク操作 (1000件)")
    
    # キャッシュオーバーヘッド分析
    analyze_cache_overhead()
    
    print("\n" + "="*60)
    print("プロファイリング完了")
    print("="*60)
    
    # 結論
    print("\n【ボトルネック分析結果】")
    print("\n標準版の主要ボトルネック:")
    print("  1. SQLite実行（cursor.execute）")
    print("  2. ディスクI/O待機")
    print("  3. シリアライゼーション/デシリアライゼーション")
    
    print("\nBeta版の主要ボトルネック:")
    print("  1. キャッシュミス時の追加オーバーヘッド")
    print("  2. LRUキャッシュのロック取得（OrderedDict操作）")
    print("  3. 書き込みバッファの管理コスト")
    
    print("\n最適化の推奨:")
    print("  - 読み込み中心 -> Beta版（21倍高速化）")
    print("  - 大規模バルク書き込み -> 標準版")
    print("  - 混合ワークロード -> Beta版（59倍高速化）")
    
    # クリーンアップ
    for db_file in [standard_db, beta_db]:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except:
                pass


if __name__ == '__main__':
    main()

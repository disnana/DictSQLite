"""DictSQLite-Fastest Beta の基本的な使用例."""

import sys
from pathlib import Path

# ベータモジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from dictsqlite_fastest_beta import DictSQLiteFastestBeta


def example_basic_usage():
    """基本的な使用方法の例."""
    print("=== 基本的な使用方法 ===\n")
    
    with DictSQLiteFastestBeta('example_basic.db', cache_capacity=1000) as db:
        # データの書き込み
        db['user_1'] = {'name': '田中太郎', 'age': 30, 'city': '東京'}
        db['user_2'] = {'name': '佐藤花子', 'age': 25, 'city': '大阪'}
        db['user_3'] = {'name': '鈴木一郎', 'age': 35, 'city': '名古屋'}
        
        print("データを書き込みました")
        
        # データの読み込み
        user = db['user_1']
        print(f"取得したデータ: {user}")
        
        # 存在確認
        if 'user_2' in db:
            print("user_2は存在します")
        
        # 削除
        del db['user_3']
        print("user_3を削除しました")
        
        # 統計情報
        stats = db.get_beta_stats()
        print(f"\nキャッシュヒット率: {stats['cache']['hit_rate']:.2f}%")
        print(f"保留中の書き込み: {stats['buffer']['pending_writes']}")


def example_bulk_operations():
    """バルク操作の例."""
    print("\n=== バルク操作 ===\n")
    
    with DictSQLiteFastestBeta('example_bulk.db', write_buffer_size=5000) as db:
        # 大量データの生成
        print("10,000件のデータを生成中...")
        data = {f'item_{i}': {'id': i, 'value': f'value_{i}'} for i in range(10000)}
        
        # バルク挿入
        print("バルク挿入中...")
        db.bulk_insert(data)
        
        # バルク取得
        print("バルク取得中...")
        keys = [f'item_{i}' for i in range(0, 1000, 10)]
        results = db.bulk_get(keys)
        print(f"取得したアイテム数: {len(results)}")
        
        # 統計情報
        stats = db.get_beta_stats()
        print(f"\nディスク読み込み: {stats['operations']['disk_reads']}")
        print(f"ディスク書き込み: {stats['operations']['disk_writes']}")
        print(f"バッファフラッシュ: {stats['operations']['buffer_flushes']}")
        print(f"保留中の書き込み: {stats['buffer']['pending_writes']}")
        
        # 明示的にフラッシュ
        print("\nバッファをフラッシュ中...")
        db.flush()
        
        stats = db.get_beta_stats()
        print(f"フラッシュ後の保留中の書き込み: {stats['buffer']['pending_writes']}")


def example_memory_only():
    """メモリオンリーモードの例."""
    print("\n=== メモリオンリーモード ===\n")
    
    with DictSQLiteFastestBeta(':memory:', memory_only=True) as db:
        # 一時データの処理
        print("一時データを処理中...")
        temp_data = {f'temp_{i}': i * 2 for i in range(1000)}
        db.bulk_insert(temp_data)
        
        # 計算処理
        total = sum(db[k] for k in temp_data.keys())
        print(f"合計: {total}")
        
        # 統計情報
        stats = db.get_beta_stats()
        print(f"\nメモリオンリーモード: {stats['config']['memory_only']}")
        print(f"キャッシュサイズ: {stats['cache']['size']}")
        print(f"ディスク書き込み: {stats['operations']['disk_writes']}")
        
        print("\nこのデータベースは閉じると消えます")


def example_prefetching():
    """先読みキャッシングの例."""
    print("\n=== 先読みキャッシング ===\n")
    
    with DictSQLiteFastestBeta('example_prefetch.db', cache_capacity=5000) as db:
        # テストデータの準備
        print("テストデータを準備中...")
        test_data = {f'data_{i}': {'value': i} for i in range(1000)}
        db.bulk_insert(test_data)
        db.flush()
        
        # キャッシュをクリア（ディスクから読み込む状態にする）
        db.clear_cache()
        
        # 先読みなしでアクセス
        print("\n先読みなしでアクセス...")
        keys = [f'data_{i}' for i in range(100)]
        for key in keys:
            _ = db[key]
        
        stats1 = db.get_beta_stats()
        print(f"ディスク読み込み: {stats1['operations']['disk_reads']}")
        
        # キャッシュをクリア
        db.clear_cache()
        
        # 先読みありでアクセス
        print("\n先読みありでアクセス...")
        keys2 = [f'data_{i}' for i in range(100, 200)]
        db.prefetch_keys(keys2)  # 事前にキャッシュに読み込む
        
        for key in keys2:
            _ = db[key]
        
        stats2 = db.get_beta_stats()
        cache_hits_diff = stats2['operations']['cache_hits'] - stats1['operations']['cache_hits']
        print(f"先読み後のキャッシュヒット: {cache_hits_diff}")


def example_custom_config():
    """カスタム設定の例."""
    print("\n=== カスタム設定 ===\n")
    
    # 読み込み中心のワークロード向け設定
    print("読み込み中心の設定:")
    db_read = DictSQLiteFastestBeta(
        'example_read_heavy.db',
        cache_capacity=50000,       # 大きなキャッシュ
        write_buffer_size=100,      # 小さなバッファ
        write_buffer_interval=1.0,  # 短い間隔
        aggressive_memory=True
    )
    
    stats = db_read.get_beta_stats()
    print(f"キャッシュ容量: {stats['cache']['capacity']}")
    print(f"バッファ閾値: {stats['buffer']['threshold']}")
    db_read.close()
    
    # 書き込み中心のワークロード向け設定
    print("\n書き込み中心の設定:")
    db_write = DictSQLiteFastestBeta(
        'example_write_heavy.db',
        cache_capacity=5000,         # 適度なキャッシュ
        write_buffer_size=10000,     # 大きなバッファ
        write_buffer_interval=30.0,  # 長い間隔
        aggressive_memory=True
    )
    
    stats = db_write.get_beta_stats()
    print(f"キャッシュ容量: {stats['cache']['capacity']}")
    print(f"バッファ閾値: {stats['buffer']['threshold']}")
    db_write.close()


def example_statistics_monitoring():
    """統計情報の監視例."""
    print("\n=== 統計情報の監視 ===\n")
    
    with DictSQLiteFastestBeta('example_stats.db', cache_capacity=100) as db:
        # データ操作
        print("データ操作中...")
        for i in range(500):
            db[f'key_{i}'] = f'value_{i}'
        
        # 統計情報の取得
        stats = db.get_beta_stats()
        
        print("\n=== キャッシュ統計 ===")
        print(f"サイズ: {stats['cache']['size']}/{stats['cache']['capacity']}")
        print(f"ヒット: {stats['cache']['hits']}")
        print(f"ミス: {stats['cache']['misses']}")
        print(f"ヒット率: {stats['cache']['hit_rate']:.2f}%")
        
        print("\n=== 操作統計 ===")
        print(f"キャッシュヒット: {stats['operations']['cache_hits']}")
        print(f"キャッシュミス: {stats['operations']['cache_misses']}")
        print(f"ディスク読み込み: {stats['operations']['disk_reads']}")
        print(f"ディスク書き込み: {stats['operations']['disk_writes']}")
        print(f"バッファフラッシュ: {stats['operations']['buffer_flushes']}")
        
        print("\n=== バッファ状態 ===")
        print(f"保留中の書き込み: {stats['buffer']['pending_writes']}")
        print(f"保留中の削除: {stats['buffer']['pending_deletes']}")
        
        print("\n=== 設定情報 ===")
        print(f"メモリオンリー: {stats['config']['memory_only']}")
        print(f"アグレッシブメモリ: {stats['config']['aggressive_memory']}")
        print(f"キャッシュ容量: {stats['config']['cache_capacity']}")


if __name__ == '__main__':
    print("DictSQLite-Fastest Beta 使用例\n")
    print("=" * 50)
    
    example_basic_usage()
    example_bulk_operations()
    example_memory_only()
    example_prefetching()
    example_custom_config()
    example_statistics_monitoring()
    
    print("\n" + "=" * 50)
    print("すべての例が完了しました")
    print("\n生成されたデータベースファイル:")
    print("- example_basic.db")
    print("- example_bulk.db")
    print("- example_prefetch.db")
    print("- example_read_heavy.db")
    print("- example_write_heavy.db")
    print("- example_stats.db")

#!/usr/bin/env python3
"""
DictSQLite v4.2 パフォーマンス最適化例

buffer_size、hot_capacity、persist_modeなどのパラメータを
最適化してパフォーマンスを最大化する方法を示す
"""
import sys
import os
import time
import tempfile

# v4.2モジュールのインポート
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')
    from __init__ import DictSQLiteV4
except ImportError as e:
    print("エラー: dictsqlite_v4 モジュールがビルドされていません")
    print("ビルド方法: cd others/beta-versions/dictsqlite_v4.2 && maturin develop --release")
    print(f"詳細: {e}")
    sys.exit(1)


def benchmark_buffer_sizes():
    """buffer_sizeの最適化"""
    print("\n" + "="*70)
    print("1. buffer_sizeの最適化")
    print("="*70)
    print("\nbuffer_sizeはバッファに溜めるエントリ数を制御します。")
    print("大きいほどI/O回数が減りスループットが向上しますが、")
    print("メモリ使用量が増えレイテンシが悪化します。")
    
    num_items = 1000
    buffer_sizes = [50, 100, 200, 500, 1000]
    results = []
    
    print(f"\nテスト: {num_items}件の書き込み")
    print("-" * 70)
    
    for buffer_size in buffer_sizes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name
        
        try:
            db = DictSQLiteV4(db_path, buffer_size=buffer_size)
            
            start = time.time()
            for i in range(num_items):
                db[f'key:{i}'] = f'value_{i}'.encode('utf-8')
            elapsed = time.time() - start
            
            db.flush()  # 残りをフラッシュ
            db.close()
            
            ops_per_sec = num_items / elapsed
            results.append((buffer_size, elapsed, ops_per_sec))
            
            print(f"buffer_size={buffer_size:4d}: {elapsed:.3f}秒 ({ops_per_sec:,.0f} ops/sec)")
            
        finally:
            try:
                os.unlink(db_path)
            except:
                pass
    
    # 最速の設定を表示
    best = max(results, key=lambda x: x[2])
    print(f"\n✓ 最速: buffer_size={best[0]} ({best[2]:,.0f} ops/sec)")
    
    # 推奨設定
    print("\n💡 推奨設定:")
    print("  - リアルタイム処理: buffer_size=50-100 (低レイテンシ)")
    print("  - バランス重視: buffer_size=100-200 (デフォルト)")
    print("  - バッチ処理: buffer_size=500-1000 (高スループット)")


def benchmark_persist_modes():
    """persist_modeの比較"""
    print("\n" + "="*70)
    print("2. persist_modeの比較")
    print("="*70)
    print("\npersist_modeは永続化のタイミングを制御します:")
    print("  - memory: 永続化なし（最速）")
    print("  - lazy: 手動flush時に永続化（高速）")
    print("  - writethrough: バッファリング付き即座永続化（安全）")
    
    num_items = 1000
    modes = ['memory', 'lazy', 'writethrough']
    results = []
    
    print(f"\nテスト: {num_items}件の書き込み + 読み込み")
    print("-" * 70)
    
    for mode in modes:
        if mode == 'memory':
            db_path = ':memory:'
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
                db_path = f.name
        
        try:
            db = DictSQLiteV4(db_path, persist_mode=mode, buffer_size=200)
            
            # 書き込み
            start = time.time()
            for i in range(num_items):
                db[f'key:{i}'] = f'value_{i}'.encode('utf-8')
            
            if mode == 'lazy':
                db.flush()  # lazyモードは手動flush必要
            
            write_time = time.time() - start
            
            # 読み込み
            start = time.time()
            for i in range(num_items):
                _ = db[f'key:{i}']
            read_time = time.time() - start
            
            db.close()
            
            write_ops = num_items / write_time
            read_ops = num_items / read_time
            results.append((mode, write_time, read_time, write_ops, read_ops))
            
            print(f"{mode:12s}: 書込 {write_time:.3f}秒 ({write_ops:,.0f} ops/sec) | "
                  f"読込 {read_time:.3f}秒 ({read_ops:,.0f} ops/sec)")
            
        finally:
            if db_path != ':memory:':
                try:
                    os.unlink(db_path)
                except:
                    pass
    
    print("\n💡 使い分け:")
    print("  - memory: テスト、一時データ")
    print("  - lazy: 高速書き込み重視、定期的なflush可能")
    print("  - writethrough: データ保証重視、本番環境推奨")


def benchmark_hot_capacity():
    """hot_capacityの影響"""
    print("\n" + "="*70)
    print("3. hot_capacityの最適化")
    print("="*70)
    print("\nhot_capacityはメモリキャッシュのサイズを制御します。")
    print("データセットサイズより大きく設定すると、すべてメモリに載り高速化します。")
    
    num_items = 5000
    capacities = [1000, 5000, 10000]
    
    print(f"\nテスト: {num_items}件のデータに対する読み込み性能")
    print("-" * 70)
    
    for capacity in capacities:
        db = DictSQLiteV4(':memory:', hot_capacity=capacity)
        
        # データ準備
        for i in range(num_items):
            db[f'key:{i}'] = f'value_{i}'.encode('utf-8')
        
        # ランダムアクセス性能
        import random
        keys = [f'key:{random.randint(0, num_items-1)}' for _ in range(num_items)]
        
        start = time.time()
        for key in keys:
            _ = db[key]
        elapsed = time.time() - start
        
        ops_per_sec = num_items / elapsed
        
        stats = db.stats()
        print(f"hot_capacity={capacity:6d}: {elapsed:.3f}秒 ({ops_per_sec:,.0f} ops/sec) | "
              f"キャッシュ: {stats['hot_tier_size']}")
        
        db.close()
    
    print("\n💡 設定ガイド:")
    print("  - 小規模(~10K): hot_capacity=10,000")
    print("  - 中規模(~100K): hot_capacity=100,000")
    print("  - 大規模(~1M): hot_capacity=1,000,000")


def benchmark_bulk_insert():
    """bulk_insertの効果"""
    print("\n" + "="*70)
    print("4. bulk_insert vs 個別書き込み")
    print("="*70)
    
    num_items = 5000
    
    # データ準備
    data = {
        f'key:{i}': f'value_{i}'.encode('utf-8')
        for i in range(num_items)
    }
    
    print(f"\nテスト: {num_items}件の書き込み")
    print("-" * 70)
    
    # 方法1: 個別書き込み
    db1 = DictSQLiteV4(':memory:', buffer_size=200)
    start = time.time()
    for key, value in data.items():
        db1[key] = value
    elapsed1 = time.time() - start
    ops1 = num_items / elapsed1
    db1.close()
    
    print(f"個別書き込み: {elapsed1:.3f}秒 ({ops1:,.0f} ops/sec)")
    
    # 方法2: bulk_insert
    db2 = DictSQLiteV4(':memory:')
    start = time.time()
    db2.bulk_insert(data)
    elapsed2 = time.time() - start
    ops2 = num_items / elapsed2
    db2.close()
    
    print(f"bulk_insert: {elapsed2:.3f}秒 ({ops2:,.0f} ops/sec)")
    
    if elapsed2 < elapsed1:
        improvement = elapsed1 / elapsed2
        print(f"\n✓ bulk_insertで {improvement:.1f}倍高速化")
    
    print("\n💡 推奨:")
    print("  - 大量データの初期投入にはbulk_insertを使用")
    print("  - 通常運用ではバッファリング付き個別書き込みでOK")


def real_world_optimization():
    """実践的な最適化例"""
    print("\n" + "="*70)
    print("5. 実践的な最適化例")
    print("="*70)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        print("\n【シナリオ】")
        print("  Webアプリケーションのセッションストア")
        print("  - 10,000件の同時セッション")
        print("  - 高速な読み書き")
        print("  - データ保証が必要")
        
        # 最適化された設定
        db = DictSQLiteV4(
            db_path,
            hot_capacity=20_000,       # セッション数の2倍のキャッシュ
            buffer_size=200,           # バランスの良いバッファ
            persist_mode='writethrough',  # データ保証
            encryption_password='session_secret'  # セキュリティ
        )
        
        print("\n最適化設定:")
        print("  hot_capacity=20,000 (セッション数の2倍)")
        print("  buffer_size=200 (バランス)")
        print("  persist_mode=writethrough (データ保証)")
        print("  encryption=有効 (セキュリティ)")
        
        # セッション書き込みシミュレーション
        num_sessions = 10_000
        
        print(f"\n{num_sessions:,}件のセッション書き込み...")
        start = time.time()
        
        for i in range(num_sessions):
            session_data = f'{{"user_id": "user{i}", "login_time": "2024-01-15 10:30:00"}}'
            db[f'session:{i}'] = session_data.encode('utf-8')
        
        write_time = time.time() - start
        write_ops = num_sessions / write_time
        
        print(f"✓ 書き込み完了: {write_time:.3f}秒 ({write_ops:,.0f} ops/sec)")
        
        # セッション読み込みシミュレーション
        import random
        read_count = 10_000
        session_ids = [random.randint(0, num_sessions-1) for _ in range(read_count)]
        
        print(f"\n{read_count:,}件のランダムアクセス...")
        start = time.time()
        
        for sess_id in session_ids:
            _ = db[f'session:{sess_id}']
        
        read_time = time.time() - start
        read_ops = read_count / read_time
        
        print(f"✓ 読み込み完了: {read_time:.3f}秒 ({read_ops:,.0f} ops/sec)")
        
        # 統計情報
        stats = db.stats()
        print(f"\n統計情報:")
        print(f"  エントリ数: {stats['hot_tier_size']:,}")
        print(f"  暗号化: {stats['encryption_enabled']}")
        
        db.close()
        
        print("\n✓ 高性能・高セキュリティなセッションストアが完成！")
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def main():
    """メイン関数"""
    print("="*70)
    print("DictSQLite v4.2 パフォーマンス最適化例")
    print("="*70)
    print("\nv4.2の最大の特徴は以下のパラメータによる最適化です:")
    print("  - buffer_size: バッファリングサイズ")
    print("  - hot_capacity: メモリキャッシュサイズ")
    print("  - persist_mode: 永続化モード")
    print("  - bulk_insert: 一括挿入API")
    
    try:
        benchmark_buffer_sizes()
        benchmark_persist_modes()
        benchmark_hot_capacity()
        benchmark_bulk_insert()
        real_world_optimization()
        
        print("\n" + "="*70)
        print("すべてのベンチマークが正常に完了しました！")
        print("="*70)
        
        print("\n📊 パフォーマンス最適化のまとめ:")
        print("  1. buffer_sizeを用途に応じて調整（50-1000）")
        print("  2. hot_capacityをデータセットサイズに合わせる")
        print("  3. persist_modeを要件に応じて選択")
        print("  4. 大量データはbulk_insertを活用")
        print("  5. 本番環境ではwritethroughモード推奨")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

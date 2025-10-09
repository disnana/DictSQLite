#!/usr/bin/env python3
"""
DictSQLite v4.2 基本使用例

v4.2の基本的な使い方を示すサンプルコード
"""
import sys
import os
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


def example_1_basic_usage():
    """例1: 基本的な使用方法"""
    print("\n" + "="*70)
    print("例1: 基本的な使用方法")
    print("="*70)
    
    # メモリ上のデータベース（永続化なし）
    # デフォルトはPickleモード：Python オブジェクトを自動的にシリアライズ
    db = DictSQLiteV4(":memory:")
    
    # 文字列を直接保存（Pickleモードで自動シリアライズ）
    db["user:alice"] = "Alice Smith"
    db["user:bob"] = "Bob Jones"
    db["user:charlie"] = "Charlie Brown"
    
    print("✓ データを保存しました（Pickleモードで自動シリアライズ）")
    
    # 読み込み（自動デシリアライズされて元の文字列が返る）
    alice = db["user:alice"]
    print(f"  Alice: {alice}")
    print(f"  型: {type(alice)}")
    
    # 存在確認
    if "user:alice" in db:
        print("✓ user:alice が存在します")
    
    # 削除
    del db["user:bob"]
    print("✓ user:bob を削除しました")
    
    # キーの一覧
    keys = list(db.keys())
    print(f"✓ 残りのキー: {keys}")
    
    # 統計情報
    stats = db.stats()
    print(f"\n統計情報:")
    print(f"  エントリ数: {stats['hot_tier_size']}")
    print(f"  暗号化: {stats['encryption_enabled']}")
    print(f"  Safe Pickle: {stats['safe_pickle_enabled']}")
    
    db.close()


def example_2_file_persistence():
    """例2: ファイルへの永続化"""
    print("\n" + "="*70)
    print("例2: ファイルへの永続化")
    print("="*70)
    
    # 一時ファイル作成
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        # データベースを作成して書き込み
        print(f"データベースパス: {db_path}")
        db = DictSQLiteV4(db_path)
        
        # Pickleモードなら文字列や数値を直接保存可能
        db["message"] = "Hello, DictSQLite v4.2!"
        db["count"] = 42
        
        print("✓ データを保存しました")
        db.close()
        
        # データベースを再度開いて読み込み
        print("\nデータベースを再度開きます...")
        db2 = DictSQLiteV4(db_path)
        
        # 自動デシリアライズされて元の型で取得
        message = db2["message"]
        count = db2["count"]
        
        print(f"✓ 読み込み成功:")
        print(f"  message: {message} (型: {type(message).__name__})")
        print(f"  count: {count} (型: {type(count).__name__})")
        
        db2.close()
        
    finally:
        # クリーンアップ
        try:
            os.unlink(db_path)
        except:
            pass


def example_3_buffer_size():
    """例3: バッファサイズの調整"""
    print("\n" + "="*70)
    print("例3: バッファサイズの調整（v4.2の新機能）")
    print("="*70)
    
    import time
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        # 小さいバッファサイズ（頻繁にフラッシュ）
        print("\n1. buffer_size=50 でテスト")
        db_small = DictSQLiteV4(db_path, buffer_size=50)
        
        start = time.time()
        for i in range(100):
            db_small[f"key:{i}"] = f"value_{i}".encode('utf-8')
        elapsed_small = time.time() - start
        
        print(f"  100件の書き込み: {elapsed_small:.4f}秒")
        print(f"  スループット: {100/elapsed_small:.0f} ops/sec")
        db_small.close()
        
        # ファイル削除
        os.unlink(db_path)
        
        # 大きいバッファサイズ（まとめてフラッシュ）
        print("\n2. buffer_size=500 でテスト")
        db_large = DictSQLiteV4(db_path, buffer_size=500)
        
        start = time.time()
        for i in range(100):
            db_large[f"key:{i}"] = f"value_{i}"  # Pickleモードで自動変換
        elapsed_large = time.time() - start
        
        print(f"  100件の書き込み: {elapsed_large:.4f}秒")
        print(f"  スループット: {100/elapsed_large:.0f} ops/sec")
        
        # バッファに残っているデータを明示的にフラッシュ
        db_large.flush()
        print("✓ バッファをフラッシュしました")
        
        db_large.close()
        
        if elapsed_large < elapsed_small:
            improvement = elapsed_small / elapsed_large
            print(f"\n✓ 大きいバッファで {improvement:.1f}倍高速化しました")
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def example_4_bulk_insert():
    """例4: 一括挿入（bulk_insert）"""
    print("\n" + "="*70)
    print("例4: 一括挿入（bulk_insert）")
    print("="*70)
    
    import time
    
    db = DictSQLiteV4(":memory:")
    
    # 大量データの準備
    data = {
        f"record:{i}": f"data_{i}"  # Pickleモードで自動変換
        for i in range(1000)
    }
    
    # 方法1: 通常の書き込み
    print("\n方法1: 通常の書き込み（forループ）")
    db.clear()
    start = time.time()
    for key, value in data.items():
        db[key] = value
    elapsed_normal = time.time() - start
    print(f"  1000件の書き込み: {elapsed_normal:.4f}秒")
    print(f"  スループット: {1000/elapsed_normal:.0f} ops/sec")
    
    # 方法2: bulk_insert
    print("\n方法2: bulk_insert")
    db.clear()
    start = time.time()
    db.bulk_insert(data)
    elapsed_bulk = time.time() - start
    print(f"  1000件の書き込み: {elapsed_bulk:.4f}秒")
    print(f"  スループット: {1000/elapsed_bulk:.0f} ops/sec")
    
    if elapsed_bulk < elapsed_normal:
        improvement = elapsed_normal / elapsed_bulk
        print(f"\n✓ bulk_insertで {improvement:.1f}倍高速化しました")
    
    # データ確認
    stats = db.stats()
    print(f"\n統計: {stats['hot_tier_size']} エントリ")
    
    db.close()


def example_5_context_manager():
    """例5: コンテキストマネージャ"""
    print("\n" + "="*70)
    print("例5: コンテキストマネージャ（自動flush/close）")
    print("="*70)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        # withステートメントで自動的にflush/closeされる
        with DictSQLiteV4(db_path, buffer_size=500) as db:
            print("データベースを開きました（コンテキストマネージャ）")
            
            # データ書き込み
            for i in range(100):
                db[f"item:{i}"] = f"value_{i}"  # Pickleモードで自動変換
            
            print("✓ 100件のデータを書き込みました")
            print("ブロック終了時に自動的にflush()とclose()が呼ばれます")
        
        # ここで自動的にflush()とclose()が実行される
        print("✓ コンテキストマネージャ終了")
        
        # データが永続化されていることを確認
        with DictSQLiteV4(db_path) as db:
            count = len(list(db.keys()))
            print(f"✓ データベースを再度開いて確認: {count}件のエントリ")
            
            # サンプル取得（自動デシリアライズ）
            sample = db["item:0"]
            print(f"  item:0 = {sample}")
    
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def example_6_persist_modes():
    """例6: 永続化モード"""
    print("\n" + "="*70)
    print("例6: 永続化モード（memory / lazy / writethrough）")
    print("="*70)
    
    # モード1: memory（永続化なし、最速）
    print("\n1. memory モード（永続化なし）")
    db_mem = DictSQLiteV4(":memory:", persist_mode="memory")
    db_mem["temp"] = b"temporary data"
    print("  ✓ データはメモリのみに保存（ディスク書き込みなし）")
    db_mem.close()
    
    # モード2: lazy（遅延書き込み、flush時に永続化）
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        print("\n2. lazy モード（遅延書き込み）")
        db_lazy = DictSQLiteV4(db_path, persist_mode="lazy")
        db_lazy["data1"] = b"value1"
        db_lazy["data2"] = b"value2"
        print("  ✓ データはまだディスクに書き込まれていません")
        
        db_lazy.flush()
        print("  ✓ flush()でディスクに書き込みました")
        db_lazy.close()
        
        os.unlink(db_path)
        
        # モード3: writethrough（即座に永続化、バッファリング付き）
        print("\n3. writethrough モード（バッファ付き即座永続化）")
        db_wt = DictSQLiteV4(db_path, persist_mode="writethrough", buffer_size=100)
        
        for i in range(150):
            db_wt[f"key:{i}"] = f"value_{i}"  # Pickleモードで自動変換
        
        print("  ✓ buffer_size(100)に達すると自動的にディスクに書き込み")
        print("  ✓ データの安全性とパフォーマンスのバランスが良い")
        
        db_wt.close()
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def main():
    """メイン関数"""
    print("="*70)
    print("DictSQLite v4.2 基本使用例")
    print("="*70)
    
    try:
        example_1_basic_usage()
        example_2_file_persistence()
        example_3_buffer_size()
        example_4_bulk_insert()
        example_5_context_manager()
        example_6_persist_modes()
        
        print("\n" + "="*70)
        print("すべての例が正常に完了しました！")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
DictSQLite v1.8.8 から v4.2 への移行サンプル

実際のコードを v1.8.8 から v4.2 に移行する方法を示す
"""
import sys
import os
import tempfile
import pickle

# v4.2モジュールのインポート
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')
    from __init__ import DictSQLiteV4
except ImportError as e:
    print("エラー: dictsqlite_v4 モジュールがビルドされていません")
    print("ビルド方法: cd others/beta-versions/dictsqlite_v4.2 && maturin develop --release")
    print(f"詳細: {e}")
    sys.exit(1)


def migration_example_1_simple_strings():
    """移行例1: シンプルな文字列データ"""
    print("\n" + "="*70)
    print("移行例1: シンプルな文字列データ")
    print("="*70)
    
    print("\n【v1.8.8のコード】")
    print("""
    from dictsqlite import DictSQLite
    
    db = DictSQLite('users.db')
    db['user:alice'] = 'Alice Smith'      # 文字列を直接保存
    db['user:bob'] = 'Bob Jones'
    
    alice = db['user:alice']              # 文字列が返る
    print(alice)  # => 'Alice Smith'
    """)
    
    print("\n【v4.2への移行】")
    db = DictSQLiteV4(':memory:')
    
    # 文字列をbytesに変換して保存
    db['user:alice'] = 'Alice Smith'.encode('utf-8')
    db['user:bob'] = 'Bob Jones'.encode('utf-8')
    
    # bytes型で読み込み、strに変換
    alice_bytes = db['user:alice']
    alice = alice_bytes.decode('utf-8')
    
    print(f"✓ Alice: {alice}")
    print(f"  型: {type(alice)}")
    
    db.close()


def migration_example_2_complex_data():
    """移行例2: 複雑なデータ（辞書、リスト）"""
    print("\n" + "="*70)
    print("移行例2: 複雑なデータ（辞書、リスト）")
    print("="*70)
    
    print("\n【v1.8.8のコード】")
    print("""
    db = DictSQLite('data.db')
    
    # 辞書を自動pickle化して保存
    db['config'] = {'theme': 'dark', 'lang': 'ja'}
    db['scores'] = [95, 87, 92, 88]
    
    config = db['config']  # 自動unpickle
    print(config['theme'])  # => 'dark'
    """)
    
    print("\n【v4.2への移行】")
    db = DictSQLiteV4(':memory:')
    
    # pickle.dumps()で明示的にシリアライズ
    config_data = {'theme': 'dark', 'lang': 'ja', 'version': '2.0'}
    db['config'] = pickle.dumps(config_data)
    
    scores_data = [95, 87, 92, 88, 91]
    db['scores'] = pickle.dumps(scores_data)
    
    # pickle.loads()で明示的にデシリアライズ
    config = pickle.loads(db['config'])
    scores = pickle.loads(db['scores'])
    
    print(f"✓ Config: {config}")
    print(f"  Theme: {config['theme']}")
    print(f"✓ Scores: {scores}")
    print(f"  Average: {sum(scores)/len(scores):.1f}")
    
    db.close()


def migration_example_3_encryption():
    """移行例3: 暗号化データベース"""
    print("\n" + "="*70)
    print("移行例3: 暗号化データベース")
    print("="*70)
    
    print("\n【v1.8.8のコード】")
    print("""
    db = DictSQLite('secrets.db', password='my_password')
    db['api_key'] = 'sk-1234567890'
    """)
    
    print("\n【v4.2への移行】")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        # パラメータ名が encryption_password に変更
        db = DictSQLiteV4(db_path, encryption_password='my_password')
        
        # bytes型で保存
        db['api_key'] = 'sk-1234567890'.encode('utf-8')
        db['secret_token'] = b'eyJhbGciOiJIUzI1NiIs...'
        
        print("✓ 暗号化データを保存しました")
        
        # 統計で暗号化が有効か確認
        stats = db.stats()
        print(f"  暗号化: {stats['encryption_enabled']}")
        
        db.close()
        
        # 再度開いて復号化
        db2 = DictSQLiteV4(db_path, encryption_password='my_password')
        api_key = db2['api_key'].decode('utf-8')
        print(f"✓ 復号化成功: {api_key}")
        
        db2.close()
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def migration_example_4_bulk_operations():
    """移行例4: 大量データの一括操作"""
    print("\n" + "="*70)
    print("移行例4: 大量データの一括操作")
    print("="*70)
    
    print("\n【v1.8.8のコード】")
    print("""
    db = DictSQLite('bulk.db')
    
    # forループで1件ずつ保存
    for i in range(1000):
        db[f'record:{i}'] = f'data_{i}'
    """)
    
    print("\n【v4.2への移行（最適化版）】")
    db = DictSQLiteV4(':memory:', buffer_size=500)
    
    import time
    
    # 方法1: 従来通りforループ（バッファリングで自動最適化）
    print("\n方法1: forループ（バッファリング付き）")
    start = time.time()
    for i in range(1000):
        db[f'record:{i}'] = f'data_{i}'.encode('utf-8')
    elapsed1 = time.time() - start
    print(f"  1000件: {elapsed1:.3f}秒 ({1000/elapsed1:.0f} ops/sec)")
    
    db.clear()
    
    # 方法2: bulk_insert（最速）
    print("\n方法2: bulk_insert（推奨）")
    data = {
        f'record:{i}': f'data_{i}'.encode('utf-8')
        for i in range(1000)
    }
    start = time.time()
    db.bulk_insert(data)
    elapsed2 = time.time() - start
    print(f"  1000件: {elapsed2:.3f}秒 ({1000/elapsed2:.0f} ops/sec)")
    
    if elapsed2 < elapsed1:
        improvement = elapsed1 / elapsed2
        print(f"\n✓ bulk_insertで {improvement:.1f}倍高速化")
    
    db.close()


def migration_example_5_real_world():
    """移行例5: 実践的なユースケース（ユーザーデータ管理）"""
    print("\n" + "="*70)
    print("移行例5: 実践的なユースケース（ユーザーデータ管理）")
    print("="*70)
    
    print("\n【シナリオ】")
    print("  Webアプリケーションのユーザーセッション管理")
    print("  - ユーザー情報の保存")
    print("  - セッションデータの管理")
    print("  - 高速な読み書き")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        # 最適化されたv4.2設定
        db = DictSQLiteV4(
            db_path,
            hot_capacity=100_000,      # アクティブセッション用のキャッシュ
            buffer_size=200,           # バランスの良いバッファ
            persist_mode="writethrough",  # データ保証
            encryption_password="session_secret_key"  # セッションの暗号化
        )
        
        print("\n✓ データベース初期化完了")
        print(f"  hot_capacity: 100,000")
        print(f"  buffer_size: 200")
        print(f"  persist_mode: writethrough")
        print(f"  encryption: 有効")
        
        # ユーザーデータの保存
        users = [
            {'id': 'user1', 'name': 'Alice', 'email': 'alice@example.com', 'role': 'admin'},
            {'id': 'user2', 'name': 'Bob', 'email': 'bob@example.com', 'role': 'user'},
            {'id': 'user3', 'name': 'Charlie', 'email': 'charlie@example.com', 'role': 'user'},
        ]
        
        print("\nユーザーデータを保存...")
        for user in users:
            user_id = user['id']
            # pickleでシリアライズして暗号化保存
            db[f'user:{user_id}'] = pickle.dumps(user)
        
        print(f"✓ {len(users)}人のユーザーを保存")
        
        # セッションデータの保存
        sessions = {
            'sess:abc123': {'user_id': 'user1', 'login_time': '2024-01-15 10:30:00', 'ip': '192.168.1.100'},
            'sess:def456': {'user_id': 'user2', 'login_time': '2024-01-15 11:00:00', 'ip': '192.168.1.101'},
        }
        
        print("\nセッションデータを保存...")
        for sess_id, sess_data in sessions.items():
            db[sess_id] = pickle.dumps(sess_data)
        
        print(f"✓ {len(sessions)}個のセッションを保存")
        
        # データの読み込みと検証
        print("\nデータ読み込みテスト:")
        user1 = pickle.loads(db['user:user1'])
        print(f"  User1: {user1['name']} ({user1['email']}) - {user1['role']}")
        
        sess1 = pickle.loads(db['sess:abc123'])
        print(f"  Session: {sess1['user_id']} logged in at {sess1['login_time']}")
        
        # 統計情報
        stats = db.stats()
        print(f"\n統計情報:")
        print(f"  総エントリ数: {stats['hot_tier_size']}")
        print(f"  暗号化: {stats['encryption_enabled']}")
        
        db.close()
        print("\n✓ すべての操作が完了しました")
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def main():
    """メイン関数"""
    print("="*70)
    print("DictSQLite v1.8.8 → v4.2 移行サンプル")
    print("="*70)
    
    try:
        migration_example_1_simple_strings()
        migration_example_2_complex_data()
        migration_example_3_encryption()
        migration_example_4_bulk_operations()
        migration_example_5_real_world()
        
        print("\n" + "="*70)
        print("すべての移行例が正常に完了しました！")
        print("="*70)
        print("\n📚 詳細は MIGRATION_GUIDE_V4.2_JP.md を参照してください")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
DictSQLite v4.2 高度な機能例

暗号化、Safe Pickle、非同期処理など、v4.2の高度な機能を示す
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


def example_encryption():
    """例1: AES-256-GCM暗号化"""
    print("\n" + "="*70)
    print("例1: AES-256-GCM暗号化")
    print("="*70)
    
    print("\nDictSQLite v4.2はネイティブでAES-256-GCM暗号化をサポートします。")
    print("データはディスク上で暗号化され、メモリ上でのみ復号化されます。")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        # 暗号化データベースの作成
        print("\n1. 暗号化データベースを作成...")
        db = DictSQLiteV4(
            db_path,
            encryption_password='super_secret_password_2024'
        )
        
        # 機密データの保存
        db['api_key'] = b'sk-1234567890abcdef'
        db['database_password'] = b'db_pass_xyz'
        db['private_token'] = 'eyJhbGciOiJIUzI1NiIs...'.encode('utf-8')
        
        # 複雑なオブジェクトも暗号化して保存
        secret_config = {
            'aws_access_key': 'AKIAIOSFODNN7EXAMPLE',
            'aws_secret_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
            'database_url': 'postgresql://user:pass@host/db'
        }
        db['secret_config'] = pickle.dumps(secret_config)
        
        print("✓ 機密データを暗号化して保存しました")
        
        # 統計で暗号化を確認
        stats = db.stats()
        print(f"  暗号化: {stats['encryption_enabled']}")
        print(f"  エントリ数: {stats['hot_tier_size']}")
        
        db.close()
        
        # データベースを再度開く
        print("\n2. 暗号化データベースを再度開く...")
        db2 = DictSQLiteV4(
            db_path,
            encryption_password='super_secret_password_2024'
        )
        
        # データの復号化と読み込み
        api_key = db2['api_key'].decode('utf-8')
        config = pickle.loads(db2['secret_config'])
        
        print(f"✓ 復号化成功:")
        print(f"  API Key: {api_key[:10]}...")
        print(f"  AWS Access Key: {config['aws_access_key'][:10]}...")
        
        db2.close()
        
        # 間違ったパスワードでのテスト
        print("\n3. 間違ったパスワードでアクセス...")
        try:
            db3 = DictSQLiteV4(
                db_path,
                encryption_password='wrong_password'
            )
            _ = db3['api_key']
            db3.close()
            print("❌ エラーが検出されませんでした（問題あり）")
        except Exception as e:
            print(f"✓ 正しくエラーが発生: 復号化に失敗")
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def example_safe_pickle():
    """例2: Safe Pickle"""
    print("\n" + "="*70)
    print("例2: Safe Pickle（安全なデシリアライゼーション）")
    print("="*70)
    
    print("\nSafe Pickleは信頼できないデータのデシリアライゼーションを")
    print("安全に行うための機能です。許可されたモジュールのみ読み込みます。")
    
    # カスタムクラスの定義（通常は別モジュール）
    class User:
        def __init__(self, name, age):
            self.name = name
            self.age = age
        
        def __repr__(self):
            return f"User(name='{self.name}', age={self.age})"
    
    # Safe Pickle有効化
    print("\n1. Safe Pickle有効化...")
    db = DictSQLiteV4(
        ':memory:',
        enable_safe_pickle=True,
        safe_pickle_allowed_modules=['__main__', 'builtins']
    )
    
    # 許可されたモジュールのオブジェクトを保存
    user = User('Alice', 30)
    db['user:alice'] = pickle.dumps(user)
    
    print(f"✓ ユーザーオブジェクトを保存: {user}")
    
    # 読み込み（Safe Pickleで検証される）
    loaded_user_bytes = db['user:alice']
    loaded_user = pickle.loads(loaded_user_bytes)
    print(f"✓ Safe Pickleで読み込み: {loaded_user}")
    
    # 基本的なPython型も使用可能
    db['config'] = pickle.dumps({'theme': 'dark', 'lang': 'ja'})
    db['scores'] = pickle.dumps([95, 87, 92, 88])
    
    config = pickle.loads(db['config'])
    scores = pickle.loads(db['scores'])
    
    print(f"✓ 辞書: {config}")
    print(f"✓ リスト: {scores}")
    
    stats = db.stats()
    print(f"\n統計:")
    print(f"  Safe Pickle: {stats['safe_pickle_enabled']}")
    
    db.close()


def example_combined_security():
    """例3: 暗号化 + Safe Pickle（最高セキュリティ）"""
    print("\n" + "="*70)
    print("例3: 暗号化 + Safe Pickle（最高セキュリティ）")
    print("="*70)
    
    print("\n暗号化とSafe Pickleを組み合わせることで、")
    print("最高レベルのセキュリティを実現できます。")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        # 最高セキュリティ設定
        db = DictSQLiteV4(
            db_path,
            encryption_password='secure_password_2024',
            enable_safe_pickle=True,
            safe_pickle_allowed_modules=['__main__', 'builtins']
        )
        
        # データの保存
        secure_data = {
            'user_id': 12345,
            'permissions': ['read', 'write', 'admin'],
            'api_keys': {
                'production': 'prod_key_xyz',
                'staging': 'stg_key_abc'
            }
        }
        
        db['secure_data'] = pickle.dumps(secure_data)
        
        print("✓ データを暗号化 + Safe Pickleで保存")
        
        stats = db.stats()
        print(f"\nセキュリティ設定:")
        print(f"  暗号化: {stats['encryption_enabled']}")
        print(f"  Safe Pickle: {stats['safe_pickle_enabled']}")
        
        db.close()
        
        # 再度開いて読み込み
        db2 = DictSQLiteV4(
            db_path,
            encryption_password='secure_password_2024',
            enable_safe_pickle=True,
            safe_pickle_allowed_modules=['__main__', 'builtins']
        )
        
        loaded_data = pickle.loads(db2['secure_data'])
        print(f"\n✓ 復号化 + Safe Pickle検証成功:")
        print(f"  User ID: {loaded_data['user_id']}")
        print(f"  Permissions: {loaded_data['permissions']}")
        
        db2.close()
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def example_stats_monitoring():
    """例4: 統計情報とモニタリング"""
    print("\n" + "="*70)
    print("例4: 統計情報とモニタリング")
    print("="*70)
    
    print("\nstats()メソッドでデータベースの状態を監視できます。")
    
    db = DictSQLiteV4(
        ':memory:',
        hot_capacity=1000,
        buffer_size=100
    )
    
    # データ投入
    print("\n1. データ投入...")
    for i in range(500):
        db[f'key:{i}'] = f'value_{i}'.encode('utf-8')
    
    # 統計情報取得
    stats = db.stats()
    
    print("\n統計情報:")
    print(f"  ホットティアサイズ: {stats['hot_tier_size']}")
    print(f"  暗号化: {stats['encryption_enabled']}")
    print(f"  Safe Pickle: {stats['safe_pickle_enabled']}")
    
    # さらにデータ追加
    print("\n2. さらにデータ追加...")
    for i in range(500, 1500):
        db[f'key:{i}'] = f'value_{i}'.encode('utf-8')
    
    stats = db.stats()
    print(f"\n更新後のホットティアサイズ: {stats['hot_tier_size']}")
    print(f"(hot_capacity={1000}を超えるとLRUでエビクション)")
    
    db.close()


def example_large_values():
    """例5: 大きな値の扱い"""
    print("\n" + "="*70)
    print("例5: 大きな値の扱い")
    print("="*70)
    
    print("\nDictSQLite v4.2は大きなバイナリデータも効率的に扱えます。")
    
    db = DictSQLiteV4(':memory:', hot_capacity=100)
    
    # 大きなバイナリデータ
    print("\n1. 大きなバイナリデータ（1MB）を保存...")
    large_data = b'X' * (1024 * 1024)  # 1MB
    db['large_binary'] = large_data
    print(f"✓ {len(large_data):,} bytes を保存")
    
    # 読み込み
    loaded = db['large_binary']
    print(f"✓ {len(loaded):,} bytes を読み込み")
    assert loaded == large_data
    print("✓ データ整合性確認OK")
    
    # 大きなオブジェクト
    print("\n2. 大きなリストオブジェクトを保存...")
    large_list = list(range(100_000))  # 10万個の整数
    db['large_list'] = pickle.dumps(large_list)
    print(f"✓ {len(large_list):,}個の要素を保存")
    
    loaded_list = pickle.loads(db['large_list'])
    print(f"✓ {len(loaded_list):,}個の要素を読み込み")
    assert loaded_list == large_list
    print("✓ データ整合性確認OK")
    
    db.close()


def example_transaction_pattern():
    """例6: トランザクションパターン"""
    print("\n" + "="*70)
    print("例6: トランザクションパターン（コンテキストマネージャ）")
    print("="*70)
    
    print("\nコンテキストマネージャを使うと、確実にデータがフラッシュされます。")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        # パターン1: 通常のトランザクション
        print("\n1. 通常のトランザクション")
        with DictSQLiteV4(db_path, buffer_size=500) as db:
            for i in range(1000):
                db[f'trans:{i}'] = f'value_{i}'.encode('utf-8')
            print("  ✓ 1000件のデータを書き込み")
            # withブロック終了時に自動的にflush()とclose()
        
        print("  ✓ 自動的にflush & close")
        
        # データの確認
        print("\n2. データ確認")
        with DictSQLiteV4(db_path) as db:
            count = len(list(db.keys()))
            print(f"  ✓ {count}件のデータが永続化されています")
        
        # パターン2: エラー時のロールバック風処理
        print("\n3. エラーハンドリング")
        try:
            with DictSQLiteV4(db_path) as db:
                db['test1'] = b'value1'
                db['test2'] = b'value2'
                # エラーが発生してもflush()は実行される
                # raise Exception("Simulated error")
                db['test3'] = b'value3'
            print("  ✓ エラーがなければ正常にflush")
        except Exception as e:
            print(f"  ⚠ エラー発生: {e}")
            print("  （flush()は実行されています）")
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def main():
    """メイン関数"""
    print("="*70)
    print("DictSQLite v4.2 高度な機能例")
    print("="*70)
    
    try:
        example_encryption()
        example_safe_pickle()
        example_combined_security()
        example_stats_monitoring()
        example_large_values()
        example_transaction_pattern()
        
        print("\n" + "="*70)
        print("すべての例が正常に完了しました！")
        print("="*70)
        
        print("\n🔒 セキュリティのまとめ:")
        print("  1. 機密データには暗号化を使用")
        print("  2. 信頼できないデータにはSafe Pickleを使用")
        print("  3. 最高セキュリティには両方を組み合わせる")
        print("  4. コンテキストマネージャで確実にflush")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

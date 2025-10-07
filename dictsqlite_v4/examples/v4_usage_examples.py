#!/usr/bin/env python3
"""
DictSQLite v4.0 使用例

暗号化とSafe Pickle機能のデモンストレーション
"""
import pickle
import tempfile
import os

try:
    from dictsqlite_v4 import DictSQLiteV4
except ImportError:
    print("エラー: dictsqlite_v4 モジュールがビルドされていません")
    print("ビルド方法: cd dictsqlite_v4 && maturin develop --release")
    exit(1)


def example_basic():
    """例1: 基本的な使用方法"""
    print("\n" + "="*60)
    print("例1: 基本的な使用方法（暗号化なし）")
    print("="*60)
    
    db = DictSQLiteV4(":memory:")
    
    # 辞書のように使用
    db["user:alice"] = b"Alice's data"
    db["user:bob"] = b"Bob's data"
    
    print(f"Alice: {db['user:alice']}")
    print(f"Bob: {db['user:bob']}")
    
    # 統計情報
    stats = db.stats()
    print(f"\n統計:")
    print(f"  保存アイテム数: {stats['hot_tier_size']}")
    print(f"  暗号化: {stats['encryption_enabled']}")
    print(f"  Safe Pickle: {stats['safe_pickle_enabled']}")


def example_encryption():
    """例2: 暗号化の使用"""
    print("\n" + "="*60)
    print("例2: AES-256-GCM 暗号化")
    print("="*60)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        # 暗号化を有効にしてデータベースを作成
        db = DictSQLiteV4(
            db_path,
            encryption_password="my_secure_password_123"
        )
        
        # 機密データを保存
        db["api_key"] = b"sk-1234567890abcdef"
        db["password"] = b"super_secret_password"
        db["credit_card"] = b"1234-5678-9012-3456"
        
        print("✓ 機密データを暗号化して保存しました")
        
        # データを読み込み（自動復号化）
        api_key = db["api_key"]
        print(f"✓ APIキーを復号化: {api_key[:10]}...")
        
        # 統計で暗号化が有効か確認
        stats = db.stats()
        print(f"\n統計:")
        print(f"  暗号化: {stats['encryption_enabled']}")
        print(f"  保存アイテム数: {stats['hot_tier_size']}")
        
        db.close()
        
        # 同じパスワードで再度開く
        print("\nデータベースを再度開きます...")
        db2 = DictSQLiteV4(
            db_path,
            encryption_password="my_secure_password_123"
        )
        
        # データが正しく復号化されることを確認
        assert db2["api_key"] == b"sk-1234567890abcdef"
        print("✓ データが正しく永続化・復号化されました")
        
        db2.close()
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def example_safe_pickle():
    """例3: Safe Pickle の使用"""
    print("\n" + "="*60)
    print("例3: Safe Pickle（安全なpickle）")
    print("="*60)
    
    # 基本的な使用（デフォルトポリシー）
    print("\n▶ デフォルトポリシー（基本型のみ）")
    db = DictSQLiteV4(
        ":memory:",
        enable_safe_pickle=True
    )
    
    # 基本的なデータ構造を保存
    user_data = {
        "id": 1,
        "name": "Alice",
        "email": "alice@example.com",
        "age": 30,
        "hobbies": ["reading", "coding", "music"],
        "metadata": {
            "created_at": "2024-01-01",
            "updated_at": "2024-01-15",
        }
    }
    
    # pickleして保存
    db["user:1"] = pickle.dumps(user_data)
    print("✓ ユーザーデータを保存しました")
    
    # 読み込みと復元
    restored = pickle.loads(db["user:1"])
    print(f"\n復元されたデータ:")
    print(f"  名前: {restored['name']}")
    print(f"  メール: {restored['email']}")
    print(f"  趣味: {', '.join(restored['hobbies'])}")
    
    # カスタムモジュールの許可（v1互換機能）
    print("\n▶ カスタムモジュールポリシー")
    print("  指定したモジュールプレフィックスを許可できます")
    print("  例: safe_pickle_allowed_modules=['myapp', 'mylib']")
    print("  → myapp.*とmylib.*配下のクラスが使用可能")
    
    # 統計
    stats = db.stats()
    print(f"\n統計:")
    print(f"  Safe Pickle: {stats['safe_pickle_enabled']}")


def example_combined():
    """例4: 暗号化 + Safe Pickle の組み合わせ"""
    print("\n" + "="*60)
    print("例4: 暗号化 + Safe Pickle（最高セキュリティ）")
    print("="*60)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        # 両方の機能を有効化
        db = DictSQLiteV4(
            db_path,
            encryption_password="ultra_secure_password",
            enable_safe_pickle=True
        )
        
        # 複数のユーザーデータを保存
        users = [
            {"id": 1, "name": "Alice", "role": "admin", "salary": 100000},
            {"id": 2, "name": "Bob", "role": "developer", "salary": 80000},
            {"id": 3, "name": "Charlie", "role": "designer", "salary": 75000},
        ]
        
        for user in users:
            key = f"user:{user['id']}"
            db[key] = pickle.dumps(user)
        
        print(f"✓ {len(users)}人のユーザーデータを暗号化して保存しました")
        
        # データを読み込み
        print("\n保存されたユーザー:")
        for i in range(1, len(users) + 1):
            user = pickle.loads(db[f"user:{i}"])
            print(f"  {user['name']:10s} - {user['role']:10s} - ${user['salary']:,}")
        
        # セキュリティ設定を確認
        stats = db.stats()
        print(f"\nセキュリティ設定:")
        print(f"  暗号化: {'✅' if stats['encryption_enabled'] else '❌'}")
        print(f"  Safe Pickle: {'✅' if stats['safe_pickle_enabled'] else '❌'}")
        
        db.close()
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def example_performance_modes():
    """例5: パフォーマンスモードの使い分け"""
    print("\n" + "="*60)
    print("例5: パフォーマンスモードの使い分け")
    print("="*60)
    
    # メモリモード（最速、永続化なし）
    print("\n1. メモリモード（最速）")
    db_memory = DictSQLiteV4(
        ":memory:",
        persist_mode="memory",
        encryption_password="test"
    )
    db_memory["key"] = b"value"
    print(f"   保存アイテム: {db_memory.stats()['hot_tier_size']}")
    
    # 遅延永続化モード（高速 + 永続化）
    print("\n2. 遅延永続化モード（高速 + 永続化）")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path_lazy = f.name
    
    try:
        db_lazy = DictSQLiteV4(
            db_path_lazy,
            persist_mode="lazy",
            encryption_password="test"
        )
        
        # データを保存
        for i in range(100):
            db_lazy[f"key_{i}"] = f"value_{i}".encode()
        
        print(f"   保存アイテム: {db_lazy.stats()['hot_tier_size']}")
        
        # 手動でフラッシュして永続化
        db_lazy.flush()
        print("   ✓ データをディスクに永続化しました")
        
        db_lazy.close()
        
    finally:
        try:
            os.unlink(db_path_lazy)
        except:
            pass
    
    # 即時永続化モード（最も安全）
    print("\n3. 即時永続化モード（最も安全）")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path_wt = f.name
    
    try:
        db_writethrough = DictSQLiteV4(
            db_path_wt,
            persist_mode="writethrough",
            encryption_password="test"
        )
        
        db_writethrough["important"] = b"critical data"
        print("   ✓ データは即座にディスクに書き込まれます")
        
        db_writethrough.close()
        
    finally:
        try:
            os.unlink(db_path_wt)
        except:
            pass


def main():
    print("="*60)
    print("DictSQLite v4.0 使用例デモンストレーション")
    print("="*60)
    
    example_basic()
    example_encryption()
    example_safe_pickle()
    example_combined()
    example_performance_modes()
    
    print("\n" + "="*60)
    print("すべての例が正常に完了しました！")
    print("="*60)
    
    print("\n推奨事項:")
    print("  • 機密データには必ず暗号化を使用")
    print("  • 信頼できないデータにはSafe Pickleを使用")
    print("  • 最高セキュリティには両方を組み合わせる")
    print("  • パスワードは環境変数から読み込む")
    print("  • データベースファイルのパーミッションを制限")


if __name__ == "__main__":
    main()

"""
DictSQLite v4.2 非同期版 使用例

AsyncDictSQLiteの新機能（JSONB、テーブルサポート）の使い方を示す包括的な例
"""

try:
    from dictsqlite_v4 import AsyncDictSQLite
except ImportError:
    print("❌ Please build dictsqlite_v4 first with: maturin develop --release")
    exit(1)

import os
import tempfile
import time

print("=" * 70)
print("DictSQLite v4.2 - AsyncDictSQLite 使用例")
print("=" * 70)

# 一時ディレクトリ作成
tmpdir = tempfile.mkdtemp()
print(f"\n一時ディレクトリ: {tmpdir}")

# ============================================================================
# 例1: JSONBモードでの基本操作
# ============================================================================
print("\n" + "=" * 70)
print("例1: JSONBモードでの基本操作")
print("=" * 70)

db_jsonb = AsyncDictSQLite(
    os.path.join(tmpdir, "async_jsonb.db"),
    storage_mode="jsonb",
    capacity=10000,
    persist_mode="lazy"
)

# 辞書データの保存
user_data = {
    "name": "田中太郎",
    "age": 30,
    "email": "tanaka@example.com",
    "skills": ["Python", "Rust", "JavaScript"],
    "active": True
}

db_jsonb["user:tanaka"] = user_data
print("\n✓ ユーザーデータをJSONB形式で保存")

# 取得
retrieved = db_jsonb["user:tanaka"]
print(f"\n✓ 取得したデータ:")
print(f"  名前: {retrieved['name']}")
print(f"  年齢: {retrieved['age']}")
print(f"  スキル: {', '.join(retrieved['skills'])}")

# 統計
size, cap = db_jsonb.stats()
print(f"\n✓ キャッシュ統計: {size}/{cap} エントリ")

db_jsonb.flush()
db_jsonb.close()

# ============================================================================
# 例2: テーブル操作（非同期版）
# ============================================================================
print("\n" + "=" * 70)
print("例2: テーブル操作")
print("=" * 70)

db_tables = AsyncDictSQLite(
    os.path.join(tmpdir, "async_tables.db"),
    storage_mode="jsonb"
)

# 複数のテーブルを作成
users = db_tables.table("users")
products = db_tables.table("products")
sessions = db_tables.table("sessions")

# 各テーブルにデータ追加
users["alice"] = {"name": "Alice", "role": "admin", "level": 5}
users["bob"] = {"name": "Bob", "role": "user", "level": 3}

products["laptop"] = {"name": "ノートPC", "price": 120000, "stock": 5}
products["mouse"] = {"name": "マウス", "price": 2500, "stock": 50}

sessions["sess1"] = {"user": "alice", "token": "abc123", "expires": 3600}
sessions["sess2"] = {"user": "bob", "token": "def456", "expires": 3600}

print("\n✓ 3つのテーブルにデータを追加:")
print(f"  - users テーブル: {len(users)} エントリ")
print(f"  - products テーブル: {len(products)} エントリ")  
print(f"  - sessions テーブル: {len(sessions)} エントリ")

# データ取得
print(f"\n✓ データ取得:")
print(f"  User 'alice': {users['alice']['name']} ({users['alice']['role']})")
print(f"  Product 'laptop': {products['laptop']['name']} - ¥{products['laptop']['price']:,}")
print(f"  Session 'sess1': User {sessions['sess1']['user']}")

db_tables.flush()
db_tables.close()

# ============================================================================
# 例3: バッチ操作
# ============================================================================
print("\n" + "=" * 70)
print("例3: バッチ操作（高性能）")
print("=" * 70)

db_batch = AsyncDictSQLite(
    os.path.join(tmpdir, "async_batch.db"),
    storage_mode="jsonb",
    capacity=100000
)

# 大量データの一括書き込み
print("\n✓ 10,000件のデータを一括書き込み中...")
start = time.perf_counter()

items = [
    (f"item_{i}", {"id": i, "value": f"data_{i}", "active": i % 2 == 0})
    for i in range(10000)
]
db_batch.batch_set(items)

elapsed = time.perf_counter() - start
print(f"  完了: {elapsed:.3f}秒 ({10000/elapsed:.0f} ops/sec)")

# バッチ読み込み
print("\n✓ 100件のデータを一括読み込み中...")
start = time.perf_counter()

keys = [f"item_{i}" for i in range(100)]
results = db_batch.batch_get(keys)

elapsed = time.perf_counter() - start
valid_results = sum(1 for r in results if r is not None)
print(f"  完了: {elapsed:.3f}秒 ({valid_results}件取得)")

# 高速バッチ取得（バイト列直接）
print("\n✓ 高速バッチ取得モード...")
start = time.perf_counter()

fast_results = db_batch.batch_get_fast(keys)

elapsed = time.perf_counter() - start
valid_fast = sum(1 for r in fast_results if r is not None)
print(f"  完了: {elapsed:.3f}秒 ({valid_fast}件取得)")

db_batch.clear()
db_batch.close()

# ============================================================================
# 例4: デフォルトテーブル名の使用
# ============================================================================
print("\n" + "=" * 70)
print("例4: デフォルトテーブル名の使用")
print("=" * 70)

# 特定のテーブルをデフォルトに設定
config_db = AsyncDictSQLite(
    os.path.join(tmpdir, "async_config.db"),
    table_name="app_config",  # すべての操作は自動的にこのテーブルに
    storage_mode="json"        # 人間が読める形式
)

# デフォルトテーブルに直接保存
config_db["theme"] = "dark"
config_db["language"] = "ja"
config_db["notifications"] = {
    "email": True,
    "push": False,
    "sms": False
}

print("\n✓ app_config テーブルに設定を保存:")
print(f"  テーマ: {config_db['theme']}")
print(f"  言語: {config_db['language']}")
print(f"  Email通知: {config_db['notifications']['email']}")

config_db.flush()
config_db.close()

# ============================================================================
# 例5: 永続化モードの比較
# ============================================================================
print("\n" + "=" * 70)
print("例5: 永続化モードの比較")
print("=" * 70)

print("\n📊 永続化モードの特徴:")
print("-" * 70)

print("\n1. Memory モード:")
print("   - 速度: 最速（100M+ ops/sec）")
print("   - 永続化: なし（メモリのみ）")
print("   - 用途: キャッシュ、一時データ")

print("\n2. Lazy モード:")
print("   - 速度: 高速（40-80M ops/sec）")
print("   - 永続化: flush()時またはclose()時")
print("   - 用途: バッチ処理、高性能が必要な場合")

print("\n3. WriteThrough モード:")
print("   - 速度: 中速（1-3M ops/sec）")
print("   - 永続化: 即座（バッファリングあり）")
print("   - 用途: データ損失が許容できない場合")

# Memory モードの例
db_memory = AsyncDictSQLite(
    os.path.join(tmpdir, "memory.db"),
    storage_mode="jsonb",
    persist_mode="memory",
    capacity=1000
)

print("\n✓ Memoryモード:")
start = time.perf_counter()
for i in range(1000):
    db_memory[f"key_{i}"] = {"value": i}
elapsed = time.perf_counter() - start
print(f"  1000件書き込み: {elapsed:.3f}秒 ({1000/elapsed:.0f} ops/sec)")
db_memory.close()

# Lazy モードの例
db_lazy = AsyncDictSQLite(
    os.path.join(tmpdir, "lazy.db"),
    storage_mode="jsonb",
    persist_mode="lazy",
    capacity=1000
)

print("\n✓ Lazyモード:")
start = time.perf_counter()
for i in range(1000):
    db_lazy[f"key_{i}"] = {"value": i}
db_lazy.flush()  # 明示的にフラッシュ
elapsed = time.perf_counter() - start
print(f"  1000件書き込み+flush: {elapsed:.3f}秒 ({1000/elapsed:.0f} ops/sec)")
db_lazy.close()

# ============================================================================
# 例6: 並行アクセスパターン
# ============================================================================
print("\n" + "=" * 70)
print("例6: 並行アクセスパターン（シミュレーション）")
print("=" * 70)

db_concurrent = AsyncDictSQLite(
    os.path.join(tmpdir, "concurrent.db"),
    storage_mode="jsonb",
    capacity=10000
)

print("\n✓ 複数のテーブルに並行アクセス...")

# 異なるテーブルへの同時書き込みをシミュレート
tables = {
    "users": db_concurrent.table("users"),
    "posts": db_concurrent.table("posts"),
    "comments": db_concurrent.table("comments"),
}

for i in range(100):
    tables["users"][f"user_{i}"] = {"name": f"User{i}", "active": True}
    tables["posts"][f"post_{i}"] = {"title": f"Post {i}", "author": f"user_{i}"}
    tables["comments"][f"comment_{i}"] = {"post": f"post_{i}", "text": f"Comment {i}"}

print(f"  Users: {len(tables['users'])} エントリ")
print(f"  Posts: {len(tables['posts'])} エントリ")
print(f"  Comments: {len(tables['comments'])} エントリ")

db_concurrent.flush()
db_concurrent.close()

# ============================================================================
# まとめ
# ============================================================================
print("\n" + "=" * 70)
print("✅ すべての例が正常に完了しました！")
print("=" * 70)

print("\n📚 AsyncDictSQLiteの主な特徴:")
print("  - GILなしのキャッシュアクセス（純粋メモリ操作）")
print("  - シャード単位の並行アクセス（CPUコア数に最適化）")
print("  - Rayonによる並列バッチ処理")
print("  - 書き込みバッファリング（300倍高速化）")
print("  - JSONBモードで最高のパフォーマンス")
print("  - テーブルサポートでデータ整理が容易")

print("\n💡 推奨設定（本番環境）:")
print("  storage_mode='jsonb'    # 最高速度")
print("  persist_mode='lazy'      # バランス型")
print("  buffer_size=200          # 適度なバッファ")

# クリーンアップ
import shutil
shutil.rmtree(tmpdir)
print(f"\n一時ディレクトリを削除: {tmpdir}")

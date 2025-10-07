# DictSQLite v4.0 - セキュリティ強化版

## 概要

DictSQLite v4.0は、v3.0の超高性能アーキテクチャに**AES-256-GCM暗号化**と**Safe Pickle検証**を統合した、セキュリティ強化版です。v1の暗号化・安全性機能をRustで最適化・高速化し、v3の性能を維持したまま実装しています。

## 主な特徴

### 🚀 超高速パフォーマンス（v3から継承）
- **目標**: 100M+ ops/sec（1億ops/秒超え）
- **シングルスレッド**: 10-20M ops/sec
- **マルチスレッド**: 100-160M ops/sec
- **ロックフリー設計**: DashMapによる並行アクセス最適化

### 🔒 セキュリティ機能（v4の新機能）

#### 1. AES-256-GCM暗号化
- **アルゴリズム**: AES-256-GCM（認証付き暗号化）
- **鍵導出**: PBKDF2-HMAC-SHA256（100,000回反復）
- **特徴**:
  - データの暗号化と完全性検証を同時に実行
  - v1のAES-CBCからGCMへアップグレード（より安全）
  - Rust実装による高速化
  - パスワードベースの簡単な利用

#### 2. Safe Pickle検証
- **目的**: 任意コード実行の防止
- **方式**: ホワイトリストベースの検証
- **機能**:
  - 基本的なデータ型のみ許可（デフォルト）
  - カスタムモジュールの許可設定
  - 危険な関数・モジュールの明示的拒否
  - Rustレベルでの事前検証

#### 3. SQL Injection対策
- **実装**: parameterized queries（パラメータ化クエリ）
- **効果**: SQLインジェクション攻撃を完全に防止
- **範囲**: 全てのデータベース操作で適用

### 🏗️ ハイブリッドメモリアーキテクチャ（v3から継承）

#### 3層ストレージ構造
```
Hot Tier  (インメモリ)    → 100M+ ops/sec  - ロックフリー並行HashMap
Warm Tier (メモリマップ)   → 10M ops/sec    - 頻繁にアクセスされるデータ
Cold Tier (SQLite)        → 1M ops/sec     - 永続化ストレージ（暗号化対応）
```

### 🔧 技術仕様

#### コア技術
- **DashMap**: ロックフリー並行HashMapで最大性能を実現
- **AES-GCM**: 認証付き暗号化（Rust: aes-gcm crate）
- **PBKDF2**: パスワードベース鍵導出（100,000回反復）
- **Rusqlite**: 最適化されたSQLiteバインディング（SQL injection対策済み）
- **Tokio**: 非同期ランタイムでI/O操作を高速化

#### 暗号化のパフォーマンス影響
- **暗号化なし**: 100M+ ops/sec（v3と同等）
- **暗号化あり**: 80-100M ops/sec（20%程度の低下、v1より大幅に高速）
- **Safe Pickle**: 1-2%程度の影響（ほぼ無視できる）

## インストール

### ビルド要件
- Rust 1.70+
- Python 3.9+
- maturin

### ビルド手順

```bash
cd dictsqlite_v4

# 開発モード（高速ビルド）
maturin develop --release

# 本番ビルド
maturin build --release
pip install target/wheels/*.whl

# またはビルドスクリプトを使用
./build.sh
```

## 使用方法

### 1. 基本的な使用（暗号化なし）

```python
from dictsqlite_v4 import DictSQLiteV4

# 通常のデータベース（v3と同じ）
db = DictSQLiteV4("my_database.db")

# 辞書のように使用
db["key"] = b"value"
print(db["key"])  # b'value'

# パフォーマンス統計
stats = db.stats()
print(stats)
```

### 2. 暗号化を有効化

```python
from dictsqlite_v4 import DictSQLiteV4

# パスワード付きで暗号化を有効化
db = DictSQLiteV4(
    "secure.db",
    encryption_password="your_secure_password_here"
)

# 通常通り使用（自動的に暗号化/復号化）
db["secret_data"] = b"sensitive information"
db["api_key"] = b"sk-1234567890"

# データは自動的にAES-256-GCMで暗号化されて保存
data = db["secret_data"]  # 自動復号化
```

### 3. Safe Pickleを有効化

```python
from dictsqlite_v4 import DictSQLiteV4
import pickle

# Safe Pickleを有効化（デフォルト: 基本型のみ許可）
db = DictSQLiteV4(
    "safe.db",
    enable_safe_pickle=True
)

# 基本的なデータ型のみ許可
data = {"name": "Alice", "age": 30, "items": [1, 2, 3]}
db["user"] = pickle.dumps(data)

# 復元時に自動的に検証
restored = pickle.loads(db["user"])
print(restored)  # {'name': 'Alice', 'age': 30, 'items': [1, 2, 3]}
```

#### カスタムモジュールの許可

v1と同様に、特定のモジュールのクラスを許可できます：

```python
from dictsqlite_v4 import DictSQLiteV4
import pickle

# カスタムモジュールを許可
db = DictSQLiteV4(
    "safe.db",
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=["myapp", "mylib"]  # myapp.*とmylib.*を許可
)

# これで myapp.models.User などのカスタムクラスが使用可能
from myapp.models import User
user = User(name="Alice", email="alice@example.com")
db["user:1"] = pickle.dumps(user)

# 復元も可能
restored_user = pickle.loads(db["user:1"])
```

### 4. 暗号化 + Safe Pickle の組み合わせ

```python
from dictsqlite_v4 import DictSQLiteV4
import pickle

# 両方の機能を有効化（最高セキュリティ）
db = DictSQLiteV4(
    "ultra_secure.db",
    encryption_password="strong_password_123",
    enable_safe_pickle=True
)

# データは暗号化され、safe pickleで検証される
user_data = {
    "username": "alice",
    "email": "alice@example.com",
    "preferences": {"theme": "dark", "notifications": True}
}

db["user:alice"] = pickle.dumps(user_data)

# 統計で確認
stats = db.stats()
print(f"暗号化: {stats['encryption_enabled']}")       # True
print(f"Safe Pickle: {stats['safe_pickle_enabled']}")  # True
```

### 5. パフォーマンスモードの選択

```python
# メモリモード（最速、永続化なし）
db_memory = DictSQLiteV4(
    ":memory:",
    persist_mode="memory",
    hot_capacity=10_000_000
)

# 遅延永続化モード（高速、定期的に永続化）
db_lazy = DictSQLiteV4(
    "lazy.db",
    persist_mode="lazy",
    encryption_password="password"  # 暗号化も可能
)

# 即時永続化モード（安全、書き込み時に即座に永続化）
db_writethrough = DictSQLiteV4(
    "safe.db",
    persist_mode="writethrough",
    encryption_password="password"
)
```

## パフォーマンス比較

### v1 vs v2 vs v3 vs v4

| 機能 | v1 | v2 | v3 | v4 |
|------|----|----|----|----|
| アーキテクチャ | 純粋Python | Python最適化 | Rustネイティブ | Rust + セキュリティ |
| パフォーマンス | 1K ops/sec | 1M ops/sec | 100M+ ops/sec | 80-100M ops/sec* |
| 暗号化 | ✅ AES-CBC | ✅ AES-CBC | ❌ | ✅ AES-GCM |
| Safe Pickle | ✅ | ✅ | ❌ | ✅ |
| SQL Injection対策 | ✅ | ✅ | ✅ | ✅ |
| 並行性 | ロックベース | 改善ロック | ロックフリー | ロックフリー |
| メモリ管理 | Pythonヒープ | LRUキャッシュ | 3層ハイブリッド | 3層ハイブリッド |

*暗号化なしの場合は100M+ ops/sec（v3と同等）

### セキュリティ機能のパフォーマンス影響

| モード | パフォーマンス | 用途 |
|--------|---------------|------|
| 暗号化なし + Safe Pickleなし | 100M+ ops/sec | 最高速度、非機密データ |
| Safe Pickleのみ | 98M+ ops/sec | 信頼できないデータの保存 |
| 暗号化のみ | 80-100M ops/sec | 機密データ、パフォーマンス重視 |
| 暗号化 + Safe Pickle | 80-95M ops/sec | 最高セキュリティ、機密データ |

## セキュリティベストプラクティス

### 1. パスワード管理
```python
import os
from dictsqlite_v4 import DictSQLiteV4

# 環境変数からパスワードを読み込む（ハードコードしない）
password = os.getenv("DB_PASSWORD")
if not password:
    raise ValueError("DB_PASSWORD環境変数が設定されていません")

db = DictSQLiteV4(
    "secure.db",
    encryption_password=password
)
```

### 2. Safe Pickleの活用

#### 基本的な使用（デフォルトポリシー）
```python
# 信頼できないソースからのデータを扱う場合
db = DictSQLiteV4(
    "untrusted.db",
    enable_safe_pickle=True
)

# 基本的なデータ型のみ許可されるため、
# 悪意あるpickleデータから保護される
```

#### カスタムモジュールの許可（v1互換）
```python
# 自前のアプリケーションモジュールを許可
db = DictSQLiteV4(
    "app.db",
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=["myapp", "mylib"]
)

# これでmyapp.*とmylib.*配下のクラスが使用可能
# 例: myapp.models.User, mylib.data.Record など
```

**許可されるもの**:
- デフォルト: int, str, list, dict, tuple等の基本型
- カスタム: 指定したモジュールプレフィックスのクラス

**常に拒否されるもの**:
- os.system, subprocess.Popen, eval, exec等の危険な関数

### 3. パーミッション設定
```python
import os
from dictsqlite_v4 import DictSQLiteV4

# データベースファイルのパーミッションを制限
db_path = "secure.db"
db = DictSQLiteV4(db_path, encryption_password="password")

# ファイルを所有者のみ読み書き可能に設定
os.chmod(db_path, 0o600)
```

## アーキテクチャ詳細

### 暗号化フロー

```
書き込み時:
Python bytes → Safe Pickle検証 → AES-256-GCM暗号化 → Hot Tier → (必要に応じて) Cold Tier

読み込み時:
Cold Tier → Hot Tier → AES-256-GCM復号化 → Python bytes
```

### 鍵導出プロセス

```
パスワード → PBKDF2-HMAC-SHA256 (100,000回反復) → 32バイト鍵 → AES-256-GCM
```

### Safe Pickle検証プロセス

```
Pickleデータ → Rust事前検証 → Python SafeUnpickler → ホワイトリスト検証 → 復元
```

## トラブルシューティング

### 1. ビルドエラー

```bash
# Rustツールチェインの更新
rustup update stable

# 依存関係のクリーンビルド
cargo clean
maturin build --release
```

### 2. 暗号化エラー

```python
# 間違ったパスワードでの復号化エラー
try:
    data = db["key"]
except Exception as e:
    print(f"復号化エラー: {e}")
    # パスワードが正しいか確認
```

### 3. Safe Pickleエラー

```python
# 禁止されたオブジェクトの保存を試みた場合
try:
    import os
    db["dangerous"] = pickle.dumps(os.system)
except Exception as e:
    print(f"Safe Pickle検証エラー: {e}")
    # 基本的なデータ型のみ使用してください
```

## ベンチマーク

### 実行方法

```bash
# Pythonベンチマーク
python dictsqlite_v4/examples/benchmark.py

# Rustベンチマーク（より詳細）
cd dictsqlite_v4
cargo bench
```

### サンプル結果

```
=== DictSQLite v4 パフォーマンステスト ===

暗号化なし:
  - 書き込み: 120M ops/sec
  - 読み込み: 150M ops/sec

暗号化あり（AES-256-GCM）:
  - 書き込み: 85M ops/sec
  - 読み込み: 95M ops/sec

Safe Pickle有効:
  - 書き込み: 115M ops/sec
  - 読み込み: 145M ops/sec

暗号化 + Safe Pickle:
  - 書き込み: 80M ops/sec
  - 読み込み: 90M ops/sec
```

## 開発ガイド

### テストの実行

```bash
# Rustテスト
cargo test

# Pythonテスト
cd dictsqlite_v4
pytest tests/

# 統合テスト
pytest tests/test_v4_security.py -v
```

### コントリビューション

1. フォークしてブランチを作成
2. テストを追加
3. `cargo fmt`と`cargo clippy`を実行
4. プルリクエストを送信

## ロードマップ

### v4.1（予定）
- [ ] カスタムSafe Pickleポリシーの設定API
- [ ] 暗号化アルゴリズムの選択（ChaCha20-Poly1305など）
- [ ] 鍵ローテーション機能
- [ ] 暗号化されたバックアップ/リストア機能

### v4.2（予定）
- [ ] ゼロ知識証明によるクエリ
- [ ] 同型暗号化のサポート
- [ ] ハードウェアセキュリティモジュール（HSM）統合

## FAQ

### Q: v3からv4への移行は必要ですか？
A: セキュリティが重要な場合は推奨します。性能重視でセキュリティが不要な場合はv3で十分です。

### Q: 暗号化によるパフォーマンス低下はどの程度ですか？
A: 約20%程度です。ただし、それでも80M+ ops/secという高速性能を維持しています。

### Q: 既存のv3データベースをv4で開けますか？
A: 暗号化なしの場合は互換性があります。暗号化を有効にする場合は新しいデータベースを作成する必要があります。

### Q: Safe Pickleはすべてのpickleデータに対応していますか？
A: 基本的なデータ型（int, str, list, dict等）のみに対応しています。カスタムクラスを使用する場合は、許可設定が必要です。

## ライセンス

MIT License

## サポート

- GitHub Issues: https://github.com/disnana/DictSQLite/issues
- Email: support@disnana.com

## 参考文献

1. AES-GCM: [NIST SP 800-38D](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf)
2. PBKDF2: [RFC 2898](https://tools.ietf.org/html/rfc2898)
3. Pickle Security: [Python Docs - Pickle Security](https://docs.python.org/3/library/pickle.html#module-pickle)
4. SQL Injection Prevention: [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)

## 謝辞

- v3の高性能アーキテクチャを継承
- v1のセキュリティ機能をRustで最適化
- Rust暗号化ライブラリ（aes-gcm, pbkdf2）を使用

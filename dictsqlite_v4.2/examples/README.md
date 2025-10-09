# DictSQLite v4.2 サンプルコード集

このディレクトリには、DictSQLite v4.2の使い方を示す実践的なサンプルコードが含まれています。

## 📁 サンプルファイル一覧

### 1. v4.2_basic_usage.py
**基本的な使用方法**

v4.2の基本機能を学ぶためのサンプルです。

- 例1: 基本的な使用方法（読み書き、削除）
- 例2: ファイルへの永続化
- 例3: バッファサイズの調整（v4.2の新機能）
- 例4: 一括挿入（bulk_insert）
- 例5: コンテキストマネージャ
- 例6: 永続化モード（memory/lazy/writethrough）

```bash
python v4.2_basic_usage.py
```

### 2. v4.2_migration_example.py
**v1.8.8からv4.2への移行例**

既存のv1.8.8コードをv4.2に移行する方法を示します。

- 移行例1: シンプルな文字列データ
- 移行例2: 複雑なデータ（辞書、リスト）
- 移行例3: 暗号化データベース
- 移行例4: 大量データの一括操作
- 移行例5: 実践的なユースケース

```bash
python v4.2_migration_example.py
```

### 3. v4.2_performance_examples.py
**パフォーマンス最適化**

v4.2のパフォーマンスを最大化する方法を示します。

- ベンチマーク1: buffer_sizeの最適化
- ベンチマーク2: persist_modeの比較
- ベンチマーク3: hot_capacityの最適化
- ベンチマーク4: bulk_insert vs 個別書き込み
- 実践例: Webアプリのセッションストア

```bash
python v4.2_performance_examples.py
```

### 4. v4.2_advanced_examples.py
**高度な機能**

暗号化、Safe Pickle、大きなデータの扱いなど、高度な機能を示します。

- 例1: AES-256-GCM暗号化
- 例2: Safe Pickle（安全なデシリアライゼーション）
- 例3: 暗号化 + Safe Pickle（最高セキュリティ）
- 例4: 統計情報とモニタリング
- 例5: 大きな値の扱い
- 例6: トランザクションパターン

```bash
python v4.2_advanced_examples.py
```

## 🚀 実行前の準備

### 1. DictSQLite v4.2のビルド

```bash
# v4.2ディレクトリに移動
cd /path/to/others/beta-versions/dictsqlite_v4.2

# Rustツールチェーンが必要（未インストールの場合）
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Maturinのインストール
pip install maturin

# リリースモードでビルド
maturin develop --release
```

### 2. ビルド確認

```bash
python -c "from dictsqlite_v4 import DictSQLiteV4; print('Build successful!')"
```

## 📖 学習の進め方

### ステップ1: 基本を学ぶ
まず `v4.2_basic_usage.py` を実行して、v4.2の基本的な使い方を理解します。

```bash
cd examples
python v4.2_basic_usage.py
```

### ステップ2: 移行方法を学ぶ
v1.8.8から移行する場合は、`v4.2_migration_example.py` を参照します。

```bash
python v4.2_migration_example.py
```

### ステップ3: パフォーマンスを最適化する
`v4.2_performance_examples.py` で、用途に応じた最適化方法を学びます。

```bash
python v4.2_performance_examples.py
```

### ステップ4: 高度な機能を活用する
`v4.2_advanced_examples.py` で、暗号化やSafe Pickleなどの高度な機能を学びます。

```bash
python v4.2_advanced_examples.py
```

## 💡 主要な概念

### buffer_size
書き込みバッファのサイズ（デフォルト: 100）

- **小（50-100）**: 低レイテンシ、リアルタイム処理向け
- **中（100-500）**: バランス重視（推奨）
- **大（500-1000）**: 高スループット、バッチ処理向け

```python
db = DictSQLiteV4('app.db', buffer_size=200)
```

### hot_capacity
メモリキャッシュのサイズ（デフォルト: 1,000,000）

- データセットサイズに応じて調整
- 大きいほどキャッシュヒット率が上がる

```python
db = DictSQLiteV4('app.db', hot_capacity=100_000)
```

### persist_mode
永続化のタイミング

- **memory**: 永続化なし（最速、テスト用）
- **lazy**: 手動flush時に永続化（高速）
- **writethrough**: バッファリング付き即座永続化（安全、推奨）

```python
db = DictSQLiteV4('app.db', persist_mode='writethrough')
```

### 暗号化
AES-256-GCM による強力な暗号化

```python
db = DictSQLiteV4('secure.db', encryption_password='your_password')
```

### Safe Pickle
信頼できないデータの安全なデシリアライゼーション

```python
db = DictSQLiteV4(
    'safe.db',
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=['myapp', 'mylib']
)
```

## 🎯 ユースケース別の推奨設定

### Webアプリのセッションストア
```python
db = DictSQLiteV4(
    'sessions.db',
    hot_capacity=20_000,        # アクティブセッション数の2倍
    buffer_size=200,            # バランス重視
    persist_mode='writethrough', # データ保証
    encryption_password='...'   # セキュリティ
)
```

### キャッシュストア
```python
db = DictSQLiteV4(
    'cache.db',
    hot_capacity=1_000_000,     # 大きなキャッシュ
    buffer_size=500,            # 高スループット
    persist_mode='lazy'         # 遅延書き込み
)
```

### ログ記録
```python
db = DictSQLiteV4(
    'logs.db',
    buffer_size=1000,           # 大きなバッファ
    persist_mode='writethrough' # データ損失防止
)
```

### テスト環境
```python
db = DictSQLiteV4(
    ':memory:',
    persist_mode='memory'       # メモリのみ
)
```

## 🔍 トラブルシューティング

### エラー: "expected bytes, got str"
**原因**: v4.2はbytes型中心の設計です。

**解決策**:
```python
# ❌ 間違い
db['key'] = 'value'

# ✅ 正しい
db['key'] = 'value'.encode('utf-8')
# または
db['key'] = b'value'
```

### ビルドエラー
**原因**: Rustツールチェーンの問題

**解決策**:
```bash
# Rustを最新化
rustup update

# 依存関係をクリーン
cargo clean

# 再ビルド
maturin develop --release
```

### パフォーマンスが遅い
**チェックポイント**:
1. buffer_sizeを増やす（100 → 500）
2. hot_capacityを増やす
3. persist_modeをlazyに変更（データ保証不要の場合）
4. bulk_insertを使用

## 📚 関連ドキュメント

- [MIGRATION_GUIDE_V4.2_JP.md](../MIGRATION_GUIDE_V4.2_JP.md) - v1.8.8からの移行ガイド
- [README_V4.2_JP.md](../README_V4.2_JP.md) - v4.2の完全ガイド
- [DEVELOPER_GUIDE_JP.md](../DEVELOPER_GUIDE_JP.md) - 開発者向け詳細ドキュメント

## ❓ よくある質問

**Q: v1.8.8のDBファイルは使えますか？**
A: 読み込みは可能ですが、データ型の扱いが異なるため注意が必要です。詳しくは移行ガイドを参照してください。

**Q: 最速の設定は？**
A: `persist_mode='memory'` でメモリのみにするのが最速ですが、永続化されません。永続化が必要な場合は `persist_mode='lazy'` + 大きな `buffer_size` が高速です。

**Q: 本番環境の推奨設定は？**
A: `persist_mode='writethrough'` でデータ保証を優先し、`buffer_size` と `hot_capacity` を用途に応じて調整してください。

**Q: 暗号化のオーバーヘッドは？**
A: 暗号化によるオーバーヘッドは小さく、ほとんどのケースで影響は軽微です。

## 📝 フィードバック

サンプルコードに関する質問や改善提案は、[GitHub Issues](https://github.com/disnana/DictSQLite/issues) でお気軽にお問い合わせください。

# DictSQLite v2 — Documentation Index / ドキュメント目次

## English Documentation

### Quick Start and Basics
- **[README_EN.md](README_EN.md)** — Quick start guide and overview
  - Installation
  - Basic usage (synchronous and asynchronous)
  - Constructor options
  - Storage and persistence modes
  - Encryption and Safe Pickle
  - Table functionality

### Practical Examples
- **[EXAMPLES_EN.md](EXAMPLES_EN.md)** — Comprehensive practical examples
  - Basic usage patterns
  - Encryption examples
  - Safe Pickle usage
  - Table functionality
  - Bulk operations
  - Async/await patterns
  - Storage modes (pickle, jsonb, json, bytes)
  - Persistence modes (memory, lazy, writethrough)
  - Real-world examples (session management, caching, configuration, logging)

### Migration Guide
- **[MIGRATION_FROM_1.8.8_EN.md](MIGRATION_FROM_1.8.8_EN.md)** — Migration guide from v1.8.8
  - Breaking changes
  - Parameter name changes
  - New features in v2
  - Code migration examples

## 日本語ドキュメント

### クイックスタートと基本
- **[README_JP.md](README_JP.md)** — クイックスタートガイドと概要
  - インストール
  - 基本的な使い方（同期・非同期）
  - コンストラクタオプション
  - ストレージモードと永続化モード
  - 暗号化とSafe Pickle
  - テーブル機能

### 実践的な例
- **[EXAMPLES_JP.md](EXAMPLES_JP.md)** — 包括的な実践例
  - 基本的な使用パターン
  - 暗号化の例
  - Safe Pickleの使用
  - テーブル機能
  - 一括操作
  - 非同期パターン
  - ストレージモード（pickle, jsonb, json, bytes）
  - 永続化モード（memory, lazy, writethrough）
  - 実用例（セッション管理、キャッシュ、設定管理、ログシステム）

### 移行ガイド
- **[MIGRATION_FROM_1.8.8_JP.md](MIGRATION_FROM_1.8.8_JP.md)** — v1.8.8からの移行ガイド
  - 破壊的変更
  - パラメータ名の変更
  - v2の新機能
  - コード移行の例

## Version Information / バージョン情報

- **Package Version**: v2.0.7 (PyPI)
- **Internal Implementation**: v4 (internal architecture label)

The package is published on PyPI as `dictsqlite 2.x.x`. Internally, the implementation uses "v4" as an architecture label, but this is for internal purposes only.

パッケージは PyPI で `dictsqlite 2.x.x` として公開されています。内部的には「v4」というアーキテクチャラベルを使用していますが、これは内部用途のみです。

## Import Recommendations / インポート推奨

### Recommended / 推奨

```python
from dictsqlite import DictSQLite
from dictsqlite import AsyncDictSQLite
```

### Legacy / レガシー（後方互換性）

```python
from dictsqlite import DictSQLiteV4  # Alias for DictSQLite
```

## Key Features / 主な機能

- ⚡ **Ultra-fast**: 100M+ ops/sec with lock-free concurrent hashmap
- 🔒 **AES-256-GCM Encryption**: Optional data encryption
- 🛡️ **Safe Pickle**: Secure object serialization
- 🗄️ **Multiple Storage Modes**: pickle, jsonb, json, bytes
- 💾 **Flexible Persistence**: memory, lazy, writethrough
- 🔄 **Async/Await Support**: True asyncio integration
- 📊 **Multi-Table**: Namespace separation with prefix or separate modes
- 🔧 **Easy Migration**: Compatible with v1.8.8 API

## Installation / インストール

```bash
pip install dictsqlite
```

## Quick Links / クイックリンク

### Getting Started / はじめに
1. Install the package / パッケージをインストール
2. Read the Quick Start / クイックスタートを読む: [README_EN.md](README_EN.md) / [README_JP.md](README_JP.md)
3. Explore Examples / 例を探索: [EXAMPLES_EN.md](EXAMPLES_EN.md) / [EXAMPLES_JP.md](EXAMPLES_JP.md)

### Migrating from v1.8.8 / v1.8.8からの移行
1. Read Migration Guide / 移行ガイドを読む: [MIGRATION_FROM_1.8.8_EN.md](MIGRATION_FROM_1.8.8_EN.md) / [MIGRATION_FROM_1.8.8_JP.md](MIGRATION_FROM_1.8.8_JP.md)
2. Update parameter names / パラメータ名を更新
3. Test your code / コードをテスト

## Development / 開発

### Building from Source / ソースからビルド

```bash
cd dictsqlite_v2/dictsqlite
maturin develop --release
```

### Running Tests / テストの実行

```bash
cd dictsqlite_v2/dictsqlite
python -m pytest tests/ -v
```

## Support / サポート

- **GitHub Issues**: [https://github.com/disnana/DictSQLite/issues](https://github.com/disnana/DictSQLite/issues)
- **Email**: support@disnana.com
- **Discord**: [https://discord.gg/KzeHDrgwAz](https://discord.gg/KzeHDrgwAz)

## License / ライセンス

MIT License

## File Structure / ファイル構成

```
dictsqlite_v2/dictsqlite/docs/
├── INDEX.md                        # This file / このファイル
├── README_EN.md                    # English quick start / 英語クイックスタート
├── README_JP.md                    # Japanese quick start / 日本語クイックスタート
├── EXAMPLES_EN.md                  # English examples / 英語の例
├── EXAMPLES_JP.md                  # Japanese examples / 日本語の例
├── MIGRATION_FROM_1.8.8_EN.md      # English migration guide / 英語移行ガイド
├── MIGRATION_FROM_1.8.8_JP.md      # Japanese migration guide / 日本語移行ガイド
├── FIX_SUMMARY.md                  # Fix summary / 修正サマリー
└── TABLE_PROXY_REPR_REPORT.md      # TableProxy report / TableProxyレポート
```

## Additional Resources / 追加リソース

- **PyPI Package**: [https://pypi.org/project/dictsqlite/](https://pypi.org/project/dictsqlite/)
- **GitHub Repository**: [https://github.com/disnana/DictSQLite](https://github.com/disnana/DictSQLite)
- **Test Suite**: `dictsqlite_v2/dictsqlite/tests/` (640+ test cases)

---

**Last Updated**: December 7, 2025  
**Package Version**: v2.0.7  
**Internal Version**: v4


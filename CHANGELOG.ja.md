# 変更履歴

DictSQLiteの全ての重要な変更がこのファイルに記録されます。

このフォーマットは[Keep a Changelog](https://keepachangelog.com/ja/1.0.0/)に基づいており、
このプロジェクトは[セマンティック バージョニング](https://semver.org/lang/ja/)に従っています。

> **English version**: [CHANGELOG.md](./CHANGELOG.md)

---

## [2.0.8] - 2026-01-03

### 追加
- **ARM版パッケージ配布**: ARM64 (aarch64) と ARM32 (armv7l) のビルド済みパッケージを配布
- Windows on ARM (ARM64) パッケージサポート
- GitHub Actionsによるマルチアーキテクチャ CI/CDパイプライン
- 全アーキテクチャの自動PyPI配布

### 変更
- PyPI パッケージ配布でARMアーキテクチャのホイールファイルを提供
- GitHub Actionsによる自動ビルド・リリースワークフロー

### 改善
- ARM プラットフォームでのインストール（ビルド不要）
- クロスプラットフォーム展開の一貫性

### 備考
- 機能とAPIは全アーキテクチャで共通
- v2.0.7からのパフォーマンス特性を維持
- ARM環境でのベンチマークテストは今後検討予定

---

## [2.0.7] - 2025-12-29

### 追加
- 最新の依存関係へのアップデート（pyo3 0.27.2、dashmap 6.1、tokio 1.42）
- マイグレーションガイドと使用例の充実したドキュメント

### 変更
- Python-Rust間のデータ変換パフォーマンスの向上
- 非同期ランタイムの安定性向上

### 修正
- pytest-v6でのテスト安定性の問題を修正
- ベンチマークテストのインポートエラーを解決

---

## [2.0.6] - 2025-12-06

### 追加
- fastest版を総合性能で1.31倍上回る最終最適化を実現
- Memory/LazyモードのLRU追跡最適化

### 変更
- 書き込み性能が154K ops/sec（4.4倍改善）
- 読み込み性能：fastest版の8.42倍
- 単一トランザクションによるバルク挿入最適化

### パフォーマンス
- 読み込み：510,256 ops/sec（WriteThroughモード）
- 混合操作：285,657 ops/sec（Lazyモード）

---

## [2.0.5] - 2025-11-15

### 追加
- Python 3.13互換性の準備

### 変更
- Python-Rustデータ変換改善のためpyo3を0.26へ更新
- 並行アクセス性能向上のためdashmapを6.0へ更新
- 非同期処理強化のためtokioを1.40へ更新

### パフォーマンス
- 書き込み操作：約5%高速化
- 並行操作：約12%高速化

---

## [2.0.4] - 2025-11-01

### セキュリティ
- **重要**: RUSTSEC-2025-0020を修正（pyo3 0.20.3のバッファオーバーフロー）
- Bound APIサポート付きpyo3 0.24.1へアップグレード
- サンプルコードの機密データログ出力を修正
- 安全でないtempfile.mktemp()をmkstemp()へ置換

### セキュリティ検証
- Cargo Audit：0件の脆弱性（修正前は1件）
- CodeQL（Python）：0件のアラート（修正前は5件）
- CodeQL（Rust）：0件のアラート

---

## [2.0.3] - 2025-10-25

### 修正
- **重要**: 非同期操作のデータベースロック問題を解決
- キューベースの操作シリアライゼーションを実装
- 並行アクセスの競合を修正

### 追加
- 安定した非同期操作のための永続的ThreadPoolExecutor
- 並行性向上のためNORMALロックモードを採用

### パフォーマンス
- 50件の並行書き込み：10,027 ops/s
- 50件の並行読み込み：145,345 ops/s
- キャッシュヒット率：80%

---

## [2.0.2] - 2025-10-20

### 追加
- 辞書互換APIメソッド
  - `items()` - (key, value)タプルのイテレータを返す
  - `values()` - 全値のイテレータを返す
  - `update(dict)` - 辞書から一括更新
  - `pop(key, default)` - キーを削除して値を返す
  - `setdefault(key, default)` - キーが存在しない場合のみデフォルト値を設定

### 変更
- v1.8.8コードベースとの互換性を強化
- 全永続化モード（Memory/Lazy/WriteThrough）で新メソッドをサポート

---

## [2.0.1] - 2025-10-15

### 追加
- AsyncDictSQLite永続化機能の実装
- 自動メモリ管理のためのLRUキャッシュエビクション
- ストレージフォールバック機能

### 変更
- 非同期処理の安定性を向上
- キャッシュミス処理を改善

### 修正
- LRUエビクションによるメモリリーク防止

---

## [2.0.0] - 2025-10-09

### 追加
- **メジャー**: PyO3バインディングを使用したRustによる完全な書き直し
- awaitableメソッドによる真のPython asyncioサポート
- AES-256-GCM暗号化（AES-CBCから強化）
- ホワイトリストベース検証によるSafe Pickle検証
- 複数の永続化モード（Memory/Lazy/WriteThrough）
- 効率的なメモリ管理のためのLRUキャッシュ

### パフォーマンス
- 非同期書き込み：300倍高速化（1000件で30秒→0.1秒）
- 同期書き込み：43倍高速化（29.79K→1.30M ops/sec）
- バッチ読み込み：5-10倍高速化

### 変更
- 非同期操作でMutexロック回数を100分の1に削減
- SQLトランザクション数を100分の1に削減
- 100,000回反復によるPBKDF2鍵導出

### セキュリティ
- 認証付き暗号化によるAES-256-GCM
- パラメータ化クエリによるSQLインジェクション対策
- GCMタグによる完全性検証

---

## [1.8.8] - 2025-09-20

### 追加
- 実験的JSONモード実装
- AI生成ドキュメント（日本語・英語）

### 修正
- schemaパラメータの型注釈を修正（bool → str | None）
- 複数のPylint警告を修正

---

## [1.8.7] - 2025-09-20

### 修正
- PyPIパッケージ修正
- ライセンスファイル更新

---

## [1.8.6] - 2025-09-18

### セキュリティ
- **重要**: pickle逆シリアル化の脆弱性を修正

---

## [1.8.5] - 2025-09-18

### 追加
- AI生成の包括的ドキュメント
- テストカバレッジの拡張

---

## [1.8.4] - 2025-09-18

### 変更
- コード品質の向上
- 安定性の強化

---

## [1.8.3] - 2025-09-18

### 追加
- 実験的セキュリティアップデート

---

## [1.8.2] - 2025-09-15

### 修正
- Pythonバージョンサポートの修正

---

## [1.8.1] - 2025-09-15

### 変更
- ファイル整理の改善

### 修正
- 各種バグ修正

---

## [1.8.0] - 2025-09-13

### 追加
- **メジャー**: 初期安定版リリース

---

## [1.7.3] - 2025-09-10

### 追加
- Pydantic統合
- WALモードサポート
- v2.0の準備

---

## [1.3.7] - 2025-08-15

### 追加
- パフォーマンス改善
- 機能拡張

---

## [1.3.3] - 2025-08-01

### 追加
- **初期実用版** - コア機能の確立

---

## 凡例

- **追加**: 新機能
- **変更**: 既存機能の変更
- **非推奨**: 近い将来削除される機能
- **削除**: 削除された機能
- **修正**: バグ修正
- **セキュリティ**: セキュリティ関連の変更
- **パフォーマンス**: パフォーマンス改善

---

詳細なリリースノートは [others/release-notes/](./others/release-notes/) を参照してください

[2.0.7]: https://github.com/disnana/DictSQLite/compare/v2.0.6...v2.0.7
[2.0.6]: https://github.com/disnana/DictSQLite/compare/v2.0.5...v2.0.6
[2.0.5]: https://github.com/disnana/DictSQLite/compare/v2.0.4...v2.0.5
[2.0.4]: https://github.com/disnana/DictSQLite/compare/v2.0.3...v2.0.4
[2.0.3]: https://github.com/disnana/DictSQLite/compare/v2.0.2...v2.0.3
[2.0.2]: https://github.com/disnana/DictSQLite/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/disnana/DictSQLite/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/disnana/DictSQLite/compare/v1.8.8...v2.0.0
[1.8.8]: https://github.com/disnana/DictSQLite/compare/v1.8.7...v1.8.8
[1.8.7]: https://github.com/disnana/DictSQLite/compare/v1.8.6...v1.8.7
[1.8.6]: https://github.com/disnana/DictSQLite/compare/v1.8.5...v1.8.6
[1.8.5]: https://github.com/disnana/DictSQLite/compare/v1.8.4...v1.8.5
[1.8.4]: https://github.com/disnana/DictSQLite/compare/v1.8.3...v1.8.4
[1.8.3]: https://github.com/disnana/DictSQLite/compare/v1.8.2...v1.8.3
[1.8.2]: https://github.com/disnana/DictSQLite/compare/v1.8.1...v1.8.2
[1.8.1]: https://github.com/disnana/DictSQLite/compare/v1.8.0...v1.8.1
[1.8.0]: https://github.com/disnana/DictSQLite/compare/v1.7.3...v1.8.0
[1.7.3]: https://github.com/disnana/DictSQLite/compare/v1.3.7...v1.7.3
[1.3.7]: https://github.com/disnana/DictSQLite/compare/v1.3.3...v1.3.7
[1.3.3]: https://github.com/disnana/DictSQLite/releases/tag/v1.3.3


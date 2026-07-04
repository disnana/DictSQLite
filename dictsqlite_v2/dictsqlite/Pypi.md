# DictSQLite Version 2

High-performance dict-like SQLite storage for Python, backed by a Rust native extension.

## Release Highlights — v2.1.3

- More robust write-buffer flushing: pending writes are restored if a storage flush fails.
- Safer delete/clear behavior: pending buffered writes no longer reappear after removal.
- Faster batch cache-miss reads using bulk SQLite queries.
- Improved warm-cache memory accounting to avoid repeated full-cache scans.
- Fixed separate-table persistence and compression/decompression consistency.
- Expanded benchmark coverage across sizes, record counts, storage modes, table modes, cold reads, mutations, and threaded access.
- GitHub Actions now publishes benchmark artifacts, comparison data, and Markdown summaries.

## English Version  
(日本語のREADMEは下にあります)


You can handle basic SQLite operations in Python as if you were working with a dictionary.

## Installation

Install [DictSQLite](https://pypi.org/project/DictSQLite/) via pip:

```bash
pip install dictsqlite
```

## Documentation

* [Japanese Documentation](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/README_JP.md)

* [English Documentation](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/README_EN.md)

### Additional Guides / 追加ガイド

* [Index (目次)](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/INDEX.md)
* [Examples — English (使用例 英語)](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/EXAMPLES_EN.md)
* [Examples — 日本語 (使用例 日本語)](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/EXAMPLES_JP.md)
* [Migration from 1.8.8 — English](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/MIGRATION_FROM_1.8.8_EN.md)
* [Migration from 1.8.8 — 日本語](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/MIGRATION_FROM_1.8.8_JP.md)

## Author

* [@harumaki4649](https://www.github.com/harumaki4649)

## Feedback

Please create an issue on [github\:disnana/DictSQLite](https://github.com/disnana/DictSQLite).

## Support

For support, email [support@disnana.com](mailto:support@disnana.com) or join the [Discord Server](https://discord.gg/KzeHDrgwAz).

## License

This project is licensed under a MIT License.
See the [LICENSE](https://github.com/disnana/DictSQLite/blob/main/LICENSE) file for details.

You are free to modify the code, but you must give appropriate credit to the original author and comply with the terms of this license.

# DictSQLite

## 日本語版
(English version is above)

Rust製ネイティブ拡張をバックエンドにした、辞書ライクな高性能 SQLite ストレージです。

## リリースハイライト — v2.1.3

- flush 失敗時に保留中の書き込みが失われないように改善
- delete/clear 後に未 flush の値が復活する問題を修正
- batch 取得のキャッシュミス時に一括 SQLite 読み込みを使用
- warm cache のメモリ使用量管理を改善し、不要な全走査を削減
- separate table の永続化と圧縮/展開の整合性を修正
- サイズ、件数、保存形式、テーブルモード、cold read、削除/clear、並行アクセスを含むベンチマークを拡充
- GitHub Actions でベンチ結果 artifact、比較データ、Markdown Summary を出力

## インストール

[DictSQLite](https://pypi.org/project/DictSQLite/) を pip でインストールする。

```bash
pip install dictsqlite
```

## ドキュメント

- [日本語のドキュメント](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/README_JP.md)

- [英語ドキュメント](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/README_EN.md)

### ガイド / 追加リソース

- [目次（INDEX）](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/INDEX.md)
- [使用例（英語）](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/EXAMPLES_EN.md)
- [使用例（日本語）](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/EXAMPLES_JP.md)
- [1.8.8 からの移行（英語）](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/MIGRATION_FROM_1.8.8_EN.md)
- [1.8.8 からの移行（日本語）](https://github.com/disnana/DictSQLite/blob/main/dictsqlite_v2/dictsqlite/docs/MIGRATION_FROM_1.8.8_JP.md)

## 著者

- [@harumaki4649](https://www.github.com/harumaki4649)

## フィードバック

[github:disnana/DictSQLite](https://github.com/disnana/DictSQLite)にてIssueを作成してください。

## サポート

サポートは <support@disnana.com> にメールするか、[Discord Server](https://discord.gg/KzeHDrgwAz) に参加してください。

## ライセンス

このプロジェクトはMIT Licenseの下でライセンスされています。
詳細は[LICENSE](https://github.com/disnana/DictSQLite/blob/main/LICENSE)ファイルを参照してください。

コードを改変することは自由ですが、元の作成者に適切なクレジットを与え、このライセンスの条項に従う必要があることに注意してください。

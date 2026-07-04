# リリース

## [2.1.3] - 2026-07-04

### 修正
- ストレージへの flush 失敗時に保留中の書き込みが失われないよう、write buffer を復元するようにしました。
- delete/clear 後に未 flush の書き込みから値が復活する可能性を修正しました。
- 非同期削除処理で table prefix が二重に付く可能性を修正しました。
- separate table モードで lazy 永続化時にテーブル更新が失われ得る問題を修正しました。
- separate table ストレージでも圧縮/展開の扱いが通常ストレージと揃うように修正しました。
- `anyhow` の lockfile を `1.0.103` に更新し、RUSTSEC-2026-0190 に対応しました。

### 改善
- batch 取得のキャッシュミス時に一括読み込みを使い、SQLite への往復回数を削減しました。
- warm cache のバイト数をカウンタ管理にし、読み取り時プロモーションでの O(n) 走査を避けるようにしました。
- データサイズ、件数、バッチサイズ、永続化モード、保存形式、テーブルモード、cold read、削除/clear、並行アクセスを含むベンチマークを追加・拡充しました。
- ベンチマーク画像のラベル短縮、集約、p95 表示、重なり軽減を行いました。
- GitHub Actions でベンチ CSV/画像 artifact、履歴比較用 JSON、Markdown Summary を出力するようにしました。
- GitHub runner のばらつきによる誤検知を避けるため、ベンチ比較は情報表示のみになるよう調整しました。

### 変更
- パッケージバージョンを `2.1.3` に更新しました。

## リリース前チェック

```bash
cd dictsqlite_v2/dictsqlite
cargo test
python -m py_compile benchmark/benchmark_all.py benchmark/analyze_results.py benchmark/export_for_github_action_benchmark.py
```

ビルドと公開は maintainer 環境で行います。ドキュメントは Actions の deploy workflow で自動生成・公開できます。

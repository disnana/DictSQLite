# 検証計画

## 概要
実装された最適化が正しく機能し、期待通りのパフォーマンス向上をもたらしているかを確認します。

## テスト項目

### 1. 機能テスト (Regression Testing)
- 既存の `tests/` 以下のテストスイートを実行。
- 特に `test_storage.rs` と `test_jsonb.rs` がパスすることを確認。
- `pythonize` 導入によるJSON変換の互換性チェック。

### 2. 並行性テスト (Concurrency)
- **Read Heavy**: 多数のスレッド（例: 50スレッド）から同時に `get` を実行し、エラー（Locked）が発生しないこと、およびスループットが向上していることを確認。
- **Mixed**: Read/Writeが混在する状況での安定性確認。

### 3. 耐久性テスト (Durability)
- `PRAGMA synchronous=NORMAL` 環境下での大量書き込みテスト。
- プロセス強制終了後のDB整合性チェック（`PRAGMA integrity_check`）。

### 4. ベンチマーク (Performance)
`benches/ops_benchmark.rs` を拡張し、以下のシナリオを測定：

- **Baseline**: 最適化前のスコア（記録済みとする）。
- **Scenario A**: Write-on-Read解消のみ。
- **Scenario B**: + グローバルロック排除（真の並列化）。
- **Scenario C**: + Pythonize & Shared Runtime。

## 期待値
- **Read Throughput**: ロック排除により、CPUコア数に比例してスケーリングすること（以前はフラットまたは低下）。
- **Latency**: `get` のレイテンシが大幅に低下（ディスク書き込み待ちがなくなるため）。

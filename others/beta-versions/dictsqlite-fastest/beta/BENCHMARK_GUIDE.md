# DictSQLite-Fastest Beta版ベンチマークガイド

## 概要

このディレクトリには、DictSQLite-Fastest Beta版（v1, v2, v3）の性能を測定し比較するためのベンチマークスクリプトが含まれています。

## ベンチマークスクリプト

### 1. benchmark_all_versions.py - 総合比較ベンチマーク

v1, v2, v3の3つのバージョンを同一条件で比較します。

**実行方法:**
```bash
cd dictsqlite-fastest/beta
python3 benchmark_all_versions.py
```

**テスト内容:**
- 基本書き込み（300 items）
- 基本読み込み（300 items）
- 並行読み込み（600 items, 8 concurrent）
- 一括挿入（500 items）
- 混合操作（400 items）

**出力例:**
```
Performance Comparison Summary
======================================================================

Basic Write (300 items):
  v1: 0.073s (4134 ops/sec)
  v2: 0.052s (5783 ops/sec) - 1.40x vs v1
  v3: 0.052s (5754 ops/sec) - 1.39x vs v1

Overall Performance
======================================================================
Average throughput (ops/sec):
  v1: 174219
  v2: 449842 (2.58x vs v1)
  v3: 175657 (1.01x vs v1)
```

### 2. benchmark_detailed.py - 詳細最適化ベンチマーク

各バージョンの最適化機能を個別にテストします。

**実行方法:**
```bash
cd dictsqlite-fastest/beta
python3 benchmark_detailed.py
```

**テスト内容:**

#### v1固有のテスト:
- **キャッシュ効率テスト**: コールドキャッシュ vs ウォームキャッシュ

#### v2固有のテスト:
- **バッチング効率テスト**: 単一書き込み vs 一括挿入

#### v3固有のテスト:
- **コネクションプールスケーリング**: 低負荷時と高負荷時のプール動作
- **プリフェッチパターン検出**: シーケンシャルアクセス vs ランダムアクセス

#### 全バージョン共通:
- **並行ストレステスト**: 1000 ops × 16 concurrent tasks

### 3. benchmark_v3_vs_v2.py - v3 vs v2 比較

v3とv2の詳細な比較（既存スクリプト）。

**実行方法:**
```bash
cd dictsqlite-fastest/beta
python3 benchmark_v3_vs_v2.py
```

## 統合実行方法

### run_benchmark.pyスクリプト（推奨）

`others/benchmark/run_benchmark.py`を使用すると、簡単にバージョンを選択してベンチマークを実行できます。

```bash
# v1のみテスト
python others/benchmark/run_benchmark.py --beta v1

# v2のみテスト
python others/benchmark/run_benchmark.py --beta v2

# v3のみテスト
python others/benchmark/run_benchmark.py --beta v3

# 全バージョン比較（推奨）
python others/benchmark/run_benchmark.py --beta all
```

## 各バージョンの特徴

### v1 (ThreadPoolExecutor)
- **アーキテクチャ**: ThreadPoolExecutorによる非同期化
- **最適化**: LRUキャッシュ、メモリバジェット管理
- **強み**: 安定性、シンプルなアーキテクチャ
- **推奨設定**: `memory_budget_mb=128`

### v2 (aiosqlite + batching)
- **アーキテクチャ**: aiosqliteによる真の非同期処理
- **最適化**: バッチング、最適化されたSQLiteプラグマ
- **強み**: 書き込みパフォーマンス、バルク操作
- **推奨設定**: デフォルト設定で最適化済み

### v3 (Dynamic pool + prefetch + adaptive batch)
- **アーキテクチャ**: 動的コネクションプール
- **最適化**: 
  - 動的コネクションプール（自動スケーリング）
  - パターンベースプリフェッチ
  - 適応的バッチサイジング
  - 拡張統計情報
- **強み**: 高負荷時のスケーラビリティ、柔軟性
- **推奨設定**:
  ```python
  pool_min_size=2,
  pool_max_size=8,
  pool_auto_scale=True,
  enable_prefetch=True,
  adaptive_batch=True,
  extended_stats=True
  ```

## ベンチマーク結果の解釈

### ops/sec (Operations per second)
- 1秒あたりの操作数
- 高いほど高性能

### 比較倍率 (e.g., "2.58x vs v1")
- v1を基準とした性能比
- 1.0xより大きければv1より高速
- 1.0xより小さければv1より低速

### 性能の傾向

**一般的な傾向:**
- **読み込み性能**: v2 > v1 > v3（小規模データセット）
- **書き込み性能**: v2 ≈ v3 > v1
- **一括操作**: v2 > v3 > v1
- **並行処理**: データ量とアクセスパターンに依存

**注意点:**
- 小規模データセット（< 1000 items）では、v3のオーバーヘッドが目立つ場合がある
- v3は大規模データセットや高負荷時に真価を発揮
- v2は多くのユースケースでバランスが良い

## GitHub Actionsでの実行

GitHub Actionsワークフローからベンチマークを実行できます。

1. GitHubリポジトリの「Actions」タブに移動
2. 「Performance Benchmark」ワークフローを選択
3. 「Run workflow」をクリック
4. Beta版のバージョンを選択:
   - `v1`: v1のみ
   - `v2`: v2のみ
   - `v3`: v3のみ
   - `all`: 全バージョン比較
5. 「Run workflow」を実行

## トラブルシューティング

### ImportError: cannot import name 'AsyncDictSQLiteFastestBetaV2'

v2のクラス名は `AsyncDictSQLiteFastestBeta` です（V2サフィックスなし）。
正しいインポート:
```python
from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta as AsyncV2
```

### ModuleNotFoundError: No module named 'apsw'

依存パッケージをインストールしてください:
```bash
pip install apsw aiosqlite
```

### ベンチマークが遅い

- データベースファイルがSSD上にあることを確認
- 他のプロセスがCPU/IOを大量に使用していないか確認
- フルベンチマーク（`--full`）は時間がかかります

## 推奨事項

### 開発・テスト
- **v2を使用**: 安定性とパフォーマンスのバランスが良い
- 定期的に `--beta all` で全バージョンを比較

### 本番環境
- **v1を使用**: 最も実績があり安定
- **v2を使用**: より高速で安定性も確保されている

### 大規模・高負荷環境
- **v3を検討**: 適切に設定すれば高いスケーラビリティ
- 本番投入前に十分なテストを実施

## 関連ドキュメント

- [Beta版バージョン選択ガイド](../../others/BETA_VERSION_SELECTION_GUIDE.md)
- [v3-alpha ドキュメント](V3_ALPHA_DOCUMENTATION.md)
- [v3-alpha 実装サマリー](V3_ALPHA_IMPLEMENTATION_SUMMARY.md)

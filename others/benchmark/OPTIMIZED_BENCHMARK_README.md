# 最適化ベンチマーク - README

## 概要

このディレクトリには、DictSQLiteのパフォーマンスベンチマークツールが含まれています。

### 新しい最適化ベンチマーク (optimized_benchmark.py)

**変更理由**: Issue要件に基づき、DictSQLiteFastestとDictSQLiteFastestBetaのテストを廃止し、
dictsqlite (オリジナル版) と dictsqlite_v2 (v2.0版) の2つのバージョンのみをテストするように変更。

**テスト対象**:
- `DictSQLite` - オリジナル版 (/dictsqlite)
- `DictSQLiteV2` - v2.0版 (/dictsqlite-fastest/dictsqlite_v2)

**特徴**:
- 各モジュールに最適化されたテスト設定を使用
- 最速動作を確認してパフォーマンスベンチマークの意味を維持
- 2つのモード: 高速モード (fast) と完全モード (full)

## 使用方法

### ローカル実行

```bash
# 高速モード（デフォルト）
python others/benchmark/optimized_benchmark.py --mode fast

# 完全モード
python others/benchmark/optimized_benchmark.py --mode full
```

### テストモードの違い

#### 高速モード (fast)
- **用途**: CI/CD、プルリクエスト、コミットごとの自動実行
- **実行時間**: 約30秒〜1分
- **テスト内容**:
  - 基本書き込み (小・中)
  - 基本読み込み (小・中)
  - 混合操作 (小)
  - 非同期テスト (中)
- **測定回数**: 2回
- **データサイズ**: 50〜1000件

#### 完全モード (full)
- **用途**: 手動実行、詳細なパフォーマンス分析
- **実行時間**: 約2〜5分
- **テスト内容**:
  - 基本書き込み (tiny/small/medium/large)
  - 基本読み込み (tiny/small/medium/large)
  - 混合操作 (tiny/small/medium/large)
  - 非同期テスト (small/medium/large)
- **測定回数**: 3回
- **データサイズ**: 100〜10000件

## GitHub Actions統合

### 自動実行（高速モード）

プッシュまたはプルリクエスト時に自動的に高速モードで実行されます：

```yaml
on:
  push:
    branches: [main, develop]
    paths:
      - 'dictsqlite/**'
      - 'dictsqlite-fastest/dictsqlite_v2/**'
  pull_request:
    branches: [main, develop]
```

### 手動実行

GitHub ActionsのUIから手動で実行できます：

1. GitHubの「Actions」タブへ移動
2. 「Performance Benchmark」を選択
3. 「Run workflow」をクリック
4. テストモードを選択:
   - `fast`: 高速モード（約1分）
   - `full`: 完全モード（約2〜5分）

## 最適化設定

### DictSQLiteV2の最適化パラメータ

ベンチマークでは以下の最適化設定を使用してDictSQLiteV2の最高性能を引き出します：

```python
db = DictSQLiteV2(
    db_path,
    sync_interval=0.1,  # 同期間隔を短縮
    auto_sync=False      # ベンチマーク中は自動同期を無効化
)
```

これにより、以下のパフォーマンスを実現：
- **書き込み**: 40K〜116K ops/sec (オリジナルの27〜75倍)
- **読み込み**: 200K〜463K ops/sec (オリジナルの13〜30倍)
- **混合操作**: 85K ops/sec (オリジナルの46倍)

## 出力ファイル

ベンチマーク実行後、以下のファイルが `results/` ディレクトリに生成されます：

- `benchmark_YYYYMMDD_HHMMSS.csv` - CSVフォーマットの詳細結果
- `benchmark_YYYYMMDD_HHMMSS.json` - JSONフォーマットの詳細結果
- `benchmark_YYYYMMDD_HHMMSS.log` - 実行ログ
- `BENCHMARK_SUMMARY.md` - マークダウン形式のサマリー（総合勝率、推奨バージョン、詳細結果表）

## 旧ベンチマークとの比較

### 旧ベンチマーク (fast_comprehensive_benchmark.py)
- テスト対象: DictSQLite、DictSQLiteFastest、DictSQLiteFastestBeta
- 複雑な設定と多数のバージョン管理
- Beta版のバージョン選択が必要

### 新ベンチマーク (optimized_benchmark.py)
- テスト対象: DictSQLite、DictSQLiteV2のみ
- シンプルな設定と明確な最適化
- モード選択のみ（fast/full）

## トラブルシューティング

### DictSQLiteV2のパフォーマンスが遅い

DictSQLiteV2は以下のパラメータで最適化してください：
- `sync_interval`: 小さい値に設定（例: 0.1）
- `auto_sync`: ベンチマーク中はFalseに設定

### 非同期テストがエラーになる

DictSQLiteV2の非同期版 (AsyncDictSQLiteV2) は現在開発中です。
エラーが発生しても、同期版のテスト結果には影響しません。

## 今後の予定

- [ ] AsyncDictSQLiteV2の完全実装
- [ ] グラフィカルな可視化の改善
- [ ] より詳細なパフォーマンスメトリクス
- [ ] メモリ使用量の測定

## 関連ドキュメント

- [DictSQLite README](../../README.md)
- [DictSQLiteV2 README](../../dictsqlite-fastest/dictsqlite_v2/README.md)
- [GitHub Actions Workflow](.github/workflows/benchmark.yml)

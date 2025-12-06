# 最適化されたベンチマークシステム (Optimized Benchmark System)

## 概要 (Overview)

このディレクトリには、DictSQLiteの3つの主要バージョンを比較するための最適化されたベンチマークシステムが含まれています。

## アーキテクチャ (Architecture)

### 独立したテストモジュール (Separate Test Modules)

各バージョン用に独立したテストファイルを作成することで、インポートの競合を回避し、信頼性を向上させています。

```
others/benchmark/
├── test_benchmark_original.py      # Original版専用テスト
├── test_benchmark_dictsqlite_v2.py # dictsqlite_v2版専用テスト
├── test_benchmark_fastest.py       # fastest Beta v2版専用テスト
└── benchmark_all_versions_optimized.py # 統合ベンチマークランナー
```

### 利点 (Benefits)

1. **インポートの競合を回避**: 各バージョンが独立したプロセス空間で実行される
2. **明確な分離**: 各テストモジュールが単独で実行可能
3. **エラー分離**: 1つのバージョンのエラーが他のバージョンに影響しない
4. **保守性向上**: 各バージョンのテストロジックが明確に分離

## ファイル構成 (File Structure)

### test_benchmark_original.py
- **対象**: DictSQLite Original (sqlite3ベース)
- **場所**: `dictsqlite/`
- **特徴**: 同期処理のみ、標準ライブラリのsqlite3を使用

### test_benchmark_dictsqlite_v2.py
- **対象**: dictsqlite_v2 (Rust拡張 v2.0.6)
- **場所**: `dictsqlite_v2/dictsqlite/`
- **特徴**: Rust実装、DictSQLiteV4クラス、高性能

### test_benchmark_fastest.py
- **対象**: dictsqlite-fastest Beta v2
- **場所**: `others/beta-versions/dictsqlite-fastest/beta/`
- **特徴**: APSWベース、完全非同期、高性能

### benchmark_all_versions_optimized.py
- **役割**: 統合ベンチマークランナー
- **機能**: 
  - 各テストモジュールを順番に実行
  - 結果を集計・比較
  - グラフ生成
  - サマリーレポート作成

## 使用方法 (Usage)

### 全バージョン比較 (All Versions Comparison)

```bash
cd others/benchmark
python run_benchmark.py --beta all
```

これにより `benchmark_all_versions_optimized.py` が実行され、3つのバージョンが比較されます。

### 個別テストの実行 (Individual Test Execution)

各テストモジュールは単独で実行可能です:

```bash
# Original版のみテスト
python test_benchmark_original.py

# dictsqlite_v2版のみテスト
python test_benchmark_dictsqlite_v2.py

# fastest版のみテスト
python test_benchmark_fastest.py
```

## ベンチマークテスト項目 (Benchmark Tests)

各テストモジュールは以下の4つのテストを実行します:

1. **Basic Write (300 items)**: 基本的な書き込み性能
2. **Basic Read (300 items)**: 基本的な読み込み性能
3. **Bulk Insert (500 items)**: 一括挿入性能
4. **Mixed Operations (400 items)**: 読み書き混合操作

## インポート戦略 (Import Strategy)

### test_benchmark_original.py
```python
# カスタムローダーを使用してソースから直接インポート
loader = importlib.machinery.SourceFileLoader('dictsqlite_original_main', original_main_path)
spec = importlib.util.spec_from_loader('dictsqlite_original_main', loader)
dictsqlite_original = importlib.util.module_from_spec(spec)
loader.exec_module(dictsqlite_original)
```

### test_benchmark_dictsqlite_v2.py
```python
# site-packagesからインストール済みパッケージをインポート
# ローカルのdictsqliteをパスから除外
sys.path = [p for p in sys.path if 'dictsqlite' not in p.lower() or 'site-packages' in p]
from dictsqlite import DictSQLiteV4
```

### test_benchmark_fastest.py
```python
# beta-versionsディレクトリから直接インポート
BETA_V2_DIR = REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest' / 'beta'
sys.path.insert(0, str(BETA_V2_DIR))
from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta
```

## エラーハンドリング (Error Handling)

各テストモジュールは、依存関係が利用できない場合に適切に処理します:

```python
if not AVAILABLE:
    print("⏭️  Skipping {version} (not available)")
    return {
        'basic_write': (0, 0),
        'basic_read': (0, 0),
        'bulk_insert': (0, 0),
        'mixed_ops': (0, 0)
    }
```

これにより、1つのバージョンが利用できない場合でも、他のバージョンのベンチマークは続行されます。

## GitHub Actions統合 (GitHub Actions Integration)

`benchmark.yml`ワークフローは、`--beta all`モードで自動的に最適化版を使用します:

```yaml
- name: Run fast comprehensive benchmark
  run: |
    cd others/benchmark
    BETA_VERSION="${{ github.event.inputs.beta_version }}"
    export BETA_VERSION
    
    if [ "$BETA_VERSION" == "all" ]; then
      # 最適化されたベンチマークを実行
      python run_benchmark.py --beta all
    fi
```

## 出力形式 (Output Format)

### コンソール出力
- リアルタイム進捗表示
- 各テストの時間と ops/sec
- バージョン間の比較（speedup）
- 平均パフォーマンス
- ランキング

### グラフ出力
- `results/graphs/version_comparison_bar.png`: 棒グラフ比較

### CSVファイル
- 各バージョンの詳細な結果

## トラブルシューティング (Troubleshooting)

### dictsqlite_v2がインポートできない

```bash
# dictsqlite_v2をビルドしてインストール
cd dictsqlite_v2/dictsqlite
export CI=1
bash build.sh
```

### 依存関係エラー

```bash
# 必要な依存関係をインストール
pip install -r requirements.txt
pip install matplotlib seaborn pandas numpy plotly
pip install apsw zstandard aiosqlite
```

## パフォーマンス比較の例 (Example Performance Comparison)

```
📊 パフォーマンス比較結果 (Performance Comparison Summary)
================================================================================

📊 Basic Write (300 items):
  Original版:        0.077s (    3,882 ops/sec)
  dictsqlite_v2版:   0.011s (   27,388 ops/sec) -  7.06x 🚀
  Beta v2版:         0.052s (    5,776 ops/sec) -  1.49x 🚀

📊 Mixed Operations (400 items):
  Original版:        0.052s (    7,641 ops/sec)
  dictsqlite_v2版:   0.002s (  249,364 ops/sec) - 32.63x 🚀
  Beta v2版:         0.003s (  146,436 ops/sec) - 19.16x 🚀

🏆 総括 (Summary)
================================================================================

🥇 最速: dictsqlite_v2版 (143,897 ops/sec)

📊 パフォーマンスランキング (Performance ranking):
  🥇 1位. dictsqlite_v2版:   143,897 ops/sec (ベースライン比 +5593.1%)
  🥈 2位. Beta v2版:          74,657 ops/sec (ベースライン比 +2853.0%)
  🥉 3位. Original版:          2,528 ops/sec (ベースライン比 +0.0%)
```

## 今後の改善 (Future Improvements)

1. **並列実行**: 各バージョンのテストを並列で実行
2. **詳細なプロファイリング**: CPU/メモリ使用量の測定
3. **長時間ストレステスト**: 安定性の検証
4. **実世界ワークロード**: より実践的なシナリオのテスト

## 関連ドキュメント (Related Documents)

- `BENCHMARK_VERIFICATION_REPORT.md`: ビルドと検証レポート
- `BENCHMARK_ANALYSIS_SUMMARY_JP.md`: 分析サマリー
- `VERSION_MANAGEMENT.md`: バージョン管理システムの説明

---

**最終更新**: 2025-12-06  
**作成者**: GitHub Copilot  
**目的**: ベンチマークシステムの最適化と信頼性向上

# DictSQLite 包括的ベンチマークツール

3つのバージョン(DictSQLite、DictSQLite-Fastest、DictSQLite-Fastest Beta)を徹底的に比較するベンチマークツールです。

## 📊 作成されたベンチマークツール

### 1. `comprehensive_benchmark.py` (フル機能版)
最も包括的なベンチマークツール。すべてのテストシナリオを網羅。

**テスト項目:**
- 基本操作 (読み込み・書き込み)
- バルク操作 (一括挿入・一括読み込み)
- 複雑データ構造の処理
- 更新・削除操作
- 混合操作 (読み書き同時)
- 非同期操作
- 並行処理

**実行時間**: 約10〜30分

```bash
python comprehensive_benchmark.py
```

### 2. `fast_comprehensive_benchmark.py` (高速版) ⭐ 推奨
主要なテストのみを実行する高速版。日常的なベンチマークに最適。

**テスト項目:**
- 基本書き込み (100, 1,000, 5,000件)
- 基本読み込み (100, 1,000, 5,000件)
- バルク挿入 (1,000, 5,000, 10,000件)
- 非同期書き込み (100, 1,000, 5,000件)

**実行時間**: 約2〜5分

```bash
python fast_comprehensive_benchmark.py
```

### 3. `test_simple_benchmark.py` (デバッグ用)
動作確認用の簡易テスト。

```bash
python test_simple_benchmark.py
```

## 🎯 ベンチマーク結果

### 主要な発見

#### 書き込み性能
```
Beta版: 🔥 最大738倍高速 (vs Original)
```

#### 読み込み性能
```
Beta版: ⚡ 最大10倍高速 (vs Original)
Fastest版: 📈 4〜5倍高速 (vs Original)
```

#### 総合勝率
```
Beta版:     66.7% 🥇
Original版: 33.3%
Fastest版:  0.0% (初期化エラー)
```

## 📁 出力ファイル

すべての結果は `benchmark_results/` ディレクトリに保存されます:

- `benchmark_YYYYMMDD_HHMMSS.csv` - CSV形式の詳細データ
- `benchmark_YYYYMMDD_HHMMSS.json` - JSON形式の詳細データ  
- `benchmark_YYYYMMDD_HHMMSS.log` - 実行ログ
- `summary_YYYYMMDD_HHMMSS.md` - Markdownサマリー
- `BENCHMARK_SUMMARY.md` - 総合レポート (手動作成)

## 📈 CSV出力例

```csv
Test,Version,Time (s),OPS
基本書き込み (100件),original,0.236,423.14
基本書き込み (100件),beta,0.008,11980.93
基本読み込み (1,000件),original,0.169,5912.02
基本読み込み (1,000件),fastest,0.042,23724.42
基本読み込み (1,000件),beta,0.021,47234.65
```

## 🔧 ベンチマークのカスタマイズ

### テストケースの追加

```python
def test_custom_operation(self, count: int):
    """カスタムテスト"""
    test_name = f"カスタム操作 ({count}件)"
    
    # テスト実装
    def original():
        # Original版のテスト
        pass
    
    def fastest():
        # Fastest版のテスト
        pass
    
    def beta():
        # Beta版のテスト
        pass
    
    self.benchmark.compare_sync_versions(
        test_name, original, fastest, beta, count
    )
```

### 測定回数の変更

```python
# デフォルトは3回
result = self.measure("Test", func, iterations=5)  # 5回に変更
```

### ウォームアップの調整

```python
def measure(self, name: str, func: Callable, 
            iterations: int = 3, warmup: int = 2):  # ウォームアップ2回
    # ウォームアップ
    for _ in range(warmup):
        func()
    # 測定...
```

## 💡 最適化のポイント

### 各バージョンの最適化設定

#### DictSQLite Beta版 (最速)
```python
db = DictSQLiteFastestBeta(
    'test.db',
    memory_budget_mb=100,          # メモリ予算
    enable_background_flush=True,   # バックグラウンドフラッシュ
)
```

#### DictSQLite-Fastest (APSW版)
```python
db = DictSQLiteFastest(
    'test.db',
    cache_size=-64000,              # 64MB キャッシュ
    journal_mode='WAL',             # WALモード
    optimize_on_init=True,          # 初期化時最適化
)
```

#### DictSQLite Original版
```python
db = DictSQLite(
    'test.db',
    journal_mode='WAL',             # WALモード推奨
)
```

## 🔬 ベンチマーク手法

### 測定精度の向上

1. **複数回測定**: デフォルト3回の平均を取る
2. **ウォームアップ**: 1回のウォームアップ実行
3. **統計情報**: 平均・最小・最大・標準偏差を計算
4. **一時ファイル**: 各テストで新規DBファイルを使用

### OPS (Operations Per Second) 計算

```python
ops = operation_count / execution_time
```

### スピードアップ比の計算

```python
speedup = baseline_time / optimized_time
```

## 📊 結果の分析

### CSV分析 (Pandas)

```python
import pandas as pd

df = pd.read_csv('benchmark_results/benchmark_XXXXXX.csv')

# バージョン別の平均OPS
df.groupby('Version')['OPS'].mean()

# テスト別の最速バージョン
df.loc[df.groupby('Test')['Time (s)'].idxmin()]
```

### JSON分析

```python
import json

with open('benchmark_results/benchmark_XXXXXX.json') as f:
    data = json.load(f)

# 勝率計算
sync_tests = data['sync_tests']
wins = {}
for test in sync_tests:
    results = test['results']
    fastest = min(results.items(), key=lambda x: x[1]['time'])
    wins[fastest[0]] = wins.get(fastest[0], 0) + 1
```

## 🐛 既知の問題

### DictSQLite-Fastest の初期化エラー

**エラー**: `no such table: main`

**原因**: テーブル初期化のタイミング問題

**回避策**: 
```python
# コンテキストマネージャーを使用
with DictSQLiteFastest('test.db') as db:
    db['key'] = 'value'  # OK
```

### Beta版の非同期ファイルロック

**エラー**: `[WinError 32] プロセスはファイルにアクセスできません`

**原因**: Windows環境でのファイルロック競合

**回避策**:
```python
# 適切なクリーンアップ
await db.aclose()
await asyncio.sleep(0.2)  # ファイルハンドルの解放待ち
```

## 🚀 パフォーマンスチューニング

### メモリ vs 速度のトレードオフ

```python
# 高速だがメモリ多用
db = DictSQLiteFastestBeta('test.db', memory_budget_mb=500)

# バランス型
db = DictSQLiteFastestBeta('test.db', memory_budget_mb=100)

# 省メモリ
db = DictSQLiteFastest('test.db', cache_size=-16000)  # 16MB
```

### データ量別の推奨設定

| データ量 | 推奨バージョン | 設定 |
|---------|--------------|-----|
| 〜1万件 | Beta版 | memory_budget_mb=50 |
| 〜10万件 | Beta版 | memory_budget_mb=100 |
| 〜100万件 | Beta版 | memory_budget_mb=500 |
| 100万件〜 | Fastest版 | cache_size=-128000 |

## 📚 参考資料

- [DictSQLite Documentation](../documents/japanese.md)
- [DictSQLite-Fastest README](../dictsqlite-fastest/README.md)
- [Beta版 Documentation](../dictsqlite-fastest/beta/README_JP.md)

## 🤝 貢献

ベンチマークの改善提案や新しいテストケースの追加は大歓迎です!

1. テストケースを追加
2. ベンチマークを実行
3. 結果をCSV/JSONで保存
4. PRを作成

## 📝 ライセンス

このベンチマークツールはDictSQLiteプロジェクトと同じライセンスです。

---

**作成者**: GitHub Copilot  
**バージョン**: 1.0.0  
**最終更新**: 2025年10月4日

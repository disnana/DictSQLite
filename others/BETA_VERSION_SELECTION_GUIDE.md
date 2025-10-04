# Beta版バージョン選択ガイド

## 概要

DictSQLite-Fastest Beta版には2つのバージョンがあります：
- **v1**: 既存の安定版（ThreadPoolExecutor）
- **v2**: 新版（aiosqlite + 内部バッチ処理、デッドロック修正済み）

## GitHub Actionsでの選択方法

1. GitHubリポジトリの「Actions」タブに移動
2. 「Performance Benchmark」ワークフローを選択
3. 「Run workflow」をクリック
4. **Beta版のバージョン選択**で以下から選択：
   - `v1`: Beta v1のみテスト（既存版）
   - `v2`: Beta v2のみテスト（新版）
   - `both`: 両方テスト（未実装）

5. オプション：フル機能ベンチマークを実行するか選択
6. 「Run workflow」を実行

### 例: v2でテストする場合

```yaml
フル機能ベンチマークを実行: false
Beta版のバージョン選択: v2
```

## ローカルでの選択方法

### 方法1: run_benchmark.pyスクリプトを使用（推奨）

```bash
# v1のみテスト（高速ベンチマーク）
python others/benchmark/run_benchmark.py --beta v1

# v2のみテスト（高速ベンチマーク）
python others/benchmark/run_benchmark.py --beta v2

# 両方テスト
python others/benchmark/run_benchmark.py --beta both

# v2でフルベンチマーク
python others/benchmark/run_benchmark.py --beta v2 --full
```

**メリット:**
- 自動的にインポートを変更
- テスト後に元に戻す
- バックアップを自動作成

### 方法2: 手動でインポートを変更

#### v1を使う場合（デフォルト）
```python
# comprehensive_benchmark.py, fast_comprehensive_benchmark.py
from dictsqlite_fastest_beta import DictSQLiteFastestBeta, AsyncDictSQLiteFastestBeta
```

#### v2を使う場合
```python
# comprehensive_benchmark.py, fast_comprehensive_benchmark.py
from dictsqlite_fastest_beta_v2 import DictSQLiteFastestBeta, AsyncDictSQLiteFastestBeta
```

変更後、通常通りベンチマークを実行：
```bash
python others/benchmark/fast_comprehensive_benchmark.py
```

## バージョン比較表

| 項目 | v1 | v2 |
|:-----|:---|:---|
| **同期版** | APSW + LRUキャッシュ + 書き込みバッファ | 同じ |
| **非同期版** | ThreadPoolExecutor | aiosqlite + 内部バッチ |
| **非同期性能** | 遅い（30秒/1000件） | 高速（0.001秒/100件） |
| **デッドロック** | なし | 修正済み |
| **安定性** | 安定 | 安定（修正後） |
| **推奨用途** | 既存システム | 新規開発 |

## トラブルシューティング

### エラー: `ImportError: cannot import name 'DictSQLiteFastestBeta'`

**原因:** インポート文が間違っているか、ファイルが存在しない

**解決策:**
```bash
# v1を確認
ls dictsqlite-fastest/beta/dictsqlite_fastest_beta.py

# v2を確認
ls dictsqlite-fastest/beta/dictsqlite_fastest_beta_v2.py
```

### エラー: `ModuleNotFoundError: No module named 'aiosqlite'`

**原因:** v2の依存関係がインストールされていない

**解決策:**
```bash
pip install aiosqlite
```

### GitHub Actionsで選択が反映されない

**原因:** ワークフローファイルが更新されていない

**解決策:**
1. `.github/workflows/benchmark.yml`を確認
2. `beta_version`入力が定義されているか確認
3. プッシュしてワークフローを更新

## 推奨事項

### 開発中
- **v2を使用**: 最新の修正とパフォーマンス改善

### 本番環境
- **v1を使用**: 実績があり安定

### テスト
- **bothを使用**: 両バージョンを比較（将来実装予定）

## 次のステップ

1. **v2の大規模テスト**: 1000～5000件でのパフォーマンス検証
2. **両バージョン比較**: パフォーマンスグラフの生成
3. **v2の本番投入**: 安定性確認後にv1を置き換え

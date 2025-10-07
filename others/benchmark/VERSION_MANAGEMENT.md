# ベンチマーク結果バージョン管理システム

## 概要

このシステムは、DictSQLiteの各バージョンのベンチマーク結果を固定名で保存・管理し、
バージョン間の比較を容易にします。

## 特徴

- ✅ **バージョン固定名**: 各バージョンの結果は固定のファイル名で保存されます
- ✅ **上書き許可**: 同じバージョンの結果は自動的に上書きされます
- ✅ **履歴管理**: 実行履歴をJSON形式で追跡します
- ✅ **比較機能**: 複数バージョン間の詳細な比較レポートを生成します
- ✅ **自動整理**: 古いバージョンの結果を自動的にクリーンアップできます

## ディレクトリ構造

```
others/benchmark/results/
├── versions/                          # バージョンごとの結果
│   ├── v1.8.9_v1.0.0_v0.1.0-beta/    # バージョン固有ディレクトリ
│   │   ├── benchmark_v1.8.9_v1.0.0_v0.1.0-beta.csv
│   │   ├── benchmark_v1.8.9_v1.0.0_v0.1.0-beta.json
│   │   ├── summary_v1.8.9_v1.0.0_v0.1.0-beta.md
│   │   ├── benchmark_v1.8.9_v1.0.0_v0.1.0-beta.log
│   │   └── graphs/                    # バージョン固有のグラフ
│   │       ├── ops_comparison.png
│   │       ├── time_comparison.png
│   │       └── ...
│   └── v1.8.10_v1.0.1_v0.1.1-beta/   # 次のバージョン
│       └── ...
├── comparisons/                       # バージョン間比較
│   ├── comparison_20241207_120000.md
│   ├── version_comparison_20241207_120000.png
│   └── ...
├── version_history.json               # バージョン履歴
├── VERSION_INDEX.md                   # バージョン一覧
├── benchmark_YYYYMMDD_HHMMSS.csv     # 一時ファイル（最新5個保持）
├── benchmark_YYYYMMDD_HHMMSS.json
├── benchmark_YYYYMMDD_HHMMSS.log
└── graphs/                            # 最新実行のグラフ
    └── ...
```

## バージョン命名規則

バージョン文字列は以下の形式で生成されます：

```
v{original}_v{fastest}_v{beta}
```

例：
- `v1.8.9_v1.0.0_v0.1.0-beta`
- `v1.8.10_v1.0.1_v0.1.1-beta`

各コンポーネントのバージョンは以下から取得されます：
- **original**: `dictsqlite/main.py` の `__version__`
- **fastest**: `others/beta-versions/dictsqlite-fastest/dictsqlite_fastest/__init__.py` の `__version__`
- **beta**: `others/beta-versions/dictsqlite-fastest/beta/__init__.py` の `__version__`

## 使い方

### 1. ベンチマーク実行（バージョン管理付き）

ベンチマークを実行すると、自動的にバージョン管理システムが結果を保存します：

```bash
cd others/benchmark

# 高速ベンチマーク（推奨）
python fast_comprehensive_benchmark.py

# フルベンチマーク
python comprehensive_benchmark.py
```

実行すると以下が自動的に行われます：
1. 現在のバージョン情報を取得
2. ベンチマーク実行
3. 結果をタイムスタンプ付きファイルに保存
4. 結果をバージョン固有のディレクトリにコピー（上書き）
5. グラフをバージョン固有のディレクトリにコピー

### 2. バージョン間比較

複数バージョンの結果を比較するには：

```bash
cd others/benchmark
python compare_versions.py
```

これにより以下が生成されます：
- バージョン間比較グラフ（PNG）
- 比較レポート（Markdown）
- バージョンインデックス（Markdown）

### 3. 特定バージョンの確認

```bash
# バージョン一覧を確認
ls results/versions/

# 特定バージョンの結果を確認
cat results/versions/v1.8.9_v1.0.0_v0.1.0-beta/summary_*.md
```

### 4. バージョン管理システムの直接利用

Pythonスクリプトから直接利用することもできます：

```python
from version_manager import VersionManager

# 初期化
manager = VersionManager()

# バージョン情報を取得
versions = manager.get_version_info()
print(f"Original: {versions['original']}")
print(f"Fastest: {versions['fastest']}")
print(f"Beta: {versions['beta']}")

# バージョン文字列を取得
version_string = manager.get_version_string()
print(f"Version string: {version_string}")

# 利用可能なバージョン一覧
available = manager.list_available_versions()
for version in available:
    print(f"- {version}")

# 結果を保存
manager.save_benchmark_result(
    csv_content="...",
    json_content={...},
    summary_content="...",
    version_string=version_string
)

# グラフをコピー
manager.copy_graphs_to_version(
    graphs_source_dir=Path("results/graphs"),
    version_string=version_string
)

# 比較レポートを作成
manager.create_comparison_report()
```

## 主要機能

### 自動上書き

同じバージョンでベンチマークを再実行すると、既存の結果が自動的に上書きされます。
これにより、各バージョンの最新の結果のみが保持されます。

### 履歴追跡

`version_history.json` には以下の情報が記録されます：
- 各バージョンの実行履歴
- 実行日時
- 保存されたファイルのパス

### クリーンアップ

古いバージョンの結果を削除するには：

```python
from version_manager import VersionManager

manager = VersionManager()
# 最新5バージョンのみを保持
manager.cleanup_old_versions(keep_latest=5)
```

## GitHub Actions との連携

GitHub Actionsでベンチマークを実行すると、結果は自動的にバージョン管理システムに保存され、
リポジトリにコミットされます。

ワークフローファイル: `.github/workflows/benchmark.yml`

手動実行方法：
1. GitHubリポジトリの「Actions」タブを開く
2. 「Performance Benchmark」を選択
3. 「Run workflow」をクリック
4. Beta版のバージョンを選択（v1, v2, v3, v4, all）
5. 実行

結果は以下の場所で確認できます：
- Artifactsセクション（90日間保持）
- リポジトリの `others/benchmark/results/` ディレクトリ
- バージョン固有ディレクトリ: `others/benchmark/results/versions/v{version}/`

## ファイル形式

### CSV形式

ベンチマーク結果は2つの形式があります：

#### Wide形式（comprehensive_benchmark.py）
```csv
Test Name,Operation Count,Original Time (s),Original OPS,Fastest Time (s),Fastest OPS,Beta Time (s),Beta OPS,...
基本書き込み (1000件),1000,1.234,810.37,0.234,4273.50,0.189,5291.00,...
```

#### Long形式（fast_comprehensive_benchmark.py）
```csv
Test,Version,Time (s),OPS
基本書き込み (100件),original,0.123,813.01
基本書き込み (100件),fastest,0.023,4347.83
基本書き込み (100件),beta,0.019,5263.16
```

### JSON形式

```json
{
  "timestamp": "20241207_120000",
  "sync_tests": [...],
  "async_tests": [...]
}
```

### バージョン履歴形式

```json
{
  "versions": {
    "v1.8.9_v1.0.0_v0.1.0-beta": [
      {
        "timestamp": "2024-12-07T12:00:00",
        "files": [...]
      }
    ]
  },
  "latest_run": "2024-12-07T12:00:00"
}
```

## トラブルシューティング

### バージョン情報が "unknown" になる

原因：
- モジュールのインポートに失敗
- バージョンファイルが見つからない

解決策：
1. 必要な依存関係をインストール: `pip install -r requirements.txt`
2. バージョンファイルのパスを確認
3. `version_manager.py` の `get_version_info()` メソッドを確認

### グラフが生成されない

原因：
- matplotlib/seaborn がインストールされていない
- 環境変数でグラフ生成がスキップされている

解決策：
1. `pip install matplotlib seaborn pandas numpy`
2. 環境変数を確認: `echo $SKIP_BENCHMARK_GRAPHS`

### 比較レポートが空

原因：
- バージョンディレクトリにCSVファイルがない

解決策：
1. ベンチマークを実行して結果を生成
2. `results/versions/` ディレクトリを確認

## 関連ファイル

- `version_manager.py`: バージョン管理システムの本体
- `compare_versions.py`: バージョン間比較ツール
- `comprehensive_benchmark.py`: フルベンチマークスクリプト（バージョン管理対応）
- `fast_comprehensive_benchmark.py`: 高速ベンチマークスクリプト（バージョン管理対応）
- `visualize_benchmark.py`: グラフ生成ツール
- `.github/workflows/benchmark.yml`: GitHub Actions ワークフロー

## 今後の拡張

- [ ] Webベースのダッシュボード
- [ ] 自動的なパフォーマンス回帰検出
- [ ] メール通知機能
- [ ] より詳細な統計分析
- [ ] インタラクティブなグラフ（Plotly）

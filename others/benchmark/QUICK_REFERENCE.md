# クイックリファレンス - ベンチマークバージョン管理システム

## 📖 よく使うコマンド

### ベンチマーク実行

```bash
cd others/benchmark

# 高速ベンチマーク（推奨、2-5分）
python fast_comprehensive_benchmark.py

# フルベンチマーク（10-20分）
python comprehensive_benchmark.py
```

### バージョン間比較

```bash
cd others/benchmark

# 全バージョンを比較
python compare_versions.py
```

### テスト

```bash
cd others/benchmark

# システムテスト
python test_version_manager.py

# バージョン情報確認
python version_manager.py
```

### 結果確認

```bash
cd others/benchmark/results

# バージョン一覧
cat VERSION_INDEX.md

# 最新の比較レポート
cat comparisons/comparison_report_*.md | tail -n 100

# 特定バージョンの結果
cat versions/v1/summary.md
cat versions/v2/summary.md
cat versions/all/summary.md
```

## 📂 重要なファイルとディレクトリ

| パス | 説明 | Git管理 |
|------|------|---------|
| `results/versions/v1/` | Beta版 v1 の結果 | ✅ はい |
| `results/versions/v2/` | Beta版 v2 の結果 | ✅ はい |
| `results/versions/v3/` | Beta版 v3 の結果 | ✅ はい |
| `results/versions/v4/` | Beta版 v4 の結果 | ✅ はい |
| `results/versions/all/` | 全バージョン比較の結果 | ✅ はい |
| `results/comparisons/` | バージョン間比較 | ✅ はい |
| `results/version_history.json` | 実行履歴 | ✅ はい |
| `results/VERSION_INDEX.md` | バージョン一覧 | ✅ はい |
| `results/benchmark_*.csv` | 一時CSV | ❌ いいえ |
| `results/graphs/` | 一時グラフ | ❌ いいえ |

## 🔍 バージョンフォルダ名

### GitHub Actions での実行時

- **v1 を選択** → `results/versions/v1/`
- **v2 を選択** → `results/versions/v2/`
- **v3 を選択** → `results/versions/v3/`
- **v4 を選択** → `results/versions/v4/`
- **all を選択** → `results/versions/all/`

各フォルダ内のファイル名は固定：
- `benchmark.csv`
- `benchmark.json`
- `summary.md`
- `benchmark.log`
- `graphs/`

### ローカル実行時の詳細バージョン文字列（環境変数未設定時）

```
v1.8.9_v1.0.0_v0.1.0-beta
│      │      │
│      │      └─ Beta版: 0.1.0-beta
│      └─ Fastest版: 1.0.0
└─ Original版: 1.8.9
```

## 💡 よくある質問

### Q: バージョン文字列が "unknown" になる

**A:** 依存関係が不足しています。以下を実行：

```bash
pip install -r requirements.txt
pip install apsw zstandard
```

### Q: グラフが生成されない

**A:** グラフ生成ライブラリが必要です：

```bash
pip install matplotlib seaborn pandas numpy
```

### Q: 古いバージョンを削除したい

**A:** Pythonで実行：

```python
from version_manager import VersionManager
manager = VersionManager()
manager.cleanup_old_versions(keep_latest=5)  # 最新5個を保持
```

### Q: GitHub Actionsで実行するには？

**A:**
1. GitHubリポジトリの「Actions」タブ
2. 「Performance Benchmark」を選択
3. 「Run workflow」をクリック
4. Beta版バージョンを選択
5. 「Run workflow」ボタンをクリック

### Q: 結果をダウンロードするには？

**A:**
- **方法1**: GitHub ActionsのArtifactsセクションからダウンロード
- **方法2**: リポジトリの `others/benchmark/results/` をクローン

## 🛠️ トラブルシューティング

### エラー: "No module named 'portalocker'"

```bash
pip install portalocker
```

### エラー: "No module named 'apsw'"

```bash
pip install apsw
```

### エラー: グラフ生成失敗

```bash
pip install matplotlib seaborn pandas numpy plotly kaleido
```

### Windows: 日本語フォント問題

システムにYu Gothic UIがインストールされていることを確認。
または `visualize_benchmark.py` の日本語フォント設定を調整。

## 📊 ファイルサイズの目安

| ファイル | サイズ |
|----------|--------|
| CSV | 5-50 KB |
| JSON | 10-100 KB |
| Summary (MD) | 5-20 KB |
| Log | 10-50 KB |
| グラフ (PNG) | 50-200 KB/枚 |

## 🔄 ワークフロー

### 1. 開発中のベンチマーク

```bash
# コードを変更
vim dictsqlite/main.py

# バージョンを更新
vim dictsqlite/main.py  # __version__ = '1.8.10'

# ベンチマーク実行
cd others/benchmark
python fast_comprehensive_benchmark.py

# 結果確認
cat results/versions/v1.8.10_*/summary_*.md
```

### 2. リリース前の詳細テスト

```bash
# フルベンチマーク実行
python comprehensive_benchmark.py

# バージョン間比較
python compare_versions.py

# 比較レポート確認
cat results/comparisons/comparison_report_*.md
```

### 3. GitHub Actionsでの自動実行

1. コードをプッシュ
2. GitHub Actionsを手動トリガー
3. Artifactsから結果をダウンロード
4. 自動的にリポジトリにコミット

## 📚 詳細情報

| ドキュメント | 内容 |
|--------------|------|
| [VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md) | 詳細な使い方 |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | 実装報告 |
| [SYSTEM_FLOW.md](SYSTEM_FLOW.md) | システムフロー図 |
| [BENCHMARK_README.md](BENCHMARK_README.md) | ベンチマーク全般の説明 |

## 🎯 ベストプラクティス

### ✅ 推奨

- 定期的にベンチマークを実行
- バージョン更新時は必ず実行
- compare_versions.py で進化を追跡
- GitHub Actionsで自動化

### ❌ 非推奨

- 一時ファイルを手動でバージョンディレクトリにコピー
- version_history.json を手動編集
- .gitignore を無視してコミット

## 🚀 次のステップ

1. **初回実行**: `python fast_comprehensive_benchmark.py`
2. **結果確認**: `cat results/VERSION_INDEX.md`
3. **バージョン更新後**: 再度ベンチマーク実行
4. **比較**: `python compare_versions.py`
5. **レポート確認**: `cat results/comparisons/comparison_report_*.md`

---

**作成日**: 2024-12-07
**バージョン**: 1.0.0

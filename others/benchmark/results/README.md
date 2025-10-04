# ベンチマーク結果ディレクトリ

このディレクトリには、ベンチマーク実行時に生成される結果ファイルが保存されます。

## 生成されるファイル

- `benchmark_YYYYMMDD_HHMMSS.csv` - CSVフォーマットのベンチマーク結果
- `benchmark_YYYYMMDD_HHMMSS.json` - JSON形式の詳細データ
- `benchmark_YYYYMMDD_HHMMSS.log` - 実行ログ
- `BENCHMARK_SUMMARY.md` - マークダウン形式のサマリー
- `graphs/` - 生成されたグラフファイル（PNG/HTML）

## 結果の確認方法

### ローカル実行の場合
```bash
cd others/benchmark
python fast_comprehensive_benchmark.py
```

### GitHub Actionsの場合
1. GitHubの「Actions」タブを開く
2. 「Performance Benchmark」を選択
3. 「Run workflow」をクリック
4. 実行完了後、Artifactsセクションから結果をダウンロード

## 注意事項

- 結果ファイルは`.gitignore`に含まれており、リポジトリにコミットされません
- GitHub Actionsでは、結果はArtifactsとして90日間保存されます

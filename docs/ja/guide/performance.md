# パフォーマンスとベンチマーク

ベンチマークは v2 パッケージ配下で実行します。quick/full/stress プロファイルで測定量を切り替えられます。

```bash
cd dictsqlite_v2/dictsqlite
python benchmark/benchmark_all.py --profile quick
python benchmark/analyze_results.py
```

## 測定軸

- データサイズ
- レコード数
- バッチサイズ
- 保存形式と永続化モード
- cold read / hot write / delete / clear / threaded access

## GitHub Actions

自動・手動の performance workflow は CSV、画像、GitHub benchmark 用 JSON、Actions Summary の Markdown を出力します。runner 差による誤検知を避けるため、比較は警告ではなく情報表示です。

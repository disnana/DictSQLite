# パフォーマンスとベンチマーク

ベンチマークは `benchmarks/benchmark_validation.py` にあります。外部依存なしで通常版とコンパイル版を比較できます。

```bash
python benchmarks/benchmark_validation.py
python benchmarks/benchmark_validation.py --json
```

## 測定内容

- `flat_basic`: 基本型中心の平坦なスキーマ
- `nested_payload`: ネストした辞書とリスト
- `collect_errors`: 複数エラー収集モード
- `class_schema`: クラス記法スキーマ

## 読み方

`speedup` が 1 より大きいほど、コンパイル版が高速です。特殊バリデータやカスタム処理が多い場合は通常版との差が小さくなります。

## コンパイル版の最適化対象

`compile(schema)` は、通常検証と `collect_errors=True` の検証で別々の生成関数を使います。ホットパスでは、同じスキーマを一度だけコンパイルして再利用してください。

`collect_errors=True` は複数の `ErrorDetail` を作成するため、通常検証より速度差は小さくなります。大量の正常データを検証する経路では通常検証、入力全体のエラー一覧が必要な経路では `collect_errors=True` を使い分けるのがおすすめです。

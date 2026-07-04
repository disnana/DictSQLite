# 事前コンパイル

同じスキーマを何度も使う場合は `compile(schema)` で専用の検証関数を生成できます。

```python
from validkit import compile, v

user_schema = compile({
"id": v.int(),
"name": v.str().min(3),
"roles": v.list(v.str()),
})

user_schema.validate({"id": 1, "name": "Alice", "roles": ["admin"]})
```

## 向いている用途

- API リクエストを大量に検証する処理
- 同じイベント形状を繰り返し検証する処理
- ETL やログ処理のホットパス

## 注意点

すべてのバリデータが完全にインライン化されるわけではありません。特殊なバリデータは通常の `validate()` 実装へフォールバックします。

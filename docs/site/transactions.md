# 部分更新とマージ

`partial=True` を使うと、欠損キーを許容できます。`base` を渡すと既存値を補完できます。

```python
from validkit import v, validate

schema = {"theme": v.str(), "volume": v.int()}
base = {"theme": "dark", "volume": 50}

updated = validate({"volume": 80}, schema, partial=True, base=base)
```

## マイグレーション

```python
schema = {"username": v.str()}
data = validate(
{"user_name": "alice"},
schema,
migrate={"user_name": "username"},
)
```

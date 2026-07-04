# ValidKit ガイド

ValidKit は、辞書ベースのデータを小さなスキーマで検証するための Python ライブラリです。

## インストール

```bash
pip install validkit-py
```

## 最小例

```python
from validkit import v, validate

schema = {
"name": v.str().min(3),
"age": v.int().range(0, 150),
"tags": v.list(v.str()).default([]),
}

user = validate({"name": "Alice", "age": 30}, schema)
print(user)
```

## スキーマの考え方

スキーマは Python の辞書です。キーは検証後の出力キーになり、値には `v.str()` などのバリデータ、ネストした辞書、または `str` / `int` / `float` / `bool` の短縮表記を置けます。

```python
schema = {
"account": {
    "email": v.str().regex(r"^[^@]+@[^@]+$"),
    "admin": bool,
}
}
```

## 次に読むもの

- [チュートリアル](./tutorial)
- [バリデーション機能](./validation)
- [パフォーマンス](./performance)
- [API](./api)

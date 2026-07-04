# バリデーション機能

## 型と範囲

```python
schema = {
"name": v.str().range(3, 20),
"score": v.float().range(0.0, 100.0),
"enabled": v.bool(),
}
```

## 型変換

```python
schema = {
"port": v.int().coerce(),
"enabled": v.bool().coerce(),
}
```

## 条件付き必須

```python
schema = {
"is_admin": v.bool(),
"admin_key": v.str().when(lambda data: data.get("is_admin") is True),
}
```

## カスタム検証

```python
def normalize(value: str) -> str:
value = value.strip()
if not value:
    raise ValueError("empty value")
return value

schema = {"name": v.str().custom(normalize)}
```

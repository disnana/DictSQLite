# エラーハンドリング

```python
from validkit import ValidationError, v, validate

try:
validate({"age": "old"}, {"age": v.int()})
except ValidationError as exc:
print(exc.path)     # age
print(exc.message)  # Expected int, got str
print(exc.value)    # old
```

## `collect_errors=True`

```python
result = validate(
{"id": "x", "name": "Al"},
{"id": v.int(), "name": v.str().min(3)},
collect_errors=True,
)

for error in result.errors:
print(error.path, error.message)
```

## 秘密値のマスク

```python
schema = {"password": v.str().min(12).secret()}
```

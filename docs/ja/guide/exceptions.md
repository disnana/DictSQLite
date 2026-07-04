# 例外と結果型

## `ValidationError`

検証に失敗したときに送出される例外です。

- `message`
- `path`
- `value`

## `ErrorDetail`

`collect_errors=True` で収集される 1 件分のエラーです。

## `ValidationResult`

複数エラー収集時の戻り値です。

```python
result = validate(data, schema, collect_errors=True)
print(result.data)
print(result.errors)
```

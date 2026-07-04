# Exceptions and Result Types

## `ValidationError`

Raised when validation fails.

- `message`
- `path`
- `value`

## `ErrorDetail`

Represents one collected error when `collect_errors=True` is used.

## `ValidationResult`

Returned when collecting multiple errors.

```python
result = validate(data, schema, collect_errors=True)
print(result.data)
print(result.errors)
```

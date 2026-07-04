# Validation Features

## Types and ranges

```python
schema = {
"name": v.str().range(3, 20),
"score": v.float().range(0.0, 100.0),
"enabled": v.bool(),
}
```

## Coercion

```python
schema = {
"port": v.int().coerce(),
"enabled": v.bool().coerce(),
}
```

## Conditional fields

```python
schema = {
"is_admin": v.bool(),
"admin_key": v.str().when(lambda data: data.get("is_admin") is True),
}
```

## Custom validation

```python
def normalize(value: str) -> str:
value = value.strip()
if not value:
    raise ValueError("empty value")
return value

schema = {"name": v.str().custom(normalize)}
```

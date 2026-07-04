# ValidKit Guide

ValidKit validates dictionary-based data with compact Python schemas.

## Installation

```bash
pip install validkit-py
```

## Minimal example

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

## Schema model

A schema is a Python dictionary. Keys become output keys, and values can be validators, nested dictionaries, or shorthand types such as `str`, `int`, `float`, and `bool`.

```python
schema = {
"account": {
    "email": v.str().regex(r"^[^@]+@[^@]+$"),
    "admin": bool,
}
}
```

## Next steps

- [Tutorial](./tutorial)
- [Validation features](./validation)
- [Performance](./performance)
- [API](./api)

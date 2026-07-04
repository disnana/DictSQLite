# Tutorial

## Validate application settings

```python
from validkit import v, validate, ValidationError

config_schema = {
"host": v.str().default("127.0.0.1"),
"port": v.int().coerce().range(1, 65535).env("APP_PORT").default(8000),
"debug": v.bool().coerce().default(False),
}

try:
config = validate({"port": "8080"}, config_schema)
except ValidationError as exc:
print(exc.path, exc.message)
```

## Use class-style schemas

```python
from typing import Optional
from validkit import validate

class User:
name: str
age: int = 18
nickname: Optional[str]

user = validate({"name": "Nana"}, User)
```

## Collect multiple errors

```python
from validkit import v, validate

schema = {"id": v.int(), "name": v.str().min(3)}
result = validate({"id": "x", "name": "Al"}, schema, collect_errors=True)

for error in result.errors:
print(error.path, error.message)
```

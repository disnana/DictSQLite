# Partial Validation and Merging

Use `partial=True` to allow missing keys. Pass `base` to fill values from existing data.

```python
from validkit import v, validate

schema = {"theme": v.str(), "volume": v.int()}
base = {"theme": "dark", "volume": 50}

updated = validate({"volume": 80}, schema, partial=True, base=base)
```

## Migration

```python
schema = {"username": v.str()}
data = validate(
{"user_name": "alice"},
schema,
migrate={"user_name": "username"},
)
```

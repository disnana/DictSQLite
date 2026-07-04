# Precompiled Validation

When a schema is used repeatedly, `compile(schema)` generates a specialized validator.

```python
from validkit import compile, v

user_schema = compile({
"id": v.int(),
"name": v.str().min(3),
"roles": v.list(v.str()),
})

user_schema.validate({"id": 1, "name": "Alice", "roles": ["admin"]})
```

## Best fit

- High-volume API payload validation
- Repeated validation of the same event shape
- ETL and logging hot paths

## Notes

Not every validator is fully inlined. Specialized validators may fall back to their normal `validate()` implementation.

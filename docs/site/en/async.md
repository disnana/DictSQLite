# Using ValidKit in Async Code

ValidKit validation is synchronous, but it performs lightweight CPU work without I/O, so it can usually be called directly inside async handlers.

```python
from validkit import v, validate

schema = {"name": v.str(), "age": v.int()}

async def create_user(request):
payload = await request.json()
data = validate(payload, schema)
return data
```

For very large payloads or hot paths, precompile schemas with `compile()` to reduce validation latency.

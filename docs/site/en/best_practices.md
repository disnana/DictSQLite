# Best Practices

## Reuse schemas

Define frequently used schemas as module constants. Use `compile()` on hot paths.

## Validate at boundaries

Validate data as soon as it crosses a trust boundary: APIs, CLIs, config files, and external events.

## Avoid leaking secrets

```python
schema = {
"api_key": v.str().secret(),
"password": v.str().secret(),
}
```

## Name complex callbacks

Keep lambdas short. Use named functions for complex `.when()` and `.custom()` callbacks so they can be tested.

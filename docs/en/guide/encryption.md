# Security

ValidKit helps validate data at trust boundaries. It is not a replacement for authorization, encryption, or output sanitization.

## Secrets

```python
schema = {
"token": v.str().secret(),
"password": v.str().secret(),
}
```

## Environment fallback

```python
schema = {
"api_key": v.str().env("APP_API_KEY").secret(),
}
```

## Recommendations

- Validate external input as soon as it is received
- Use `.secret()` for values that may appear in logs
- Unit-test complex `.custom()` callbacks

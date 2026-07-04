# Safety

## Safe Pickle

Pickle is convenient but unsafe for untrusted data. DictSQLite v2 can restrict allowed types with Safe Pickle policies.

```python
db = DictSQLite("safe.db", storage_mode="pickle", safe_pickle=True)
```

## Encryption

```python
db = DictSQLite("secure.db", encryption_password="change-me")
```

Encryption uses AES-256-GCM. Keep passwords and keys in environment variables or secret management, not source code.

## Recommendations

- Do not load untrusted pickle data
- Always call `close()` when persistence matters
- Keep benchmark alerts informational in GitHub Actions

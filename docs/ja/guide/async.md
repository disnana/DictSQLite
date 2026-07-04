# 非同期コードでの利用

ValidKit の検証処理は同期関数ですが、I/O を行わない軽量な CPU 処理なので、通常は async ハンドラ内でそのまま呼び出せます。

```python
from validkit import v, validate

schema = {"name": v.str(), "age": v.int()}

async def create_user(request):
payload = await request.json()
data = validate(payload, schema)
return data
```

非常に大きい payload を大量に処理する場合は、ホットパスのスキーマを `compile()` しておくとレイテンシを抑えやすくなります。

# セキュリティ

ValidKit は入力データの境界検証を助けます。認可、暗号化、サニタイズの代替ではありません。

## 秘密値

```python
schema = {
"token": v.str().secret(),
"password": v.str().secret(),
}
```

## 環境変数フォールバック

```python
schema = {
"api_key": v.str().env("APP_API_KEY").secret(),
}
```

## 推奨

- 外部入力は受け取った直後に検証する
- ログに出る可能性がある値は `.secret()` を使う
- 複雑な `.custom()` は単体テストを書く

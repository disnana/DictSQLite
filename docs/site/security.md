# 安全性

## Safe Pickle

pickle は便利ですが、信頼できないデータには危険です。DictSQLite v2 は Safe Pickle ポリシーで許可型を制限できます。

```python
db = DictSQLite("safe.db", storage_mode="pickle", safe_pickle=True)
```

## 暗号化

```python
db = DictSQLite("secure.db", encryption_password="change-me")
```

暗号化は AES-256-GCM を使います。パスワードや鍵はソースコードに直書きせず、環境変数やシークレット管理に置いてください。

## 推奨

- 信頼できない pickle データを読み込まない
- 永続化が必要な処理では `close()` を必ず呼ぶ
- GitHub Actions では benchmark alert を情報表示に留める

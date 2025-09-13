# DictSQLite

[![PyPI version](https://img.shields.io/pypi/v/dictsqlite.svg)](https://pypi.org/project/dictsqlite/)
[![Python versions](https://img.shields.io/pypi/pyversions/dictsqlite.svg)](https://pypi.org/project/dictsqlite/)
[![License](https://img.shields.io/badge/License-MIT%20%28Custom%29-blue.svg)](https://github.com/disnana/DictSQLite/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/dictsqlite)](https://pepy.tech/project/dictsqlite)

**SQLiteデータベースを、Pythonの辞書のようにシンプルに扱えます。**

---

[View in English (英語のREADMEはこちら)](../README.md)

DictSQLiteは、SQLiteデータベースに対してPythonicで辞書のようなインターフェースを提供し、データベース操作を直感的かつ簡単に行えるようにします。基本的なCRUD（作成、読み取り、更新、削除）操作のために複雑なSQLクエリを書きたくない開発者向けに設計されています。

## ✨ 主な特徴

- **辞書のようなインターフェース**: 使い慣れた辞書構文 (`db['key'] = 'value'`) でデータベーステーブルと対話できます。
- **自動スキーマ管理**: テーブルとカラムは必要に応じて自動的に作成されます。
- **トランザクション制御**: データベーストランザクションを簡単に処理するためのコンテキストマネージャを提供します。
- **組み込み暗号化**: オプションのAES暗号化でデータを保護します。
- **クロスプロセス/スレッドセーフ**: `portalocker` を使用してデータの整合性を保証します。
- **軽量＆依存関係が少ない**: `portalocker` と `cryptography` を除けば、純粋なPythonで書かれています。

## 🚀 使ってみる

### インストール

pipでインストールします:

```bash
pip install dictsqlite
```

### 簡単な例

```python
from dictsqlite import DictSQLite
import os

db_file = 'sample.db'
if os.path.exists(db_file):
    os.remove(db_file)

# データベースを初期化
db = DictSQLite(db_file)

# --- 基本操作 ---
# 作成/更新
db['name'] = 'Alice'
db['age'] = 30
db.update({'city': 'New York', 'country': 'USA'})

# 読み取り
print(f"Name: {db['name']}")  # 出力: Name: Alice
print(f"City: {db.get('city')}") # 出力: City: New York

# 削除
del db['country']

# 存在確認
print('country' in db)  # 出力: False

# イテレーション
for key, value in db.items():
    print(f"{key}: {value}")

# --- テーブルの使用 ---
users = db.table('users')
users['user1'] = {'name': 'Bob', 'age': 25}
users['user2'] = {'name': 'Charlie', 'age': 35}

print(users['user1']) # 出力: {'name': 'Bob', 'age': 25}

# --- トランザクション ---
try:
    with db.transaction() as t:
        t['status'] = 'pending'
        # この変更はロールバックされます
        raise ValueError("問題が発生しました")
except ValueError as e:
    print(e)

print(db.get('status')) # 出力: None (トランザクションがロールバックされたため)

# 接続を閉じる
db.close()
```

## 📚 ドキュメント

詳細な使用方法、APIリファレンス、高度なトピックについては、公式ドキュメントを参照してください:

- [**日本語ドキュメント**](../documents/japanese.md)
- [**英語ドキュメント**](../documents/english.md)

## 🤝 コントリビューション

コントリビューション、Issue、機能リクエストを歓迎します！お気軽に [Issueページ](https://github.com/disnana/DictSQLite/issues) をご確認ください。

## 📜 ライセンス

このプロジェクトはカスタムMITライセンスの下でライセンスされています。コードを自由に使用・改変できますが、元の作成者に適切なクレジットを表示する必要があります。

詳細は [LICENSE](../LICENSE) ファイルを参照してください。

## ❤️ サポート

このプロジェクトが役に立ったと思ったら、ぜひGitHubで ⭐ をお願いします！

質問やサポートについては、Issueを立てるか、<support@disnana.com> までご連絡ください。


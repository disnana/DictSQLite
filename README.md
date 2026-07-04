# DictSQLite

[![PyPI version](https://img.shields.io/pypi/v/dictsqlite.svg)](https://pypi.org/project/dictsqlite/)
[![Python versions](https://img.shields.io/pypi/pyversions/dictsqlite.svg)](https://pypi.org/project/dictsqlite/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/disnana/DictSQLite/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/dictsqlite)](https://pepy.tech/project/dictsqlite)
[![Docs](https://img.shields.io/badge/docs-dictsqlite.disnana.com-blue)](https://dictsqlite.disnana.com/)

**Handle SQLite databases in Python with the simplicity of a dictionary.**

---

[日本語のREADMEはこちら (View in Japanese)](./readmes/README_JP.md)

DictSQLite provides a Pythonic, dictionary-like interface for SQLite databases, making database operations intuitive and straightforward. It's designed for developers who want to manage SQLite data without writing complex SQL queries for basic CRUD (Create, Read, Update, Delete) operations.

## ✨ Features

- **Dictionary-like Interface**: Interact with your database tables using familiar dictionary syntax (`db['key'] = 'value'`).
- **Automatic Schema Management**: Tables and columns are created on-the-fly.
- **Transaction Control**: Simple context manager for handling database transactions.
- **Built-in Encryption**: Secure your data with optional AES encryption.
- **Cross-process/thread Safety**: Uses `portalocker` to ensure data integrity.
- **Lightweight & Zero-dependency**: Besides `portalocker` and `cryptography`, it's pure Python.

## 🚀 Getting Started

### Installation

Install via pip:

```bash
pip install dictsqlite
```

### Quick Example

```python
from dictsqlite import DictSQLite
import os

db_file = 'sample.db'
if os.path.exists(db_file):
    os.remove(db_file)

# Initialize the database
db = DictSQLite(db_file)

# --- Basic Operations ---
# Create/Update
db['name'] = 'Alice'
db['age'] = 30
db.update({'city': 'New York', 'country': 'USA'})

# Read
print(f"Name: {db['name']}")  # Output: Name: Alice
print(f"City: {db.get('city')}") # Output: City: New York

# Delete
del db['country']

# Check existence
print('country' in db)  # Output: False

# Iterate
for key, value in db.items():
    print(f"{key}: {value}")

# --- Using Tables ---
users = db.table('users')
users['user1'] = {'name': 'Bob', 'age': 25}
users['user2'] = {'name': 'Charlie', 'age': 35}

print(users['user1']) # Output: {'name': 'Bob', 'age': 25}

# --- Transactions ---
try:
    with db.transaction() as t:
        t['status'] = 'pending'
        # This change will be rolled back
        raise ValueError("Something went wrong")
except ValueError as e:
    print(e)

print(db.get('status')) # Output: None (The transaction was rolled back)


# Close the connection
db.close()
```

## 📚 Documentation

For detailed usage, API reference, storage modes, async usage, safety notes, and benchmarks, please refer to the official documentation:

- [**Official Documentation**](https://dictsqlite.disnana.com/)
- [**English Documentation**](https://dictsqlite.disnana.com/en/)
- [**日本語ドキュメント**](https://dictsqlite.disnana.com/)

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/disnana/DictSQLite/issues).

## 📜 License

This project is licensed under a custom MIT License. While you are free to use and modify the code, you must give appropriate credit to the original creator.

See the [LICENSE](./LICENSE) file for more details.

## ❤️ Support

If you find this project useful, please give it a ⭐ on GitHub!

For questions or support, please open an issue or contact us at <support@disnana.com>.


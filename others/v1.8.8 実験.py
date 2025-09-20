import time

import dictsqlite
from pydantic import BaseModel

try:
    class Example(BaseModel):
        name: str
        age: int
        is_student: bool


    db = dictsqlite.DictSQLite("example_v2.db", version=2, journal_mode="WAL", storage_mode="json")

    db.create_table("example")
    db["example"]["key2"] = (1, 2, 3)
    db["example"]["key3"] = {"a": 1, "b": 2}
    db["example"]["key1"] = Example(name="Alice", age=30, is_student=False)
    db["example"]["key2"] = dictsqlite.expiring_dict(30)
    db["example"]["key2"]["temp"] = 0

    print(db["example"]["key2"])

    db.clear_db()
    db.close()
except Exception as e:
    print(f"Error: {e}")
    print("おそらくこの例外は正常です。")


db = dictsqlite.DictSQLite("example_v2.db", version=2, journal_mode="WAL", storage_mode="json")

db.create_table("example")
db["example"]["key2"] = (1, 2, 3)
db["example"]["key3"] = {"a": 1, "b": 2}
db["example"]["key2"] = 0

print(db["example"])

db.clear_db()
db.close()
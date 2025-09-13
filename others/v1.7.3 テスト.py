import time

import dictsqlite
from pydantic import BaseModel

class Example(BaseModel):
    name: str
    age: int
    is_student: bool

db = dictsqlite.DictSQLite("example_v2.db", version=2, journal_mode="WAL")

db.create_table("example")
db["example"]["key2"] = (1, 2, 3)
db["example"]["key3"] = {"a": 1, "b": 2}
db["example"]["key1"] = Example(name="Alice", age=30, is_student=False)
db["example"]["key2"] = dictsqlite.expiring_dict(3)
db["example"]["key2"]["temp"] = "This is temporary data"
for _ in range(5):
    time.sleep(1)
    if "temp" in db["example"]["key2"]:
        print("key2のtemp:", db["example"]["key2"]["temp"])
    else:
        print("key2のtempは期限切れで削除されました")
        break


print("exampleテーブルの内容:", db["example"])
print(db["example"]["key3"].items())
db.clear_db()
db.close()

db = dictsqlite.DictSQLite("example_v2.db", journal_mode="WAL")
db["example"] = (1, 2, 3)
db["example2"] = Example(name="Alice", age=30, is_student=False)
db["example3"] = {"a": 1, "b": 2}

print("exampleテーブルの内容:", db["example"])
print(db["example"])
print(db["example3"].items())
db.clear_db()
db.close()

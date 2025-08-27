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

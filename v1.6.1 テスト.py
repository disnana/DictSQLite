import dictsqlite
from pydantic import BaseModel

class Example(BaseModel):
    name: str
    age: int
    is_student: bool

db = dictsqlite.DictSQLite("example_v2.db", version=2, journal_mode="WAL")

db.create_table("example")
db["example"]["key2"] = (1, 2, 3)


print("exampleテーブルの内容:", db["example"])
db.clear_db()
db.close()

db = dictsqlite.DictSQLite("example_v2.db", journal_mode="WAL")
db["example"] = (1, 2, 3)

print("exampleテーブルの内容:", db["example"])
db.clear_db()
db.close()

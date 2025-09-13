import dictsqlite

db = dictsqlite.DictSQLite("example_v2.db", version=2, journal_mode="WAL")

db.create_table("example")
db["example"]["key1"] = "value1"
db["example"]["key2"] = [1, 2, 3]
db["example"]["key2"].append(4)

db["example"]["key3"] = {"subkey1": "subvalue1", "subkey2": "subvalue2"}
db["example"]["key3"]["subkey3"] = "subvalue3"

db["example"]["key4"] = set([1, 2, 3])

print("exampleテーブルの内容:", db["example"])
db.clear_db()
db.close()

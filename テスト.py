import random
import dict_sqlite

db = dict_sqlite.DictSQLite("./test.db", version=2, password="test")
db.clear_db()
print(db)
db.create_table("main", schema=None)
db.create_table("sub", schema=None)
db.create_table("test", schema=None)
print(db)
db["main"]["test"] = 0
print(db)
db["test"]["data"] = 0
print(db)
db["sub"]["test"] = "test"
db["sub"]["test2"] = "test2"
print(db)
print(db["sub"])

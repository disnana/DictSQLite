import random
import dict_sqlite

db = dict_sqlite.DictSQLite("./test.db", version=2)
db.clear_db()
print(db)
db.create_table("main", schema=None)
db["main"] = 0
print(db)
db["sub"] = 1
print(db)
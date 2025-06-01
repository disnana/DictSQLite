import random
import dictsqlite

db = dictsqlite.DictSQLite("./sample.db", version=1)
db.clear_db()
print(db)
db.create_table("main", schema="(key TEXT PRIMARY KEY, value TEXT)")
db.execute_custom('''
INSERT INTO main (key, value)
VALUES (?, ?)
''', ("John Doe", 30))
print(db)
for _ in range(10):
    db.create_table("A" + str(random.randint(111111, 999999)))
print(db.tables())
print(len(db.tables()))
db["test"] = 0
print(db)
db["test"] += 1
print(db)
db.close()
db = dictsqlite.DictSQLite("./sample.db")
print(db)
db["John Doe"] += 1
print(db)
db["list_test"] = [1, 2, 3]  # リストを使用
db["list_test"].append(4)  # リストに値を追加
db["list_test"].append(5)  # リストに値を追加
for i in db["list_test"]:
    print(i)
print(db["list_test"])
db["list_test"].remove(2)  # リストから値を削除
print(db["list_test"])
del db["list_test"][1]
print(db["list_test"])
db["list_test"].pop(1)
print(db["list_test"])
db.close()

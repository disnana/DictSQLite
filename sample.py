import random
import dict_sqlite

db = dict_sqlite.DictSQLite("./sample.db")
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
db.close()

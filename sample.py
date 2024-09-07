import dict_sqlite

db = dict_sqlite.DictSQLite("./sample.db")
db.clear_db()
print(db)
db.create_table("main", schema="(name TEXT)")
db.execute_custom('''
INSERT INTO main (name)
VALUES (?)
''', ("John Doe"))
print(db)
db.close()

import dict_sqlite


# 使用例
db = dict_sqlite.DictSQLite('example.db')
print(db.switch_table("main"))
print(db)
db[('foo', 'lol')] = 'bar'
print(db)  # '{'foo': 'bar2'}'
print(db.tables())
print(db)
print(db[("foo", "lol")])
db.close()

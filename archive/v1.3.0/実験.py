import dict_sqlite


# 使用例
db = dict_sqlite.DictSQLite('example.db')
print(db)
db['foo'] = 'bar'
print(db)  # '{'foo': 'bar2'}'
db.close()

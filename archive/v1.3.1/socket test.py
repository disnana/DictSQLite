import dict_sqlite
with dict_sqlite.DictSQLite("sample.db") as context_db:
    context_db['context_key'] = 'context_value'
    print("コンテキスト内のデータ:", context_db)

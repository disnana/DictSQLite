import dict_sqlite

data = {
    "token": {
        "検知": True,
        "検知レベル": 2,
        "処罰": ["timeout"],
        "期間": "3600s",
        "違反回数に基づく処罰": {},
        "検知除外": {"ユーザー・ボット・webhook": [], "チャンネル": []}
    },
    "権限": {
        "許可ユーザー": [],
        "許可ロール": [],
        "オーナーのみ変更を許可": True
    },
    "言語": "日本語",
    "発言safety": {
        "検知対象カテゴリ": ["TOXICITY", "SEVERE_TOXICITY", "IDENTITY_ATTACK", "INSULT", "PROFANITY", "THREAT"],
        "スコア": 0.6,
        "カテゴリ毎の設定": {},
        "処罰": {"timeout": "5s"},
        "検知": True,
        "除外": {"ユーザー": [], "チャンネル": []}
    }
}


# 使用例
db = dict_sqlite.DictSQLite('example.db')
print(db)
db[('foo', 'lol')] = 'bar'
print(db)  # '{'foo': 'bar2'}'
print(db.tables())
print(db)
print(db["test"])
print(db[("foo", "lol")])
print(db.keys("lol"))
db["data"] = data
print(db)
print(db["data"])
db.close()

import threading
import dict_sqlite


def write_data(key, value):
    with dict_sqlite.DictSQLite(':memory:') as db:
        db[key] = value
        print(f"Written {key}: {value}")


def read_data(db, key):
    try:
        value = db[key]
        print(f"Read {key}: {value}")
    except KeyError:
        print(f"Key {key} not found")


def test_concurrent_writes():
    threads = []

    # 10個のスレッドを作成して、各スレッドが異なるキーに書き込みを行う
    for i in range(100):
        t = threading.Thread(target=write_data, args=(f'key{i}', f'value{i}'))
        threads.append(t)

    # 全てのスレッドをスタート
    for t in threads:
        t.start()

    # 全てのスレッドが終了するのを待つ
    for t in threads:
        t.join()


test_concurrent_writes()
db = dict_sqlite.DictSQLite(':memory:')  # メモリ内データベースを使用
# 書き込まれたデータを確認
for i in range(100):
    read_data(db, f'key{i}')

db.close()

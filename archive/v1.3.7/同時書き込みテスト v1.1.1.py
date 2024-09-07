import threading
import dict_sqlite
import time


def write_data(db, key, value):
    db[key] = value
    print(f"Written {key}: {value}")


def read_data(db, key):
    try:
        value = db[key]
        print(f"Read {key}: {value}")
    except KeyError:
        print(f"Key {key} not found")


def test_concurrent_writes():
    db = dict_sqlite.DictSQLite(':memory:', lock_file="./test.lock")  # メモリ内データベースを使用
    threads = []

    # 10個のスレッドを作成して、各スレッドが異なるキーに書き込みを行う
    for i in range(100):
        t = threading.Thread(target=write_data, args=(db, f'key{i}', f'value{i}'))
        threads.append(t)

    # 全てのスレッドをスタート
    for t in threads:
        t.start()

    # 全てのスレッドが終了するのを待つ
    for t in threads:
        t.join()

    # 書き込まれたデータを確認
    for i in range(100):
        read_data(db, f'key{i}')

    db.close()


lists = 0.0
lists2 = 0.0
count = 100

for _ in range(count):
    # 計測開始
    start = time.perf_counter()

    test_concurrent_writes()

    # 計測終了
    end = time.perf_counter()

    # 実行時間を計算
    execution_time = end - start
    # f-stringを使用する方法
    decimal_str = f"実行速度：{execution_time:.20f}"  # 小数点以下の桁数を20桁に設定
    print(decimal_str)
    lists += execution_time
    lists2 += execution_time / count

# f-stringを使用する方法
lists = lists / count
lists2 = lists2 / count
decimal_str = f"100回の書き込み{count}回した平均：{lists:.20f}"  # 小数点以下の桁数を20桁に設定
print(decimal_str)
decimal_str = f"{100*count}回の書き込みをした平均：{lists2:.20f}"  # 小数点以下の桁数を20桁に設定
print(decimal_str)

# client.py
from multiprocessing.managers import BaseManager
import multiprocessing
import secrets
import string
import time
from example_operation import example_operation


class ManagerWithList(BaseManager):
    pass


def main():
    # Managerのインスタンスを作成
    ManagerWithList.register('get_queue')
    manager = ManagerWithList(address=('127.0.0.1', 50000), authkey=b'secret')
    manager.register('get_queue')
    manager.connect()

    # シェアされるキューの取得
    shared_queue = manager.get_queue()

    # 操作をキューに追加
    result_queue = multiprocessing.Manager().Queue()
    shared_queue.put((example_operation, (5,), {}, result_queue))

    # 結果の取得
    result = result_queue.get()
    print(f"Operation result: {result}")

    # 終了するまで待機
    time.sleep(2)  # サーバーが終了するのを待つ（サーバーが停止しない場合）


if __name__ == '__main__':
    main()

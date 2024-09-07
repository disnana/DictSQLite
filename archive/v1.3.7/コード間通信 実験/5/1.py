# server.py
import threading
from multiprocessing.managers import BaseManager
import multiprocessing
import secrets
import string
from example_operation import example_operation


class ManagerWithList(BaseManager):
    pass

class SharedListManager:
    def __init__(self):
        print("OK")
    def get_queue(self):
        return multiprocessing.Manager().Queue()


def process_queue(shared_queue):
    while True:
        try:
            # キューから操作を取り出す
            operation, args, kwargs, result_queue = shared_queue.get()
            if operation is None:
                break  # Noneがキューに追加されたら終了

            # 操作を実行
            result = operation(*args, **kwargs)
            print(result)

            # 結果を結果キューに入れる
            if result_queue is not None:
                result_queue.put(result)

            shared_queue.task_done()  # タスク完了を通知
        except Exception as e:
            print(f"An error occurred while processing the queue: {e}")


def main():
    ww = SharedListManager()
    # Managerのインスタンスを作成
    ManagerWithList.register('get_queue', ww.get_queue)
    manager = ManagerWithList(address=('127.0.0.1', 50000), authkey=b'secret')
    manager.register('get_queue', callable=ww.get_queue)

    # Managerを開始する
    server = manager.get_server()

    print("Server is running...")
    try:
        server.serve_forever()
        wk = threading.Thread(target=server.serve_forever)
        wk.daemon = KeyError
        wk.start()
        # キュー処理用のスレッドを開始
        shared_queue = manager.get_queue()
        worker_thread = threading.Thread(target=process_queue, args=(shared_queue,))
        worker_thread.daemon = True
        worker_thread.start()
    except KeyboardInterrupt:
        print("Server is stopping...")


if __name__ == '__main__':
    main()

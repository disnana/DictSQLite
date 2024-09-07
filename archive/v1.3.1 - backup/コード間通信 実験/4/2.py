import portalocker
import time


def worker(lock_file: str):
    """ファイルロックを使った処理"""
    while True:
        with portalocker.Lock(lock_file, 'w') as file:
            print("lock check")


# 使用例
if __name__ == "__main__":
    worker('my_lock_file.lock')

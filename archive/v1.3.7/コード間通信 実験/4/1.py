import portalocker
import time


def worker(lock_file: str):
    """ファイルロックを使った処理"""
    with open(lock_file, 'w') as file:
        portalocker.lock(file, portalocker.LOCK_EX)
        print("ロックを取得しました")
        print("ロックを解放しました")
    time.sleep(3)


# 使用例
if __name__ == "__main__":
    worker('my_lock_file.lock')

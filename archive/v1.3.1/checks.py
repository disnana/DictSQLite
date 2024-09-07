import time

import portalocker


def _check_lock(self):
    """ロックファイルのロック状態を確認します。"""
    try:
        with open(self, 'w') as file:
            try:
                portalocker.lock(file, portalocker.LOCK_EX | portalocker.LOCK_NB)
                portalocker.unlock(file)
                print("ロックを取得できました (ロックされていません)")
                return True
            except portalocker.LockException:
                print("ロックは既に取得されています")
                return False
    except Exception as e:
        print(f"エラー: {e}")

while True:
    time.sleep(1)
    _check_lock("./sample.db.lock")
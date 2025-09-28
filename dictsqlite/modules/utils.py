"""ユーティリティモジュール: 有効期限付き辞書などの補助クラスを提供。"""

import time
import asyncio
import threading
import logging
from typing import Optional, Any
import collections.abc

# ロガーの設定
logger = logging.getLogger(__name__)


class ExpiringDict(collections.abc.MutableMapping):
    """有効期限付き辞書クラス。指定時間後に自動的にキーが削除される。"""

    def __init__(self, expiration_time: float):
        self.data = {}
        self.expiration_time = expiration_time
        self.expiration_tasks = {}  # 非同期 loop.call_later ハンドル管理 (以前は asyncio.Task)
        self.expiration_timers = {}  # 同期タイマー管理
        self._loop = None

    def __getstate__(self):
        """
        pickle化する際に呼ばれるメソッド。
        保存すべき状態だけを含む辞書を返す。
        """
        return {
            'data': self.data,
            'expiration_time': self.expiration_time,
        }

    def __setstate__(self, state):
        """
        pickleから復元する際に呼ばれるメソッド。
        __getstate__で返した辞書を受け取り、オブジェクトの状態を復元する。
        """
        self.data = state['data']
        self.expiration_time = state['expiration_time']

        # タイマーやタスクに関連する変数を初期化する
        self.expiration_tasks = {}
        self.expiration_timers = {}
        self._loop = None

        # 復元されたデータすべてに対して、再度タイマーを設定し直す
        # 注意: 復元された時点から新しい有効期限がスタートする
        for key in list(self.data.keys()):
            self._set_expiration(key)

    def _get_or_create_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """実行中のループを取得、なければ新規作成"""
        try:
            loop = asyncio.get_running_loop()
            return loop
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                return loop
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                return loop

    def _set_expiration_sync(self, key: str):
        """同期版の有効期限設定（daemon化）"""
        if key in self.expiration_timers:
            self.expiration_timers[key].cancel()

        def remove_key():
            if key in self.data:
                del self.data[key]
                logger.info("Key '%s' expired and removed at %s", key, time.time())
            if key in self.expiration_timers:
                del self.expiration_timers[key]

        timer = threading.Timer(self.expiration_time, remove_key)
        timer.daemon = True
        timer.start()
        self.expiration_timers[key] = timer

    # 旧: async def _set_expiration_async + asyncio.create_task + sleep
    # 新: loop.call_later を使い Task を生成しないのでテスト終了時の "Task was destroyed" 警告回避
    def _set_expiration_async(self, key: str):
        if key in self.expiration_tasks:
            handle = self.expiration_tasks.pop(key)
            try:
                handle.cancel()
            except Exception:  # noqa: BLE001
                pass
        loop = asyncio.get_running_loop()

        def remove_key():
            if key in self.data:
                self.data.pop(key, None)
                logger.info("Key '%s' expired and removed at %s", key, time.time())
            self.expiration_tasks.pop(key, None)

        handle = loop.call_later(self.expiration_time, remove_key)
        self.expiration_tasks[key] = handle

    def _set_expiration(self, key: str):
        """自動判定で有効期限を設定"""
        try:
            asyncio.get_running_loop()
            self._set_expiration_async(key)
        except RuntimeError:
            self._set_expiration_sync(key)

    def __setitem__(self, key: str, value: Any):
        """辞書風の値設定（同期・非同期自動判定）"""
        self.data[key] = value
        self._set_expiration(key)

    def __getitem__(self, key: str):
        return self.data[key]

    def __delitem__(self, key: str):
        if key in self.data:
            del self.data[key]
            if key in self.expiration_timers:
                self.expiration_timers[key].cancel()
                del self.expiration_timers[key]
            if key in self.expiration_tasks:
                try:
                    self.expiration_tasks[key].cancel()
                except Exception:  # noqa: BLE001
                    pass
                del self.expiration_tasks[key]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __contains__(self, key: str):
        return key in self.data

    def __repr__(self):
        return repr(self.data)

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def values(self):
        return self.data.values()

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def clear(self):
        self.data.clear()
        for timer in self.expiration_timers.values():
            timer.cancel()
        self.expiration_timers.clear()
        for handle in self.expiration_tasks.values():
            try:
                handle.cancel()
            except Exception:  # noqa: BLE001
                pass
        self.expiration_tasks.clear()

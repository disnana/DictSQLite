"""utils.ExpiringDict の単体テスト。

- 挿入後、期限を過ぎると自動的に削除される
- ピクル化/復元後もタイマーが再構築され、期限が効く
"""
from __future__ import annotations

import time
import pickle
import pytest

from dictsqlite.modules import utils


@pytest.mark.parametrize("ttl", [0.05, 0.1])
def test_expiring_dict_basic_expiration(ttl):
    """TTL 経過後にキーが自動的に失効することを検証。
    """
    ed = utils.ExpiringDict(ttl)  # type: ignore[arg-type]
    ed["a"] = 1
    assert ("a" in ed) is True
    time.sleep(ttl * 3)
    assert ("a" in ed) is False


def test_expiring_dict_pickle_roundtrip_restarts_timers():
    """pickle 往復後にタイマーが再構築され、再び期限が効くことを検証。
    """
    ed = utils.ExpiringDict(0.1)  # type: ignore[arg-type]
    ed["x"] = 10

    data = pickle.dumps(ed, protocol=pickle.HIGHEST_PROTOCOL)
    restored: utils.ExpiringDict = pickle.loads(data)

    # 値は復元される
    assert restored["x"] == 10

    # 復元後のタイマーが効く（復元時点からカウント）
    restored["y"] = 20
    time.sleep(0.25)
    assert ("y" in restored) is False

"""DictSQLite パッケージ: SQLiteを辞書のように扱うためのライブラリ。"""

from .main import *  # pylint: disable=wildcard-import,unused-wildcard-import
from .modules import utils


def expiring_dict(expiration_time: int):  # pylint: disable=function-redefined
    """有効期限付き辞書を作成する関数。

    Args:
        expiration_time (int): 有効期限（秒）

    Returns:
        ExpiringDict: 有効期限付き辞書オブジェクト
    """
    data = utils.ExpiringDict(expiration_time)
    return data

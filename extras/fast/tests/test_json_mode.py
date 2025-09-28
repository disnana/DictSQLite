"""JSON storage_mode に関する機能テスト。

主目的:
- 基本的な型の保存/取得
- 同期コレクション(DBSyncedList/DBSyncedSet) の挙動
- ネスト辞書の部分更新 (リストは非同期である点)
- シリアライズ不能オブジェクトでの例外
- 暗号化併用時の JSON モード
- version=2 でも JSON モードが動作すること
"""
# pylint: disable=no-member,too-few-public-methods

from typing import cast
import pytest
from dictsqlite_fast import FastDictSQLite
from dictsqlite import DBSyncedList, DBSyncedSet


def test_json_basic_store_and_load(tmp_path):
    """基本型/コレクションを JSON モードで保存取得できること。"""
    db = FastDictSQLite(str(tmp_path / 'json_basic.db'), storage_mode='json')  # pylint: disable=unexpected-keyword-arg
    db['int'] = 123
    db['str'] = 'hello'
    db['list'] = [1, 2, 3]
    db['dict'] = {'a': 1, 'b': 2}
    db['set'] = {'x', 'y'}

    assert db['int'] == 123
    assert db['str'] == 'hello'
    assert db['list'] == [1, 2, 3]
    assert db['dict']['a'] == 1 and db['dict']['b'] == 2
    assert db['set'] == {'x', 'y'}  # set は順序非保持
    db.close()


def test_json_synced_list_and_set(tmp_path):
    """DBSyncedList / DBSyncedSet が JSON モードでも自動同期されること。"""
    db = FastDictSQLite(str(tmp_path / 'json_synced.db'), storage_mode='json')  # pylint: disable=unexpected-keyword-arg
    db['numbers'] = [1, 2]
    db['tags'] = {'a', 'b'}

    numbers = cast(DBSyncedList, db['numbers'])  # 明示 cast で Pylint 属性警告回避
    numbers.append(3)  # pylint: disable=no-member
    numbers.extend([4, 5])  # pylint: disable=no-member
    assert db['numbers'] == [1, 2, 3, 4, 5]

    tags = cast(DBSyncedSet, db['tags'])
    tags.add('c')  # pylint: disable=no-member
    tags.discard('b')  # pylint: disable=no-member
    assert db['tags'] == {'a', 'c'}
    db.close()


def test_json_nested_dict_updates(tmp_path):
    """ネストした dict の部分更新が反映され list は同期されない挙動を確認。"""
    db = FastDictSQLite(str(tmp_path / 'json_nested.db'), storage_mode='json')  # pylint: disable=unexpected-keyword-arg
    db['conf'] = {"section": {"k": 1}, 'list': [10, 20]}

    conf = db['conf']              # RecursiveDict 想定
    conf['section']['k'] = 2       # 深いパス更新
    conf['section']['new'] = 99
    conf['list'][0] = 11           # 通常 list なので DB には即反映されない

    conf2 = db['conf']
    assert conf2['section']['k'] == 2
    assert conf2['section']['new'] == 99
    assert conf2['list'][0] == 10  # list は非同期
    db.close()


def test_json_not_serializable_raises(tmp_path):
    """シリアライズ不能オブジェクト保存で TypeError になること。"""
    db = FastDictSQLite(str(tmp_path / 'json_err.db'), storage_mode='json')  # pylint: disable=unexpected-keyword-arg

    class X:  # JSON化できない任意クラス
        """Dummy クラス (JSON シリアライズ不能)。"""
        # pylint: disable=too-few-public-methods,unnecessary-pass
        pass

    with pytest.raises(TypeError):
        db['x'] = X()
    db.close()


def test_json_mode_with_encryption(tmp_path):
    """暗号化と JSON モード併用時に通常通り読み書きできること。"""
    pub = tmp_path / 'pub.pem'
    priv = tmp_path / 'priv.pem'
    db = FastDictSQLite(  # pylint: disable=unexpected-keyword-arg
        str(tmp_path / 'json_enc.db'),
        storage_mode='json',
        password='pw',
        key_create=True,
        publickey_path=str(pub),
        privatekey_path=str(priv),
    )
    db['secure'] = {'v': 42, 's': {'a', 'b'}}
    assert db['secure']['v'] == 42
    assert db['secure']['s'] == {'a', 'b'}
    db.close()


def test_json_mode_type_error_under_encryption(tmp_path):
    """暗号化併用時でもシリアライズ不能値は TypeError となること。"""
    pub = tmp_path / 'pub2.pem'
    priv = tmp_path / 'priv2.pem'
    db = FastDictSQLite(  # pylint: disable=unexpected-keyword-arg
        str(tmp_path / 'json_enc_err.db'),
        storage_mode='json',
        password='pw',
        key_create=True,
        publickey_path=str(pub),
        privatekey_path=str(priv),
    )

    with pytest.raises(TypeError):
        db['bad'] = lambda x: x  # シリアライズ不可 (function)
    db.close()


def test_json_basic_store_and_load_v2(tmp_path):
    """version=2 でも JSON モードが動作 (明示テーブル作成後) すること (tuple指定)。"""
    db = FastDictSQLite(str(tmp_path / 'json_basic_v2.db'), version=2, storage_mode='json')  # pylint: disable=unexpected-keyword-arg
    db.create_table()  # 'main' テーブル作成
    # version=2 では (key, table_name) タプル指定で設定可能
    db[('k', 'main')] = {'n': 1}
    assert db['main']['k']['n'] == 1  # TableProxy 経由で取得
    db.close()

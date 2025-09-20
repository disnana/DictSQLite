import pytest
from dictsqlite import DictSQLite

# JSONモード動作検証

def test_json_basic_store_and_load(tmp_path):
    db = DictSQLite(str(tmp_path / 'json_basic.db'), storage_mode='json')
    db['int'] = 123
    db['str'] = 'hello'
    db['list'] = [1, 2, 3]
    db['dict'] = {'a': 1, 'b': 2}
    db['set'] = {'x', 'y'}

    assert db['int'] == 123
    assert db['str'] == 'hello'
    assert db['list'] == [1, 2, 3]
    assert db['dict']['a'] == 1 and db['dict']['b'] == 2
    # set は順序不定
    assert db['set'] == {'x', 'y'}
    db.close()


def test_json_synced_list_and_set(tmp_path):
    db = DictSQLite(str(tmp_path / 'json_synced.db'), storage_mode='json')
    db['numbers'] = [1, 2]
    db['tags'] = {'a', 'b'}

    numbers = db['numbers']  # DBSyncedList
    numbers.append(3)
    numbers.extend([4, 5])
    assert db['numbers'] == [1, 2, 3, 4, 5]

    tags = db['tags']  # DBSyncedSet
    tags.add('c')
    tags.discard('b')
    assert db['tags'] == {'a', 'c'}
    db.close()


def test_json_nested_dict_updates(tmp_path):
    db = DictSQLite(str(tmp_path / 'json_nested.db'), storage_mode='json')
    db['conf'] = {"section": {"k": 1}, 'list': [10, 20]}

    conf = db['conf']              # RecursiveDict
    conf['section']['k'] = 2       # 深いパスの値更新
    conf['section']['new'] = 99
    conf['list'][0] = 11           # ネストした list は通常listなのでDB自動反映されない

    # 再取得して検証（list は再保存されていないことに注意）
    conf2 = db['conf']
    assert conf2['section']['k'] == 2
    assert conf2['section']['new'] == 99
    # ネストlistは同期対象外なので元の10のまま
    assert conf2['list'][0] == 10
    db.close()


def test_json_not_serializable_raises(tmp_path):
    db = DictSQLite(str(tmp_path / 'json_err.db'), storage_mode='json')

    class X:  # JSON化できない任意クラス
        pass

    with pytest.raises(TypeError):
        db['x'] = X()
    db.close()


def test_json_mode_with_encryption(tmp_path):
    pub = tmp_path / 'pub.pem'
    priv = tmp_path / 'priv.pem'
    db = DictSQLite(
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
    pub = tmp_path / 'pub2.pem'
    priv = tmp_path / 'priv2.pem'
    db = DictSQLite(
        str(tmp_path / 'json_enc_err.db'),
        storage_mode='json',
        password='pw',
        key_create=True,
        publickey_path=str(pub),
        privatekey_path=str(priv),
    )

    with pytest.raises(TypeError):
        db['bad'] = lambda x: x  # シリアライズ不可
    db.close()


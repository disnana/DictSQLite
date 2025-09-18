"""pickle任意コード実行対策の検証用テスト。

主に以下を検証する:
- 悪性payload（os.systemなど）がDB経由で復元される際に実行されないこと
- 混在payload（安全なdict内に悪性要素が含まれる）でも安全に拒否されること
- safe_pickleポリシーでプロジェクト配下の関数復元を許可した場合のみ、関数が復元できること
- safe_pickle.safe_loads が組み込みの安全型を許容すること
"""
from __future__ import annotations

import base64
import os
import sys
import tempfile
import time
import pickle
import pytest

from dictsqlite.main import DictSQLite
from dictsqlite.modules import safe_pickle


class Evil:
    def __reduce__(self):  # 実行時にシステムコマンドを呼ぶ悪性オブジェクト
        # 実行されると一時ファイルに書き込むコマンド
        tmp_file = os.path.join(tempfile.gettempdir(), "dictsqlite_rce_test.txt")
        # Pythonを使って確実にファイルを書き込む（クロスプラットフォーム）
        cmd = f'"{sys.executable}" -c "open(\"{tmp_file}\",\"w\").write(\"PWNED\")"'
        return (os.system, (cmd,))


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "test_rce.db"


@pytest.fixture()
def db(db_path):
    d = DictSQLite(str(db_path))
    yield d
    d.close()


def _payload_would_create_marker():
    marker = os.path.join(tempfile.gettempdir(), "dictsqlite_rce_test.txt")
    return marker, os.path.exists(marker)


def test_evil_payload_is_not_executed_and_value_is_str(db: DictSQLite):
    # まずマーカーが存在しないことを確認
    marker, existed_before = _payload_would_create_marker()
    if existed_before:
        os.remove(marker)

    # 悪性オブジェクトを書き込む（保存時は実行されない）
    db["evil"] = Evil()

    # 読み出し時にsafe_unpicklerが拒否し、値はbase64文字列として返る
    val = db["evil"]
    assert isinstance(val, str)

    # 少し待ってもマーカーは作られていない（実行されていない）
    time.sleep(0.1)
    assert os.path.exists(marker) is False


def test_mixed_payload_is_blocked_and_string_returned(db: DictSQLite):
    # 安全なdictの中に悪性要素を含める
    mixed = {"safe": 1, "evil": Evil()}
    db["mixed"] = mixed

    # 読み出しは安全のため丸ごとbase64文字列へフォールバック
    val = db["mixed"]
    assert isinstance(val, str)


def test_safe_pickle_allows_safe_builtins_directly():
    safe_data = {"a": [1, 2, 3], "b": (1, 2)}
    dumped = pickle.dumps(safe_data)
    restored = safe_pickle.safe_loads(dumped)
    assert restored == safe_data


def test_policy_allows_project_function(db_path):
    # プロジェクト配下の関数を保存し、ポリシーで関数復元を許可
    from dictsqlite.main import randomstrings

    d = DictSQLite(
        str(db_path),
        safe_pickle_policy=safe_pickle.SafePolicy.for_package(
            "dictsqlite", allow_functions_from_prefixes=True
        ),
    )
    try:
        d["func"] = randomstrings
        f = d["func"]
        assert callable(f)
        s = f(5)
        assert isinstance(s, str) and len(s) == 5
    finally:
        d.close()


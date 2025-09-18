"""pickle 任意コード実行対策の検証用テスト群。"""
from __future__ import annotations

# pytest のフィクスチャ名再定義は意図的に使用するため無効化
# 併せて一部環境でのimport解決やシグネチャ誤検知を抑止
# pylint: disable=redefined-outer-name,import-error,no-name-in-module,unexpected-keyword-arg

import os
import sys
import tempfile
import time
import pickle
import pytest

from dictsqlite.main import DictSQLite, randomstrings, safe_pickle as _safe_pickle


class Evil:  # pylint: disable=too-few-public-methods
    """復元時に外部コマンドを実行しようとする悪性オブジェクト。"""

    def __reduce__(self):
        """os.system を用いたコマンド実行を企図する reduce 実装。"""
        # 実行されると一時ファイルに書き込むコマンド
        tmp_file = os.path.join(tempfile.gettempdir(), "dictsqlite_rce_test.txt")
        # Pythonを使って確実にファイルを書き込む（クロスプラットフォーム）
        cmd = f'"{sys.executable}" -c "open(\"{tmp_file}\",\"w\").write(\"PWNED\")"'
        return (os.system, (cmd,))


@pytest.fixture()
def db_path(tmp_path):
    """一時DBファイルパスを提供するフィクスチャ。"""
    return tmp_path / "test_rce.db"


@pytest.fixture()
def db(db_path):
    """DictSQLite のインスタンスを提供し、テスト後にクローズ。"""
    d = DictSQLite(str(db_path))
    yield d
    d.close()


def _payload_would_create_marker():
    """悪性 payload が実行されると作成されるはずのマーカー情報を返す。"""
    marker = os.path.join(tempfile.gettempdir(), "dictsqlite_rce_test.txt")
    return marker, os.path.exists(marker)


def test_evil_payload_is_not_executed_and_value_is_str(db: DictSQLite):
    """悪性オブジェクトは実行されず、読み出し時は安全のため文字列化される。"""
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
    """安全な辞書内に悪性要素が混在していても、読み出しは文字列フォールバックとなる。"""
    # 安全なdictの中に悪性要素を含める
    mixed = {"safe": 1, "evil": Evil()}
    db["mixed"] = mixed

    # 読み出しは安全のため丸ごとbase64文字列へフォールバック
    val = db["mixed"]
    assert isinstance(val, str)


def test_safe_pickle_allows_safe_builtins_directly():
    """safe_loads が安全な組み込み型をそのまま復元できることを確認。"""
    safe_data = {"a": [1, 2, 3], "b": (1, 2)}
    dumped = pickle.dumps(safe_data)
    restored = _safe_pickle.safe_loads(dumped)
    assert restored == safe_data


def test_policy_allows_project_function(db_path):
    """プロジェクト配下の関数を保存し、ポリシー許可時のみ復元/実行できること。"""
    kwargs = {
        "safe_pickle_policy": _safe_pickle.SafePolicy.for_package(
            "dictsqlite", allow_functions_from_prefixes=True
        )
    }
    d = DictSQLite(str(db_path), **kwargs)
    try:
        d["func"] = randomstrings
        func = d["func"]
        # callable 属性経由で安全に呼び出す
        s = getattr(func, "__call__")(5)
        # セキュリティ上重要な検証は最適化時にも削除されないよう明示的にチェック
        if not isinstance(s, str):
            raise TypeError(f"Expected str, got {type(s)}")
        if len(s) != 5:
            raise ValueError(f"Expected length 5, got {len(s)}")
    finally:
        d.close()

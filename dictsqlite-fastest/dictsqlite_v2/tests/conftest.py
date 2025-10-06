"""pytest設定とフィクスチャ"""

import pytest
import tempfile
import shutil
import sys
from pathlib import Path


# パスの設定
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'beta'))


@pytest.fixture
def temp_db_path(tmp_path):
    """一時的なDBパスを提供するフィクスチャ"""
    db_path = tmp_path / "test.db"
    yield str(db_path)
    # クリーンアップ
    for ext in ['', '-wal', '-shm']:
        file_path = Path(str(db_path) + ext)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass


@pytest.fixture
def temp_dir():
    """一時ディレクトリを提供するフィクスチャ"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # クリーンアップ
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass


@pytest.fixture
def baseline_dir(tmp_path):
    """ベースライン保存用ディレクトリ"""
    baseline_dir = tmp_path / "baselines"
    baseline_dir.mkdir(exist_ok=True)
    return baseline_dir

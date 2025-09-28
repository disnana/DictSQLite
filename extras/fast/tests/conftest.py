import sys, os, importlib.util, pytest

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
PACKAGE_ROOT = os.path.abspath(os.path.join(THIS_DIR, '..'))
PROJECT_ROOT = None
_cur = THIS_DIR
# 上位へ辿って pyproject.toml (DictSQLite 本体) が見つかる場所を探索
for _ in range(8):  # 深さ制限
    candidate = os.path.join(_cur, 'pyproject.toml')
    if os.path.isfile(candidate) and 'DictSQLite' in open(candidate, 'r', encoding='utf-8').read():  # noqa: PTH123
        PROJECT_ROOT = _cur
        break
    _cur = os.path.dirname(_cur)

# sys.path へ追加 (順序: プロジェクトルート -> パッケージルート)
for p in [p for p in [PROJECT_ROOT, PACKAGE_ROOT] if p and p not in sys.path]:
    sys.path.insert(0, p)

# apsw が無い場合は全テスト skip
if importlib.util.find_spec('apsw') is None:  # pragma: no cover
    pytest.skip('apsw not installed - skipping fast package tests', allow_module_level=True)

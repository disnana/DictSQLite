import sys, os, importlib.util, pytest, importlib, pathlib

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

# sys.path へ追加 (順序: パッケージルート -> プロジェクトルート) ※ ルート直下の旧 dictsqlite_fast を避けるため
for p in [p for p in [PACKAGE_ROOT, PROJECT_ROOT] if p and p not in sys.path]:
    sys.path.insert(0, p)

# --- 強制的に extras/fast/dictsqlite_fast を "dictsqlite_fast" としてロードし、ルート重複を回避 ---
extras_pkg_dir = pathlib.Path(PACKAGE_ROOT) / 'dictsqlite_fast'
init_file = extras_pkg_dir / '__init__.py'
if init_file.is_file():
    # 既存キャッシュを除去
    if 'dictsqlite_fast' in sys.modules:
        del sys.modules['dictsqlite_fast']
    spec = importlib.util.spec_from_file_location('dictsqlite_fast', str(init_file))  # type: ignore[arg-type]
    if spec and spec.loader:  # pragma: no branch - 正常系
        module = importlib.util.module_from_spec(spec)
        sys.modules['dictsqlite_fast'] = module
        spec.loader.exec_module(module)  # type: ignore[assignment]

# APSW が無い場合でも sqlite3 フォールバックでテスト継続
# 強制的に apsw をテストから参照したい場合は環境変数 FAST_REQUIRE_APSW=1 を設定
if os.environ.get('FAST_REQUIRE_APSW') == '1' and importlib.util.find_spec('apsw') is None:  # pragma: no cover
    pytest.skip('FAST_REQUIRE_APSW=1 だが apsw 未インストールのためスキップ', allow_module_level=True)

import sys, pickle
sys.path.insert(0, r'c:\Users\msi-z\Downloads\新しいフォルダー\プロジェクトCode\DictSQLite\others\beta-versions\dictsqlite_v4.2')
import modules.safe_pickle as sp

# Test the same dangerous object as the test: __import__ builtin function
data = pickle.dumps(__import__)
print('Pickled __import__ function, calling safe_loads...')
try:
    sp.safe_loads(data, allowed_module_prefixes=('dictsqlite',))
    print('ERROR: SAFE_LOADS_DID_NOT_RAISE')
    sys.exit(1)
except Exception as e:
    print('OK: RAISED', type(e).__name__, ':', e)
    sys.exit(0)

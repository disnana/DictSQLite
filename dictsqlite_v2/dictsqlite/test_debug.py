"""デバッグ用テスト"""
import pickle
import logging

logging.basicConfig(level=logging.DEBUG)

# まず直接safe_pickleをテスト
print("=" * 60)
print("Test 1: Direct safe_pickle test")
print("=" * 60)
try:
    from modules.safe_pickle import safe_loads, SafePolicy
    dangerous = pickle.dumps(__import__)
    print(f"Pickled data: {dangerous[:50]}...")
    
    # デフォルトポリシーで試す
    policy = SafePolicy()
    print(f"Policy denied_globals: {policy.denied_globals}")
    print(f"'builtins.__import__' in denied_globals: {'builtins.__import__' in policy.denied_globals}")
    
    safe_loads(dangerous)
    print("ERROR: No exception raised!")
except Exception as e:
    print(f"SUCCESS: Exception raised: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("Test 2: DictSQLiteV4 test")
print("=" * 60)
try:
    from dictsqlite_v4 import DictSQLiteV4
    db = DictSQLiteV4(':memory:', enable_safe_pickle=True)
    stats = db.stats()
    print(f"Stats: {stats}")
    print(f"safe_pickle_enabled: {stats.get('safe_pickle_enabled')}")
    
    dangerous = pickle.dumps(__import__)
    print(f"Attempting to set dangerous pickle...")
    db['test'] = dangerous
    print("ERROR: No exception raised!")
except Exception as e:
    print(f"SUCCESS: Exception raised: {type(e).__name__}: {e}")

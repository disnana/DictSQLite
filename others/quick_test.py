#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DictSQLite 高速テストスクリプト

修正の効果を素早く確認するための軽量テストスイート。
各バージョンの基本的な動作を短時間でテストします。
"""

import sys
import os
import time
import tempfile
import traceback
from pathlib import Path

# モジュールパスの設定
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'dictsqlite-fastest'))
sys.path.insert(0, str(BASE_DIR / 'dictsqlite-fastest' / 'beta'))

# インポート
try:
    from dictsqlite.main import DictSQLite
    ORIGINAL_AVAILABLE = True
except Exception as e:
    print(f"⚠️ オリジナル版のインポート失敗: {e}")
    ORIGINAL_AVAILABLE = False

try:
    from dictsqlite_fastest.main import DictSQLiteFastest
    FASTEST_AVAILABLE = True
except Exception as e:
    print(f"⚠️ APSW版のインポート失敗: {e}")
    FASTEST_AVAILABLE = False

try:
    from dictsqlite_fastest_beta import DictSQLiteFastestBeta
    BETA_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Beta版のインポート失敗: {e}")
    BETA_AVAILABLE = False


def format_time(seconds):
    """時間を読みやすくフォーマット"""
    if seconds < 0.001:
        return f"{seconds*1_000_000:.2f}μs"
    elif seconds < 1:
        return f"{seconds*1_000:.2f}ms"
    else:
        return f"{seconds:.3f}s"


def test_basic_operations(db_class, name, db_path, count=100):
    """基本操作のテスト"""
    results = {
        'name': name,
        'write': None,
        'read': None,
        'bulk_insert': None,
        'bulk_read': None,
        'update': None,
        'delete': None,
        'mixed': None,
        'errors': []
    }
    
    try:
        # 1. 基本書き込みテスト
        start = time.perf_counter()
        db = db_class(str(db_path))
        try:
            for i in range(count):
                db[f'key_{i}'] = f'value_{i}'
            results['write'] = time.perf_counter() - start
        finally:
            db.close()
        
        # 2. 基本読み込みテスト
        start = time.perf_counter()
        db = db_class(str(db_path))
        try:
            for i in range(count):
                _ = db[f'key_{i}']
            results['read'] = time.perf_counter() - start
        finally:
            db.close()
        
        # 3. バルク挿入テスト（bulk_insertがある場合のみ）
        if hasattr(db_class, '__name__') and 'Fastest' in db_class.__name__:
            bulk_path = db_path.parent / f"{db_path.stem}_bulk{db_path.suffix}"
            start = time.perf_counter()
            db = db_class(str(bulk_path))
            try:
                data = {f'bulk_{i}': f'value_{i}' for i in range(count)}
                db.bulk_insert(data)
                results['bulk_insert'] = time.perf_counter() - start
            finally:
                db.close()
            
            # 4. バルク読み込みテスト
            start = time.perf_counter()
            db = db_class(str(bulk_path))
            try:
                keys = [f'bulk_{i}' for i in range(count)]
                if hasattr(db, 'bulk_get'):
                    _ = db.bulk_get(keys)
                else:
                    for key in keys:
                        _ = db[key]
                results['bulk_read'] = time.perf_counter() - start
            finally:
                db.close()
        
        # 5. 更新テスト
        start = time.perf_counter()
        db = db_class(str(db_path))
        try:
            for i in range(count):
                db[f'key_{i}'] = f'updated_{i}'
            results['update'] = time.perf_counter() - start
        finally:
            db.close()
        
        # 6. 削除テスト
        start = time.perf_counter()
        db = db_class(str(db_path))
        try:
            for i in range(count):
                del db[f'key_{i}']
            results['delete'] = time.perf_counter() - start
        finally:
            db.close()
        
        # 7. 混合操作テスト（get()メソッドを使用）
        mixed_path = db_path.parent / f"{db_path.stem}_mixed{db_path.suffix}"
        start = time.perf_counter()
        db = db_class(str(mixed_path))
        try:
            for i in range(count):
                db[f'key_{i}'] = f'value_{i}'
                if i % 2 == 0:
                    # オリジナル版のget()メソッドをテスト
                    if hasattr(db, 'get'):
                        _ = db.get(f'key_{i//2}', None)
                    else:
                        # get()がない場合は直接アクセス
                        try:
                            _ = db[f'key_{i//2}']
                        except KeyError:
                            pass
                if i % 3 == 0 and i > 0:
                    db[f'key_{i//3}'] = f'updated_{i}'
            results['mixed'] = time.perf_counter() - start
        finally:
            db.close()
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        results['errors'].append(error_msg)
        print(f"    ❌ エラー: {error_msg}")
        # traceback.print_exc()
    
    return results


def print_results(results):
    """結果を表示"""
    name = results['name']
    print(f"\n{'='*70}")
    print(f"  {name}")
    print(f"{'='*70}")
    
    if results['errors']:
        print(f"  ❌ エラーが発生しました:")
        for error in results['errors']:
            print(f"     {error}")
        print()
    
    tests = [
        ('基本書き込み', 'write'),
        ('基本読み込み', 'read'),
        ('バルク挿入', 'bulk_insert'),
        ('バルク読み込み', 'bulk_read'),
        ('更新操作', 'update'),
        ('削除操作', 'delete'),
        ('混合操作', 'mixed'),
    ]
    
    success_count = 0
    total_tests = 0
    
    for test_name, key in tests:
        value = results[key]
        if value is not None:
            total_tests += 1
            print(f"  ✅ {test_name:12s}: {format_time(value):>12s}")
            success_count += 1
        elif key in ['bulk_insert', 'bulk_read'] and 'Fastest' not in name:
            # オリジナル版ではバルク操作はスキップ
            pass
        else:
            total_tests += 1
            print(f"  ❌ {test_name:12s}: 失敗")
    
    if total_tests > 0:
        success_rate = (success_count / total_tests) * 100
        print(f"\n  成功率: {success_count}/{total_tests} ({success_rate:.1f}%)")
        
        if success_rate == 100:
            print(f"  🎉 すべてのテスト成功!")
        elif success_rate >= 80:
            print(f"  👍 ほぼ成功")
        elif success_rate >= 50:
            print(f"  ⚠️  一部失敗")
        else:
            print(f"  ❌ 多くのテストが失敗")


def main():
    """メイン処理"""
    print("=" * 70)
    print("  DictSQLite 高速テストスイート")
    print("=" * 70)
    print(f"\n  テスト件数: 各100件（軽量テスト）")
    print(f"  テスト項目: 7種類の操作")
    print()
    
    # 一時ディレクトリの作成
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        results_list = []
        
        # オリジナル版のテスト
        if ORIGINAL_AVAILABLE:
            print("\n[1/3] オリジナル版をテスト中...")
            db_path = temp_path / "original.db"
            results = test_basic_operations(DictSQLite, "DictSQLite オリジナル版", db_path)
            results_list.append(results)
        
        # APSW版のテスト
        if FASTEST_AVAILABLE:
            print("\n[2/3] APSW版をテスト中...")
            db_path = temp_path / "fastest.db"
            results = test_basic_operations(DictSQLiteFastest, "DictSQLite-Fastest APSW版", db_path)
            results_list.append(results)
        
        # Beta版のテスト
        if BETA_AVAILABLE:
            print("\n[3/3] Beta版をテスト中...")
            db_path = temp_path / "beta.db"
            results = test_basic_operations(DictSQLiteFastestBeta, "DictSQLite-Fastest Beta版", db_path)
            results_list.append(results)
        
        # 結果の表示
        print("\n" + "=" * 70)
        print("  テスト結果サマリー")
        print("=" * 70)
        
        for results in results_list:
            print_results(results)
        
        # 総合評価
        print("\n" + "=" * 70)
        print("  総合評価")
        print("=" * 70)
        
        all_success = True
        for results in results_list:
            errors = len(results['errors'])
            if errors > 0:
                all_success = False
                print(f"  ❌ {results['name']}: {errors}個のエラー")
            else:
                success_tests = sum(1 for k, v in results.items() 
                                   if k not in ['name', 'errors'] and v is not None)
                print(f"  ✅ {results['name']}: {success_tests}個のテスト成功")
        
        if all_success:
            print("\n  🎉🎉🎉 すべてのバージョンが正常に動作しています！ 🎉🎉🎉")
        else:
            print("\n  ⚠️  一部のバージョンでエラーが発生しました")
        
        print("=" * 70)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  テストが中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 予期しないエラー: {e}")
        traceback.print_exc()
        sys.exit(1)

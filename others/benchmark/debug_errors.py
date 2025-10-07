#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DictSQLite エラー集中デバッグスクリプト

GitHub Actionsで失敗したテストケースのみを詳細にテストします。
各テストで詳細なログを出力し、エラーの原因を特定します。
"""

import sys
import os
import time
import tempfile
import traceback
from pathlib import Path

# モジュールパスの設定
BASE_DIR = Path(__file__).parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest'))
sys.path.insert(0, str(REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest' / 'beta'))

# インポート
from dictsqlite.main import DictSQLite
from dictsqlite_fastest.main import DictSQLiteFastest
from dictsqlite_fastest_beta import DictSQLiteFastestBeta


class ErrorDebugger:
    """エラー集中デバッグクラス"""
    
    def __init__(self):
        self.test_results = []
    
    def log(self, message, level="INFO"):
        """ログ出力"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def test_basic_write(self, db_class, name, count=1000):
        """基本書き込みテスト"""
        self.log(f"\n{'='*70}")
        self.log(f"テスト: {name} - 基本書き込み ({count}件)")
        self.log(f"{'='*70}")
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            self.log(f"DBパス: {db_path}")
            self.log("DB初期化開始...")
            
            db = db_class(db_path)
            self.log(f"DB初期化完了: {type(db).__name__}")
            self.log(f"  - db_name: {db.db_name}")
            self.log(f"  - table_name: {db.table_name}")
            self.log(f"  - journal_mode: {db.journal_mode}")
            
            # 初回書き込み前の状態確認
            self.log("初回書き込み前の接続確認...")
            try:
                conn = db._get_connection()
                cursor = conn.cursor()
                # テーブル存在確認
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                self.log(f"  既存テーブル: {tables}")
                cursor.close()
            except Exception as e:
                self.log(f"  接続確認エラー: {e}", "ERROR")
            
            self.log(f"書き込み開始...")
            start = time.perf_counter()
            
            for i in range(count):
                if i == 0:
                    self.log(f"  最初の書き込み: key_0 = value_0")
                try:
                    db[f'key_{i}'] = f'value_{i}'
                    if i == 0:
                        self.log(f"  最初の書き込み成功")
                except Exception as e:
                    self.log(f"  書き込みエラー (i={i}): {e}", "ERROR")
                    self.log(f"  スタックトレース:", "ERROR")
                    traceback.print_exc()
                    raise
            
            duration = time.perf_counter() - start
            self.log(f"✅ 成功: {count}件を{duration:.3f}秒で書き込み")
            self.log(f"  スループット: {count/duration:.2f} ops/sec")
            
            db.close()
            return True
            
        except Exception as e:
            self.log(f"❌ 失敗: {type(e).__name__}: {e}", "ERROR")
            traceback.print_exc()
            return False
        finally:
            try:
                os.unlink(db_path)
            except:
                pass
    
    def test_bulk_insert(self, db_class, name, count=1000):
        """バルク挿入テスト"""
        self.log(f"\n{'='*70}")
        self.log(f"テスト: {name} - バルク挿入 ({count}件)")
        self.log(f"{'='*70}")
        
        if not hasattr(db_class, '__name__') or 'Fastest' not in db_class.__name__:
            self.log("⚠️  スキップ: bulk_insertメソッドなし")
            return None
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            self.log(f"DBパス: {db_path}")
            self.log("DB初期化開始...")
            
            db = db_class(db_path)
            self.log(f"DB初期化完了: {type(db).__name__}")
            
            # 初期化直後の状態確認
            self.log("初期化直後のテーブル確認...")
            try:
                conn = db._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                self.log(f"  テーブル一覧: {tables}")
                
                # テーブル存在確認
                cursor.execute(f"SELECT COUNT(*) FROM {db.table_name}")
                count_result = cursor.fetchone()
                self.log(f"  {db.table_name}の行数: {count_result}")
                cursor.close()
            except Exception as e:
                self.log(f"  テーブル確認エラー: {e}", "ERROR")
                traceback.print_exc()
            
            self.log(f"バルクデータ準備...")
            data = {f'key_{i}': f'value_{i}' for i in range(count)}
            self.log(f"  データサイズ: {len(data)}件")
            
            self.log(f"バルク挿入開始...")
            start = time.perf_counter()
            
            try:
                db.bulk_insert(data)
                duration = time.perf_counter() - start
                self.log(f"✅ 成功: {count}件を{duration:.3f}秒でバルク挿入")
                self.log(f"  スループット: {count/duration:.2f} ops/sec")
                result = True
            except Exception as e:
                self.log(f"❌ バルク挿入エラー: {type(e).__name__}: {e}", "ERROR")
                self.log(f"  スタックトレース:", "ERROR")
                traceback.print_exc()
                result = False
            
            db.close()
            return result
            
        except Exception as e:
            self.log(f"❌ 失敗: {type(e).__name__}: {e}", "ERROR")
            traceback.print_exc()
            return False
        finally:
            try:
                os.unlink(db_path)
            except:
                pass
    
    def test_complex_data(self, db_class, name, count=100):
        """複雑データテスト"""
        self.log(f"\n{'='*70}")
        self.log(f"テスト: {name} - 複雑データ ({count}件)")
        self.log(f"{'='*70}")
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            self.log(f"DBパス: {db_path}")
            db = db_class(db_path)
            self.log(f"DB初期化完了: {type(db).__name__}")
            
            self.log(f"複雑データ書き込み開始...")
            start = time.perf_counter()
            
            for i in range(count):
                complex_data = {
                    'id': i,
                    'name': f'User {i}',
                    'tags': [f'tag{j}' for j in range(5)],
                    'metadata': {'score': i * 1.5, 'active': i % 2 == 0}
                }
                
                if i == 0:
                    self.log(f"  最初のデータ: {complex_data}")
                
                try:
                    db[f'user_{i}'] = complex_data
                    if i == 0:
                        self.log(f"  最初のデータ書き込み成功")
                except Exception as e:
                    self.log(f"  書き込みエラー (i={i}): {e}", "ERROR")
                    traceback.print_exc()
                    raise
            
            duration = time.perf_counter() - start
            self.log(f"✅ 成功: {count}件を{duration:.3f}秒で書き込み")
            
            db.close()
            return True
            
        except Exception as e:
            self.log(f"❌ 失敗: {type(e).__name__}: {e}", "ERROR")
            traceback.print_exc()
            return False
        finally:
            try:
                os.unlink(db_path)
            except:
                pass
    
    def test_update(self, db_class, name, count=1000):
        """更新操作テスト"""
        self.log(f"\n{'='*70}")
        self.log(f"テスト: {name} - 更新操作 ({count}件)")
        self.log(f"{'='*70}")
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            # 初期データ作成
            self.log("初期データ作成...")
            db = db_class(db_path)
            for i in range(count):
                db[f'key_{i}'] = f'value_{i}'
            self.log(f"  {count}件の初期データ作成完了")
            db.close()
            
            # 更新テスト
            self.log("更新操作開始...")
            db = db_class(db_path)
            start = time.perf_counter()
            
            for i in range(count):
                try:
                    db[f'key_{i}'] = f'updated_{i}'
                except Exception as e:
                    self.log(f"  更新エラー (i={i}): {e}", "ERROR")
                    traceback.print_exc()
                    raise
            
            duration = time.perf_counter() - start
            self.log(f"✅ 成功: {count}件を{duration:.3f}秒で更新")
            
            db.close()
            return True
            
        except Exception as e:
            self.log(f"❌ 失敗: {type(e).__name__}: {e}", "ERROR")
            traceback.print_exc()
            return False
        finally:
            try:
                os.unlink(db_path)
            except:
                pass
    
    def test_delete(self, db_class, name, count=1000):
        """削除操作テスト"""
        self.log(f"\n{'='*70}")
        self.log(f"テスト: {name} - 削除操作 ({count}件)")
        self.log(f"{'='*70}")
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            # 初期データ作成
            self.log("初期データ作成...")
            db = db_class(db_path)
            for i in range(count):
                db[f'key_{i}'] = f'value_{i}'
            self.log(f"  {count}件の初期データ作成完了")
            db.close()
            
            # 削除テスト
            self.log("削除操作開始...")
            db = db_class(db_path)
            start = time.perf_counter()
            
            for i in range(count):
                try:
                    del db[f'key_{i}']
                except Exception as e:
                    self.log(f"  削除エラー (i={i}): {e}", "ERROR")
                    traceback.print_exc()
                    raise
            
            duration = time.perf_counter() - start
            self.log(f"✅ 成功: {count}件を{duration:.3f}秒で削除")
            
            db.close()
            return True
            
        except Exception as e:
            self.log(f"❌ 失敗: {type(e).__name__}: {e}", "ERROR")
            traceback.print_exc()
            return False
        finally:
            try:
                os.unlink(db_path)
            except:
                pass
    
    def test_mixed_operations(self, db_class, name, count=1000):
        """混合操作テスト"""
        self.log(f"\n{'='*70}")
        self.log(f"テスト: {name} - 混合操作 ({count}件)")
        self.log(f"{'='*70}")
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = db_class(db_path)
            self.log(f"DB初期化完了: {type(db).__name__}")
            
            # get()メソッドの存在確認
            has_get = hasattr(db, 'get')
            self.log(f"  get()メソッド: {'あり' if has_get else 'なし'}")
            
            self.log("混合操作開始...")
            start = time.perf_counter()
            
            for i in range(count):
                # 書き込み
                db[f'key_{i}'] = f'value_{i}'
                
                # 読み込み（get使用）
                if i % 2 == 0 and i > 0:
                    if has_get:
                        _ = db.get(f'key_{i//2}', None)
                    else:
                        try:
                            _ = db[f'key_{i//2}']
                        except KeyError:
                            pass
                
                # 更新
                if i % 3 == 0 and i > 0:
                    db[f'key_{i//3}'] = f'updated_{i}'
            
            duration = time.perf_counter() - start
            self.log(f"✅ 成功: {duration:.3f}秒で完了")
            
            db.close()
            return True
            
        except Exception as e:
            self.log(f"❌ 失敗: {type(e).__name__}: {e}", "ERROR")
            traceback.print_exc()
            return False
        finally:
            try:
                os.unlink(db_path)
            except:
                pass


def main():
    """メイン処理"""
    print("="*70)
    print("  🔍 DictSQLite エラー集中デバッグ")
    print("="*70)
    print("\nGitHub Actionsで失敗したテストケースを詳細にデバッグします。\n")
    
    debugger = ErrorDebugger()
    
    # テスト対象
    test_cases = [
        # APSW版のエラーケース
        ("APSW版", DictSQLiteFastest, [
            ("基本書き込み", "test_basic_write", 1000),
            ("バルク挿入", "test_bulk_insert", 1000),
            ("複雑データ", "test_complex_data", 100),
            ("更新操作", "test_update", 1000),
            ("削除操作", "test_delete", 1000),
            ("混合操作", "test_mixed_operations", 1000),
        ]),
        
        # Beta版のエラーケース
        ("Beta版", DictSQLiteFastestBeta, [
            ("バルク挿入", "test_bulk_insert", 1000),
            ("複雑データ", "test_complex_data", 100),
            ("更新操作", "test_update", 1000),
            ("削除操作", "test_delete", 1000),
        ]),
        
        # オリジナル版の混合操作
        ("オリジナル版", DictSQLite, [
            ("混合操作", "test_mixed_operations", 1000),
        ]),
    ]
    
    results = []
    
    for version_name, db_class, tests in test_cases:
        debugger.log(f"\n{'#'*70}")
        debugger.log(f"  {version_name} デバッグ開始")
        debugger.log(f"{'#'*70}")
        
        for test_name, method_name, count in tests:
            method = getattr(debugger, method_name)
            result = method(db_class, version_name, count)
            results.append({
                'version': version_name,
                'test': test_name,
                'result': result
            })
            
            # 少し間隔を開ける
            time.sleep(0.5)
    
    # サマリー表示
    print("\n" + "="*70)
    print("  📊 デバッグ結果サマリー")
    print("="*70)
    
    success_count = 0
    failure_count = 0
    skip_count = 0
    
    for r in results:
        if r['result'] is None:
            status = "⚠️  スキップ"
            skip_count += 1
        elif r['result']:
            status = "✅ 成功"
            success_count += 1
        else:
            status = "❌ 失敗"
            failure_count += 1
        
        print(f"  {status:12s} {r['version']:15s} - {r['test']}")
    
    print("\n" + "-"*70)
    print(f"  成功: {success_count}  失敗: {failure_count}  スキップ: {skip_count}")
    print("="*70)
    
    if failure_count == 0:
        print("\n🎉 すべてのテストが成功しました！")
    else:
        print(f"\n⚠️  {failure_count}個のテストが失敗しました。")
        print("上記のログを確認して、エラーの原因を特定してください。")


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

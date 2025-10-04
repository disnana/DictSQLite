"""診断テスト - どこでフリーズするか特定"""

import asyncio
import sys
import os
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "dictsqlite-fastest" / "beta"))

from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta


def cleanup_db(db_path):
    """テスト用DBを削除"""
    for ext in ['', '-wal', '-shm']:
        try:
            os.remove(db_path + ext)
        except:
            pass


async def test_step_by_step():
    """ステップバイステップで診断"""
    print("="*80)
    print("診断テスト - フリーズ箇所の特定")
    print("="*80)
    
    db_path = "test_diagnose.db"
    cleanup_db(db_path)
    
    try:
        # Step 1: インスタンス作成
        print("\n[Step 1] インスタンス作成...")
        try:
            db = AsyncDictSQLiteFastestBeta(
                db_name=db_path,
                cache_capacity=10,
                async_batch_size=5,
                async_commit_interval=0  # バックグラウンドタスク無効
            )
            print("   [OK] 作成完了")
        except Exception as e:
            print(f"   [ERROR] {e}")
            return
        
        # Step 2: 初期化
        print("\n[Step 2] 初期化...")
        try:
            await asyncio.wait_for(db._ensure_initialized(), timeout=5.0)
            print("   [OK] 初期化完了")
        except asyncio.TimeoutError:
            print("   [TIMEOUT] 初期化でタイムアウト")
            print("   原因: aiosqlite接続またはPRAGMA設定")
            return
        except Exception as e:
            print(f"   [ERROR] {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Step 3: 書き込み
        print("\n[Step 3] 書き込みテスト（10件）...")
        try:
            for i in range(10):
                await asyncio.wait_for(
                    db.aset(f'key_{i}', f'value_{i}'),
                    timeout=1.0
                )
                print(f"   書き込み {i+1}/10 完了")
            print("   [OK] 書き込み完了")
        except asyncio.TimeoutError:
            print(f"   [TIMEOUT] 書き込み {i+1}/10 でタイムアウト")
            return
        except Exception as e:
            print(f"   [ERROR] {e}")
            return
        
        # Step 4: フラッシュ
        print("\n[Step 4] フラッシュ...")
        try:
            await asyncio.wait_for(db._flush_write_buffer(), timeout=5.0)
            print("   [OK] フラッシュ完了")
        except asyncio.TimeoutError:
            print("   [TIMEOUT] フラッシュでタイムアウト")
            print("   原因: executemany または commit")
            return
        except Exception as e:
            print(f"   [ERROR] {e}")
            return
        
        # Step 5: 読み取り
        print("\n[Step 5] 読み取りテスト（10件）...")
        try:
            for i in range(10):
                value = await asyncio.wait_for(
                    db.aget(f'key_{i}'),
                    timeout=1.0
                )
                assert value == f'value_{i}'
                print(f"   読み取り {i+1}/10 完了")
            print("   [OK] 読み取り完了")
        except asyncio.TimeoutError:
            print(f"   [TIMEOUT] 読み取り {i+1}/10 でタイムアウト")
            return
        except Exception as e:
            print(f"   [ERROR] {e}")
            return
        
        # Step 6: クローズ
        print("\n[Step 6] クローズ...")
        try:
            await asyncio.wait_for(db.aclose(), timeout=5.0)
            print("   [OK] クローズ完了")
        except asyncio.TimeoutError:
            print("   [TIMEOUT] クローズでタイムアウト")
            print("   原因: バックグラウンドタスクまたは接続クローズ")
            return
        except Exception as e:
            print(f"   [ERROR] {e}")
            return
        
        print("\n" + "="*80)
        print("[SUCCESS] 全ステップ成功！")
        print("="*80)
        
    finally:
        await asyncio.sleep(0.3)
        cleanup_db(db_path)


async def main():
    """メイン"""
    try:
        await asyncio.wait_for(test_step_by_step(), timeout=30.0)
    except asyncio.TimeoutError:
        print("\n" + "="*80)
        print("[CRITICAL] 全体で30秒タイムアウト")
        print("="*80)


if __name__ == "__main__":
    print("[INFO] 診断開始（全体タイムアウト: 30秒）")
    asyncio.run(main())
    print("[INFO] 診断終了")

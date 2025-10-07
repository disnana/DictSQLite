#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バージョン管理システムの簡易テスト
"""

import sys
from pathlib import Path
import tempfile
import shutil

# モジュールパスの設定
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from version_manager import VersionManager


def test_version_manager():
    """バージョンマネージャーの基本機能をテスト"""
    print("=" * 80)
    print("バージョン管理システム テスト")
    print("=" * 80)
    
    # テスト用の一時ディレクトリを作成
    test_dir = Path(tempfile.mkdtemp(prefix="benchmark_test_"))
    print(f"\nテストディレクトリ: {test_dir}")
    
    try:
        # 1. バージョンマネージャーを初期化
        print("\n[1/6] バージョンマネージャー初期化")
        manager = VersionManager(test_dir)
        print("  ✓ 初期化成功")
        
        # 2. バージョン情報を取得
        print("\n[2/6] バージョン情報取得")
        versions = manager.get_version_info()
        print(f"  Original: {versions['original']}")
        print(f"  Fastest: {versions['fastest']}")
        print(f"  Beta: {versions['beta']}")
        
        version_string = manager.get_version_string()
        print(f"  バージョン文字列: {version_string}")
        
        # 3. パスを取得
        print("\n[3/6] ファイルパス取得")
        paths = manager.get_version_paths()
        print(f"  CSV: {paths['csv'].name}")
        print(f"  JSON: {paths['json'].name}")
        print(f"  Summary: {paths['summary'].name}")
        print(f"  Log: {paths['log'].name}")
        
        # 4. ダミーデータを保存
        print("\n[4/6] ベンチマーク結果保存テスト")
        csv_content = "Test,Version,Time (s),OPS\nTest1,original,1.0,1000\nTest1,fastest,0.5,2000\n"
        json_content = {"test": "data", "timestamp": "20241207_120000"}
        summary_content = "# テストサマリー\n\nこれはテストです。"
        log_content = "Test log entry 1\nTest log entry 2\n"
        
        saved_files = manager.save_benchmark_result(
            csv_content=csv_content,
            json_content=json_content,
            summary_content=summary_content,
            log_content=log_content
        )
        
        print(f"  ✓ {len(saved_files)}個のファイルを保存")
        
        # 5. 保存されたファイルを確認
        print("\n[5/6] 保存ファイル確認")
        for file_type, file_path in saved_files.items():
            if file_path.exists():
                print(f"  ✓ {file_type}: {file_path.name} ({file_path.stat().st_size} bytes)")
            else:
                print(f"  ✗ {file_type}: ファイルが存在しません")
        
        # 6. バージョン一覧を取得
        print("\n[6/6] バージョン一覧取得")
        available = manager.list_available_versions()
        print(f"  利用可能なバージョン: {len(available)}個")
        for v in available:
            print(f"    - {v}")
        
        print("\n" + "=" * 80)
        print("✅ すべてのテストが成功しました！")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # クリーンアップ
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print(f"\nテストディレクトリを削除: {test_dir}")


if __name__ == '__main__':
    success = test_version_manager()
    sys.exit(0 if success else 1)

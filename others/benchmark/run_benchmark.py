#!/usr/bin/env python3
"""ベンチマーク実行スクリプト - Beta版バージョン選択対応

使用方法:
    python run_benchmark.py --beta v1              # v1のみテスト
    python run_benchmark.py --beta v2              # v2のみテスト
    python run_benchmark.py --beta both            # 両方テスト
    python run_benchmark.py --beta v1 --full       # v1でフルベンチマーク
"""

import sys
import os
import argparse
import subprocess
import shutil
from pathlib import Path


def replace_import_in_file(file_path, version):
    """ファイル内のインポートをバージョンに応じて置換"""
    if not os.path.exists(file_path):
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if version == 'v1':
        # v2のインポートをv1に戻す
        new_content = content.replace(
            'from dictsqlite_fastest_beta_v2 import',
            'from dictsqlite_fastest_beta import'
        )
    elif version == 'v2':
        # v1のインポートをv2に変更
        new_content = content.replace(
            'from dictsqlite_fastest_beta import',
            'from dictsqlite_fastest_beta_v2 import'
        )
    else:
        return False
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    
    return False


def run_benchmark(beta_version, full_benchmark=False):
    """ベンチマークを実行"""
    
    # ベンチマークディレクトリに移動
    benchmark_dir = Path(__file__).parent
    os.chdir(benchmark_dir)
    
    # バックアップを作成
    scripts = [
        'comprehensive_benchmark.py',
        'fast_comprehensive_benchmark.py'
    ]
    
    backups = {}
    for script in scripts:
        if os.path.exists(script):
            backup = f"{script}.backup"
            shutil.copy2(script, backup)
            backups[script] = backup
            print(f"📋 バックアップ作成: {backup}")
    
    try:
        # インポートを変更
        if beta_version in ['v1', 'v2']:
            print(f"\n🔄 ベンチマークスクリプトを{beta_version}用に変更...")
            for script in scripts:
                if replace_import_in_file(script, beta_version):
                    print(f"   ✓ {script} を {beta_version} 用に変更")
        
        # ベンチマーク実行
        if full_benchmark:
            script = 'comprehensive_benchmark.py'
            print(f"\n🔬 フル機能ベンチマーク ({beta_version}) を実行中...")
        else:
            script = 'fast_comprehensive_benchmark.py'
            print(f"\n⚡ 高速ベンチマーク ({beta_version}) を実行中...")
        
        result = subprocess.run(
            [sys.executable, script],
            env={**os.environ, 'BETA_VERSION': beta_version}
        )
        
        if result.returncode != 0:
            print(f"\n❌ ベンチマーク失敗 (終了コード: {result.returncode})")
            return False
        
        print(f"\n✅ ベンチマーク成功 ({beta_version})")
        return True
        
    finally:
        # バックアップから復元
        print("\n🔙 元のファイルに復元中...")
        for script, backup in backups.items():
            if os.path.exists(backup):
                shutil.move(backup, script)
                print(f"   ✓ {script} を復元")


def main():
    parser = argparse.ArgumentParser(
        description='DictSQLite Beta版ベンチマーク実行スクリプト'
    )
    parser.add_argument(
        '--beta',
        choices=['v1', 'v2', 'both'],
        default='v1',
        help='Beta版のバージョン (デフォルト: v1)'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='フル機能ベンチマークを実行（時間がかかります）'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("DictSQLite Beta版ベンチマーク")
    print("=" * 80)
    print(f"Beta版: {args.beta}")
    print(f"ベンチマークタイプ: {'フル機能' if args.full else '高速'}")
    print("=" * 80)
    
    if args.beta == 'both':
        print("\n📊 両バージョンのベンチマークを実行...")
        
        # v1を実行
        print("\n" + "=" * 80)
        print("Part 1/2: Beta v1")
        print("=" * 80)
        success_v1 = run_benchmark('v1', args.full)
        
        # v2を実行
        print("\n" + "=" * 80)
        print("Part 2/2: Beta v2")
        print("=" * 80)
        success_v2 = run_benchmark('v2', args.full)
        
        # 結果サマリー
        print("\n" + "=" * 80)
        print("結果サマリー")
        print("=" * 80)
        print(f"v1: {'✅ 成功' if success_v1 else '❌ 失敗'}")
        print(f"v2: {'✅ 成功' if success_v2 else '❌ 失敗'}")
        
        if success_v1 and success_v2:
            print("\n🎉 両バージョンのベンチマークが成功しました！")
            return 0
        else:
            print("\n⚠️  一部のベンチマークが失敗しました")
            return 1
    else:
        # 単一バージョンを実行
        success = run_benchmark(args.beta, args.full)
        return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

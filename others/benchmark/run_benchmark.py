#!/usr/bin/env python3
"""ベンチマーク実行スクリプト - Beta版バージョン選択対応

使用方法:
    python run_benchmark.py --beta v1              # v1のみテスト
    python run_benchmark.py --beta v2              # v2のみテスト
    python run_benchmark.py --beta v3              # v3のみテスト
    python run_benchmark.py --beta v4              # v4のみテスト
    python run_benchmark.py --beta all             # v1, v2, v3, v4を全て比較
    python run_benchmark.py --beta all --full      # 全バージョンでフルベンチマーク
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
        # 他のバージョンのインポートをv1に戻す
        new_content = content.replace(
            'from dictsqlite_fastest_beta_v2 import',
            'from dictsqlite_fastest_beta import'
        ).replace(
            'from dictsqlite_fastest_beta_v3_alpha import',
            'from dictsqlite_fastest_beta import'
        ).replace(
            'from dictsqlite_fastest_beta_v4_final import',
            'from dictsqlite_fastest_beta import'
        )
    elif version == 'v2':
        # v1のインポートをv2に変更
        new_content = content.replace(
            'from dictsqlite_fastest_beta import',
            'from dictsqlite_fastest_beta_v2 import'
        )
    elif version == 'v3':
        # v1のインポートをv3-alphaに変更
        new_content = content.replace(
            'from dictsqlite_fastest_beta import',
            'from dictsqlite_fastest_beta_v3_alpha import'
        )
    elif version == 'v4':
        # v1のインポートをv4-finalに変更
        new_content = content.replace(
            'from dictsqlite_fastest_beta import',
            'from dictsqlite_fastest_beta_v4_final import'
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
    
    # v1, v2, v3, v4をサポート
    if beta_version not in ['v1', 'v2', 'v3', 'v4']:
        print(f"\n❌ エラー: {beta_version} はサポートされていません。v1, v2, v3, v4のみサポートされています。")
        return False
    
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
        if beta_version in ['v1', 'v2', 'v3', 'v4']:
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


def run_all_versions_benchmark():
    """Run comprehensive benchmark comparing all versions (v1, v2, v3, v4)."""
    
    # ベンチマークディレクトリに移動
    benchmark_dir = Path(__file__).parent
    
    # 専用の比較ベンチマークを実行
    script = benchmark_dir / 'benchmark_all_versions.py'
    
    if not script.exists():
        print(f"\n❌ エラー: {script} が見つかりません")
        return False
    
    print("\n🔬 v1, v2, v3, v4 総合比較ベンチマークを実行中...")
    print(f"スクリプト: {script}")
    
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(benchmark_dir)
    )
    
    if result.returncode != 0:
        print(f"\n❌ ベンチマーク失敗 (終了コード: {result.returncode})")
        return False
    
    print(f"\n✅ 総合ベンチマーク成功")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='DictSQLite Beta版ベンチマーク実行スクリプト'
    )
    parser.add_argument(
        '--beta',
        choices=['v1', 'v2', 'v3', 'v4', 'all'],
        default='v1',
        help='Beta版のバージョン (デフォルト: v1, all=全バージョン比較)'
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
    
    if args.beta == 'all':
        print("\n📊 全バージョン (v1, v2, v3) の比較ベンチマークを実行...")
        success = run_all_versions_benchmark()
        return 0 if success else 1
    else:
        # 単一バージョンを実行
        success = run_benchmark(args.beta, args.full)
        return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

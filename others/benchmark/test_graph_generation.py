#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
グラフ生成機能のテストスクリプト

統計画像と徹底比較グラフの生成をテストします。
"""

import sys
import tempfile
from pathlib import Path
import shutil

# モジュールパスの設定
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from generate_graphs import BenchmarkGraphGenerator


def create_test_csv_v1():
    """v1用のテストCSVデータを作成"""
    csv_content = """Test,Version,Time (s),OPS
基本書き込み (100件),original,0.123,813.01
基本書き込み (100件),fastest,0.023,4347.83
基本書き込み (100件),beta,0.019,5263.16
基本読み込み (100件),original,0.089,1123.60
基本読み込み (100件),fastest,0.018,5555.56
基本読み込み (100件),beta,0.015,6666.67
バルク挿入 (1000件),original,0.456,2192.98
バルク挿入 (1000件),fastest,0.089,11235.96
バルク挿入 (1000件),beta,0.067,14925.37
"""
    return csv_content


def create_test_csv_all():
    """all用のテストCSVデータを作成（より多くのデータ）"""
    csv_content = """Test,Version,Time (s),OPS,Operation Count
基本書き込み (100件),original,0.123,813.01,100
基本書き込み (100件),fastest,0.023,4347.83,100
基本書き込み (100件),beta,0.019,5263.16,100
基本書き込み (1000件),original,1.234,810.37,1000
基本書き込み (1000件),fastest,0.234,4273.50,1000
基本書き込み (1000件),beta,0.189,5291.00,1000
基本読み込み (100件),original,0.089,1123.60,100
基本読み込み (100件),fastest,0.018,5555.56,100
基本読み込み (100件),beta,0.015,6666.67,100
基本読み込み (1000件),original,0.756,1322.75,1000
基本読み込み (1000件),fastest,0.145,6896.55,1000
基本読み込み (1000件),beta,0.123,8130.08,1000
バルク挿入 (1000件),original,0.456,2192.98,1000
バルク挿入 (1000件),fastest,0.089,11235.96,1000
バルク挿入 (1000件),beta,0.067,14925.37,1000
バルク挿入 (5000件),original,2.345,2132.20,5000
バルク挿入 (5000件),fastest,0.456,10964.91,5000
バルク挿入 (5000件),beta,0.334,14970.06,5000
非同期書き込み (100件),original,0.145,689.66,100
非同期書き込み (100件),fastest,0.034,2941.18,100
非同期書き込み (100件),beta,0.028,3571.43,100
"""
    return csv_content


def test_graph_generation():
    """グラフ生成テスト"""
    print("=" * 80)
    print("グラフ生成機能テスト")
    print("=" * 80)
    
    # テスト用の一時ディレクトリを作成
    test_dir = Path(tempfile.mkdtemp(prefix="graph_test_"))
    print(f"\nテストディレクトリ: {test_dir}")
    
    try:
        # Test 1: v1バージョンのグラフ生成
        print("\n" + "=" * 80)
        print("Test 1: v1バージョンのグラフ生成")
        print("=" * 80)
        
        v1_dir = test_dir / "v1"
        v1_dir.mkdir()
        v1_csv = v1_dir / "benchmark.csv"
        v1_csv.write_text(create_test_csv_v1(), encoding='utf-8')
        
        generator_v1 = BenchmarkGraphGenerator(v1_csv, version_type='v1')
        generator_v1.generate_all_graphs()
        
        # v1の結果を確認
        v1_graphs = list((v1_dir / "graphs").glob("*.png"))
        print(f"\n✓ v1グラフ生成完了: {len(v1_graphs)}個のファイル")
        for graph in v1_graphs:
            print(f"  - {graph.name} ({graph.stat().st_size} bytes)")
        
        # 統計サマリーのみが生成されることを確認
        assert (v1_dir / "graphs" / "stats_summary.png").exists(), "統計サマリーが生成されていません"  # nosec B101
        assert len(v1_graphs) == 1, f"v1では統計サマリーのみ生成されるべきですが、{len(v1_graphs)}個生成されました"  # nosec B101
        
        print("✓ v1テスト: OK（統計サマリーのみ生成）")
        
        # Test 2: allバージョンのグラフ生成
        print("\n" + "=" * 80)
        print("Test 2: allバージョンのグラフ生成")
        print("=" * 80)
        
        all_dir = test_dir / "all"
        all_dir.mkdir()
        all_csv = all_dir / "benchmark.csv"
        all_csv.write_text(create_test_csv_all(), encoding='utf-8')
        
        generator_all = BenchmarkGraphGenerator(all_csv, version_type='all')
        generator_all.generate_all_graphs()
        
        # allの結果を確認
        all_graphs = list((all_dir / "graphs").glob("*.png"))
        print(f"\n✓ allグラフ生成完了: {len(all_graphs)}個のファイル")
        for graph in sorted(all_graphs):
            print(f"  - {graph.name} ({graph.stat().st_size} bytes)")
        
        # すべてのグラフが生成されることを確認
        expected_files = [
            "stats_summary.png",
            "comparison_ops.png",
            "comparison_time.png",
            "comparison_speedup.png",
            "comparison_heatmap.png",
            "comparison_scalability.png",
            "comparison_evolution.png",
            "comparison_metrics.png",
            "comparison_coverage.png",
        ]
        
        for expected_file in expected_files:
            file_path = all_dir / "graphs" / expected_file
            assert file_path.exists(), f"{expected_file}が生成されていません"  # nosec B101
        
        assert len(all_graphs) == len(expected_files), \
            f"allでは{len(expected_files)}個のグラフが生成されるべきですが、{len(all_graphs)}個生成されました"  # nosec B101
        
        print(f"✓ allテスト: OK（{len(expected_files)}個のグラフ生成）")
        
        # Test 3: 固定ファイル名の確認
        print("\n" + "=" * 80)
        print("Test 3: 固定ファイル名の確認")
        print("=" * 80)
        
        # v1とallで同じファイル名が使われていることを確認
        v1_stats = v1_dir / "graphs" / "stats_summary.png"
        all_stats = all_dir / "graphs" / "stats_summary.png"
        
        assert v1_stats.exists() and all_stats.exists(), "統計サマリーが両方に存在することを確認"  # nosec B101
        print("✓ 固定ファイル名: OK（stats_summary.png が両方に存在）")
        
        # Test 4: 上書きテスト
        print("\n" + "=" * 80)
        print("Test 4: 上書きテスト")
        print("=" * 80)
        
        # v1を再生成
        original_mtime = v1_stats.stat().st_mtime
        import time
        time.sleep(0.1)  # タイムスタンプ変更を確実にするため
        
        generator_v1_2 = BenchmarkGraphGenerator(v1_csv, version_type='v1')
        generator_v1_2.generate_all_graphs()
        
        new_mtime = v1_stats.stat().st_mtime
        assert new_mtime > original_mtime, "ファイルが上書きされていません"  # nosec B101
        print("✓ 上書きテスト: OK（ファイルが正常に上書きされました）")
        
        print("\n" + "=" * 80)
        print("✅ すべてのテストが成功しました！")
        print("=" * 80)
        
        # サマリー
        print("\n📊 テスト結果サマリー:")
        print(f"  - v1グラフ: {len(v1_graphs)}個（統計サマリーのみ）")
        print(f"  - allグラフ: {len(all_graphs)}個（統計 + 徹底比較）")
        print(f"  - 固定ファイル名: ✓")
        print(f"  - 上書き機能: ✓")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # クリーンアップ
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print(f"\nテストディレクトリを削除: {test_dir}")


if __name__ == '__main__':
    success = test_graph_generation()
    sys.exit(0 if success else 1)

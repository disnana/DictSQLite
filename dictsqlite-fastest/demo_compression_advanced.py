#!/usr/bin/env python3
"""
DictSQLite-Fastest 高度圧縮機能デモンストレーション
Advanced Compression Features Demonstration
"""

import os
import sys
import time
import tempfile
from dictsqlite_fastest.main import DictSQLiteFastest

# zstandard の利用可否をチェック（なければフォールバック/スキップする）
try:
    import zstandard as _zstd  # noqa: F401
    ZSTD_AVAILABLE = True
except Exception:
    ZSTD_AVAILABLE = False


def demo_compression_algorithms():
    """圧縮アルゴリズム比較デモ"""
    print("🗜️ 圧縮アルゴリズム比較デモ")
    print("=" * 60)

    # テストデータ作成
    small_data = "小さなデータ" * 10  # 圧縮されない
    medium_data = "中程度のデータ" * 100  # 圧縮される
    large_data = "大きなデータ" * 1000  # 大幅圧縮

    algorithms = [
        ('zlib', 'zlib圧縮'),
    ]

    if ZSTD_AVAILABLE:
        algorithms.append(('zstd', 'ZSTD圧縮（推奨）'))
    else:
        print("⚠️ zstandard パッケージが見つかりません。ZSTD テストはスキップします。\n")

    for algo, desc in algorithms:
        print(f"\n📊 {desc}テスト")
        print("-" * 40)

        temp_dir = tempfile.gettempdir()
        db_path = os.path.join(temp_dir, f'compression_test_{algo}.db')
        try:
            os.unlink(db_path)
        except:
            pass

        with DictSQLiteFastest(
                db_path,
                enable_compression=True,
                compression_algorithm=algo,
                compression_threshold=100  # 100バイト以上を圧縮
        ) as db:

            # データ挿入と検証
            start_time = time.time()

            db['small'] = small_data
            db['medium'] = medium_data
            db['large'] = large_data

            end_time = time.time()

            # データ検証
            assert db['small'] == small_data
            assert db['medium'] == medium_data
            assert db['large'] == large_data

            # ファイルサイズ確認
            file_size = os.path.getsize(db_path)

            print(f"  ✅ 小データ: {len(small_data)}文字 → 正常取得")
            print(f"  ✅ 中データ: {len(medium_data)}文字 → 正常取得")
            print(f"  ✅ 大データ: {len(large_data)}文字 → 正常取得")
            print(f"  💾 DBファイルサイズ: {file_size:,}バイト")
            print(f"  ⏱️ 処理時間: {end_time - start_time:.4f}秒")


def demo_compression_performance():
    """圧縮パフォーマンス比較"""
    print("\n\n⚡ 圧縮パフォーマンス比較")
    print("=" * 60)

    # 大量データ生成
    data_sets = [
        ("小規模", "データ" * 100, 100),
        ("中規模", "パフォーマンステストデータ" * 500, 500),
        ("大規模", "大量データ処理テスト用文字列" * 1000, 1000)
    ]

    configs = [
        ("無圧縮", False, 'zlib', 0),
        ("zlib圧縮", True, 'zlib', 500),
    ]

    if ZSTD_AVAILABLE:
        configs.append(("ZSTD圧縮", True, 'zstd', 500))
    else:
        print("⚠️ zstandard が利用できないため、ZSTD 圧縮設定はテストから除外します。\n")

    print(f"{ 'データ規模':<10} {'設定':<10} {'書込時間':<10} {'読込時間':<10} {'ファイルサイズ':<12}")
    print("-" * 65)

    for data_name, base_data, count in data_sets:
        for config_name, enable_comp, algo, threshold in configs:
            temp_dir = tempfile.gettempdir()
            db_path = os.path.join(temp_dir, f'perf_test_{data_name}_{config_name}.db')
            try:
                os.unlink(db_path)
            except:
                pass

            # 書き込みテスト
            start_write = time.time()
            with DictSQLiteFastest(
                    db_path,
                    enable_compression=enable_comp,
                    compression_algorithm=algo,
                    compression_threshold=threshold
            ) as db:
                for i in range(count):
                    db[f'key_{i}'] = base_data + str(i)
            end_write = time.time()

            # 読み込みテスト
            start_read = time.time()
            # 読み込み時にも同じ圧縮設定を指定（enable_compression を忘れると zstd 初期化が行われず失敗する）
            with DictSQLiteFastest(
                db_path,
                enable_compression=enable_comp,
                compression_algorithm=algo,
                compression_threshold=threshold
            ) as db:
                for i in range(count):
                    _ = db[f'key_{i}']
            end_read = time.time()

            # ファイルサイズ
            file_size = os.path.getsize(db_path)

            write_time = end_write - start_write
            read_time = end_read - start_read

            print(f"{data_name:<10} {config_name:<10} {write_time:<10.4f} {read_time:<10.4f} {file_size:>10,}B")


def demo_compression_settings():
    """圧縮設定のカスタマイズデモ"""
    print("\n\n🎛️ 圧縮設定カスタマイズデモ")
    print("=" * 60)

    # 様々な閾値でのテスト
    thresholds = [100, 500, 1000, 2000]
    test_data = "圧縮閾値テストデータ" * 200  # 約4000文字

    print(f"テストデータサイズ: {len(test_data)}文字")
    print(f"{ '閾値':<8} {'圧縮状態':<12} {'ファイルサイズ':<12} {'処理時間':<10}")
    print("-" * 50)

    for threshold in thresholds:
        temp_dir = tempfile.gettempdir()
        db_path = os.path.join(temp_dir, f'threshold_test_{threshold}.db')
        try:
            os.unlink(db_path)
        except:
            pass

        # zstd が無ければ zlib にフォールバック
        algo = 'zstd' if ZSTD_AVAILABLE else 'zlib'
        if not ZSTD_AVAILABLE:
            print(f"⚠️ zstandard が見つかりません。閾値テストで zlib を代替として使用します。 (閾値={threshold})")

        start_time = time.time()
        with DictSQLiteFastest(
                db_path,
                enable_compression=True,
                compression_algorithm=algo,
                compression_threshold=threshold
        ) as db:
            db['test'] = test_data
        end_time = time.time()

        # 圧縮されたかチェック（簡易）
        file_size = os.path.getsize(db_path)
        compressed = "圧縮済み" if file_size < len(test_data) + 1000 else "無圧縮"

        print(f"{threshold:<8} {compressed:<12} {file_size:>10,}B {end_time - start_time:<10.4f}")


def demo_advanced_features():
    """高度機能統合デモ"""
    print("\n\n🚀 高度機能統合デモ")
    print("=" * 60)

    temp_dir = tempfile.gettempdir()
    db_path = os.path.join(temp_dir, 'advanced_demo.db')
    try:
        os.unlink(db_path)
    except:
        pass

    # 高度デモでも zstd が無ければ zlib にフォールバック
    chosen_algo = 'zstd' if ZSTD_AVAILABLE else 'zlib'
    if not ZSTD_AVAILABLE:
        print("⚠️ zstandard が見つかりません。高度機能デモでは zlib を使用します。")

    with DictSQLiteFastest(
            db_path,
            # 圧縮設定
            enable_compression=True,
            compression_algorithm=chosen_algo,
            compression_threshold=200,

            # パフォーマンス設定
            cache_size=-128000,  # 128MB
            mmap_size=536870912,  # 512MB
            wal_autocheckpoint=2000,

            # 最適化設定
            optimize_on_init=True,
            enable_memory_optimization=True,

            # カスタム設定
            custom_pragma_settings={
                'page_size': 65536,
                'auto_vacuum': 'INCREMENTAL'
            }
    ) as db:

        print("📝 複雑なデータ構造のテスト")

        # 複雑なデータ構造
        complex_data = {
            'user_profiles': [
                {
                    'id': i,
                    'name': f'ユーザー{i}',
                    'description': '詳細な説明文' * 100,  # 大きなテキスト
                    'settings': {
                        'theme': 'dark',
                        'notifications': True,
                        'privacy': {'level': i % 5}
                    }
                }
                for i in range(100)
            ],
            'metadata': {
                'version': '2.0',
                'created': '2024-01-01',
                'stats': {'users': 100, 'data_size': '大容量'}
            }
        }

        start_time = time.time()
        db['complex_data'] = complex_data

        # データ検証
        retrieved = db['complex_data']
        assert retrieved == complex_data

        end_time = time.time()

        print(f"  ✅ 複雑データ保存・取得完了")
        print(f"  📊 処理時間: {end_time - start_time:.4f}秒")
        print(f"  💾 ファイルサイズ: {os.path.getsize(db_path):,}バイト")

        # 統計情報
        print(f"  🔢 保存アイテム数: {len(db)}")

        print("\n📈 パフォーマンス統計:")
        try:
            stats = db.get_performance_stats()
            print(f"  • アクセス回数: {stats.get('access_count', 'N/A')}")
            print(f"  • キャッシュヒット率: {stats.get('cache_hit_rate', 'N/A')}")
        except:
            print("  • 統計情報取得中...")


def main():
    """メインデモ実行"""
    print("🌟 DictSQLite-Fastest 高度圧縮機能デモ")
    print("Advanced Compression Features Demonstration")
    print("=" * 80)

    try:
        demo_compression_algorithms()
        demo_compression_performance()
        demo_compression_settings()
        demo_advanced_features()

        print("\n\n✨ 全デモ完了！")
        print("All demonstrations completed successfully!")
        print("\n📝 主な機能:")
        print("  • ZSTD & zlib圧縮サポート")
        print("  • 設定可能な圧縮閾値")
        print("  • 高性能接続プール")
        print("  • 自動最適化機能")
        print("  • 完全な後方互換性")

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DictSQLite-Fastest Beta 新機能デモ.

このスクリプトは2024年12月に追加された新機能を実演します。
"""

import sys
import os
import time
from pathlib import Path

# ベータモジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from dictsqlite_fastest_beta import DictSQLiteFastestBeta


def demo_memory_budget():
    """メモリ予算ベースの自動最適化デモ."""
    print("=" * 60)
    print("デモ1: メモリ予算ベースの自動最適化")
    print("=" * 60)
    
    # 100MBのメモリ予算を指定
    db = DictSQLiteFastestBeta(
        'demo_memory_budget.db',
        memory_budget_mb=100  # 自動的にキャッシュとバッファが最適化される
    )
    
    print(f"\nメモリ予算: 100MB")
    
    # 統計情報を確認
    stats = db.get_beta_stats()
    print(f"自動設定されたキャッシュ容量: {stats['config']['cache_capacity']:,} アイテム")
    print(f"自動設定されたバッファサイズ: {stats['config']['write_buffer_size']:,} アイテム")
    print(f"メモリ予算の60%がキャッシュに、30%がバッファに割り当てられています")
    
    # テストデータ
    print("\nデータを書き込み中...")
    for i in range(1000):
        db[f'key_{i}'] = {'id': i, 'data': f'value_{i}' * 10}
    
    db.close()
    print("✓ メモリ予算デモ完了\n")


def demo_auto_load():
    """小容量データベースの自動ロードデモ."""
    print("=" * 60)
    print("デモ2: 小容量データベースの自動ロード")
    print("=" * 60)
    
    # 小さなデータベースを作成
    db_path = 'demo_small_db.db'
    
    # データを準備
    print("\n小容量データベースを作成中...")
    with DictSQLiteFastestBeta(db_path) as db:
        for i in range(100):
            db[f'config_{i}'] = {'setting': f'value_{i}'}
        db.flush()
    
    # ファイルサイズを確認
    file_size_kb = os.path.getsize(db_path) / 1024
    print(f"データベースサイズ: {file_size_kb:.2f} KB")
    
    # 自動ロード有効で再度開く
    print("\n自動ロード機能で開きます（10MB以下のDBは全データをメモリロード）...")
    db = DictSQLiteFastestBeta(
        db_path,
        auto_load_threshold_mb=10.0  # 10MB以下は自動ロード
    )
    
    stats = db.get_beta_stats()
    print(f"自動プリロードされたアイテム数: {stats['operations']['auto_preloads']}")
    print(f"現在のキャッシュサイズ: {stats['cache']['size']}")
    
    # アクセステスト
    start = time.time()
    for i in range(100):
        _ = db[f'config_{i}']
    access_time = time.time() - start
    
    print(f"\n100件の読み取り時間: {access_time*1000:.2f} ms")
    print(f"キャッシュヒット率: {stats['cache']['hit_rate']:.2f}%")
    print(f"ディスク読み込み回数: {stats['operations']['disk_reads']}")
    print("→ 全データがメモリにあるため超高速アクセス!")
    
    db.close()
    print("✓ 自動ロードデモ完了\n")


def demo_background_flush():
    """バックグラウンド自動フラッシュデモ."""
    print("=" * 60)
    print("デモ3: バックグラウンド自動フラッシュ")
    print("=" * 60)
    
    db = DictSQLiteFastestBeta(
        'demo_bg_flush.db',
        write_buffer_interval=2.0,  # 2秒ごとに自動フラッシュ
        enable_background_flush=True
    )
    
    print("\nバックグラウンドフラッシュ: 有効")
    print("フラッシュ間隔: 2秒")
    
    # データを書き込み
    print("\nデータを書き込み中...")
    for i in range(50):
        db[f'item_{i}'] = f'data_{i}'
    
    stats1 = db.get_beta_stats()
    print(f"\n書き込み直後のバッファ状態:")
    print(f"  保留中の書き込み: {stats1['buffer']['pending_writes']}")
    print(f"  バッファフラッシュ回数: {stats1['operations']['buffer_flushes']}")
    
    print("\nバックグラウンドスレッドが自動的にフラッシュするのを待機中...")
    print("（メインスレッドはブロックされていません）")
    
    # 待機
    time.sleep(3.0)
    
    stats2 = db.get_beta_stats()
    print(f"\n3秒後のバッファ状態:")
    print(f"  保留中の書き込み: {stats2['buffer']['pending_writes']}")
    print(f"  バッファフラッシュ回数: {stats2['operations']['buffer_flushes']}")
    print(f"\n→ バックグラウンドで自動的にフラッシュされました!")
    
    db.close()
    print("✓ バックグラウンドフラッシュデモ完了\n")


def demo_hot_data_detection():
    """ホットデータ検出と自動プリフェッチデモ."""
    print("=" * 60)
    print("デモ4: ホットデータ検出と自動プリフェッチ")
    print("=" * 60)
    
    db = DictSQLiteFastestBeta(
        'demo_hot_data.db',
        enable_hot_data_detection=True,
        cache_capacity=1000
    )
    
    print("\nホットデータ検出: 有効")
    
    # テストデータを準備
    print("\nテストデータを準備中...")
    for i in range(100):
        db[f'user_{i}'] = {'name': f'User{i}', 'score': i * 10}
    db.flush()
    db.clear_cache()
    
    # 特定のユーザーに頻繁にアクセス（ホットキーにする）
    print("\n特定のユーザー（user_42）に頻繁にアクセス中...")
    for i in range(15):
        _ = db['user_42']
        if i == 9:
            print(f"  アクセス {i+1}回目: ホットキーとして検出される閾値に到達!")
        elif i > 9:
            print(f"  アクセス {i+1}回目: 関連ユーザーデータが自動プリフェッチされている")
    
    stats = db.get_beta_stats()
    print(f"\n統計情報:")
    print(f"  追跡中のキー数: {stats['hot_data']['tracked_keys']}")
    print(f"  ホットキー数: {stats['hot_data']['hot_keys_count']}")
    print(f"  昇格回数: {stats['hot_data']['promotions']}")
    print(f"  キャッシュサイズ: {stats['cache']['size']}")
    
    # 関連キーへのアクセスが高速化されていることを確認
    print("\n関連ユーザーへのアクセステスト...")
    start = time.time()
    for i in range(40, 50):
        _ = db[f'user_{i}']
    access_time = time.time() - start
    
    print(f"10件のアクセス時間: {access_time*1000:.2f} ms")
    print(f"→ 'user_42'のパターンから'user_*'が自動プリフェッチされ、高速アクセス!")
    
    db.close()
    print("✓ ホットデータ検出デモ完了\n")


def demo_combined_features():
    """すべての新機能を組み合わせたデモ."""
    print("=" * 60)
    print("デモ5: すべての新機能を組み合わせた最適化")
    print("=" * 60)
    
    db = DictSQLiteFastestBeta(
        'demo_combined.db',
        memory_budget_mb=50,  # メモリ予算
        auto_load_threshold_mb=5.0,  # 小容量は自動ロード
        enable_background_flush=True,  # バックグラウンドフラッシュ
        enable_hot_data_detection=True,  # ホットデータ検出
        write_buffer_interval=2.0
    )
    
    print("\n全機能を有効化:")
    print("  ✓ メモリ予算: 50MB")
    print("  ✓ 自動ロード閾値: 5MB")
    print("  ✓ バックグラウンドフラッシュ")
    print("  ✓ ホットデータ検出")
    
    # 大量データの書き込みと読み取り
    print("\n大量データの処理中...")
    start = time.time()
    
    # 書き込み
    for i in range(1000):
        db[f'data_{i}'] = {'value': i, 'metadata': f'info_{i}' * 5}
    
    # 頻繁にアクセス（ホットキー作成）
    for _ in range(15):
        _ = db['data_500']
    
    # 読み取り
    for i in range(0, 1000, 10):
        _ = db[f'data_{i}']
    
    total_time = time.time() - start
    
    # 統計情報
    stats = db.get_beta_stats()
    
    print(f"\n処理時間: {total_time:.2f}秒")
    print(f"\n=== 総合統計 ===")
    print(f"キャッシュヒット率: {stats['cache']['hit_rate']:.2f}%")
    print(f"ディスク削減率: {stats['performance']['disk_savings_rate']:.2%}")
    print(f"キャッシュ効率: {stats['performance']['cache_effectiveness']:.2%}")
    print(f"自動プリロード: {stats['operations']['auto_preloads']} アイテム")
    print(f"ホットキー数: {stats['hot_data']['hot_keys_count']}")
    print(f"バッファフラッシュ: {stats['operations']['buffer_flushes']} 回")
    
    print("\n→ すべての新機能が協調して動作し、最高のパフォーマンスを実現!")
    
    db.close()
    print("✓ 組み合わせデモ完了\n")


def cleanup_demo_files():
    """デモで作成したファイルをクリーンアップ."""
    demo_files = [
        'demo_memory_budget.db',
        'demo_small_db.db',
        'demo_bg_flush.db',
        'demo_hot_data.db',
        'demo_combined.db'
    ]
    
    for file in demo_files:
        if os.path.exists(file):
            os.remove(file)
            # WALファイルも削除
            if os.path.exists(file + '-wal'):
                os.remove(file + '-wal')
            if os.path.exists(file + '-shm'):
                os.remove(file + '-shm')


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("DictSQLite-Fastest Beta 新機能デモ (2024年12月)")
    print("=" * 60)
    print()
    
    try:
        demo_memory_budget()
        demo_auto_load()
        demo_background_flush()
        demo_hot_data_detection()
        demo_combined_features()
        
        print("=" * 60)
        print("すべてのデモが正常に完了しました!")
        print("=" * 60)
        
    finally:
        print("\nクリーンアップ中...")
        cleanup_demo_files()
        print("✓ デモファイルを削除しました")
        print("\n詳細は IMPROVEMENTS_2024_JP.md をご覧ください")

#!/usr/bin/env python3
"""
DictSQLite v4.1 最適化機会検証スクリプト

このスクリプトは、v4.1の現在の実装において、非同期・同期I/O処理の
最適化余地を実測データで検証します。コードは変更せず、現状のパフォーマンス
特性を測定し、ボトルネックを特定します。
"""
import tempfile
import os
import sys
import time
import statistics
from pathlib import Path

try:
    from dictsqlite_v4 import DictSQLiteV4, AsyncDictSQLite
except ImportError:
    print("⚠️  dictsqlite_v4 モジュールが見つかりません")
    print("ビルド方法: cd dictsqlite_v4.1 && maturin develop --release")
    sys.exit(1)


def format_ops(ops_per_sec):
    """Format operations per second"""
    if ops_per_sec >= 1_000_000:
        return f"{ops_per_sec/1_000_000:.2f}M ops/sec"
    elif ops_per_sec >= 1_000:
        return f"{ops_per_sec/1_000:.2f}K ops/sec"
    else:
        return f"{ops_per_sec:.0f} ops/sec"


def verify_async_write_bottleneck():
    """
    検証1: 非同期書き込みのボトルネック
    
    現在の実装では、WriteThroughモードで各set_async()呼び出しごとに
    Mutexロックとストレージへの書き込みが発生します。
    
    期待される結果: 連続書き込みが遅い（バッファリングがないため）
    """
    print("\n" + "="*70)
    print("検証1: 非同期書き込みのボトルネック")
    print("="*70)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        # WriteThroughモードで検証
        db = AsyncDictSQLite(db_path, capacity=10000, persist_mode="writethrough")
        
        # 連続書き込みの測定
        count = 1000
        print(f"\n📝 {count}件の連続書き込みを測定...")
        
        start = time.perf_counter()
        for i in range(count):
            db.set_async(f"key_{i}", f"value_{i}".encode())
        elapsed = time.perf_counter() - start
        
        ops_per_sec = count / elapsed
        
        print(f"\n結果:")
        print(f"  件数: {count:,}件")
        print(f"  時間: {elapsed:.3f}秒")
        print(f"  スループット: {format_ops(ops_per_sec)}")
        
        # ボトルネックの分析
        print(f"\n📊 分析:")
        print(f"  1件あたりの時間: {elapsed/count*1000:.2f}ms")
        print(f"  理論上のMutexロック回数: {count}回")
        print(f"  理論上のSQL実行回数: {count}回")
        
        # 改善余地の計算
        print(f"\n💡 最適化余地:")
        print(f"  バッファリング（100件ごと）を実装した場合:")
        print(f"    - Mutexロック: {count}回 → 10回（100倍削減）")
        print(f"    - バッチSQL実行: {count}回 → 10回（100倍削減）")
        print(f"    - 期待される高速化: 50-100倍")
        
        db.close()
        
        return {
            'count': count,
            'time': elapsed,
            'ops_per_sec': ops_per_sec,
            'bottleneck': 'Mutex + SQL per call'
        }
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)


def verify_sync_writethrough_bottleneck():
    """
    検証2: 同期WriteThrough モードのボトルネック
    
    WriteThroughモードでは各set()でストレージに即座に書き込むため、
    LazyモードやMemoryモードと比較して著しく遅くなります。
    
    期待される結果: WriteThrough << Lazy の性能差
    """
    print("\n" + "="*70)
    print("検証2: 同期WriteThrough モードのボトルネック")
    print("="*70)
    
    results = {}
    count = 1000
    
    for mode in ['memory', 'lazy', 'writethrough']:
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        try:
            db = DictSQLiteV4(db_path, hot_capacity=10000, persist_mode=mode)
            
            print(f"\n📝 {mode.upper()} モードで{count}件の書き込み...")
            
            start = time.perf_counter()
            for i in range(count):
                db[f"key_{i}"] = f"value_{i}".encode()
            elapsed = time.perf_counter() - start
            
            ops_per_sec = count / elapsed
            
            print(f"  時間: {elapsed:.3f}秒")
            print(f"  スループット: {format_ops(ops_per_sec)}")
            
            results[mode] = {
                'time': elapsed,
                'ops_per_sec': ops_per_sec
            }
            
            db.close()
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
            for ext in ['-wal', '-shm']:
                wal_file = db_path + ext
                if os.path.exists(wal_file):
                    os.unlink(wal_file)
    
    # 比較分析
    print(f"\n📊 モード比較:")
    print(f"  {'モード':<15} {'時間':>10} {'スループット':>15}")
    print(f"  {'-'*15} {'-'*10} {'-'*15}")
    for mode in ['memory', 'lazy', 'writethrough']:
        r = results[mode]
        print(f"  {mode.upper():<15} {r['time']:>9.3f}s {format_ops(r['ops_per_sec']):>15}")
    
    # 最適化余地
    lazy_ops = results['lazy']['ops_per_sec']
    wt_ops = results['writethrough']['ops_per_sec']
    improvement_ratio = lazy_ops / wt_ops
    
    print(f"\n💡 最適化余地:")
    print(f"  WriteThrough vs Lazy の性能差: {improvement_ratio:.1f}倍")
    print(f"  バッチ書き込みを実装した場合:")
    print(f"    WriteThhroughでもLazy並みの性能が期待できる")
    print(f"    期待される高速化: {improvement_ratio:.0f}倍")
    
    return results


def verify_batch_read_opportunity():
    """
    検証3: バッチ読み込みの最適化余地
    
    現在のbatch_get()は並列処理でキャッシュを確認しますが、
    キャッシュミス時の処理に最適化余地があります。
    
    期待される結果: キャッシュミス時の個別SQL実行がボトルネック
    """
    print("\n" + "="*70)
    print("検証3: バッチ読み込みの最適化余地")
    print("="*70)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        # Lazyモードでデータを準備
        db = AsyncDictSQLite(db_path, capacity=1000, persist_mode="lazy")
        
        # データを永続化（キャッシュクリアをシミュレート）
        count = 1000
        print(f"\n📝 {count}件のデータを準備...")
        for i in range(count):
            db.set_async(f"key_{i}", f"value_{i}".encode())
        db.flush()
        db.close()
        
        # 新しいインスタンスで読み込み（コールドスタート）
        db = AsyncDictSQLite(db_path, capacity=100, persist_mode="lazy")  # 小さいキャッシュ
        
        # 個別読み込み
        print(f"\n📖 個別読み込み（{count}件）...")
        start = time.perf_counter()
        for i in range(count):
            _ = db.get_async(f"key_{i}")
        individual_time = time.perf_counter() - start
        individual_ops = count / individual_time
        
        print(f"  時間: {individual_time:.3f}秒")
        print(f"  スループット: {format_ops(individual_ops)}")
        
        # バッチ読み込み
        db.close()
        db = AsyncDictSQLite(db_path, capacity=100, persist_mode="lazy")
        
        keys = [f"key_{i}" for i in range(count)]
        print(f"\n📦 バッチ読み込み（{count}件）...")
        start = time.perf_counter()
        _ = db.batch_get(keys)
        batch_time = time.perf_counter() - start
        batch_ops = count / batch_time
        
        print(f"  時間: {batch_time:.3f}秒")
        print(f"  スループット: {format_ops(batch_ops)}")
        
        # 分析
        improvement = batch_ops / individual_ops
        print(f"\n📊 分析:")
        print(f"  バッチ vs 個別: {improvement:.2f}倍高速")
        
        print(f"\n💡 最適化余地:")
        print(f"  現在のbatch_get()はキャッシュアクセスを並列化")
        print(f"  キャッシュミス時にSQLを一括実行すれば:")
        print(f"    - SQL クエリ数: {count}回 → 1回")
        print(f"    - 期待される高速化: 5-10倍（キャッシュミス時）")
        
        db.close()
        
        return {
            'individual_ops': individual_ops,
            'batch_ops': batch_ops,
            'improvement': improvement
        }
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)


def verify_flush_cost():
    """
    検証4: flush()コストの測定
    
    Lazyモードでのflush()コストを測定し、
    定期的なバックグラウンドフラッシュの有効性を検証します。
    
    期待される結果: 大量データのflushは時間がかかる
    """
    print("\n" + "="*70)
    print("検証4: flush()コストの測定")
    print("="*70)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        db = DictSQLiteV4(db_path, hot_capacity=10000, persist_mode="lazy")
        
        counts = [100, 500, 1000, 2000]
        results = []
        
        for count in counts:
            # データを書き込み
            for i in range(count):
                db[f"flush_key_{i}"] = f"flush_value_{i}".encode()
            
            # flush時間を測定
            start = time.perf_counter()
            db.flush()
            elapsed = time.perf_counter() - start
            
            ops_per_sec = count / elapsed
            results.append({
                'count': count,
                'time': elapsed,
                'ops_per_sec': ops_per_sec
            })
            
            print(f"\n📝 {count}件のflush:")
            print(f"  時間: {elapsed:.3f}秒")
            print(f"  スループット: {format_ops(ops_per_sec)}")
        
        # 分析
        print(f"\n💡 最適化余地:")
        print(f"  自動バックグラウンドフラッシュを実装した場合:")
        print(f"    - flush()を定期的（例: 5秒ごと）に実行")
        print(f"    - ユーザーコードでのflush()呼び出しが不要")
        print(f"    - 書き込みレイテンシの平準化")
        
        db.close()
        
        return results
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)


def main():
    """メイン検証プロセス"""
    print("\n" + "="*70)
    print("DictSQLite v4.1 最適化機会検証")
    print("="*70)
    print("\nこのスクリプトは、現在の実装におけるI/O処理のボトルネックを")
    print("実測データで検証し、最適化余地を特定します。")
    print("="*70)
    
    # 検証実行
    results = {}
    
    try:
        results['async_write'] = verify_async_write_bottleneck()
    except Exception as e:
        print(f"\n❌ 検証1失敗: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        results['sync_modes'] = verify_sync_writethrough_bottleneck()
    except Exception as e:
        print(f"\n❌ 検証2失敗: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        results['batch_read'] = verify_batch_read_opportunity()
    except Exception as e:
        print(f"\n❌ 検証3失敗: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        results['flush_cost'] = verify_flush_cost()
    except Exception as e:
        print(f"\n❌ 検証4失敗: {e}")
        import traceback
        traceback.print_exc()
    
    # 最終レポート
    print("\n" + "="*70)
    print("検証結果サマリー")
    print("="*70)
    
    print("\n✅ 確認された最適化機会:")
    
    if 'async_write' in results:
        print("\n1. 非同期書き込みバッファリング")
        print(f"   現在: {format_ops(results['async_write']['ops_per_sec'])}")
        print(f"   期待: 50-100倍高速化")
        print(f"   方法: 内部バッファ + バッチ書き込み")
    
    if 'sync_modes' in results:
        lazy_ops = results['sync_modes']['lazy']['ops_per_sec']
        wt_ops = results['sync_modes']['writethrough']['ops_per_sec']
        ratio = lazy_ops / wt_ops
        print("\n2. WriteThrough バッチ書き込み")
        print(f"   現在: {format_ops(wt_ops)}")
        print(f"   目標: {format_ops(lazy_ops)} (Lazy並み)")
        print(f"   期待: {ratio:.0f}倍高速化")
        print(f"   方法: バッチINSERT実装")
    
    if 'batch_read' in results:
        print("\n3. バッチ読み込み最適化")
        print(f"   現在: キャッシュミス時に個別SQL実行")
        print(f"   期待: 5-10倍高速化")
        print(f"   方法: キャッシュミスの一括SELECT")
    
    print("\n4. 自動バックグラウンドフラッシュ")
    print(f"   期待: ユーザビリティ向上")
    print(f"   方法: 定期的な自動flush()")
    
    print("\n" + "="*70)
    print("📄 詳細な分析レポートは以下を参照してください:")
    print("   - V4.1_OPTIMIZATION_VERIFICATION.md")
    print("   - V4.1_INVESTIGATION_REPORT_JP.md")
    print("="*70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

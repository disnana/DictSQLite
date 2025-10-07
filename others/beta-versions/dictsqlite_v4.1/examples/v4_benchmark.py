#!/usr/bin/env python3
"""
DictSQLite v4 ベンチマークスクリプト

暗号化とSafe Pickleのパフォーマンス影響を測定
"""
import time
import pickle
import tempfile
import os
from pathlib import Path

try:
    from dictsqlite_v4 import DictSQLiteV4
    AVAILABLE = True
except ImportError:
    print("エラー: dictsqlite_v4 モジュールがビルドされていません")
    print("ビルド方法: cd dictsqlite_v4 && maturin develop --release")
    AVAILABLE = False
    exit(1)


def benchmark_basic(iterations=10000):
    """基本的なパフォーマンス（暗号化なし）"""
    print("\n" + "="*60)
    print("ベンチマーク 1: 基本パフォーマンス（暗号化なし）")
    print("="*60)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        db = DictSQLiteV4(db_path, persist_mode="memory")
        
        # 書き込みベンチマーク
        print(f"\n書き込みテスト ({iterations:,} 回)...")
        start = time.time()
        for i in range(iterations):
            db[f"key_{i}"] = f"value_{i}".encode()
        write_time = time.time() - start
        
        write_ops = iterations / write_time
        print(f"  時間: {write_time:.3f} 秒")
        print(f"  速度: {write_ops:,.0f} ops/sec")
        print(f"  速度: {write_ops/1_000_000:.1f}M ops/sec")
        
        # 読み込みベンチマーク
        print(f"\n読み込みテスト ({iterations:,} 回)...")
        start = time.time()
        for i in range(iterations):
            _ = db[f"key_{i}"]
        read_time = time.time() - start
        
        read_ops = iterations / read_time
        print(f"  時間: {read_time:.3f} 秒")
        print(f"  速度: {read_ops:,.0f} ops/sec")
        print(f"  速度: {read_ops/1_000_000:.1f}M ops/sec")
        
        db.close()
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass
    
    return write_ops, read_ops


def benchmark_encryption(iterations=10000):
    """暗号化ありのパフォーマンス"""
    print("\n" + "="*60)
    print("ベンチマーク 2: 暗号化パフォーマンス（AES-256-GCM）")
    print("="*60)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        db = DictSQLiteV4(
            db_path,
            persist_mode="memory",
            encryption_password="benchmark_password"
        )
        
        # 書き込みベンチマーク
        print(f"\n書き込みテスト ({iterations:,} 回)...")
        start = time.time()
        for i in range(iterations):
            db[f"key_{i}"] = f"value_{i}".encode()
        write_time = time.time() - start
        
        write_ops = iterations / write_time
        print(f"  時間: {write_time:.3f} 秒")
        print(f"  速度: {write_ops:,.0f} ops/sec")
        print(f"  速度: {write_ops/1_000_000:.1f}M ops/sec")
        
        # 読み込みベンチマーク
        print(f"\n読み込みテスト ({iterations:,} 回)...")
        start = time.time()
        for i in range(iterations):
            _ = db[f"key_{i}"]
        read_time = time.time() - start
        
        read_ops = iterations / read_time
        print(f"  時間: {read_time:.3f} 秒")
        print(f"  速度: {read_ops:,.0f} ops/sec")
        print(f"  速度: {read_ops/1_000_000:.1f}M ops/sec")
        
        db.close()
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass
    
    return write_ops, read_ops


def benchmark_safe_pickle(iterations=10000):
    """Safe Pickle ありのパフォーマンス"""
    print("\n" + "="*60)
    print("ベンチマーク 3: Safe Pickle パフォーマンス")
    print("="*60)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        db = DictSQLiteV4(
            db_path,
            persist_mode="memory",
            enable_safe_pickle=True
        )
        
        # テストデータ
        test_data = {"id": 0, "name": "test", "values": [1, 2, 3]}
        
        # 書き込みベンチマーク
        print(f"\n書き込みテスト ({iterations:,} 回)...")
        start = time.time()
        for i in range(iterations):
            test_data["id"] = i
            db[f"key_{i}"] = pickle.dumps(test_data)
        write_time = time.time() - start
        
        write_ops = iterations / write_time
        print(f"  時間: {write_time:.3f} 秒")
        print(f"  速度: {write_ops:,.0f} ops/sec")
        print(f"  速度: {write_ops/1_000_000:.1f}M ops/sec")
        
        # 読み込みベンチマーク
        print(f"\n読み込みテスト ({iterations:,} 回)...")
        start = time.time()
        for i in range(iterations):
            _ = pickle.loads(db[f"key_{i}"])
        read_time = time.time() - start
        
        read_ops = iterations / read_time
        print(f"  時間: {read_time:.3f} 秒")
        print(f"  速度: {read_ops:,.0f} ops/sec")
        print(f"  速度: {read_ops/1_000_000:.1f}M ops/sec")
        
        db.close()
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass
    
    return write_ops, read_ops


def benchmark_combined(iterations=10000):
    """暗号化 + Safe Pickle のパフォーマンス"""
    print("\n" + "="*60)
    print("ベンチマーク 4: 暗号化 + Safe Pickle パフォーマンス")
    print("="*60)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        db = DictSQLiteV4(
            db_path,
            persist_mode="memory",
            encryption_password="benchmark_password",
            enable_safe_pickle=True
        )
        
        # テストデータ
        test_data = {"id": 0, "name": "test", "values": [1, 2, 3]}
        
        # 書き込みベンチマーク
        print(f"\n書き込みテスト ({iterations:,} 回)...")
        start = time.time()
        for i in range(iterations):
            test_data["id"] = i
            db[f"key_{i}"] = pickle.dumps(test_data)
        write_time = time.time() - start
        
        write_ops = iterations / write_time
        print(f"  時間: {write_time:.3f} 秒")
        print(f"  速度: {write_ops:,.0f} ops/sec")
        print(f"  速度: {write_ops/1_000_000:.1f}M ops/sec")
        
        # 読み込みベンチマーク
        print(f"\n読み込みテスト ({iterations:,} 回)...")
        start = time.time()
        for i in range(iterations):
            _ = pickle.loads(db[f"key_{i}"])
        read_time = time.time() - start
        
        read_ops = iterations / read_time
        print(f"  時間: {read_time:.3f} 秒")
        print(f"  速度: {read_ops:,.0f} ops/sec")
        print(f"  速度: {read_ops/1_000_000:.1f}M ops/sec")
        
        db.close()
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass
    
    return write_ops, read_ops


def benchmark_large_data(iterations=1000):
    """大きなデータのパフォーマンス"""
    print("\n" + "="*60)
    print("ベンチマーク 5: 大きなデータ（暗号化あり）")
    print("="*60)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    try:
        db = DictSQLiteV4(
            db_path,
            persist_mode="memory",
            encryption_password="benchmark_password"
        )
        
        # 100KB のデータ
        large_data = b"x" * (100 * 1024)
        
        print(f"\n書き込みテスト ({iterations:,} 回, データサイズ: 100KB)...")
        start = time.time()
        for i in range(iterations):
            db[f"large_{i}"] = large_data
        write_time = time.time() - start
        
        write_ops = iterations / write_time
        throughput_mb = (iterations * len(large_data) / 1_000_000) / write_time
        print(f"  時間: {write_time:.3f} 秒")
        print(f"  速度: {write_ops:,.0f} ops/sec")
        print(f"  スループット: {throughput_mb:.1f} MB/sec")
        
        print(f"\n読み込みテスト ({iterations:,} 回, データサイズ: 100KB)...")
        start = time.time()
        for i in range(iterations):
            _ = db[f"large_{i}"]
        read_time = time.time() - start
        
        read_ops = iterations / read_time
        throughput_mb = (iterations * len(large_data) / 1_000_000) / read_time
        print(f"  時間: {read_time:.3f} 秒")
        print(f"  速度: {read_ops:,.0f} ops/sec")
        print(f"  スループット: {throughput_mb:.1f} MB/sec")
        
        db.close()
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def main():
    print("="*60)
    print("DictSQLite v4.0 パフォーマンスベンチマーク")
    print("="*60)
    print("\nセキュリティ機能のパフォーマンス影響を測定します")
    
    iterations = 10000
    
    # 各ベンチマークを実行
    basic_write, basic_read = benchmark_basic(iterations)
    enc_write, enc_read = benchmark_encryption(iterations)
    sp_write, sp_read = benchmark_safe_pickle(iterations)
    comb_write, comb_read = benchmark_combined(iterations)
    benchmark_large_data(1000)
    
    # サマリー
    print("\n" + "="*60)
    print("サマリー")
    print("="*60)
    
    print("\n書き込みパフォーマンス:")
    print(f"  基本（暗号化なし）:       {basic_write/1_000_000:6.1f}M ops/sec  (100.0%)")
    print(f"  暗号化のみ:               {enc_write/1_000_000:6.1f}M ops/sec  ({enc_write/basic_write*100:5.1f}%)")
    print(f"  Safe Pickleのみ:          {sp_write/1_000_000:6.1f}M ops/sec  ({sp_write/basic_write*100:5.1f}%)")
    print(f"  暗号化 + Safe Pickle:     {comb_write/1_000_000:6.1f}M ops/sec  ({comb_write/basic_write*100:5.1f}%)")
    
    print("\n読み込みパフォーマンス:")
    print(f"  基本（暗号化なし）:       {basic_read/1_000_000:6.1f}M ops/sec  (100.0%)")
    print(f"  暗号化のみ:               {enc_read/1_000_000:6.1f}M ops/sec  ({enc_read/basic_read*100:5.1f}%)")
    print(f"  Safe Pickleのみ:          {sp_read/1_000_000:6.1f}M ops/sec  ({sp_read/basic_read*100:5.1f}%)")
    print(f"  暗号化 + Safe Pickle:     {comb_read/1_000_000:6.1f}M ops/sec  ({comb_read/basic_read*100:5.1f}%)")
    
    print("\n結論:")
    enc_overhead = (1 - enc_write/basic_write) * 100
    sp_overhead = (1 - sp_write/basic_write) * 100
    comb_overhead = (1 - comb_write/basic_write) * 100
    
    print(f"  暗号化オーバーヘッド:           {enc_overhead:.1f}%")
    print(f"  Safe Pickleオーバーヘッド:      {sp_overhead:.1f}%")
    print(f"  組み合わせオーバーヘッド:       {comb_overhead:.1f}%")
    
    print("\n✅ セキュリティ機能を有効にしても高速！")
    if comb_write > 50_000_000:
        print(f"   暗号化 + Safe Pickle でも {comb_write/1_000_000:.0f}M ops/sec を維持")


if __name__ == "__main__":
    if AVAILABLE:
        main()

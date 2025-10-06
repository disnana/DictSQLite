#!/usr/bin/env python
"""Automatic profiling script for DictSQLite-v2.0

This script profiles the current implementation to identify bottlenecks
and optimization opportunities following the ReAct autonomous cycle.
"""

import cProfile
import pstats
import io
import sys
import os
import tempfile
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'beta'))

from dictsqlite_v2.core import DictSQLiteV2


def profile_write_operations(num_items=1000):
    """Profile write operations"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db = DictSQLiteV2(db_path, write_buffer_size=1)
        
        # Individual writes
        for i in range(num_items):
            db[f'key_{i}'] = f'value_{i}_' + 'x' * 50
        
        db.close()
    finally:
        for ext in ['', '-wal', '-shm']:
            try:
                os.unlink(db_path + ext)
            except:
                pass


def profile_read_operations(num_items=1000):
    """Profile read operations"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Setup data
        db = DictSQLiteV2(db_path, write_buffer_size=1)
        for i in range(num_items):
            db[f'key_{i}'] = f'value_{i}_' + 'x' * 50
        db.close()
        
        # Profile reads
        db = DictSQLiteV2(db_path)
        for i in range(num_items):
            _ = db[f'key_{i}']
        db.close()
    finally:
        for ext in ['', '-wal', '-shm']:
            try:
                os.unlink(db_path + ext)
            except:
                pass


def profile_bulk_operations(num_items=1000):
    """Profile bulk operations"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db = DictSQLiteV2(db_path, write_buffer_size=1)
        
        # Bulk write
        data = {f'key_{i}': f'value_{i}' for i in range(num_items)}
        db.bulk_insert(data)
        
        db.close()
    finally:
        for ext in ['', '-wal', '-shm']:
            try:
                os.unlink(db_path + ext)
            except:
                pass


def run_profiling():
    """Run profiling on all operations"""
    print("=" * 80)
    print("DictSQLite-v2.0 Profiling Analysis")
    print("=" * 80)
    
    operations = [
        ('Write Operations', profile_write_operations),
        ('Read Operations', profile_read_operations),
        ('Bulk Operations', profile_bulk_operations),
    ]
    
    all_stats = []
    
    for op_name, op_func in operations:
        print(f"\n{'='*80}")
        print(f"Profiling: {op_name}")
        print(f"{'='*80}")
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        op_func(num_items=500)  # Smaller for profiling
        
        profiler.disable()
        
        # Capture stats
        s = io.StringIO()
        stats = pstats.Stats(profiler, stream=s)
        stats.strip_dirs()
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # Top 20 functions
        
        output = s.getvalue()
        print(output)
        all_stats.append((op_name, output))
    
    # Save profiling results
    reports_dir = Path(__file__).parent / 'reports'
    profiling_file = reports_dir / 'profiling_results.txt'
    
    with open(profiling_file, 'w') as f:
        f.write("DictSQLite-v2.0 Profiling Results\n")
        f.write("=" * 80 + "\n\n")
        
        for op_name, output in all_stats:
            f.write(f"\n{'='*80}\n")
            f.write(f"{op_name}\n")
            f.write(f"{'='*80}\n")
            f.write(output)
            f.write("\n")
    
    print(f"\n{'='*80}")
    print(f"✅ Profiling results saved to: {profiling_file}")
    print(f"{'='*80}")
    
    return str(profiling_file)


if __name__ == '__main__':
    profiling_file = run_profiling()
    print(f"\nProfiled successfully: {profiling_file}")

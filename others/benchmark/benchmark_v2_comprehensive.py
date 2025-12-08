"""
DictSQLite 全バージョン統合ベンチマーク

3つの主要バージョンを比較し、統一スコアでランキングします:
1. dictsqlite (Original版) - 標準sqlite3ベース
2. dictsqlite_v2 (Rust拡張版) - 全モード (memory/lazy/writethrough, pickle/bytes)
3. dictsqlite-fastest beta v2 - APSWベース高性能版

テスト項目:
- GET: 単一キー取得
- SET: 単一キー設定
- BATCH_GET: 複数キー一括取得
- BATCH_SET: 複数キー一括設定
- DELETE: キー削除
- KEYS: 全キー取得

スコアリング:
- 各テストで ops/sec を計測
- 全バージョン共通で正規化 (0-100)
- 総合スコアでランキング

出力:
- benchmark_all_versions.csv - 詳細結果
- benchmark_scores.csv - スコアサマリー
- images/*.png - グラフ
"""

import time
import csv
import os
import sys
import gc
from dataclasses import dataclass
from typing import List, Dict, Optional
import statistics
from datetime import datetime

# 結果ディレクトリ
RESULTS_DIR = "results/v2_comprehensive"
IMAGES_DIR = f"{RESULTS_DIR}/images"

# テスト設定
ITERATIONS_FAST = 500
ITERATIONS_BATCH = 50
WARMUP = 100
DATA_SIZES = [100, 1000, 5000]


@dataclass
class TestResult:
    """テスト結果"""
    version: str  # Original, V2, Fastest
    category: str  # DictSQLite, AsyncDictSQLite, etc.
    test_name: str  # set, get, batch_set, etc.
    mode: str  # memory, lazy, writethrough, default
    storage: str  # pickle, bytes, json, default
    is_async: bool
    iterations: int
    data_size: int
    ops_per_sec: float
    avg_time_ms: float
    score: float = 0.0


def benchmark_op(func, iterations: int = 500, warmup: int = 100) -> Dict:
    """操作のベンチマーク"""
    for _ in range(warmup):
        try:
            func()
        except:
            pass
    gc.collect()
    
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        times.append((time.perf_counter() - start) * 1000)
    
    total = sum(times)
    return {
        "ops_per_sec": iterations / (total / 1000) if total > 0 else 0,
        "avg_ms": total / iterations if iterations > 0 else 0,
    }


def test_original_dictsqlite() -> List[TestResult]:
    """Original版 (dictsqlite/) のテスト"""
    results = []
    print("\n" + "=" * 60)
    print("📦 Original DictSQLite (sqlite3ベース)")
    print("=" * 60)
    
    # Original版はリポジトリルートのdictsqlite/フォルダにある
    # sys.pathに追加してインポート
    import importlib
    import importlib.util
    
    # リポジトリルートを探す（others/benchmarkから2つ上）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(script_dir))
    original_path = os.path.join(repo_root, "dictsqlite")
    
    try:
        if os.path.exists(original_path):
            # Temporarily add repo_root to sys.path for import
            sys.path.insert(0, repo_root)
            print(f"  📂 Original path: {original_path}")
        
        from dictsqlite.main import DictSQLite as OriginalDictSQLite
        print("  ✅ Original DictSQLite インポート成功")
    except ImportError as e:
        print(f"  ⚠️ Original版がインポートできません: {e}")
        return results
    finally:
        # IMPORTANT: Clean up sys.path and sys.modules to prevent shadowing V2 wheel
        # V2 wheel installs as 'dictsqlite' package, and we need to ensure
        # subsequent imports get the wheel version, not the original from repo
        if repo_root in sys.path:
            sys.path.remove(repo_root)
            print("  🧹 Cleaned up sys.path to prevent shadowing V2 wheel")
        
        # Also clear the 'dictsqlite' package from sys.modules so V2 can import fresh
        # We keep references to specific imports (OriginalDictSQLite), but clear the package cache
        # This ensures that when V2 tries to import 'dictsqlite', it gets the wheel version
        # Use list() to avoid RuntimeError if sys.modules is modified during iteration
        modules_to_clear = [key for key in list(sys.modules.keys()) if key == 'dictsqlite' or key.startswith('dictsqlite.')]
        for mod in modules_to_clear:
            if mod in sys.modules:  # Double-check as another thread might have removed it
                del sys.modules[mod]
                print(f"  🧹 Cleared {mod} from sys.modules")
    
    try:
        db_path = "/tmp/bench_original.db"
        db = OriginalDictSQLite(db_path)
        
        for size in DATA_SIZES:
            value = "x" * size  # Original版は文字列
            
            # SET
            key_counter = [0]
            def set_op():
                key_counter[0] += 1
                db[f"key_{key_counter[0]}"] = value
            
            print(f"  [SET] size={size}...", end=" ")
            res = benchmark_op(set_op, ITERATIONS_FAST)
            print(f"{res['ops_per_sec']:.0f} ops/s")
            results.append(TestResult(
                version="Original", category="DictSQLite", test_name="set",
                mode="default", storage="pickle", is_async=False,
                iterations=ITERATIONS_FAST, data_size=size,
                ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
            ))
            
            # GET
            db["bench_key"] = value
            print(f"  [GET] size={size}...", end=" ")
            res = benchmark_op(lambda: db["bench_key"], ITERATIONS_FAST)
            print(f"{res['ops_per_sec']:.0f} ops/s")
            results.append(TestResult(
                version="Original", category="DictSQLite", test_name="get",
                mode="default", storage="pickle", is_async=False,
                iterations=ITERATIONS_FAST, data_size=size,
                ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
            ))
        
        # KEYS
        print(f"  [KEYS]...", end=" ")
        res = benchmark_op(lambda: db.keys(), ITERATIONS_FAST)
        print(f"{res['ops_per_sec']:.0f} ops/s")
        results.append(TestResult(
            version="Original", category="DictSQLite", test_name="keys",
            mode="default", storage="pickle", is_async=False,
            iterations=ITERATIONS_FAST, data_size=0,
            ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
        ))
        
    except Exception as e:
        print(f"  ❌ エラー: {e}")
    
    return results


def test_dictsqlite_v2() -> List[TestResult]:
    """dictsqlite_v2 (Rust拡張版) の全モードテスト"""
    results = []
    print("\n" + "=" * 60)
    print("🦀 DictSQLite V2 (Rust拡張)")
    print("=" * 60)
    
    # V2はRust拡張で、DictSQLiteとAsyncDictSQLiteをエクスポート
    DictSQLiteV2 = None
    AsyncDictSQLiteV2 = None
    
    # CRITICAL FIX for issue #223:
    # Ensure we import the V2 wheel from site-packages, NOT the original dictsqlite/ folder
    # from the repository. We need to temporarily remove repo paths from sys.path.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(script_dir))
    
    # Save original sys.path
    original_sys_path = sys.path.copy()
    import_successful = False
    
    try:
        # Remove any paths that could lead to the original dictsqlite folder
        paths_to_remove = {repo_root}
        
        # Also check for paths that might contain the original dictsqlite
        # Only check paths that could realistically be repository paths (not system paths)
        for path in sys.path[:]:
            # Skip if path is clearly a system path
            if 'site-packages' in path or 'dist-packages' in path:
                continue
            # Check if this path contains original dictsqlite (has main.py)
            dictsqlite_init = os.path.join(path, 'dictsqlite', '__init__.py')
            dictsqlite_main = os.path.join(path, 'dictsqlite', 'main.py')
            if os.path.exists(dictsqlite_init) and os.path.exists(dictsqlite_main):
                paths_to_remove.add(path)
        
        # Filter sys.path to remove problematic paths
        sys.path[:] = [p for p in sys.path if p not in paths_to_remove]
        if paths_to_remove:
            print(f"  🧹 Removed {len(paths_to_remove)} path(s) from sys.path to prevent shadowing")
        
        # Import dictsqlite package (should now come from wheel in site-packages)
        from dictsqlite import DictSQLite as DictSQLiteV2
        from dictsqlite import AsyncDictSQLite as AsyncDictSQLiteV2
        print("  ✅ dictsqlite からインポート成功")
        
        # Verify we imported the correct version by checking the already-imported module
        # Use the reference from sys.modules to avoid re-importing
        dictsqlite_module = sys.modules.get('dictsqlite')
        if dictsqlite_module:
            module_file = getattr(dictsqlite_module, '__file__', None)
            if module_file:
                print(f"  📂 Imported from: {module_file}")
                # Check if it's from site-packages (wheel) or from repo (wrong!)
                if 'site-packages' in module_file or 'dist-packages' in module_file:
                    print("  ✅ Correctly imported from installed wheel")
                    import_successful = True
                elif repo_root in module_file:
                    print(f"  ❌ ERROR: Imported from repository folder, not wheel!")
                    print(f"  ❌ This is the original dictsqlite, not V2. Skipping V2 tests.")
                    return results
        
        # DictSQLiteV4 があるか確認（これがV2の証拠）
        try:
            from dictsqlite import DictSQLiteV4
            print("  ✅ DictSQLiteV4 確認 (V2 Rust拡張)")
        except ImportError:
            print("  ⚠️ DictSQLiteV4 なし (Originalかも？)")
            # Original版の可能性がある場合はスキップ
            if not hasattr(DictSQLiteV2, 'batch_set'):
                print("  ⚠️ batch_set なし - これはOriginal版です。V2スキップ。")
                return results
    
    except ImportError as e:
        print(f"  ⚠️ dictsqlite インポートエラー: {e}")
        return results
    
    finally:
        # Restore original sys.path
        sys.path[:] = original_sys_path
        if import_successful:
            print("  🔄 Restored original sys.path (import successful)")
        else:
            print("  🔄 Restored original sys.path")
    
    persist_modes = ["memory", "lazy", "writethrough"]
    storage_modes = ["pickle", "bytes"]
    
    for persist in persist_modes:
        for storage in storage_modes:
            print(f"\n  ### {persist} / {storage} ###")
            
            try:
                db_path = f"/tmp/bench_v2_{persist}_{storage}.db"
                db = DictSQLiteV2(db_path, persist_mode=persist, storage_mode=storage)
                
                for size in DATA_SIZES:
                    value = b"x" * size
                    
                    # SYNC SET
                    key_counter = [0]
                    def set_op():
                        key_counter[0] += 1
                        db[f"key_{key_counter[0]}"] = value
                    
                    print(f"    [SYNC SET] size={size}...", end=" ")
                    res = benchmark_op(set_op, ITERATIONS_FAST)
                    print(f"{res['ops_per_sec']:.0f} ops/s")
                    results.append(TestResult(
                        version="V2", category="DictSQLite", test_name="set",
                        mode=persist, storage=storage, is_async=False,
                        iterations=ITERATIONS_FAST, data_size=size,
                        ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
                    ))
                    
                    # SYNC GET
                    db["bench_key"] = value
                    print(f"    [SYNC GET] size={size}...", end=" ")
                    res = benchmark_op(lambda: db["bench_key"], ITERATIONS_FAST)
                    print(f"{res['ops_per_sec']:.0f} ops/s")
                    results.append(TestResult(
                        version="V2", category="DictSQLite", test_name="get",
                        mode=persist, storage=storage, is_async=False,
                        iterations=ITERATIONS_FAST, data_size=size,
                        ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
                    ))
                
                # BATCH
                print(f"    [BATCH_SET] 100 items...", end=" ")
                items = [(f"bkey_{i}", b"val" * 10) for i in range(100)]
                res = benchmark_op(lambda: db.batch_set(items), ITERATIONS_BATCH)
                print(f"{res['ops_per_sec']:.0f} ops/s")
                results.append(TestResult(
                    version="V2", category="DictSQLite", test_name="batch_set_100",
                    mode=persist, storage=storage, is_async=False,
                    iterations=ITERATIONS_BATCH, data_size=30,
                    ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
                ))
                
                print(f"    [BATCH_GET] 100 keys...", end=" ")
                keys = [f"bkey_{i}" for i in range(100)]
                res = benchmark_op(lambda: db.batch_get(keys), ITERATIONS_BATCH)
                print(f"{res['ops_per_sec']:.0f} ops/s")
                results.append(TestResult(
                    version="V2", category="DictSQLite", test_name="batch_get_100",
                    mode=persist, storage=storage, is_async=False,
                    iterations=ITERATIONS_BATCH, data_size=30,
                    ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
                ))
                
                # KEYS
                print(f"    [KEYS]...", end=" ")
                res = benchmark_op(lambda: db.keys(), ITERATIONS_FAST)
                print(f"{res['ops_per_sec']:.0f} ops/s")
                results.append(TestResult(
                    version="V2", category="DictSQLite", test_name="keys",
                    mode=persist, storage=storage, is_async=False,
                    iterations=ITERATIONS_FAST, data_size=0,
                    ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
                ))
                
                db.close()
                
            except Exception as e:
                print(f"    ❌ 同期エラー: {e}")
            
            # ASYNC
            try:
                async_db_path = f"/tmp/bench_v2_async_{persist}_{storage}.db"
                async_db = AsyncDictSQLiteV2(async_db_path, persist_mode=persist, storage_mode=storage)
                
                for size in DATA_SIZES:
                    value = b"x" * size
                    
                    # ASYNC SET
                    akey_counter = [0]
                    def async_set():
                        akey_counter[0] += 1
                        async_db[f"akey_{akey_counter[0]}"] = value
                    
                    print(f"    [ASYNC SET] size={size}...", end=" ")
                    res = benchmark_op(async_set, ITERATIONS_FAST)
                    print(f"{res['ops_per_sec']:.0f} ops/s")
                    results.append(TestResult(
                        version="V2", category="AsyncDictSQLite", test_name="set",
                        mode=persist, storage=storage, is_async=True,
                        iterations=ITERATIONS_FAST, data_size=size,
                        ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
                    ))
                    
                    # ASYNC GET
                    async_db["async_bench_key"] = value
                    print(f"    [ASYNC GET] size={size}...", end=" ")
                    res = benchmark_op(lambda: async_db["async_bench_key"], ITERATIONS_FAST)
                    print(f"{res['ops_per_sec']:.0f} ops/s")
                    results.append(TestResult(
                        version="V2", category="AsyncDictSQLite", test_name="get",
                        mode=persist, storage=storage, is_async=True,
                        iterations=ITERATIONS_FAST, data_size=size,
                        ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
                    ))
                
                # ASYNC BATCH
                print(f"    [ASYNC BATCH_SET]...", end=" ")
                items = [(f"abkey_{i}", b"val" * 10) for i in range(100)]
                res = benchmark_op(lambda: async_db.batch_set(items), ITERATIONS_BATCH)
                print(f"{res['ops_per_sec']:.0f} ops/s")
                results.append(TestResult(
                    version="V2", category="AsyncDictSQLite", test_name="batch_set_100",
                    mode=persist, storage=storage, is_async=True,
                    iterations=ITERATIONS_BATCH, data_size=30,
                    ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
                ))
                
                print(f"    [ASYNC BATCH_GET]...", end=" ")
                keys = [f"abkey_{i}" for i in range(100)]
                res = benchmark_op(lambda: async_db.batch_get(keys), ITERATIONS_BATCH)
                print(f"{res['ops_per_sec']:.0f} ops/s")
                results.append(TestResult(
                    version="V2", category="AsyncDictSQLite", test_name="batch_get_100",
                    mode=persist, storage=storage, is_async=True,
                    iterations=ITERATIONS_BATCH, data_size=30,
                    ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
                ))
                
                async_db.close()
                
            except Exception as e:
                print(f"    ❌ 非同期エラー: {e}")
    
    return results


def test_fastest_beta() -> List[TestResult]:
    """dictsqlite-fastest beta v2 のテスト"""
    results = []
    print("\n" + "=" * 60)
    print("⚡ DictSQLite-Fastest Beta v2 (APSWベース)")
    print("=" * 60)
    
    # Calculate absolute path to fastest beta directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(script_dir))
    fastest_beta_path = os.path.join(repo_root, "others/beta-versions/dictsqlite-fastest/beta")
    fastest_root_path = os.path.join(repo_root, "others/beta-versions/dictsqlite-fastest")
    
    # Save original sys.path
    original_sys_path = sys.path.copy()
    
    try:
        # Add fastest paths if not already in sys.path
        paths_to_add = [fastest_beta_path, fastest_root_path]
        for path in paths_to_add:
            if path not in sys.path:
                sys.path.insert(0, path)
                print(f"  📂 Added to sys.path: {path}")
        
        from dictsqlite_fastest_beta_v2 import DictSQLite as FastestDict
        print("  ✅ dictsqlite-fastest beta v2 インポート成功")
    except ImportError as e:
        print(f"  ⚠️ dictsqlite-fastest beta v2がインポートできません: {e}")
        print(f"  📂 Tried paths: {fastest_beta_path}, {fastest_root_path}")
        return results
    finally:
        # Restore original sys.path to avoid affecting other tests
        sys.path[:] = original_sys_path
    
    try:
        db_path = "/tmp/bench_fastest.db"
        db = FastestDict(db_path)
        
        for size in DATA_SIZES:
            value = b"x" * size
            
            # SET
            key_counter = [0]
            def set_op():
                key_counter[0] += 1
                db[f"key_{key_counter[0]}"] = value
            
            print(f"  [SET] size={size}...", end=" ")
            res = benchmark_op(set_op, ITERATIONS_FAST)
            print(f"{res['ops_per_sec']:.0f} ops/s")
            results.append(TestResult(
                version="Fastest", category="DictSQLite", test_name="set",
                mode="default", storage="zstd", is_async=False,
                iterations=ITERATIONS_FAST, data_size=size,
                ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
            ))
            
            # GET
            db["bench_key"] = value
            print(f"  [GET] size={size}...", end=" ")
            res = benchmark_op(lambda: db["bench_key"], ITERATIONS_FAST)
            print(f"{res['ops_per_sec']:.0f} ops/s")
            results.append(TestResult(
                version="Fastest", category="DictSQLite", test_name="get",
                mode="default", storage="zstd", is_async=False,
                iterations=ITERATIONS_FAST, data_size=size,
                ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
            ))
        
        # BATCH (if available)
        if hasattr(db, 'batch_set'):
            print(f"  [BATCH_SET] 100 items...", end=" ")
            items = [(f"bkey_{i}", b"val" * 10) for i in range(100)]
            res = benchmark_op(lambda: db.batch_set(items), ITERATIONS_BATCH)
            print(f"{res['ops_per_sec']:.0f} ops/s")
            results.append(TestResult(
                version="Fastest", category="DictSQLite", test_name="batch_set_100",
                mode="default", storage="zstd", is_async=False,
                iterations=ITERATIONS_BATCH, data_size=30,
                ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
            ))
        
        if hasattr(db, 'batch_get'):
            print(f"  [BATCH_GET] 100 keys...", end=" ")
            keys = [f"bkey_{i}" for i in range(100)]
            res = benchmark_op(lambda: db.batch_get(keys), ITERATIONS_BATCH)
            print(f"{res['ops_per_sec']:.0f} ops/s")
            results.append(TestResult(
                version="Fastest", category="DictSQLite", test_name="batch_get_100",
                mode="default", storage="zstd", is_async=False,
                iterations=ITERATIONS_BATCH, data_size=30,
                ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
            ))
        
        # KEYS
        print(f"  [KEYS]...", end=" ")
        res = benchmark_op(lambda: list(db.keys()), ITERATIONS_FAST)
        print(f"{res['ops_per_sec']:.0f} ops/s")
        results.append(TestResult(
            version="Fastest", category="DictSQLite", test_name="keys",
            mode="default", storage="zstd", is_async=False,
            iterations=ITERATIONS_FAST, data_size=0,
            ops_per_sec=res["ops_per_sec"], avg_time_ms=res["avg_ms"]
        ))
        
    except Exception as e:
        print(f"  ❌ エラー: {e}")
    
    return results


def calculate_scores(results: List[TestResult]) -> List[TestResult]:
    """全バージョン共通でスコア計算"""
    # テスト名+サイズごとに最大ops/secを取得
    max_ops = {}
    for r in results:
        key = f"{r.test_name}_{r.data_size}"
        if key not in max_ops or r.ops_per_sec > max_ops[key]:
            max_ops[key] = r.ops_per_sec
    
    # スコア計算 (0-100)
    for r in results:
        key = f"{r.test_name}_{r.data_size}"
        r.score = (r.ops_per_sec / max_ops[key]) * 100 if max_ops.get(key, 0) > 0 else 0
    
    return results


def generate_rankings(results: List[TestResult]) -> List[Dict]:
    """ランキング生成"""
    # バージョン+モード+ストレージでグループ化
    groups = {}
    for r in results:
        key = f"{r.version} {r.category} ({r.mode}/{r.storage})"
        if r.is_async:
            key += " [async]"
        if key not in groups:
            groups[key] = []
        groups[key].append(r.score)
    
    rankings = []
    for key, scores in groups.items():
        avg = sum(scores) / len(scores) if scores else 0
        rankings.append({"name": key, "avg_score": avg, "tests": len(scores)})
    
    rankings.sort(key=lambda x: x["avg_score"], reverse=True)
    for i, r in enumerate(rankings, 1):
        r["rank"] = i
    
    return rankings


def save_results(results: List[TestResult], rankings: List[Dict]):
    """結果を保存"""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    # 詳細結果
    with open(f"{RESULTS_DIR}/benchmark_all_versions.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["version", "category", "test_name", "mode", "storage", 
                        "is_async", "data_size", "ops_per_sec", "avg_ms", "score"])
        for r in results:
            writer.writerow([r.version, r.category, r.test_name, r.mode, r.storage,
                           r.is_async, r.data_size, f"{r.ops_per_sec:.1f}",
                           f"{r.avg_time_ms:.4f}", f"{r.score:.1f}"])
    
    # ランキング
    with open(f"{RESULTS_DIR}/benchmark_scores.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "name", "avg_score", "tests"])
        for r in rankings:
            writer.writerow([r["rank"], r["name"], f"{r['avg_score']:.1f}", r["tests"]])
    
    print(f"\n📊 結果を保存: {RESULTS_DIR}/")


def generate_graphs(results: List[TestResult], rankings: List[Dict]):
    """グラフ生成"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')
    except ImportError:
        print("⚠️ matplotlib未インストール")
        return
    
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    # 1. ランキング
    fig, ax = plt.subplots(figsize=(14, 10))
    names = [r["name"][:40] for r in rankings[:20]]
    scores = [r["avg_score"] for r in rankings[:20]]
    colors = ['#2ecc71' if 'V2' in n else '#3498db' if 'Fastest' in n else '#e74c3c' for n in names]
    
    bars = ax.barh(names[::-1], scores[::-1], color=colors[::-1])
    ax.set_xlabel("Average Score (0-100)")
    ax.set_title("DictSQLite All Versions Performance Ranking")
    ax.set_xlim(0, 105)
    
    for bar, score in zip(bars, scores[::-1]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f'{score:.0f}', va='center', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(f"{IMAGES_DIR}/ranking_all_versions.png", dpi=150)
    plt.close()
    print(f"保存: {IMAGES_DIR}/ranking_all_versions.png")
    
    # 2. バージョン別比較
    fig, ax = plt.subplots(figsize=(12, 6))
    
    version_scores = {}
    for r in results:
        if r.version not in version_scores:
            version_scores[r.version] = []
        version_scores[r.version].append(r.score)
    
    versions = list(version_scores.keys())
    avgs = [sum(v)/len(v) for v in version_scores.values()]
    colors = ['#e74c3c', '#2ecc71', '#3498db']
    
    ax.bar(versions, avgs, color=colors[:len(versions)])
    ax.set_ylabel("Average Score")
    ax.set_title("Performance by Version")
    ax.set_ylim(0, 105)
    
    for i, (v, a) in enumerate(zip(versions, avgs)):
        ax.text(i, a + 2, f'{a:.1f}', ha='center')
    
    plt.tight_layout()
    plt.savefig(f"{IMAGES_DIR}/version_comparison.png", dpi=150)
    plt.close()
    print(f"保存: {IMAGES_DIR}/version_comparison.png")
    
    # 3. 操作別比較
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    for idx, op in enumerate(["set", "get"]):
        ax = axes[idx]
        op_data = {}
        for r in results:
            if r.test_name == op and r.data_size == 1000:
                key = f"{r.version}\n({r.mode[:3]})"
                if key not in op_data:
                    op_data[key] = []
                op_data[key].append(r.ops_per_sec)
        
        if op_data:
            names = list(op_data.keys())
            ops = [sum(v)/len(v) for v in op_data.values()]
            ax.bar(names, ops)
            ax.set_ylabel("Ops/sec")
            ax.set_title(f"{op.upper()} (1KB)")
            ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(f"{IMAGES_DIR}/operation_comparison.png", dpi=150)
    plt.close()
    print(f"保存: {IMAGES_DIR}/operation_comparison.png")


def print_summary(results: List[TestResult], rankings: List[Dict]):
    """サマリー表示"""
    print("\n" + "=" * 70)
    print("🏆 ALL VERSIONS BENCHMARK RANKING")
    print("=" * 70)
    
    print(f"\n{'Rank':<6}{'Name':<50}{'Score':<10}")
    print("-" * 66)
    for r in rankings[:15]:
        print(f"#{r['rank']:<5}{r['name'][:48]:<50}{r['avg_score']:<10.1f}")
    
    # バージョン別統計
    print("\n📊 VERSION STATISTICS:")
    version_stats = {}
    for r in results:
        if r.version not in version_stats:
            version_stats[r.version] = {"scores": [], "ops": []}
        version_stats[r.version]["scores"].append(r.score)
        version_stats[r.version]["ops"].append(r.ops_per_sec)
    
    for v, s in version_stats.items():
        avg_score = sum(s["scores"]) / len(s["scores"]) if s["scores"] else 0
        max_ops = max(s["ops"]) if s["ops"] else 0
        print(f"  {v}: Avg Score={avg_score:.1f}, Max Ops={max_ops:,.0f}/s")
    
    # ベスト
    if results:
        best = max(results, key=lambda r: r.ops_per_sec)
        print(f"\n🚀 FASTEST OPERATION:")
        print(f"   {best.version} {best.category} {best.test_name}")
        print(f"   Mode: {best.mode}/{best.storage}")
        print(f"   {best.ops_per_sec:,.0f} ops/sec")


def main():
    print(f"🕐 開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print("📊 DictSQLite All Versions Comprehensive Benchmark")
    print("=" * 70)
    
    results = []
    
    # 各バージョンをテスト
    results.extend(test_original_dictsqlite())
    results.extend(test_dictsqlite_v2())
    results.extend(test_fastest_beta())
    
    if not results:
        print("❌ テスト結果がありません")
        return
    
    # スコア計算
    results = calculate_scores(results)
    rankings = generate_rankings(results)
    
    # 保存と表示
    save_results(results, rankings)
    generate_graphs(results, rankings)
    print_summary(results, rankings)
    
    print(f"\n🕐 終了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ 完了！")


if __name__ == "__main__":
    main()

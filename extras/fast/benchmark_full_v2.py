#!/usr/bin/env python
"""benchmark_full_v2

v1 で提供していた DictSQLite (baseline) と dictsqlite_fast (高速版) の
同期/非同期実装を同一テーブル形式で比較し、コンソール表示 + ファイル出力
(JSON / CSV / Markdown) を一括で行う総合ベンチマーク。

目的:
  - v1 の benchmark.py では from-scratch のオプションが多く出力形式が固定的。
  - 本スクリプトは *再現性* と *一括ファイル出力* にフォーカスし、デフォルトで
    results/<timestamp>/ 以下へ結果を書き出す。
  - 追加で --no-baseline / --no-fast などのフィルタや --modes 選択が可能。

計測対象:
  SYNC  : DictSQLite, FastDictSQLite
  ASYNC : AsyncDictSQLiteWrapper (DictSQLite)、AsyncFastDictSQLite

シナリオ (v1 をベースに軽量化 + 代表ケース):
  small_insert      : 小さな整数値の一括挿入
  large_insert      : そこそこのサイズ(約2KB payload)オブジェクト挿入
  random_get        : ランダム取得 + 一部ミス
  mixed_update      : 読み書き混在 (ホットキー更新)
  transaction_bulk  : トランザクション内一括挿入
  table_switch      : テーブル切替を挟む挿入
  bulk_set          : (fast 専用最適化) bulk_set / baseline は逐次挿入

出力:
  - コンソール: シナリオ x 実装 (ops/s) テーブル + 詳細行
  - JSON: raw サンプルと集計
  - CSV : 1 レコード / (scenario, impl, mode, run)
  - Markdown: 見やすいサマリ表

使い方例:
  python extras/fast/benchmark_full_v2.py
  python extras/fast/benchmark_full_v2.py --keys 5000 --runs 5 --only small_insert mixed_update --json out.json
  python extras/fast/benchmark_full_v2.py --no-baseline --modes sync --csv fast_only.csv

注意:
  - 非同期 baseline (DictSQLite) は簡易 AsyncDictSQLiteWrapper で to_thread 利用。
  - 実際の性能は OS / ディスク / キャッシュ / GIL 状況で変動します。

"""
from __future__ import annotations

import argparse
import asyncio
import csv
import dataclasses
import json
import math
import os
import random
import statistics
import string
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

# ルート追加 (ローカルリポジトリ直実行対応)
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# baseline
from dictsqlite.main import DictSQLite  # type: ignore  # noqa: E402
# fast
try:  # noqa: SIM105
    from dictsqlite_fast import FastDictSQLite, AsyncFastDictSQLite  # type: ignore  # noqa: E402
    FAST_AVAILABLE = True
except Exception:  # pragma: no cover
    FastDictSQLite = None  # type: ignore
    AsyncFastDictSQLite = None  # type: ignore
    FAST_AVAILABLE = False

RNG = random.Random(12345)


# ---------------- Async baseline wrapper ----------------
class AsyncDictSQLiteWrapper:
    """シンプルな to_thread ラッパ (ベンチ専用)。"""
    def __init__(self, *a, **kw):
        self._inner = DictSQLite(*a, **kw)
    async def set(self, k, v):
        await asyncio.to_thread(self._inner.__setitem__, k, v)
    async def get(self, k):
        try:
            return await asyncio.to_thread(self._inner.__getitem__, k)
        except KeyError:
            return None
    async def close(self):
        await asyncio.to_thread(self._inner.close)
    async def flush(self):  # noqa: D401
        # DictSQLite は push 型でキュー無し -> no-op
        return


# ---------------- シナリオ生成ヘルパ ----------------

def _rand_key(n=12):
    chars = string.ascii_letters + string.digits
    return ''.join(RNG.choice(chars) for _ in range(n))

def _large_payload() -> Dict[str, Any]:
    return {
        "name": _rand_key(16),
        "flags": [RNG.randint(0, 1000) for _ in range(40)],
        "blob": os.urandom(2048),
        "nested": {"x": RNG.random(), "y": _rand_key(24)},
    }

# ---------------- 同期シナリオ実装 ----------------

def sc_small_insert(db, keys: int):
    for i in range(keys):
        db[_rand_key()] = i

def sc_large_insert(db, keys: int):
    for _ in range(keys):
        db[_rand_key()] = _large_payload()

def sc_random_get(db, keys: int):
    inserted = [_rand_key() for _ in range(keys)]
    for k in inserted:
        db[k] = k
    RNG.shuffle(inserted)
    miss = 0
    for k in inserted:
        _ = db[k]
        if RNG.random() < 0.02:
            try:
                _ = db[k+"_X"]
            except KeyError:
                miss += 1
    return miss

def sc_mixed_update(db, keys: int):
    hot = [_rand_key() for _ in range(min(100, max(10, keys//10)))]
    for k in hot:
        db[k] = 0
    for _ in range(keys):
        k = RNG.choice(hot)
        if RNG.random() < 0.6:
            db[k] = db[k] + 1
        else:
            _ = db[k]

def sc_transaction_bulk(db, keys: int):
    if hasattr(db, 'begin_transaction'):
        db.begin_transaction()
        try:
            for i in range(keys):
                db[_rand_key()] = i
            db.commit_transaction()
        except Exception:
            db.rollback_transaction(); raise
    elif hasattr(db, 'begin'):
        db.begin()
        try:
            for i in range(keys):
                db[_rand_key()] = i
            db.commit()
        except Exception:
            db.rollback(); raise

def sc_table_switch(db, keys: int):
    for i in range(max(2, keys//10)):
        t = f"t{i}"
        if hasattr(db, 'switch_table'):
            db.switch_table(t)
        db[_rand_key()] = i
    if hasattr(db, 'switch_table'):
        db.switch_table('main')

def sc_bulk_set(db, keys: int):
    if hasattr(db, 'bulk_set'):
        db.bulk_set(((_rand_key(), i) for i in range(keys)))
    else:  # baseline fallback
        for i in range(keys):
            db[_rand_key()] = i

SYNC_SCENARIOS = {
    'small_insert': sc_small_insert,
    'large_insert': sc_large_insert,
    'random_get': sc_random_get,
    'mixed_update': sc_mixed_update,
    'transaction_bulk': sc_transaction_bulk,
    'table_switch': sc_table_switch,
    'bulk_set': sc_bulk_set,
}

# ---------------- 非同期シナリオ実装 ----------------
async def asc_small_insert(db, keys):
    for i in range(keys):
        await db.set(_rand_key(), i)
async def asc_large_insert(db, keys):
    for _ in range(keys):
        await db.set(_rand_key(), _large_payload())
async def asc_random_get(db, keys):
    inserted = [_rand_key() for _ in range(keys)]
    for k in inserted:
        await db.set(k, k)
    RNG.shuffle(inserted)
    for k in inserted:
        await db.get(k)
        if RNG.random() < 0.02:
            await db.get(k+"_X")
async def asc_mixed_update(db, keys):
    hot = [_rand_key() for _ in range(min(100, max(10, keys//10)))]
    for k in hot:
        await db.set(k, 0)
    for _ in range(keys):
        k = RNG.choice(hot)
        val = await db.get(k)
        if RNG.random() < 0.6:
            await db.set(k, (val or 0) + 1)
        else:
            await db.get(k)
async def asc_transaction_bulk(db, keys):
    # fast async: bulk_set + transaction; baseline: set loop
    if hasattr(db, 'bulk_set'):
        await db.bulk_set([( _rand_key(), i) for i in range(keys)])
    else:
        for i in range(keys):
            await db.set(_rand_key(), i)
async def asc_table_switch(db, keys):
    for i in range(max(2, keys//10)):
        if hasattr(db, 'switch_table'):
            try:
                await db.switch_table(f"t{i}")
            except Exception:  # noqa: BLE001
                pass
        await db.set(_rand_key(), i)
    if hasattr(db, 'switch_table'):
        try:
            await db.switch_table('main')
        except Exception:  # noqa: BLE001
            pass
async def asc_bulk_set(db, keys):
    if hasattr(db, 'bulk_set'):
        await db.bulk_set([( _rand_key(), i) for i in range(keys)])
    else:
        for i in range(keys):
            await db.set(_rand_key(), i)

ASYNC_SCENARIOS = {
    'small_insert': asc_small_insert,
    'large_insert': asc_large_insert,
    'random_get': asc_random_get,
    'mixed_update': asc_mixed_update,
    'transaction_bulk': asc_transaction_bulk,
    'table_switch': asc_table_switch,
    'bulk_set': asc_bulk_set,
}

# ---------------- 計測結果データ構造 ----------------
@dataclass
class Sample:
    scenario: str
    impl: str  # dictsqlite / fast
    mode: str  # sync / async
    run: int
    seconds: float
    operations: int
    @property
    def ops_per_sec(self) -> float:
        return self.operations / self.seconds if self.seconds else math.inf

# ---------------- 計測実行 ----------------

def run_sync_impl(impl: str, scenario: str, keys: int, tmp: Path) -> float:
    if impl == 'dictsqlite':
        db = DictSQLite(str(tmp / 'baseline.db'))
    elif impl == 'fast':
        if not FAST_AVAILABLE:
            return float('nan')
        db = FastDictSQLite(str(tmp / 'fast.db'))  # type: ignore
    else:
        raise ValueError(impl)
    fn = SYNC_SCENARIOS[scenario]
    start = time.perf_counter()
    try:
        fn(db, keys)
        if hasattr(db, 'flush'):
            try: db.flush()
            except Exception:  # noqa: BLE001
                pass
    finally:
        db.close()
    return time.perf_counter() - start

async def _run_async_impl(impl: str, scenario: str, keys: int, tmp: Path) -> float:
    if impl == 'dictsqlite':
        adb = AsyncDictSQLiteWrapper(str(tmp / 'abs.db'))
    elif impl == 'fast':
        if not FAST_AVAILABLE or AsyncFastDictSQLite is None:  # type: ignore
            return float('nan')
        adb = AsyncFastDictSQLite(str(tmp / 'afs.db'))  # type: ignore
    else:
        raise ValueError(impl)
    fn = ASYNC_SCENARIOS[scenario]
    start = time.perf_counter()
    try:
        await fn(adb, keys)
        if hasattr(adb, 'flush'):
            try:
                await adb.flush()
            except Exception:  # noqa: BLE001
                pass
    finally:
        try:
            await adb.close()
        except Exception:  # noqa: BLE001
            pass
    return time.perf_counter() - start

def run_async_impl(impl: str, scenario: str, keys: int, tmp: Path) -> float:
    return asyncio.run(_run_async_impl(impl, scenario, keys, tmp))

# ---------------- メインロジック ----------------

def benchmark(args) -> List[Sample]:
    scenarios = args.only or list(SYNC_SCENARIOS.keys())
    selected_modes: List[str]
    if args.modes == 'both':
        selected_modes = ['sync','async']
    else:
        selected_modes = [args.modes]
    implementations = []
    if not args.no_baseline:
        implementations.append('dictsqlite')
    if not args.no_fast:
        implementations.append('fast')

    samples: List[Sample] = []
    for scenario in scenarios:
        for impl in implementations:
            for mode in selected_modes:
                for run in range(1, args.runs + 1):
                    with tempfile.TemporaryDirectory() as d:
                        tmp = Path(d)
                        if mode == 'sync':
                            seconds = run_sync_impl(impl, scenario, args.keys, tmp)
                        else:
                            seconds = run_async_impl(impl, scenario, args.keys, tmp)
                        if math.isnan(seconds):
                            continue
                        operations = args.keys  # 簡易: 各シナリオ主操作数=keys とする
                        samples.append(Sample(scenario, impl, mode, run, seconds, operations))
                        if args.verbose:
                            print(f"[detail] scenario={scenario} impl={impl} mode={mode} run={run} seconds={seconds:.4f} ops/s={operations/seconds:,.0f}")
    return samples

# ---------------- 出力フォーマット ----------------

def _aggregate(samples: List[Sample]):
    agg: Dict[Tuple[str,str,str], Dict[str, Any]] = {}
    for s in samples:
        key = (s.scenario, s.impl, s.mode)
        d = agg.setdefault(key, {"seconds": [], "ops": []})
        d["seconds"].append(s.seconds)
        d["ops"].append(s.ops_per_sec)
    rows = []
    for (scenario, impl, mode), d in agg.items():
        rows.append({
            'scenario': scenario,
            'impl': impl,
            'mode': mode,
            'runs': len(d['seconds']),
            'median_seconds': statistics.median(d['seconds']),
            'mean_seconds': statistics.mean(d['seconds']),
            'p90_seconds': statistics.quantiles(d['seconds'], n=10)[8] if len(d['seconds']) >= 10 else max(d['seconds']),
            'median_ops_per_sec': statistics.median(d['ops']),
            'mean_ops_per_sec': statistics.mean(d['ops'])
        })
    return rows

def print_console_table(agg_rows: List[Dict[str, Any]]):
    # シナリオごと × impl+mode を列に束ねる
    scenarios = sorted({r['scenario'] for r in agg_rows})
    impl_modes = sorted({(r['impl'], r['mode']) for r in agg_rows})
    # ヘッダ
    header = ["scenario"] + [f"{impl}.{mode}" for impl, mode in impl_modes]
    col_widths = [max(len(h), 10) for h in header]
    def fmt_cell(text, w):
        return str(text).ljust(w)
    print("\n=== Aggregate Throughput (median ops/s) ===")
    print(' '.join(fmt_cell(h, w) for h, w in zip(header, col_widths)))
    for sc in scenarios:
        row_vals = [sc]
        for impl, mode in impl_modes:
            match = [r for r in agg_rows if r['scenario']==sc and r['impl']==impl and r['mode']==mode]
            if match:
                val = f"{int(match[0]['median_ops_per_sec']):,}"
            else:
                val = '-'
            row_vals.append(val)
        print(' '.join(fmt_cell(v, w) for v, w in zip(row_vals, col_widths)))

# ---------------- ファイル書き出し ----------------

def write_outputs(samples: List[Sample], args, agg_rows: List[Dict[str, Any]]):
    out_dir = Path(args.output_dir) if args.output_dir else Path('results') / time.strftime('%Y%m%d_%H%M%S')
    out_dir.mkdir(parents=True, exist_ok=True)
    # JSON (raw + aggregate)
    if args.json:
        data = {
            'meta': {
                'keys': args.keys,
                'runs': args.runs,
                'modes': args.modes,
                'implementations': ["dictsqlite" if not args.no_baseline else None, "fast" if not args.no_fast else None],
                'timestamp': time.time(),
            },
            'samples': [dataclasses.asdict(s) for s in samples],
            'aggregate': agg_rows,
        }
        with open(out_dir / args.json, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    # CSV (samples)
    if args.csv:
        with open(out_dir / args.csv, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['scenario','impl','mode','run','seconds','ops_per_sec'])
            for s in samples:
                w.writerow([s.scenario, s.impl, s.mode, s.run, f"{s.seconds:.6f}", f"{s.ops_per_sec:.2f}"])
    # Markdown (aggregate)
    if args.markdown:
        scenarios = sorted({r['scenario'] for r in agg_rows})
        impl_modes = sorted({(r['impl'], r['mode']) for r in agg_rows})
        lines = ["# Benchmark Summary", "", f"Keys per scenario: {args.keys}", f"Runs: {args.runs}", "", "| Scenario | " + " | ".join(f"{i}.{m}" for i,m in impl_modes) + " |", "|---|" + "|".join(["---" for _ in impl_modes]) + "|"]
        for sc in scenarios:
            row = [sc]
            for impl, mode in impl_modes:
                match = [r for r in agg_rows if r['scenario']==sc and r['impl']==impl and r['mode']==mode]
                if match:
                    row.append(f"{int(match[0]['median_ops_per_sec']):,}")
                else:
                    row.append('-')
            lines.append("| " + " | ".join(row) + " |")
        with open(out_dir / args.markdown, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    print(f"\n[output] results written to: {out_dir.resolve()}")
    if args.json:
        print(f"  JSON: {out_dir / args.json}")
    if args.csv:
        print(f"  CSV : {out_dir / args.csv}")
    if args.markdown:
        print(f"  MD  : {out_dir / args.markdown}")

# ---------------- CLI ----------------

def parse_args():
    p = argparse.ArgumentParser(description='Full benchmark (baseline vs fast, sync & async)')
    p.add_argument('--keys', type=int, default=2000)
    p.add_argument('--runs', type=int, default=3, help='各 (scenario,impl,mode) の繰り返し回数')
    p.add_argument('--only', nargs='*', help='対象シナリオ限定 (空白区切り)')
    p.add_argument('--modes', choices=['sync','async','both'], default='both')
    p.add_argument('--no-baseline', action='store_true', help='DictSQLite を除外')
    p.add_argument('--no-fast', action='store_true', help='FastDictSQLite を除外')
    p.add_argument('--json', default='benchmark.json')
    p.add_argument('--csv', default='benchmark.csv')
    p.add_argument('--markdown', default='benchmark.md')
    p.add_argument('--output-dir', help='出力ディレクトリ (未指定=results/<timestamp>)')
    p.add_argument('--verbose', action='store_true')
    return p.parse_args()

# ---------------- エントリポイント ----------------

def main():  # noqa: D401
    args = parse_args()
    if args.no_baseline and args.no_fast:
        print('何も計測対象がありません (--no-baseline と --no-fast が同時指定)')
        return 1
    samples = benchmark(args)
    agg_rows = _aggregate(samples)
    print_console_table(agg_rows)
    write_outputs(samples, args, agg_rows)
    return 0

if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())


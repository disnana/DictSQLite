#!/usr/bin/env python
"""benchmark_v2: FastDictSQLite / AsyncFastDictSQLite 改良版向けベンチマーク

主目的:
  - v1(従来 extras/fast/benchmark.py) では DictSQLite との比較や多目的機能があり冗長。
  - v2 は改良 fast 実装 (TableProxy キャッシュ / N+1 クエリ除去 / bulk_set / async bulk_set) の
    効果確認にフォーカスした軽量版。

特徴:
  - シナリオ: small_insert / large_object / mixed_update / bulk_set / nested_mutation / transaction_bulk
  - sync/async の両方計測 (async は AsyncFastDictSQLite)
  - bulk_set シナリオでは 1 件ずつ set する従来方法との差分を併記
  - JSON や CSV 出力オプション (必要最小限)
  - --repeat で複数回計測し中央値/平均/最速を表示

使い方例:
  python extras/fast/dictsqlite_fast/benchmark_v2.py
  python extras/fast/dictsqlite_fast/benchmark_v2.py --keys 5000 --repeat 5 --only bulk_set --csv result.csv

注意:
  - I/O キャッシュ / CPU スケールにより値は変動します。
  - apsw 無インストール時は sqlite3 フォールバック (backend=sqlite3) と表示。
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import os
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Tuple, Dict, Callable

# ルートを sys.path へ (リポジトリ直下どこからでも動作させるため)
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extras.fast.dictsqlite_fast.fast import FastDictSQLite  # type: ignore  # noqa: E402
from extras.fast.dictsqlite_fast.async_fast import AsyncFastDictSQLite  # type: ignore  # noqa: E402

try:  # backend 判定用
    USING_APSW = (FastDictSQLite(':memory:').backend == 'apsw')
except Exception:  # noqa: BLE001
    USING_APSW = False

# ---------------- Scenario 定義 -----------------

def scenario_small_insert(db: FastDictSQLite, keys: int):  # noqa: D401
    for i in range(keys):
        db[f"k{i}"] = i

def scenario_large_object(db: FastDictSQLite, keys: int):  # noqa: D401
    blob = os.urandom(2048)
    for i in range(keys):
        db[f"L{i}"] = {"idx": i, "payload": blob, "arr": list(range(50))}

def scenario_mixed_update(db: FastDictSQLite, keys: int):  # noqa: D401
    for i in range(keys):
        k = f"m{i%100}"  # 100 個を回転
        try:
            db[k] = db.get(k, 0) + 1
        except Exception:  # noqa: BLE001
            db[k] = 1

def scenario_nested_mutation(db: FastDictSQLite, keys: int):  # noqa: D401
    root = "cfg"
    db[root] = {"lvl1": {"counter": 0, "items": []}}
    for _ in range(keys):
        cfg = db[root]
        lvl1 = cfg['lvl1']
        lvl1['counter'] = lvl1['counter'] + 1
        arr = lvl1['items']
        if isinstance(arr, list):
            arr.append(_ % 7)
        # top dict を再保存 (ネスト list 反映)
        db[root] = cfg.to_dict() if hasattr(cfg, 'to_dict') else cfg

def scenario_transaction_bulk(db: FastDictSQLite, keys: int):  # noqa: D401
    db.begin()
    try:
        for i in range(keys):
            db[f"t{i}"] = i
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback(); raise

def scenario_bulk_set(db: FastDictSQLite, keys: int):  # noqa: D401
    items = [(f"b{i}", i) for i in range(keys)]
    db.bulk_set(items)  # 新高速 API

SCENARIOS: Dict[str, Callable[[FastDictSQLite, int], None]] = {
    "small_insert": scenario_small_insert,
    "large_object": scenario_large_object,
    "mixed_update": scenario_mixed_update,
    "nested_mutation": scenario_nested_mutation,
    "transaction_bulk": scenario_transaction_bulk,
    "bulk_set": scenario_bulk_set,
}

# Async 版 (sync シナリオを再利用できるものは bulk_set を個別実装)
async def async_run(adb: AsyncFastDictSQLite, scenario: str, keys: int):  # noqa: D401
    if scenario == 'bulk_set':
        await adb.bulk_set([(f"b{i}", i) for i in range(keys)])
        return
    if scenario == 'transaction_bulk':
        pairs = [(f"t{i}", i) for i in range(keys)]
        await adb.bulk_set(pairs, use_transaction=True)
        return
    if scenario == 'small_insert':
        for i in range(keys):
            await adb.set(f"k{i}", i)
        return
    if scenario == 'large_object':
        blob = os.urandom(2048)
        for i in range(keys):
            await adb.set(f"L{i}", {"idx": i, "payload": blob, "arr": list(range(50))})
        return
    if scenario == 'mixed_update':
        for i in range(keys):
            k = f"m{i%100}"
            cur = await adb.get(k, 0)
            await adb.set(k, cur + 1)
        return
    if scenario == 'nested_mutation':
        await adb.set('cfg', {"lvl1": {"counter": 0, "items": []}})
        for i in range(keys):
            cfg = await adb.get('cfg')
            if cfg is None:
                continue
            lvl1 = cfg['lvl1']
            lvl1['counter'] = lvl1['counter'] + 1
            arr = lvl1['items']
            if isinstance(arr, list):
                arr.append(i % 7)
            await adb.set('cfg', cfg if not hasattr(cfg, 'to_dict') else cfg.to_dict())
        return
    raise ValueError(scenario)

# ---------------- 計測ヘルパ -----------------

def time_sync(scenario: str, keys: int, tmp: Path) -> float:
    db = FastDictSQLite(str(tmp / 'bench.db'))
    try:
        fn = SCENARIOS[scenario]
        start = time.perf_counter()
        fn(db, keys)
        db.flush()
        return time.perf_counter() - start
    finally:
        db.close()

def time_async(scenario: str, keys: int, tmp: Path) -> float:
    async def _run():
        adb = AsyncFastDictSQLite(str(tmp / 'abench.db'))
        try:
            start = time.perf_counter()
            await async_run(adb, scenario, keys)
            await adb.flush()
            return time.perf_counter() - start
        finally:
            await adb.close()
    return asyncio.run(_run())

@dataclass
class Result:
    scenario: str
    mode: str  # sync / async
    seconds: float
    keys: int
    ops_per_sec: float

# ---------------- メイン -----------------

def run(args):
    scenarios = args.only or list(SCENARIOS.keys())
    results: List[Result] = []
    for sc in scenarios:
        for mode in (['sync'] if args.mode == 'sync' else ['async'] if args.mode == 'async' else ['sync','async']):
            samples: List[float] = []
            for _ in range(args.repeat):
                with tempfile.TemporaryDirectory() as d:
                    tmp = Path(d)
                    if mode == 'sync':
                        dur = time_sync(sc, args.keys, tmp)
                    else:
                        dur = time_async(sc, args.keys, tmp)
                    samples.append(dur)
            median = statistics.median(samples)
            ops = args.keys / median if median else float('inf')
            results.append(Result(sc, mode, median, args.keys, ops))
            print(f"{sc:16s} {mode:5s} median={median:.4f}s ops/s={ops:,.0f} (runs={args.repeat})")
    # サマリ
    print("\nSummary (sorted by ops/s desc):")
    for r in sorted(results, key=lambda x: x.ops_per_sec, reverse=True):
        print(f"{r.scenario:16s} {r.mode:5s} {r.ops_per_sec:,.0f} ops/s ({r.seconds:.4f}s)")
    if args.json:
        import json as _json
        with open(args.json, 'w', encoding='utf-8') as f:
            _json.dump([r.__dict__ for r in results], f, ensure_ascii=False, indent=2)
    if args.csv:
        with open(args.csv, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['scenario','mode','seconds','keys','ops_per_sec'])
            for r in results:
                w.writerow([r.scenario, r.mode, f"{r.seconds:.6f}", r.keys, f"{r.ops_per_sec:.2f}"])


def parse_args():
    p = argparse.ArgumentParser(description='FastDictSQLite v2 benchmark')
    p.add_argument('--keys', type=int, default=2000, help='1シナリオ当たりのキー数')
    p.add_argument('--repeat', type=int, default=3, help='各シナリオ繰り返し回数(中央値採用)')
    p.add_argument('--only', nargs='*', help='実行するシナリオを限定 (space 区切り)')
    p.add_argument('--mode', choices=['sync','async','both'], default='both')
    p.add_argument('--json', help='結果を JSON 出力')
    p.add_argument('--csv', help='結果を CSV 出力')
    return p.parse_args()

if __name__ == '__main__':  # pragma: no cover
    run(parse_args())


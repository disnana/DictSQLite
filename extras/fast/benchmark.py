#!/usr/bin/env python
"""DictSQLite vs dictsqlite-fast ベンチマークツール

機能:
  - 同期版: DictSQLite / FastDictSQLite
  - 非同期版: 擬似 AsyncWrapper(DictSQLite) / AsyncFastDictSQLite
  - シナリオ: 小さな挿入 / 大きな挿入 / ランダム取得 / 混在読み書き / ネスト更新 / list/set同期 / 取引(トランザクション)一括 / テーブル切替
  - 出力: テキスト表, --json で JSON, --csv で CSV
  - フォールバック: apsw 無い場合 fast は sqlite3 fallback と表示

使い方例:
  python extras/fast/benchmark.py
  python extras/fast/benchmark.py --keys 5000 --runs 3 --json results.json
  python extras/fast/benchmark.py --only sync,async_fast --scenarios small_insert,random_get

注意:
  計測は単純な perf_counter ベース。I/O キャッシュや CPU 周波数スケーリングなどで変動します。
"""
from __future__ import annotations

import argparse
import asyncio
import json as _json
import os
import random
import statistics
import string
import sys
import time
import tempfile
import csv
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence

# ルートパス追加 (リポジトリ内直接実行用)
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dictsqlite.main import DictSQLite  # type: ignore  # noqa: E402

# fast パッケージ import (shim 経由可)
try:  # noqa: SIM105
    import dictsqlite_fast  # type: ignore  # noqa: E401
    from dictsqlite_fast import FastDictSQLite  # type: ignore  # noqa: E401
    try:
        from dictsqlite_fast import AsyncFastDictSQLite  # type: ignore  # noqa: E401
    except Exception:  # pragma: no cover
        AsyncFastDictSQLite = None  # type: ignore
    FAST_AVAILABLE = True
except Exception:  # pragma: no cover
    FAST_AVAILABLE = False
    FastDictSQLite = None  # type: ignore
    AsyncFastDictSQLite = None  # type: ignore

RANDOM = random.Random(12345)


def _rand_key(n=12):
    letters = string.ascii_letters + string.digits
    return ''.join(RANDOM.choice(letters) for _ in range(n))


def _large_obj():
    # 約 1KB 程度の JSON 生成
    return {
        "name": _rand_key(16),
        "flags": [RANDOM.randint(0, 1000) for _ in range(50)],
        "payload": _rand_key(256),
        "nested": {"alpha": RANDOM.random(), "beta": [_rand_key(8) for _ in range(10)]},
    }


@dataclass
class ScenarioResult:
    scenario: str
    impl: str
    mode: str
    run: int
    seconds: float
    operations: int

    @property
    def ops_per_sec(self) -> float:  # noqa: D401
        return self.operations / self.seconds if self.seconds else float('inf')


# ---------------------------- Async wrapper (baseline DictSQLite) ----------------------------
class AsyncDictSQLiteWrapper:
    """簡易非同期ラッパ: CPU バウンド/SQLite I/O を to_thread に逃がす。"""

    def __init__(self, *a, **kw):
        self._inner = DictSQLite(*a, **kw)

    async def set(self, key, value):
        await asyncio.to_thread(self._inner.__setitem__, key, value)

    async def get(self, key):
        try:
            return await asyncio.to_thread(self._inner.__getitem__, key)
        except KeyError:
            return None  # miss 時は None

    async def contains(self, key):  # noqa: D401
        return await asyncio.to_thread(lambda k: k in self._inner, key)

    async def clear(self):  # noqa: D401
        await asyncio.to_thread(self._inner.clear_table)

    async def transaction_bulk(self, data):  # noqa: D401
        await asyncio.to_thread(self._inner.begin_transaction)
        try:
            for k, v in data:
                self._inner[k] = v
        finally:
            await asyncio.to_thread(self._inner.commit_transaction)

    async def close(self):  # noqa: D401
        await asyncio.to_thread(self._inner.close)


# ---------------------------- Scenario implementations ----------------------------

class ScenarioRegistry:
    def __init__(self):
        self._scenarios: Dict[str, Callable] = {}

    def register(self, name: str):
        def deco(fn):
            self._scenarios[name] = fn
            return fn
        return deco

    def names(self):  # noqa: D401
        return list(self._scenarios.keys())

    def run(self, name: str, fn_args: Dict[str, Any]):
        return self._scenarios[name](**fn_args)


REGISTRY = ScenarioRegistry()


@REGISTRY.register("small_insert")
def scenario_small_insert(db, keys: int, large: bool = False):  # noqa: D401
    for i in range(keys):
        db[_rand_key()] = i


@REGISTRY.register("large_insert")
def scenario_large_insert(db, keys: int):  # noqa: D401
    for _ in range(keys):
        db[_rand_key()] = _large_obj()


@REGISTRY.register("random_get")
def scenario_random_get(db, keys: int):  # noqa: D401
    inserted = [_rand_key() for _ in range(keys)]
    for k in inserted:
        db[k] = k
    RANDOM.shuffle(inserted)
    miss = 0
    for k in inserted:
        _ = db[k]
        # 少数ミスアクセスも混ぜる
        if RANDOM.random() < 0.01:
            try:
                _ = db[k + "_x"]
            except KeyError:
                miss += 1


@REGISTRY.register("mixed_update")
def scenario_mixed_update(db, keys: int):  # noqa: D401
    base_keys = [_rand_key() for _ in range(keys)]
    for k in base_keys:
        db[k] = 0
    for _ in range(keys):
        k = RANDOM.choice(base_keys)
        if RANDOM.random() < 0.6:
            db[k] = db[k] + 1
        else:
            _ = db[k]


@REGISTRY.register("nested_mutation")
def scenario_nested_mutation(db, keys: int):  # noqa: D401
    """ネスト辞書のカウンタ更新とネスト list 追加。

    注意: ネスト list は自動同期されないため、更新ごとに to_dict() でプレーン dict を保存し
    プロキシ(DB接続参照)が pickle 対象にならないようにする。
    """
    root_key = "cfg"
    db[root_key] = {"lvl1": {"counter": 0, "items": []}}
    for _ in range(keys):
        cfg = db[root_key]              # RecursiveDict
        lvl1 = cfg["lvl1"]             # RecursiveDict (下位)
        lvl1["counter"] = lvl1["counter"] + 1  # __setitem__ 経由で永続化
        items = lvl1["items"]          # ネスト list (生の list) -> 自動同期されない
        if isinstance(items, list):
            items.append(_rand_key(4))
        # ネスト list 変更を反映させるためトップレベル dict をプレーン化して再保存
        db[root_key] = cfg.to_dict()


@REGISTRY.register("list_set_sync")
def scenario_list_set_sync(db, keys: int):  # noqa: D401
    """トップレベル list/set の同期計測。

    DBSyncedList / DBSyncedSet はメソッド呼び出しで自動同期されるので再代入しない。
    再代入するとプロキシ自体を pickle しようとして接続オブジェクトを含み失敗するため。
    """
    db["L"] = [0]
    db["S"] = {0}
    for i in range(1, keys):
        lst = db["L"]  # DBSyncedList
        st = db["S"]  # DBSyncedSet
        # 直接 append / add (各メソッド内部で同期)
        if hasattr(lst, 'append'):
            lst.append(i)
        if hasattr(st, 'add'):
            st.add(i)


@REGISTRY.register("transaction_bulk")
def scenario_transaction_bulk(db, keys: int):  # noqa: D401
    if hasattr(db, 'begin_transaction'):
        db.begin_transaction()
        try:
            for i in range(keys):
                db[_rand_key()] = i
            db.commit_transaction()
        except Exception:
            db.rollback_transaction()
            raise
    else:  # fast begin wrapper
        if hasattr(db, 'begin'):
            db.begin()
        try:
            for i in range(keys):
                db[_rand_key()] = i
            if hasattr(db, 'commit'):
                db.commit()
        except Exception:
            if hasattr(db, 'rollback'):
                db.rollback()
            raise


@REGISTRY.register("table_switch")
def scenario_table_switch(db, keys: int):  # noqa: D401
    for i in range(max(2, keys // 10)):
        t = f"t{i}"
        if hasattr(db, 'switch_table'):
            db.switch_table(t)
        db[_rand_key()] = i
    if hasattr(db, 'switch_table'):
        db.switch_table('main')


# ---------------------------- Async versions ----------------------------
async def async_run(db, scenario: str, keys: int):
    # db は async API を持つ (set/get/clear など) 前提
    if scenario == 'small_insert':
        for i in range(keys):
            await db.set(_rand_key(), i)
    elif scenario == 'large_insert':
        for _ in range(keys):
            await db.set(_rand_key(), _large_obj())
    elif scenario == 'random_get':
        inserted = [_rand_key() for _ in range(keys)]
        for k in inserted:
            await db.set(k, k)
        RANDOM.shuffle(inserted)
        for k in inserted:
            await db.get(k)
            if RANDOM.random() < 0.01:
                # miss は例外にしない (baseline wrapper は None を返す)
                _ = await db.get(k + '_x')
    elif scenario == 'mixed_update':
        base_keys = [_rand_key() for _ in range(keys)]
        for k in base_keys:
            await db.set(k, 0)
        for _ in range(keys):
            k = RANDOM.choice(base_keys)
            if RANDOM.random() < 0.6:
                val = await db.get(k)
                await db.set(k, val + 1)
            else:
                await db.get(k)
    elif scenario == 'nested_mutation':
        await db.set('cfg', {"lvl1": {"counter": 0, "items": []}})
        for _ in range(keys):
            cfg = await db.get('cfg')
            cfg['lvl1']['counter'] += 1
            cfg['lvl1']['items'].append(_rand_key(4))
            await db.set('cfg', cfg)
    elif scenario == 'list_set_sync':
        await db.set('L', [0])
        await db.set('S', {0})
        for i in range(1, keys):
            lst = await db.get('L')
            st = await db.get('S')
            lst.append(i)
            st.add(i)
            await db.set('L', lst)
            await db.set('S', st)
    elif scenario == 'transaction_bulk':
        # 簡易: 逐次 (async トランザクション API は fast のみ対応可能だが統一性重視で省略)
        for i in range(keys):
            await db.set(_rand_key(), i)
    elif scenario == 'table_switch':
        # fast async の switch_table を利用 (ベースラッパは未実装なので try/except)
        for i in range(max(2, keys // 10)):
            t = f"t{i}"
            if hasattr(db, 'switch_table'):
                try:
                    await db.switch_table(t)
                except Exception:  # noqa: BLE001
                    pass
            await db.set(_rand_key(), i)
        if hasattr(db, 'switch_table'):
            try:
                await db.switch_table('main')
            except Exception:  # noqa: BLE001
                pass
    else:
        raise ValueError(f"Unknown scenario: {scenario}")


# ---------------------------- Benchmark harness ----------------------------

def run_sync_impl(impl: str, scenario: str, keys: int, tmpdir: Path) -> float:
    start = time.perf_counter()
    if impl == 'dictsqlite':
        dbpath = tmpdir / 'base.db'
        db = DictSQLite(str(dbpath))
    elif impl == 'fast':
        dbpath = tmpdir / 'fast.db'
        db = FastDictSQLite(str(dbpath))  # type: ignore
    else:
        raise ValueError(impl)
    try:
        REGISTRY.run(scenario, {"db": db, "keys": keys})
    finally:
        db.close()
    return time.perf_counter() - start


def run_async_impl(impl: str, scenario: str, keys: int, tmpdir: Path) -> float:
    async def _runner():
        if impl == 'dictsqlite':
            dbpath = tmpdir / 'ab.db'
            wrapper = AsyncDictSQLiteWrapper(str(dbpath))
            await async_run(wrapper, scenario, keys)
            await wrapper.close()
        elif impl == 'fast':
            if AsyncFastDictSQLite is None:
                return
            dbpath = tmpdir / 'af.db'
            try:
                adb = AsyncFastDictSQLite(str(dbpath))  # type: ignore
            except ImportError:
                # apsw 未導入など -> async fast をスキップ
                return
            await async_run(adb, scenario, keys)
            try:
                await adb.close()
            except Exception:  # noqa: BLE001
                pass
        else:
            raise ValueError(impl)

    start = time.perf_counter()
    asyncio.run(_runner())
    return time.perf_counter() - start


# ---------------------------- Formatting ----------------------------

def format_table(results: List[ScenarioResult]) -> str:
    # 集計: (scenario, impl, mode) -> list
    grouped: Dict[tuple, List[ScenarioResult]] = {}
    for r in results:
        grouped.setdefault((r.scenario, r.impl, r.mode), []).append(r)
    lines = []
    header = f"{'SCENARIO':20} {'IMPL':11} {'MODE':8} {'RUNS':>4} {'MED(s)':>8} {'MIN':>8} {'MAX':>8} {'OPS/s':>12}"
    lines.append(header)
    lines.append('-' * len(header))
    for (sc, impl, mode), lst in sorted(grouped.items()):
        secs = [x.seconds for x in lst]
        ops = lst[0].operations if lst else 0
        median = statistics.median(secs)
        line = f"{sc:20} {impl:11} {mode:8} {len(secs):4d} {median:8.4f} {min(secs):8.4f} {max(secs):8.4f} {ops/median:12.1f}"
        lines.append(line)
    return '\n'.join(lines)


def dump_json(results: List[ScenarioResult], path: Path):  # noqa: D401
    data = [asdict(r) | {"ops_per_sec": r.ops_per_sec} for r in results]
    path.write_text(_json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def dump_csv(results: List[ScenarioResult], path: Path):  # noqa: D401
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["scenario", "impl", "mode", "run", "seconds", "operations", "ops_per_sec"])
        for r in results:
            w.writerow([r.scenario, r.impl, r.mode, r.run, f"{r.seconds:.6f}", r.operations, f"{r.ops_per_sec:.2f}"])


# ---------------------------- Main ----------------------------

def parse_args():
    p = argparse.ArgumentParser(description="DictSQLite vs dictsqlite-fast benchmark")
    p.add_argument('--keys', type=int, default=2000, help='各シナリオの操作件数の代表値')
    p.add_argument('--runs', type=int, default=2, help='各 (impl,scenario,mode) の繰り返し回数 (中央値採用)')
    p.add_argument('--scenarios', default=','.join(REGISTRY.names()), help='カンマ区切りでシナリオ指定')
    p.add_argument('--only', default='dictsqlite,fast', help='実装指定: dictsqlite,fast')
    p.add_argument('--modes', default='sync,async', help='sync,async')
    p.add_argument('--json', dest='json_path', help='結果を JSON 出力するパス')
    p.add_argument('--csv', dest='csv_path', help='結果を CSV 出力するパス')
    p.add_argument('--quiet', action='store_true', help='表の標準出力を抑制')
    return p.parse_args()


def main():
    args = parse_args()
    scenarios = [s for s in args.scenarios.split(',') if s]
    impls = [i for i in args.only.split(',') if i]
    modes = [m for m in args.modes.split(',') if m]

    missing = []
    if 'fast' in impls and not FAST_AVAILABLE:
        missing.append('fast (package import failed)')
    if missing:
        print('WARNING: ' + ', '.join(missing))

    results: List[ScenarioResult] = []

    for scenario in scenarios:
        if scenario not in REGISTRY.names():
            print(f"Skip unknown scenario: {scenario}")
            continue
        for impl in impls:
            if impl == 'fast' and not FAST_AVAILABLE:
                continue
            for mode in modes:
                for run in range(1, args.runs + 1):
                    tmpdir = Path(tempfile.mkdtemp(prefix='ds_bench_'))
                    ops = args.keys
                    try:
                        if mode == 'sync':
                            elapsed = run_sync_impl(impl, scenario, args.keys, tmpdir)
                        elif mode == 'async':
                            # fast の async がない場合は skip
                            if impl == 'fast' and AsyncFastDictSQLite is None:
                                continue
                            elapsed = run_async_impl(impl, scenario, args.keys // 2, tmpdir)  # async はオーバーヘッドのため少し縮小
                            ops = args.keys // 2
                        else:
                            continue
                        results.append(ScenarioResult(scenario, impl, mode, run, elapsed, ops))
                        print(f"[OK] {scenario} {impl} {mode} run={run} {elapsed:.4f}s")
                    except Exception as e:  # noqa: BLE001
                        print(f"[ERR] {scenario} {impl} {mode} run={run}: {e}")
                    finally:
                        # 一時 DB は OS に任せて削除(クリティカルでない)
                        pass

    if not args.quiet:
        print('\n' + format_table(results))

    if args.json_path:
        dump_json(results, Path(args.json_path))
        print(f"JSON written -> {args.json_path}")
    if args.csv_path:
        dump_csv(results, Path(args.csv_path))
        print(f"CSV written -> {args.csv_path}")

    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())

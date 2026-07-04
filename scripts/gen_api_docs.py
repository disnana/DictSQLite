#!/usr/bin/env python3
"""Generate DictSQLite documentation pages for the VitePress site."""

from __future__ import annotations

import inspect
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SITE = DOCS / "site"
V2_DOCS = ROOT / "dictsqlite_v2" / "dictsqlite" / "docs"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = inspect.cleandoc(content).strip()
    path.write_text(text + "\n", encoding="utf-8")


def read_v2_doc(name: str, fallback: str) -> str:
    path = V2_DOCS / name
    return path.read_text(encoding="utf-8") if path.exists() else fallback


def release_notes(lang: str) -> str:
    changelog = ROOT / ("CHANGELOG.ja.md" if lang == "ja" else "CHANGELOG.md")
    text = changelog.read_text(encoding="utf-8")
    match = re.search(r"## \[2\.1\.3\].*?(?=\n---\n\n## |\Z)", text, re.S)
    if match:
        return match.group(0).strip()
    return "## 2.1.3\n\n- Stability, performance, benchmark, and workflow updates."


def hero(lang: str) -> str:
    ja = lang == "ja"
    return f"""---
    layout: home

    hero:
      name: "DictSQLite"
      text: "{'高速・安全な Python 辞書型 SQLite ストア' if ja else 'Fast, safe SQLite-backed Python dictionaries'}"
      tagline: "{'Rust/PyO3 実装、非同期 API、暗号化、Safe Pickle、テーブル機能、ベンチマークを備えた永続化辞書です。' if ja else 'A Rust/PyO3 persistent dictionary with async APIs, encryption, Safe Pickle, table support, and benchmark tooling.'}"
      actions:
        - theme: brand
          text: {'はじめる' if ja else 'Get Started'}
          link: {'./guide' if ja else '/en/guide'}
        - theme: alt
          text: API
          link: {'./api' if ja else '/en/api'}
        - theme: alt
          text: Benchmark
          link: {'./performance' if ja else '/en/performance'}

    features:
      - title: "{'dict として使える' if ja else 'Use it like a dict'}"
        details: "{'get/set/delete/batch 操作を Python の辞書に近い感覚で扱えます。' if ja else 'Get, set, delete, and batch operations feel close to normal Python dictionaries.'}"
      - title: "{'安全性と永続化' if ja else 'Safety and persistence'}"
        details: "{'AES-256-GCM、Safe Pickle、lazy/writethrough/memory モードを選べます。' if ja else 'Choose AES-256-GCM encryption, Safe Pickle, and lazy, writethrough, or memory persistence.'}"
      - title: "{'非同期とテーブル' if ja else 'Async and table support'}"
        details: "{'AsyncDictSQLite と TableProxy で asyncio や名前空間分離に対応します。' if ja else 'AsyncDictSQLite and TableProxy support asyncio workflows and separated namespaces.'}"
      - title: "{'測定しやすい' if ja else 'Benchmark-ready'}"
        details: "{'サイズ、件数、バッチ、保存形式、永続化モード別に性能を比較できます。' if ja else 'Compare performance by size, quantity, batch size, storage mode, and persistence mode.'}"
    ---"""


def guide(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {'ガイド' if ja else 'Guide'}

    {'DictSQLite は、SQLite をバックエンドにした高速な永続化辞書です。v2 は Rust/PyO3 実装で、同期 API と非同期 API の両方を提供します。' if ja else 'DictSQLite is a fast persistent dictionary backed by SQLite. Version 2 is implemented with Rust/PyO3 and provides both sync and async APIs.'}

    ## {'インストール' if ja else 'Installation'}

    ```bash
    pip install dictsqlite
    ```

    ## {'最小例' if ja else 'Minimal example'}

    ```python
    from dictsqlite import DictSQLite

    db = DictSQLite("cache.db")
    db["user:1"] = {{"name": "Alice", "score": 42}}

    print(db["user:1"])
    db.close()
    ```

    ## {'非同期 API' if ja else 'Async API'}

    ```python
    import asyncio
    from dictsqlite import AsyncDictSQLite

    async def main():
        db = AsyncDictSQLite("cache.db")
        await db.set("job:1", {{"status": "queued"}})
        print(await db.get("job:1"))
        await db.close()

    asyncio.run(main())
    ```

    ## {'保存形式と永続化モード' if ja else 'Storage and persistence modes'}

    - `storage_mode`: `pickle`, `jsonb`, `json`, `bytes`
    - `persist_mode`: `memory`, `lazy`, `writethrough`
    - `table_mode`: `prefix`, `separate`

    {'Safe Pickle や暗号化が必要な場合は、信頼境界に合わせて設定してください。大量の書き込みでは `lazy`、確実な即時保存では `writethrough` が向いています。' if ja else 'Use Safe Pickle and encryption according to your trust boundary. `lazy` is useful for heavy write throughput, while `writethrough` is best when each write must be persisted immediately.'}
    """


def api(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    ---
    outline: [2, 3]
    ---

    # {'API リファレンス' if ja else 'API Reference'}

    ## `DictSQLite`

    ```python
    from dictsqlite import DictSQLite

    db = DictSQLite(
        "data.db",
        storage_mode="pickle",
        persist_mode="lazy",
        table_mode="prefix",
        safe_pickle=True,
    )
    ```

    | {'操作' if ja else 'Operation'} | {'説明' if ja else 'Description'} |
    |---|---|
    | `db[key] = value` / `db.set(key, value)` | {'値を保存します。' if ja else 'Store a value.'} |
    | `db[key]` / `db.get(key, default=None)` | {'値を取得します。' if ja else 'Read a value.'} |
    | `del db[key]` / `db.delete(key)` | {'キーを削除します。' if ja else 'Delete a key.'} |
    | `db.batch_set(dict)` | {'複数キーをまとめて保存します。' if ja else 'Write many keys at once.'} |
    | `db.batch_get(keys)` | {'複数キーをまとめて取得します。' if ja else 'Read many keys at once.'} |
    | `db.clear()` | {'全データを削除します。' if ja else 'Remove all entries.'} |
    | `db.flush()` | {'lazy buffer をストレージへ反映します。' if ja else 'Flush lazy writes to storage.'} |
    | `db.close()` | {'flush してリソースを閉じます。' if ja else 'Flush and close resources.'} |

    ## `AsyncDictSQLite`

    ```python
    from dictsqlite import AsyncDictSQLite

    db = AsyncDictSQLite("data.db")
    await db.set("key", "value")
    value = await db.get("key")
    await db.close()
    ```

    {'非同期版は `asyncio` ワークロード向けです。バッチ取得ではストレージの一括読み込みを利用し、キャッシュミス時の SQLite 往復を抑えます。' if ja else 'The async API is designed for asyncio workloads. Batch reads use bulk storage reads to reduce SQLite round trips on cache misses.'}

    ## `TableProxy`

    ```python
    users = db.table("users")
    users["alice"] = {{"role": "admin"}}
    ```

    {'テーブルは名前空間を分けるための API です。`prefix` モードではキー接頭辞、`separate` モードでは SQLite の別テーブルを使います。' if ja else 'Tables provide namespaced access. `prefix` mode stores prefixed keys, while `separate` mode uses separate SQLite tables.'}

    ## {'主なオプション' if ja else 'Key options'}

    | {'オプション' if ja else 'Option'} | {'値' if ja else 'Values'} |
    |---|---|
    | `storage_mode` | `pickle`, `jsonb`, `json`, `bytes` |
    | `persist_mode` | `memory`, `lazy`, `writethrough` |
    | `table_mode` | `prefix`, `separate` |
    | `safe_pickle` | `True` / `False` |
    | `encryption_password` | `str` / `None` |
    | `compression` | {'設定により有効化' if ja else 'Enabled through configuration'} |
    """


def storage(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {'保存形式と永続化' if ja else 'Storage and Persistence'}

    ## `storage_mode`

    - `pickle`: {'Python オブジェクトを広く扱えます。Safe Pickle 推奨です。' if ja else 'Supports broad Python objects. Safe Pickle is recommended.'}
    - `jsonb`: {'JSON 互換データ向けの MessagePack 系保存形式です。' if ja else 'MessagePack-style storage for JSON-compatible data.'}
    - `json`: {'可読性を優先する JSON 保存です。' if ja else 'Human-readable JSON storage.'}
    - `bytes`: {'バイナリをそのまま保存します。' if ja else 'Stores bytes as-is.'}

    ## `persist_mode`

    - `memory`: {'プロセス内のみ。高速ですが終了時に消えます。' if ja else 'In-process only. Fast, but data is not persisted after exit.'}
    - `lazy`: {'バッファリングしてまとめて書き込みます。高スループット向けです。' if ja else 'Buffers writes and flushes them in batches. Best for throughput.'}
    - `writethrough`: {'書き込みごとに永続化します。耐久性優先です。' if ja else 'Persists every write immediately. Best for durability.'}

    ## {'安定化ポイント' if ja else 'Stability notes'}

    {'v2.1.3 では flush 失敗時の再投入、delete/clear 後のバッファ復活防止、separate table の lazy 永続化を重点的に修正しています。' if ja else 'Version 2.1.3 hardens failed-flush requeueing, prevents buffered writes from returning after delete/clear, and fixes lazy persistence for separate tables.'}
    """


def async_page(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {'非同期 API' if ja else 'Async API'}

    ```python
    from dictsqlite import AsyncDictSQLite

    db = AsyncDictSQLite("async.db", persist_mode="lazy")
    await db.set("k", "v")
    value = await db.get("k")
    await db.flush()
    await db.close()
    ```

    ## {'バッチ操作' if ja else 'Batch operations'}

    ```python
    await db.batch_set({{"a": 1, "b": 2}})
    values = await db.batch_get(["a", "b", "missing"])
    ```

    {'v2.1.3 では batch get のキャッシュミスを一括読み込みに寄せ、SQLite への細かい往復を減らしています。' if ja else 'Version 2.1.3 routes batch-get cache misses through bulk reads, reducing small SQLite round trips.'}

    ## {'終了処理' if ja else 'Shutdown'}

    {'`lazy` モードでは `flush()` または `close()` を呼んでください。flush 失敗時は保留データを戻して再試行できるようにしています。' if ja else 'Call `flush()` or `close()` in `lazy` mode. If a flush fails, pending writes are restored so they can be retried.'}
    """


def security(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {'安全性' if ja else 'Safety'}

    ## Safe Pickle

    {'pickle は便利ですが、信頼できないデータには危険です。DictSQLite v2 は Safe Pickle ポリシーで許可型を制限できます。' if ja else 'Pickle is convenient but unsafe for untrusted data. DictSQLite v2 can restrict allowed types with Safe Pickle policies.'}

    ```python
    db = DictSQLite("safe.db", storage_mode="pickle", safe_pickle=True)
    ```

    ## {'暗号化' if ja else 'Encryption'}

    ```python
    db = DictSQLite("secure.db", encryption_password="change-me")
    ```

    {'暗号化は AES-256-GCM を使います。パスワードや鍵はソースコードに直書きせず、環境変数やシークレット管理に置いてください。' if ja else 'Encryption uses AES-256-GCM. Keep passwords and keys in environment variables or secret management, not source code.'}

    ## {'推奨' if ja else 'Recommendations'}

    - {'信頼できない pickle データを読み込まない' if ja else 'Do not load untrusted pickle data'}
    - {'永続化が必要な処理では `close()` を必ず呼ぶ' if ja else 'Always call `close()` when persistence matters'}
    - {'GitHub Actions では benchmark alert を情報表示に留める' if ja else 'Keep benchmark alerts informational in GitHub Actions'}
    """


def performance(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {'パフォーマンスとベンチマーク' if ja else 'Performance and Benchmarks'}

    {'ベンチマークは v2 パッケージ配下で実行します。quick/full/stress プロファイルで測定量を切り替えられます。' if ja else 'Benchmarks run from the v2 package directory. Use quick, full, and stress profiles to control coverage.'}

    ```bash
    cd dictsqlite_v2/dictsqlite
    python benchmark/benchmark_all.py --profile quick
    python benchmark/analyze_results.py
    ```

    ## {'測定軸' if ja else 'Measured axes'}

    - {'データサイズ' if ja else 'Data size'}
    - {'レコード数' if ja else 'Record count'}
    - {'バッチサイズ' if ja else 'Batch size'}
    - {'保存形式と永続化モード' if ja else 'Storage and persistence modes'}
    - {'cold read / hot write / delete / clear / threaded access' if ja else 'Cold reads, hot writes, delete, clear, and threaded access'}

    ## GitHub Actions

    {'自動・手動の performance workflow は CSV、画像、GitHub benchmark 用 JSON、Actions Summary の Markdown を出力します。runner 差による誤検知を避けるため、比較は警告ではなく情報表示です。' if ja else 'The automatic and manual performance workflows produce CSV, images, GitHub benchmark JSON, and Markdown in the Actions Summary. Comparison is informational to avoid false alerts from runner variance.'}
    """


def release(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {'リリース' if ja else 'Release'}

    {release_notes(lang)}

    ## {'リリース前チェック' if ja else 'Pre-release checks'}

    ```bash
    cd dictsqlite_v2/dictsqlite
    cargo test
    python -m py_compile benchmark/benchmark_all.py benchmark/analyze_results.py benchmark/export_for_github_action_benchmark.py
    ```

    {'ビルドと公開は maintainer 環境で行います。ドキュメントは Actions の deploy workflow で自動生成・公開できます。' if ja else 'Build and publish from the maintainer environment. Documentation can be generated and deployed by the docs deploy workflow.'}
    """


def changelog(lang: str) -> str:
    path = ROOT / ("CHANGELOG.ja.md" if lang == "ja" else "CHANGELOG.md")
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^> \*\*.*(?:version|版)\*\*:.*\n\n?", "", text, flags=re.M | re.I)
    text = re.sub(r"^.*others/release-notes.*\n\n?", "", text, flags=re.M)
    return text


def readme(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {'DictSQLite ドキュメント' if ja else 'DictSQLite Documentation'}

    {'このディレクトリは自動生成されます。編集する場合は `scripts/gen_api_docs.py` を更新してください。' if ja else 'This directory is generated. Update `scripts/gen_api_docs.py` when changing generated documentation.'}

    - [{'ガイド' if ja else 'Guide'}](guide/guide.md)
    - [API](api/dictsqlite.md)
    - [{'保存形式と永続化' if ja else 'Storage and persistence'}](guide/storage.md)
    - [{'非同期 API' if ja else 'Async API'}](guide/async.md)
    - [{'安全性' if ja else 'Safety'}](guide/security.md)
    - [{'パフォーマンス' if ja else 'Performance'}](guide/performance.md)
    - [{'リリース' if ja else 'Release'}](guide/release.md)
    """


def config() -> str:
    return """
    import { defineConfig } from 'vitepress'

    export default defineConfig({
      title: 'DictSQLite',
      description: 'Fast, safe SQLite-backed Python dictionaries',
      base: '/',
      cleanUrls: true,
      themeConfig: {
        nav: [
          { text: 'ホーム', link: '/' },
          { text: 'ガイド', link: '/guide' },
          { text: 'API', link: '/api' },
          { text: 'Benchmark', link: '/performance' },
          { text: 'Release', link: '/release' }
        ],
        sidebar: [
          {
            text: 'DictSQLite',
            items: [
              { text: 'ガイド', link: '/guide' },
              { text: 'API', link: '/api' },
              { text: '保存形式と永続化', link: '/storage' },
              { text: '非同期 API', link: '/async' },
              { text: '安全性', link: '/security' },
              { text: 'パフォーマンス', link: '/performance' },
              { text: 'リリース', link: '/release' },
              { text: '変更履歴', link: '/changelog' }
            ]
          }
        ],
        socialLinks: [
          { icon: 'github', link: 'https://github.com/disnana/DictSQLite' }
        ]
      },
      locales: {
        root: {
          label: '日本語',
          lang: 'ja-JP'
        },
        en: {
          label: 'English',
          lang: 'en-US',
          link: '/en/',
          themeConfig: {
            nav: [
              { text: 'Home', link: '/en/' },
              { text: 'Guide', link: '/en/guide' },
              { text: 'API', link: '/en/api' },
              { text: 'Benchmark', link: '/en/performance' },
              { text: 'Release', link: '/en/release' }
            ],
            sidebar: [
              {
                text: 'DictSQLite',
                items: [
                  { text: 'Guide', link: '/en/guide' },
                  { text: 'API', link: '/en/api' },
                  { text: 'Storage and Persistence', link: '/en/storage' },
                  { text: 'Async API', link: '/en/async' },
                  { text: 'Safety', link: '/en/security' },
                  { text: 'Performance', link: '/en/performance' },
                  { text: 'Release', link: '/en/release' },
                  { text: 'Changelog', link: '/en/changelog' }
                ]
              }
            ]
          }
        }
      }
    })
    """


def package_json() -> str:
    return """
    {
      "name": "dictsqlite-docs",
      "version": "2.1.3",
      "private": true,
      "type": "module",
      "scripts": {
        "docs:gen": "python ../../scripts/gen_api_docs.py",
        "dev": "vitepress dev",
        "build": "vitepress build",
        "preview": "vitepress preview"
      },
      "devDependencies": {
        "@tailwindcss/postcss": "^4.2.2",
        "autoprefixer": "^10.4.27",
        "postcss": "^8.5.9",
        "tailwindcss": "^4.2.2",
        "vite": "^6.4.3",
        "vitepress": "^1.6.4",
        "vue": "^3.5.32"
      },
      "overrides": {
        "vite": "^6.4.3"
      }
    }
    """


PAGES = {
    "index.md": hero,
    "guide.md": guide,
    "api.md": api,
    "storage.md": storage,
    "async.md": async_page,
    "security.md": security,
    "performance.md": performance,
    "release.md": release,
    "changelog.md": changelog,
}


def main() -> None:
    for lang, base in [("ja", SITE), ("en", SITE / "en")]:
        for filename, generator in PAGES.items():
            write(base / filename, generator(lang))

    for lang, base in [("ja", DOCS / "ja"), ("en", DOCS / "en")]:
        write(base / "README.md", readme(lang))
        write(base / "api" / "dictsqlite.md", api(lang))
        write(base / "guide" / "guide.md", guide(lang))
        write(base / "guide" / "storage.md", storage(lang))
        write(base / "guide" / "async.md", async_page(lang))
        write(base / "guide" / "security.md", security(lang))
        write(base / "guide" / "performance.md", performance(lang))
        write(base / "guide" / "release.md", release(lang))

    write(SITE / ".vitepress" / "config.mts", config())
    write(SITE / "package.json", package_json())
    write(SITE / "public" / "CNAME", "dictsqlite.disnana.com")

    print("DictSQLite docs generated.")


if __name__ == "__main__":
    main()

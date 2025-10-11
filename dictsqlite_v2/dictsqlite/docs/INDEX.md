DictSQLite v4 — Docs Index / ドキュメント目次

English
-------
- README_EN.md — Quick start and overview (English)
- EXAMPLES_EN.md — Practical examples: sync/async/encryption/bulk
- MIGRATION_FROM_1.8.8_EN.md — Migration guide from v1.8.8 to v4.x (English)

日本語
-----
- README_JP.md — クイックスタート（日本語）
- EXAMPLES_JP.md — 実用例: 同期/非同期/暗号化/一括挿入
- MIGRATION_FROM_1.8.8_JP.md — v1.8.8 から v4.x への移行ガイド（日本語）

Notes
-----
- The examples and migration guides assume the native extension is built. If you see a RuntimeError mentioning the native extension, follow the build instructions in the repository root (or run `maturin develop --release` in development environments).
- The repository includes examples under `examples/` — refer to them for runnable migration demonstrations (for example: `examples/v4.2_migration_example.py`).

ファイル配置（相対パス）
---------------------
- dictsqlite/docs/README_EN.md
- dictsqlite/docs/EXAMPLES_EN.md
- dictsqlite/docs/MIGRATION_FROM_1.8.8_EN.md
- dictsqlite/docs/README_JP.md
- dictsqlite/docs/EXAMPLES_JP.md
- dictsqlite/docs/MIGRATION_FROM_1.8.8_JP.md
- dictsqlite/Pypi.md (updated to reference these docs)

If you'd like, I can also:
- generate a small migration helper script that scans your codebase and suggests replacements (e.g. `password=` -> `encryption_password=`), or
- run the examples in a controlled environment (if you want me to run tests/builds here, tell me and I'll run the appropriate commands).

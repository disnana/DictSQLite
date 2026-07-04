# Release

## [2.1.3] - 2026-07-04

### Fixed
- Hardened write-buffer flushing so pending writes are restored if storage flush fails.
- Fixed delete/clear paths that could allow pending buffered writes to reappear after removal.
- Fixed table-name prefix handling in async deletion paths.
- Fixed separate-table persistence so durable modes write table data directly instead of losing lazy-mode table updates.
- Fixed compression/decompression consistency for separate-table storage.
- Updated `anyhow` lockfile entry to `1.0.103` to resolve RUSTSEC-2026-0190.

### Improved
- Added bulk storage reads for batch cache misses to reduce SQLite round trips.
- Reworked warm-cache byte accounting to avoid O(n) cache scans on hot read promotion.
- Improved benchmark coverage across data sizes, batch sizes, record counts, persistence modes, storage modes, table modes, cold reads, mutation operations, and threaded access.
- Improved benchmark graph generation with compact labels, aggregation, p95 latency views, and less label overlap.
- Added GitHub Actions benchmark CSV/graph artifacts, benchmark-history export, and Markdown run summaries.
- Configured GitHub benchmark comparison as informational only to avoid false alerts from runner variance.

### Changed
- Bumped package version to `2.1.3`.

## Pre-release checks

```bash
cd dictsqlite_v2/dictsqlite
cargo test
python -m py_compile benchmark/benchmark_all.py benchmark/analyze_results.py benchmark/export_for_github_action_benchmark.py
```

Build and publish from the maintainer environment. Documentation can be generated and deployed by the docs deploy workflow.

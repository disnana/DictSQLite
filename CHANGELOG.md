# Changelog

All notable changes to DictSQLite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **日本語版**: [CHANGELOG.ja.md](./CHANGELOG.ja.md)

---

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

---

## [2.1.1] - 2026-03-03

### Security
- Updated pyo3 to v0.28.2 (Rust-Python bindings security and compatibility fixes)
- Updated pythonize to 0.28 (aligned with pyo3 0.28)
- Updated papaya to 0.2 (concurrent hash map security fixes)
- Updated base64 to 0.22

### Changed
- Updated actions/cache to v5
- Updated actions/checkout to v6
- Updated actions/setup-python to v6
- Updated google/osv-scanner-action to v2.3.3
- Updated criterion to 0.8 (benchmarking dependency)

---

## [2.1.0] - 2026-02-11

### Security
- Fixed vulnerabilities in used libraries

### Fixed
- Fixed internal bugs

---

## [2.0.9] - 2026-01-08

### Changed
- Internal code organization and cleanup for improved code quality and maintainability

### Note
- No functional changes or improvements
- No performance impact
- API remains identical to v2.0.8
- Full backward compatibility with v2.0.8

---

## [2.0.8] - 2026-01-03

### Added
- **ARM Package Distribution**: Pre-built packages for ARM64 (aarch64) and ARM32 (armv7l)
- Windows on ARM (ARM64) package support
- Multi-architecture CI/CD pipeline with GitHub Actions
- Automated PyPI deployment for all architectures

### Changed
- PyPI package distribution now includes ARM architecture wheels
- GitHub Actions automated build and release workflow

### Improved
- Installation on ARM platforms (no compilation needed)
- Cross-platform deployment consistency

### Note
- Functionality and API remain identical across all architectures
- Performance characteristics maintained from v2.0.7
- ARM benchmark testing under consideration for future releases

---

## [2.0.7] - 2025-12-29

### Added
- Updated dependencies to latest versions (pyo3 0.27.2, dashmap 6.1, tokio 1.42)
- Enhanced documentation with migration guide and examples

### Changed
- Improved Python-Rust data conversion performance
- Enhanced async runtime stability

### Fixed
- Fixed test stability issues with pytest-v6
- Resolved import errors in benchmark tests

---

## [2.0.6] - 2025-12-06

### Added
- Final optimization achieving 1.31x better overall performance than fastest version
- LRU tracking optimization for Memory/Lazy modes

### Changed
- Write performance improved to 154K ops/sec (4.4x improvement)
- Read performance: 8.42x faster than fastest version
- Bulk insert optimization with single transaction

### Performance
- Read: 510,256 ops/sec (WriteThrough mode)
- Mixed operations: 285,657 ops/sec (Lazy mode)

---

## [2.0.5] - 2025-11-15

### Added
- Python 3.13 compatibility preparation

### Changed
- Updated pyo3 to 0.26 for improved Python-Rust data conversion
- Updated dashmap to 6.0 for better concurrent access performance
- Updated tokio to 1.40 for enhanced async processing

### Performance
- Write operations: ~5% faster
- Concurrent operations: ~12% faster

---

## [2.0.4] - 2025-11-01

### Security
- **CRITICAL**: Fixed RUSTSEC-2025-0020 (buffer overflow in pyo3 0.20.3)
- Upgraded pyo3 to 0.24.1 with Bound API support
- Fixed sensitive data logging in examples
- Replaced unsafe tempfile.mktemp() with mkstemp()

### Security Validation
- Cargo Audit: 0 vulnerabilities (was 1)
- CodeQL (Python): 0 alerts (was 5)
- CodeQL (Rust): 0 alerts

---

## [2.0.3] - 2025-10-25

### Fixed
- **CRITICAL**: Resolved database lock issues in async operations
- Implemented queue-based operation serialization
- Fixed concurrent access conflicts

### Added
- Persistent ThreadPoolExecutor for stable async operations
- NORMAL locking mode for better concurrency

### Performance
- 50 concurrent writes: 10,027 ops/s
- 50 concurrent reads: 145,345 ops/s
- Cache hit rate: 80%

---

## [2.0.2] - 2025-10-20

### Added
- Dictionary-compatible API methods
  - `items()` - Returns iterator of (key, value) tuples
  - `values()` - Returns iterator of all values
  - `update(dict)` - Bulk update from dictionary
  - `pop(key, default)` - Remove key and return value
  - `setdefault(key, default)` - Set default if key doesn't exist

### Changed
- Enhanced compatibility with v1.8.8 codebases
- All persistence modes (Memory/Lazy/WriteThrough) support new methods

---

## [2.0.1] - 2025-10-15

### Added
- AsyncDictSQLite persistence implementation
- LRU cache eviction for automatic memory management
- Storage fallback functionality

### Changed
- Improved async processing stability
- Enhanced cache miss handling

### Fixed
- Memory leak prevention with LRU eviction

---

## [2.0.0] - 2025-10-09

### Added
- **MAJOR**: Complete rewrite in Rust using PyO3 bindings
- True Python asyncio support with awaitable methods
- AES-256-GCM encryption (upgraded from AES-CBC)
- Safe Pickle validation with whitelist-based verification
- Multiple persistence modes (Memory/Lazy/WriteThrough)
- LRU cache for efficient memory management

### Performance
- Async writes: 300x faster (30s → 0.1s for 1000 items)
- Sync writes: 43x faster (29.79K → 1.30M ops/sec)
- Batch reads: 5-10x faster

### Changed
- Mutex lock count reduced 100x in async operations
- SQL transaction count reduced 100x
- PBKDF2 key derivation with 100,000 iterations

### Security
- AES-256-GCM with authenticated encryption
- SQL injection protection with parameterized queries
- Integrity verification with GCM tags

---

## [1.8.8] - 2025-09-20

### Added
- Experimental JSON mode implementation
- AI-generated documentation (Japanese and English)

### Fixed
- Fixed schema parameter type annotation (bool → str | None)
- Fixed multiple Pylint warnings

---

## [1.8.7] - 2025-09-20

### Fixed
- PyPI package fixes
- License file updates

---

## [1.8.6] - 2025-09-18

### Security
- **CRITICAL**: Fixed pickle deserialization vulnerability

---

## [1.8.5] - 2025-09-18

### Added
- AI-generated comprehensive documentation
- Extended test coverage

---

## [1.8.4] - 2025-09-18

### Changed
- Code quality improvements
- Stability enhancements

---

## [1.8.3] - 2025-09-18

### Added
- Experimental security updates

---

## [1.8.2] - 2025-09-15

### Fixed
- Python version support corrections

---

## [1.8.1] - 2025-09-15

### Changed
- File organization improvements

### Fixed
- Various bug fixes

---

## [1.8.0] - 2025-09-13

### Added
- **MAJOR**: Initial stable release

---

## [1.7.3] - 2025-09-10

### Added
- Pydantic integration
- WAL mode support
- Preparation for v2.0

---

## [1.3.7] - 2025-08-15

### Added
- Performance improvements
- Feature enhancements

---

## [1.3.3] - 2025-08-01

### Added
- **Initial practical release** - Core functionality established

---

## Legend

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security-related changes
- **Performance**: Performance improvements

---

For detailed release notes, see [others/release-notes/](./others/release-notes/)

[2.1.3]: https://github.com/disnana/DictSQLite/compare/v2.1.1...v2.1.3
[2.1.1]: https://github.com/disnana/DictSQLite/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/disnana/DictSQLite/compare/v2.0.9...v2.1.0
[2.0.9]: https://github.com/disnana/DictSQLite/compare/v2.0.8...v2.0.9
[2.0.8]: https://github.com/disnana/DictSQLite/compare/v2.0.7...v2.0.8
[2.0.7]: https://github.com/disnana/DictSQLite/compare/v2.0.6...v2.0.7
[2.0.6]: https://github.com/disnana/DictSQLite/compare/v2.0.5...v2.0.6
[2.0.5]: https://github.com/disnana/DictSQLite/compare/v2.0.4...v2.0.5
[2.0.4]: https://github.com/disnana/DictSQLite/compare/v2.0.3...v2.0.4
[2.0.3]: https://github.com/disnana/DictSQLite/compare/v2.0.2...v2.0.3
[2.0.2]: https://github.com/disnana/DictSQLite/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/disnana/DictSQLite/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/disnana/DictSQLite/compare/v1.8.8...v2.0.0
[1.8.8]: https://github.com/disnana/DictSQLite/compare/v1.8.7...v1.8.8
[1.8.7]: https://github.com/disnana/DictSQLite/compare/v1.8.6...v1.8.7
[1.8.6]: https://github.com/disnana/DictSQLite/compare/v1.8.5...v1.8.6
[1.8.5]: https://github.com/disnana/DictSQLite/compare/v1.8.4...v1.8.5
[1.8.4]: https://github.com/disnana/DictSQLite/compare/v1.8.3...v1.8.4
[1.8.3]: https://github.com/disnana/DictSQLite/compare/v1.8.2...v1.8.3
[1.8.2]: https://github.com/disnana/DictSQLite/compare/v1.8.1...v1.8.2
[1.8.1]: https://github.com/disnana/DictSQLite/compare/v1.8.0...v1.8.1
[1.8.0]: https://github.com/disnana/DictSQLite/compare/v1.7.3...v1.8.0
[1.7.3]: https://github.com/disnana/DictSQLite/compare/v1.3.7...v1.7.3
[1.3.7]: https://github.com/disnana/DictSQLite/compare/v1.3.3...v1.3.7
[1.3.3]: https://github.com/disnana/DictSQLite/releases/tag/v1.3.3


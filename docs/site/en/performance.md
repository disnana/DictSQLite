# Performance and Benchmarks

Benchmarks run from the v2 package directory. Use quick, full, and stress profiles to control coverage.

```bash
cd dictsqlite_v2/dictsqlite
python benchmark/benchmark_all.py --profile quick
python benchmark/analyze_results.py
```

## Measured axes

- Data size
- Record count
- Batch size
- Storage and persistence modes
- Cold reads, hot writes, delete, clear, and threaded access

## GitHub Actions

The automatic and manual performance workflows produce CSV, images, GitHub benchmark JSON, and Markdown in the Actions Summary. Comparison is informational to avoid false alerts from runner variance.

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use dictsqlite_v3::DictSQLiteV3;
use std::sync::Arc;
use std::thread;

fn benchmark_sequential_writes(c: &mut Criterion) {
    let mut group = c.benchmark_group("sequential_writes");

    for size in [1000, 10_000, 100_000].iter() {
        group.throughput(Throughput::Elements(*size as u64));
        group.bench_with_input(BenchmarkId::from_parameter(size), size, |b, &size| {
            b.iter(|| {
                let db = DictSQLiteV3::new(":memory:".to_string(), size, false).unwrap();

                for i in 0..size {
                    let key = format!("key_{}", i);
                    let value = format!("value_{}", i).into_bytes();
                    db.set(key, value).unwrap();
                }
            });
        });
    }
    group.finish();
}

fn benchmark_sequential_reads(c: &mut Criterion) {
    let mut group = c.benchmark_group("sequential_reads");

    for size in [1000, 10_000, 100_000].iter() {
        // Pre-populate data
        let db = DictSQLiteV3::new(":memory:".to_string(), *size, false).unwrap();

        for i in 0..*size {
            let key = format!("key_{}", i);
            let value = format!("value_{}", i).into_bytes();
            db.set(key, value).unwrap();
        }

        group.throughput(Throughput::Elements(*size as u64));
        group.bench_with_input(BenchmarkId::from_parameter(size), size, |b, &size| {
            b.iter(|| {
                for i in 0..size {
                    let key = format!("key_{}", i);
                    black_box(db.get(key, pyo3::Python::acquire_gil().python()).unwrap());
                }
            });
        });
    }
    group.finish();
}

fn benchmark_concurrent_writes(c: &mut Criterion) {
    let mut group = c.benchmark_group("concurrent_writes");

    for threads in [2, 4, 8].iter() {
        group.bench_with_input(
            BenchmarkId::from_parameter(threads),
            threads,
            |b, &num_threads| {
                b.iter(|| {
                    let db = Arc::new(
                        DictSQLiteV3::new(":memory:".to_string(), 100_000, false).unwrap(),
                    );

                    let handles: Vec<_> = (0..num_threads)
                        .map(|thread_id| {
                            let db_clone = Arc::clone(&db);
                            thread::spawn(move || {
                                for i in 0..10_000 {
                                    let key = format!("key_{}_{}", thread_id, i);
                                    let value = format!("value_{}_{}", thread_id, i).into_bytes();
                                    db_clone.set(key, value).unwrap();
                                }
                            })
                        })
                        .collect();

                    for handle in handles {
                        handle.join().unwrap();
                    }
                });
            },
        );
    }
    group.finish();
}

fn benchmark_mixed_operations(c: &mut Criterion) {
    c.bench_function("mixed_ops_100k", |b| {
        b.iter(|| {
            let db = DictSQLiteV3::new(":memory:".to_string(), 100_000, false).unwrap();

            // 50% writes, 50% reads
            for i in 0..50_000 {
                let key = format!("key_{}", i);
                let value = format!("value_{}", i).into_bytes();
                db.set(key.clone(), value).unwrap();
                black_box(db.get(key, pyo3::Python::acquire_gil().python()).unwrap());
            }
        });
    });
}

criterion_group!(
    benches,
    benchmark_sequential_writes,
    benchmark_sequential_reads,
    benchmark_concurrent_writes,
    benchmark_mixed_operations
);

criterion_main!(benches);

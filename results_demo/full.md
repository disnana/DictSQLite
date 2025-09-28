# Benchmark Summary

Keys per scenario: 300
Runs: 1

| Scenario | dictsqlite.async | dictsqlite.sync | fast.async | fast.sync |
|---|---|---|---|---|
| bulk_set | 342 | 356 | 65,018 | 103,284 |
| large_insert | 374 | 424 | 3,231 | 8,265 |
| mixed_update | 478 | 538 | 2,741 | 24,955 |
| random_get | 361 | 403 | 3,179 | 20,563 |
| small_insert | 403 | 304 | 5,513 | 23,547 |
| table_switch | 4,219 | 2,073 | 17,179 | 44,019 |
| transaction_bulk | 428 | 32,878 | 76,396 | 93,399 |

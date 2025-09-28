# Benchmark Summary

Keys per scenario: 300
Runs: 1

| Scenario | dictsqlite.async | dictsqlite.sync | fast.async | fast.sync |
|---|---|---|---|---|
| bulk_set | 346 | 357 | 33,744 | 40,623 |
| large_insert | 382 | 404 | 4,975 | 5,820 |
| mixed_update | 379 | 502 | 2,168 | 4,527 |
| random_get | 355 | 390 | 2,966 | 4,686 |
| small_insert | 417 | 430 | 10,023 | 10,098 |
| table_switch | 3,584 | 1,558 | 9,706 | 15,209 |
| transaction_bulk | 400 | 37,324 | 26,596 | 36,571 |

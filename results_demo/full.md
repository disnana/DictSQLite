# Benchmark Summary

Keys per scenario: 300
Runs: 1

| Scenario | dictsqlite.async | dictsqlite.sync | fast.async | fast.sync |
|---|---|---|---|---|
| bulk_set | 370 | 429 | 91,982 | 147,586 |
| large_insert | 395 | 430 | 8,243 | 8,567 |
| mixed_update | 459 | 283 | 3,769 | 27,212 |
| random_get | 381 | 366 | 5,634 | 27,497 |
| small_insert | 420 | 414 | 19,252 | 27,452 |
| table_switch | 4,177 | 2,089 | 21,089 | 50,273 |
| transaction_bulk | 420 | 33,448 | 96,871 | 128,738 |

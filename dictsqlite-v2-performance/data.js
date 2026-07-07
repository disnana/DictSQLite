window.BENCHMARK_DATA = {
  "lastUpdate": 1783405986086,
  "repoUrl": "https://github.com/disnana/DictSQLite",
  "entries": {
    "Benchmark": [
      {
        "commit": {
          "author": {
            "email": "83683593+harumaki4649@users.noreply.github.com",
            "name": "harumaki4649",
            "username": "harumaki4649"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "0590ea684e54256ebe2be585f010e5973c639a15",
          "message": "Merge pull request #292 from disnana/dev\n\nno message",
          "timestamp": "2026-07-06T15:11:37+09:00",
          "tree_id": "7b3e457a49817bf288e99492fea928bcf8c443aa",
          "url": "https://github.com/disnana/DictSQLite/commit/0590ea684e54256ebe2be585f010e5973c639a15"
        },
        "date": 1783318424346,
        "tool": "customBiggerIsBetter",
        "benches": [
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / bytes / size=32 / batch=1",
            "value": 307877.22341,
            "unit": "ops/sec",
            "extra": "avg=0.003248ms, p95=0.004719ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / bytes / size=32 / batch=1",
            "value": 2237416.767366,
            "unit": "ops/sec",
            "extra": "avg=0.000447ms, p95=0.000501ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / bytes / size=1024 / batch=1",
            "value": 345012.227193,
            "unit": "ops/sec",
            "extra": "avg=0.002898ms, p95=0.003597ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / bytes / size=1024 / batch=1",
            "value": 1681927.355452,
            "unit": "ops/sec",
            "extra": "avg=0.000595ms, p95=0.000581ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / bytes / size=16384 / batch=1",
            "value": 95112.691408,
            "unit": "ops/sec",
            "extra": "avg=0.010514ms, p95=0.014006ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / bytes / size=16384 / batch=1",
            "value": 139668.549783,
            "unit": "ops/sec",
            "extra": "avg=0.007160ms, p95=0.006993ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / jsonb / size=32 / batch=1",
            "value": 251935.113577,
            "unit": "ops/sec",
            "extra": "avg=0.003969ms, p95=0.005320ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / jsonb / size=32 / batch=1",
            "value": 874180.892131,
            "unit": "ops/sec",
            "extra": "avg=0.001144ms, p95=0.001213ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / jsonb / size=1024 / batch=1",
            "value": 233438.474047,
            "unit": "ops/sec",
            "extra": "avg=0.004284ms, p95=0.004879ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / jsonb / size=1024 / batch=1",
            "value": 635094.832351,
            "unit": "ops/sec",
            "extra": "avg=0.001575ms, p95=0.001653ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / jsonb / size=16384 / batch=1",
            "value": 61665.937363,
            "unit": "ops/sec",
            "extra": "avg=0.016216ms, p95=0.023474ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / jsonb / size=16384 / batch=1",
            "value": 238306.082204,
            "unit": "ops/sec",
            "extra": "avg=0.004196ms, p95=0.004148ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / pickle / size=32 / batch=1",
            "value": 237254.453489,
            "unit": "ops/sec",
            "extra": "avg=0.004215ms, p95=0.004729ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / pickle / size=32 / batch=1",
            "value": 658239.446334,
            "unit": "ops/sec",
            "extra": "avg=0.001519ms, p95=0.001704ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / pickle / size=1024 / batch=1",
            "value": 248001.603181,
            "unit": "ops/sec",
            "extra": "avg=0.004032ms, p95=0.004829ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / pickle / size=1024 / batch=1",
            "value": 528744.675423,
            "unit": "ops/sec",
            "extra": "avg=0.001891ms, p95=0.001994ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / pickle / size=16384 / batch=1",
            "value": 188308.029738,
            "unit": "ops/sec",
            "extra": "avg=0.005310ms, p95=0.006392ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / pickle / size=16384 / batch=1",
            "value": 214793.240069,
            "unit": "ops/sec",
            "extra": "avg=0.004656ms, p95=0.004689ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / bytes / size=32 / batch=1",
            "value": 349283.967916,
            "unit": "ops/sec",
            "extra": "avg=0.002863ms, p95=0.004097ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / bytes / size=32 / batch=1",
            "value": 2007354.952511,
            "unit": "ops/sec",
            "extra": "avg=0.000498ms, p95=0.000481ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / bytes / size=1024 / batch=1",
            "value": 409869.661612,
            "unit": "ops/sec",
            "extra": "avg=0.002440ms, p95=0.003396ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / bytes / size=1024 / batch=1",
            "value": 1701073.717536,
            "unit": "ops/sec",
            "extra": "avg=0.000588ms, p95=0.000641ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / bytes / size=16384 / batch=1",
            "value": 275254.004442,
            "unit": "ops/sec",
            "extra": "avg=0.003633ms, p95=0.004589ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / bytes / size=16384 / batch=1",
            "value": 139271.033103,
            "unit": "ops/sec",
            "extra": "avg=0.007180ms, p95=0.007124ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / jsonb / size=32 / batch=1",
            "value": 231328.333557,
            "unit": "ops/sec",
            "extra": "avg=0.004323ms, p95=0.005370ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / jsonb / size=32 / batch=1",
            "value": 877553.240961,
            "unit": "ops/sec",
            "extra": "avg=0.001140ms, p95=0.001192ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / jsonb / size=1024 / batch=1",
            "value": 219706.437048,
            "unit": "ops/sec",
            "extra": "avg=0.004552ms, p95=0.005260ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / jsonb / size=1024 / batch=1",
            "value": 593226.773752,
            "unit": "ops/sec",
            "extra": "avg=0.001686ms, p95=0.003066ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / jsonb / size=16384 / batch=1",
            "value": 86130.418675,
            "unit": "ops/sec",
            "extra": "avg=0.011610ms, p95=0.013035ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / jsonb / size=16384 / batch=1",
            "value": 259509.464814,
            "unit": "ops/sec",
            "extra": "avg=0.003853ms, p95=0.003928ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / pickle / size=32 / batch=1",
            "value": 252210.626127,
            "unit": "ops/sec",
            "extra": "avg=0.003965ms, p95=0.005721ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / pickle / size=32 / batch=1",
            "value": 687506.359099,
            "unit": "ops/sec",
            "extra": "avg=0.001455ms, p95=0.001483ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / pickle / size=1024 / batch=1",
            "value": 258496.522223,
            "unit": "ops/sec",
            "extra": "avg=0.003869ms, p95=0.004778ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / pickle / size=1024 / batch=1",
            "value": 536872.395936,
            "unit": "ops/sec",
            "extra": "avg=0.001863ms, p95=0.001934ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / pickle / size=16384 / batch=1",
            "value": 183712.761465,
            "unit": "ops/sec",
            "extra": "avg=0.005443ms, p95=0.007093ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / pickle / size=16384 / batch=1",
            "value": 217877.455285,
            "unit": "ops/sec",
            "extra": "avg=0.004590ms, p95=0.004588ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / bytes / size=32 / batch=1",
            "value": 421300.267641,
            "unit": "ops/sec",
            "extra": "avg=0.002374ms, p95=0.003496ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / bytes / size=32 / batch=1",
            "value": 2279171.11049,
            "unit": "ops/sec",
            "extra": "avg=0.000439ms, p95=0.000471ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / bytes / size=1024 / batch=1",
            "value": 122115.927108,
            "unit": "ops/sec",
            "extra": "avg=0.008189ms, p95=0.003527ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / bytes / size=1024 / batch=1",
            "value": 1878936.368049,
            "unit": "ops/sec",
            "extra": "avg=0.000532ms, p95=0.000601ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / bytes / size=16384 / batch=1",
            "value": 110173.412965,
            "unit": "ops/sec",
            "extra": "avg=0.009077ms, p95=0.011101ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / bytes / size=16384 / batch=1",
            "value": 507201.243163,
            "unit": "ops/sec",
            "extra": "avg=0.001972ms, p95=0.002044ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / jsonb / size=32 / batch=1",
            "value": 281994.85404,
            "unit": "ops/sec",
            "extra": "avg=0.003546ms, p95=0.004479ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / jsonb / size=32 / batch=1",
            "value": 812445.362567,
            "unit": "ops/sec",
            "extra": "avg=0.001231ms, p95=0.001222ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / jsonb / size=1024 / batch=1",
            "value": 97148.270797,
            "unit": "ops/sec",
            "extra": "avg=0.010294ms, p95=0.005411ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / jsonb / size=1024 / batch=1",
            "value": 695039.089019,
            "unit": "ops/sec",
            "extra": "avg=0.001439ms, p95=0.001513ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / jsonb / size=16384 / batch=1",
            "value": 82241.603462,
            "unit": "ops/sec",
            "extra": "avg=0.012159ms, p95=0.015880ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / jsonb / size=16384 / batch=1",
            "value": 223228.636108,
            "unit": "ops/sec",
            "extra": "avg=0.004480ms, p95=0.004489ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / pickle / size=32 / batch=1",
            "value": 313084.685697,
            "unit": "ops/sec",
            "extra": "avg=0.003194ms, p95=0.004318ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / pickle / size=32 / batch=1",
            "value": 712193.898924,
            "unit": "ops/sec",
            "extra": "avg=0.001404ms, p95=0.001443ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / pickle / size=1024 / batch=1",
            "value": 105970.235921,
            "unit": "ops/sec",
            "extra": "avg=0.009437ms, p95=0.004979ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / pickle / size=1024 / batch=1",
            "value": 572045.727093,
            "unit": "ops/sec",
            "extra": "avg=0.001748ms, p95=0.001833ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / pickle / size=16384 / batch=1",
            "value": 171901.644789,
            "unit": "ops/sec",
            "extra": "avg=0.005817ms, p95=0.007574ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / pickle / size=16384 / batch=1",
            "value": 195152.109378,
            "unit": "ops/sec",
            "extra": "avg=0.005124ms, p95=0.008577ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / batch_set / batch_hot_write / lazy / bytes / size=80 / batch=10",
            "value": 241519.058333,
            "unit": "ops/sec",
            "extra": "avg=0.004140ms, p95=0.004698ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / batch_get / warm_batch_read / lazy / bytes / size=80 / batch=10",
            "value": 240218.310337,
            "unit": "ops/sec",
            "extra": "avg=0.004163ms, p95=0.005110ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / batch_set / batch_hot_write / lazy / bytes / size=80 / batch=100",
            "value": 28933.527532,
            "unit": "ops/sec",
            "extra": "avg=0.034562ms, p95=0.051417ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / batch_get / warm_batch_read / lazy / bytes / size=80 / batch=100",
            "value": 27152.840077,
            "unit": "ops/sec",
            "extra": "avg=0.036829ms, p95=0.040256ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / batch_set / batch_hot_write / lazy / bytes / size=80 / batch=1000",
            "value": 3162.873032,
            "unit": "ops/sec",
            "extra": "avg=0.316168ms, p95=0.337144ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / batch_get / warm_batch_read / lazy / bytes / size=80 / batch=1000",
            "value": 2653.803011,
            "unit": "ops/sec",
            "extra": "avg=0.376818ms, p95=0.391726ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / flush / lazy_flush / lazy / bytes / size=80 / batch=0",
            "value": 277.075296,
            "unit": "ops/sec",
            "extra": "avg=3.609127ms, p95=3.689941ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / batch_set / batch_hot_write / lazy / bytes / size=80 / batch=10",
            "value": 42602.392719,
            "unit": "ops/sec",
            "extra": "avg=0.023473ms, p95=0.025538ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / batch_get / warm_batch_read / lazy / bytes / size=80 / batch=10",
            "value": 57190.897493,
            "unit": "ops/sec",
            "extra": "avg=0.017485ms, p95=0.020198ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / batch_set / batch_hot_write / lazy / bytes / size=80 / batch=100",
            "value": 12510.321014,
            "unit": "ops/sec",
            "extra": "avg=0.079934ms, p95=0.102262ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / batch_get / warm_batch_read / lazy / bytes / size=80 / batch=100",
            "value": 14163.034084,
            "unit": "ops/sec",
            "extra": "avg=0.070606ms, p95=0.086622ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / batch_set / batch_hot_write / lazy / bytes / size=80 / batch=1000",
            "value": 2701.887755,
            "unit": "ops/sec",
            "extra": "avg=0.370112ms, p95=0.407816ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / batch_get / warm_batch_read / lazy / bytes / size=80 / batch=1000",
            "value": 3973.358788,
            "unit": "ops/sec",
            "extra": "avg=0.251676ms, p95=0.292910ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / flush / lazy_flush / lazy / bytes / size=80 / batch=0",
            "value": 274.456668,
            "unit": "ops/sec",
            "extra": "avg=3.643562ms, p95=3.725247ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / batch_get / cold_storage_read / lazy / bytes / size=10 / batch=100",
            "value": 6461.551186,
            "unit": "ops/sec",
            "extra": "avg=0.154762ms, p95=0.298069ms, iterations=10"
          },
          {
            "name": "DictSQLiteV4 / batch_get / cold_storage_read / lazy / bytes / size=10 / batch=1000",
            "value": 590.746837,
            "unit": "ops/sec",
            "extra": "avg=1.692773ms, p95=2.564597ms, iterations=10"
          },
          {
            "name": "TableProxy / table_set / table_write / lazy / bytes / size=11 / batch=1",
            "value": 702286.645103,
            "unit": "ops/sec",
            "extra": "avg=0.001424ms, p95=0.001312ms, iterations=100"
          },
          {
            "name": "TableProxy / table_get / table_read / lazy / bytes / size=11 / batch=1",
            "value": 1842367.078269,
            "unit": "ops/sec",
            "extra": "avg=0.000543ms, p95=0.000572ms, iterations=100"
          },
          {
            "name": "TableProxy / table_contains / table_membership / lazy / bytes / size=11 / batch=1",
            "value": 2350949.794977,
            "unit": "ops/sec",
            "extra": "avg=0.000425ms, p95=0.000470ms, iterations=100"
          },
          {
            "name": "TableProxy / table_set / table_write / lazy / bytes / size=11 / batch=1 / table=separate",
            "value": 23485.965492,
            "unit": "ops/sec",
            "extra": "avg=0.042579ms, p95=0.057719ms, iterations=100"
          },
          {
            "name": "TableProxy / table_get / table_read / lazy / bytes / size=11 / batch=1 / table=separate",
            "value": 2511805.476101,
            "unit": "ops/sec",
            "extra": "avg=0.000398ms, p95=0.000431ms, iterations=100"
          },
          {
            "name": "TableProxy / table_contains / table_membership / lazy / bytes / size=11 / batch=1 / table=separate",
            "value": 2823263.689173,
            "unit": "ops/sec",
            "extra": "avg=0.000354ms, p95=0.000391ms, iterations=100"
          },
          {
            "name": "AsyncTableProxy / table_set / table_write / lazy / bytes / size=11 / batch=1",
            "value": 835540.552109,
            "unit": "ops/sec",
            "extra": "avg=0.001197ms, p95=0.001413ms, iterations=100"
          },
          {
            "name": "AsyncTableProxy / table_get / table_read / lazy / bytes / size=11 / batch=1",
            "value": 1580353.059152,
            "unit": "ops/sec",
            "extra": "avg=0.000633ms, p95=0.000631ms, iterations=100"
          },
          {
            "name": "AsyncTableProxy / table_contains / table_membership / lazy / bytes / size=11 / batch=1",
            "value": 1869822.927454,
            "unit": "ops/sec",
            "extra": "avg=0.000535ms, p95=0.000541ms, iterations=100"
          },
          {
            "name": "AsyncTableProxy / table_set / table_write / lazy / bytes / size=11 / batch=1 / table=separate",
            "value": 25225.376122,
            "unit": "ops/sec",
            "extra": "avg=0.039643ms, p95=0.070562ms, iterations=100"
          },
          {
            "name": "AsyncTableProxy / table_get / table_read / lazy / bytes / size=11 / batch=1 / table=separate",
            "value": 2520605.960678,
            "unit": "ops/sec",
            "extra": "avg=0.000397ms, p95=0.000451ms, iterations=100"
          },
          {
            "name": "AsyncTableProxy / table_contains / table_membership / lazy / bytes / size=11 / batch=1 / table=separate",
            "value": 2826855.131948,
            "unit": "ops/sec",
            "extra": "avg=0.000354ms, p95=0.000391ms, iterations=100"
          },
          {
            "name": "DictSQLiteV4 / delete / set_then_delete / writethrough / bytes / size=5 / batch=1",
            "value": 88368.184269,
            "unit": "ops/sec",
            "extra": "avg=0.011316ms, p95=0.013175ms, iterations=100"
          },
          {
            "name": "DictSQLiteV4 / clear / clear_100_items / writethrough / bytes / size=5 / batch=100",
            "value": 3028.359374,
            "unit": "ops/sec",
            "extra": "avg=0.330212ms, p95=0.368632ms, iterations=10"
          },
          {
            "name": "DictSQLiteV4 / mixed_get_set / threaded_2 / memory / bytes / size=5 / batch=2",
            "value": 833678.61522,
            "unit": "ops/sec",
            "extra": "avg=0.001200ms, p95=0.000000ms, iterations=1000"
          },
          {
            "name": "DictSQLiteV4 / mixed_get_set / threaded_4 / memory / bytes / size=5 / batch=4",
            "value": 737366.605773,
            "unit": "ops/sec",
            "extra": "avg=0.001356ms, p95=0.000000ms, iterations=2000"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "83683593+harumaki4649@users.noreply.github.com",
            "name": "harumaki4649",
            "username": "harumaki4649"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "5843a6551f75e39cff7869fae470521063d78095",
          "message": "Merge pull request #294 from disnana/dev\n\nsec update.",
          "timestamp": "2026-07-07T15:29:09+09:00",
          "tree_id": "d88c387e42afadbb1b9e659b8cbd289074a8602c",
          "url": "https://github.com/disnana/DictSQLite/commit/5843a6551f75e39cff7869fae470521063d78095"
        },
        "date": 1783405985425,
        "tool": "customBiggerIsBetter",
        "benches": [
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / bytes / size=32 / batch=1",
            "value": 259312.158984,
            "unit": "ops/sec",
            "extra": "avg=0.003856ms, p95=0.005838ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / bytes / size=32 / batch=1",
            "value": 2312994.405121,
            "unit": "ops/sec",
            "extra": "avg=0.000432ms, p95=0.000481ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / bytes / size=1024 / batch=1",
            "value": 293059.529753,
            "unit": "ops/sec",
            "extra": "avg=0.003412ms, p95=0.004306ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / bytes / size=1024 / batch=1",
            "value": 2019745.031752,
            "unit": "ops/sec",
            "extra": "avg=0.000495ms, p95=0.000540ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / bytes / size=16384 / batch=1",
            "value": 80095.294181,
            "unit": "ops/sec",
            "extra": "avg=0.012485ms, p95=0.016204ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / bytes / size=16384 / batch=1",
            "value": 367755.222093,
            "unit": "ops/sec",
            "extra": "avg=0.002719ms, p95=0.002614ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / jsonb / size=32 / batch=1",
            "value": 223339.116229,
            "unit": "ops/sec",
            "extra": "avg=0.004477ms, p95=0.005077ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / jsonb / size=32 / batch=1",
            "value": 877045.269846,
            "unit": "ops/sec",
            "extra": "avg=0.001140ms, p95=0.001212ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / jsonb / size=1024 / batch=1",
            "value": 202723.46821,
            "unit": "ops/sec",
            "extra": "avg=0.004933ms, p95=0.005829ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / jsonb / size=1024 / batch=1",
            "value": 651392.80801,
            "unit": "ops/sec",
            "extra": "avg=0.001535ms, p95=0.001693ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / jsonb / size=16384 / batch=1",
            "value": 55727.10836,
            "unit": "ops/sec",
            "extra": "avg=0.017945ms, p95=0.025838ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / jsonb / size=16384 / batch=1",
            "value": 229189.375477,
            "unit": "ops/sec",
            "extra": "avg=0.004363ms, p95=0.006330ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / pickle / size=32 / batch=1",
            "value": 195011.298947,
            "unit": "ops/sec",
            "extra": "avg=0.005128ms, p95=0.007861ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / pickle / size=32 / batch=1",
            "value": 531904.70805,
            "unit": "ops/sec",
            "extra": "avg=0.001880ms, p95=0.003065ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / pickle / size=1024 / batch=1",
            "value": 213373.39064,
            "unit": "ops/sec",
            "extra": "avg=0.004687ms, p95=0.007101ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / pickle / size=1024 / batch=1",
            "value": 425329.204751,
            "unit": "ops/sec",
            "extra": "avg=0.002351ms, p95=0.004256ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / memory / pickle / size=16384 / batch=1",
            "value": 175650.856691,
            "unit": "ops/sec",
            "extra": "avg=0.005693ms, p95=0.008712ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / memory / pickle / size=16384 / batch=1",
            "value": 200925.543435,
            "unit": "ops/sec",
            "extra": "avg=0.004977ms, p95=0.004897ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / bytes / size=32 / batch=1",
            "value": 316085.595995,
            "unit": "ops/sec",
            "extra": "avg=0.003164ms, p95=0.004186ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / bytes / size=32 / batch=1",
            "value": 2186117.284805,
            "unit": "ops/sec",
            "extra": "avg=0.000457ms, p95=0.000451ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / bytes / size=1024 / batch=1",
            "value": 349539.37705,
            "unit": "ops/sec",
            "extra": "avg=0.002861ms, p95=0.004066ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / bytes / size=1024 / batch=1",
            "value": 1791074.717031,
            "unit": "ops/sec",
            "extra": "avg=0.000558ms, p95=0.000611ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / bytes / size=16384 / batch=1",
            "value": 257543.182271,
            "unit": "ops/sec",
            "extra": "avg=0.003883ms, p95=0.005428ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / bytes / size=16384 / batch=1",
            "value": 449158.008524,
            "unit": "ops/sec",
            "extra": "avg=0.002226ms, p95=0.002254ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / jsonb / size=32 / batch=1",
            "value": 198523.304252,
            "unit": "ops/sec",
            "extra": "avg=0.005037ms, p95=0.007731ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / jsonb / size=32 / batch=1",
            "value": 850606.312746,
            "unit": "ops/sec",
            "extra": "avg=0.001176ms, p95=0.001252ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / jsonb / size=1024 / batch=1",
            "value": 199129.08904,
            "unit": "ops/sec",
            "extra": "avg=0.005022ms, p95=0.005819ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / jsonb / size=1024 / batch=1",
            "value": 649202.259925,
            "unit": "ops/sec",
            "extra": "avg=0.001540ms, p95=0.001632ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / jsonb / size=16384 / batch=1",
            "value": 77414.935702,
            "unit": "ops/sec",
            "extra": "avg=0.012917ms, p95=0.016735ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / jsonb / size=16384 / batch=1",
            "value": 231272.26571,
            "unit": "ops/sec",
            "extra": "avg=0.004324ms, p95=0.004357ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / pickle / size=32 / batch=1",
            "value": 197488.421228,
            "unit": "ops/sec",
            "extra": "avg=0.005064ms, p95=0.006360ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / pickle / size=32 / batch=1",
            "value": 633666.979794,
            "unit": "ops/sec",
            "extra": "avg=0.001578ms, p95=0.001462ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / pickle / size=1024 / batch=1",
            "value": 218959.434686,
            "unit": "ops/sec",
            "extra": "avg=0.004567ms, p95=0.005788ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / pickle / size=1024 / batch=1",
            "value": 539074.258299,
            "unit": "ops/sec",
            "extra": "avg=0.001855ms, p95=0.001983ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / lazy / pickle / size=16384 / batch=1",
            "value": 162697.07497,
            "unit": "ops/sec",
            "extra": "avg=0.006146ms, p95=0.008723ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / lazy / pickle / size=16384 / batch=1",
            "value": 200959.299296,
            "unit": "ops/sec",
            "extra": "avg=0.004976ms, p95=0.005048ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / bytes / size=32 / batch=1",
            "value": 410701.231533,
            "unit": "ops/sec",
            "extra": "avg=0.002435ms, p95=0.004016ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / bytes / size=32 / batch=1",
            "value": 2455916.302909,
            "unit": "ops/sec",
            "extra": "avg=0.000407ms, p95=0.000451ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / bytes / size=1024 / batch=1",
            "value": 115482.989106,
            "unit": "ops/sec",
            "extra": "avg=0.008659ms, p95=0.004086ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / bytes / size=1024 / batch=1",
            "value": 1991857.286165,
            "unit": "ops/sec",
            "extra": "avg=0.000502ms, p95=0.000551ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / bytes / size=16384 / batch=1",
            "value": 195619.530976,
            "unit": "ops/sec",
            "extra": "avg=0.005112ms, p95=0.007090ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / bytes / size=16384 / batch=1",
            "value": 436056.652393,
            "unit": "ops/sec",
            "extra": "avg=0.002293ms, p95=0.002494ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / jsonb / size=32 / batch=1",
            "value": 295680.230161,
            "unit": "ops/sec",
            "extra": "avg=0.003382ms, p95=0.004977ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / jsonb / size=32 / batch=1",
            "value": 837133.921405,
            "unit": "ops/sec",
            "extra": "avg=0.001195ms, p95=0.001192ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / jsonb / size=1024 / batch=1",
            "value": 90591.263812,
            "unit": "ops/sec",
            "extra": "avg=0.011039ms, p95=0.005748ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / jsonb / size=1024 / batch=1",
            "value": 689653.269791,
            "unit": "ops/sec",
            "extra": "avg=0.001450ms, p95=0.001552ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / jsonb / size=16384 / batch=1",
            "value": 78230.954055,
            "unit": "ops/sec",
            "extra": "avg=0.012783ms, p95=0.014782ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / jsonb / size=16384 / batch=1",
            "value": 222738.976652,
            "unit": "ops/sec",
            "extra": "avg=0.004490ms, p95=0.004557ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / pickle / size=32 / batch=1",
            "value": 255511.641566,
            "unit": "ops/sec",
            "extra": "avg=0.003914ms, p95=0.005648ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / pickle / size=32 / batch=1",
            "value": 679611.914648,
            "unit": "ops/sec",
            "extra": "avg=0.001471ms, p95=0.001482ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / pickle / size=1024 / batch=1",
            "value": 95443.526059,
            "unit": "ops/sec",
            "extra": "avg=0.010477ms, p95=0.005498ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / pickle / size=1024 / batch=1",
            "value": 571747.442554,
            "unit": "ops/sec",
            "extra": "avg=0.001749ms, p95=0.001833ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / set / hot_write / writethrough / pickle / size=16384 / batch=1",
            "value": 155010.785674,
            "unit": "ops/sec",
            "extra": "avg=0.006451ms, p95=0.008252ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / get / hot_read / writethrough / pickle / size=16384 / batch=1",
            "value": 192558.314406,
            "unit": "ops/sec",
            "extra": "avg=0.005193ms, p95=0.007451ms, iterations=250"
          },
          {
            "name": "DictSQLiteV4 / batch_set / batch_hot_write / lazy / bytes / size=80 / batch=10",
            "value": 216645.291055,
            "unit": "ops/sec",
            "extra": "avg=0.004616ms, p95=0.007531ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / batch_get / warm_batch_read / lazy / bytes / size=80 / batch=10",
            "value": 254012.121471,
            "unit": "ops/sec",
            "extra": "avg=0.003937ms, p95=0.004908ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / batch_set / batch_hot_write / lazy / bytes / size=80 / batch=100",
            "value": 29219.944365,
            "unit": "ops/sec",
            "extra": "avg=0.034223ms, p95=0.054800ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / batch_get / warm_batch_read / lazy / bytes / size=80 / batch=100",
            "value": 25125.514507,
            "unit": "ops/sec",
            "extra": "avg=0.039800ms, p95=0.059778ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / batch_set / batch_hot_write / lazy / bytes / size=80 / batch=1000",
            "value": 3242.823745,
            "unit": "ops/sec",
            "extra": "avg=0.308373ms, p95=0.326039ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / batch_get / warm_batch_read / lazy / bytes / size=80 / batch=1000",
            "value": 2586.086554,
            "unit": "ops/sec",
            "extra": "avg=0.386685ms, p95=0.436271ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / flush / lazy_flush / lazy / bytes / size=80 / batch=0",
            "value": 261.101456,
            "unit": "ops/sec",
            "extra": "avg=3.829929ms, p95=3.981093ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / batch_set / batch_hot_write / lazy / bytes / size=80 / batch=10",
            "value": 34553.963616,
            "unit": "ops/sec",
            "extra": "avg=0.028940ms, p95=0.033760ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / batch_get / warm_batch_read / lazy / bytes / size=80 / batch=10",
            "value": 58349.661516,
            "unit": "ops/sec",
            "extra": "avg=0.017138ms, p95=0.024345ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / batch_set / batch_hot_write / lazy / bytes / size=80 / batch=100",
            "value": 12372.501374,
            "unit": "ops/sec",
            "extra": "avg=0.080824ms, p95=0.103632ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / batch_get / warm_batch_read / lazy / bytes / size=80 / batch=100",
            "value": 19238.501629,
            "unit": "ops/sec",
            "extra": "avg=0.051979ms, p95=0.067549ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / batch_set / batch_hot_write / lazy / bytes / size=80 / batch=1000",
            "value": 2353.836188,
            "unit": "ops/sec",
            "extra": "avg=0.424838ms, p95=0.460817ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / batch_get / warm_batch_read / lazy / bytes / size=80 / batch=1000",
            "value": 3859.424328,
            "unit": "ops/sec",
            "extra": "avg=0.259106ms, p95=0.289206ms, iterations=50"
          },
          {
            "name": "AsyncDictSQLite / flush / lazy_flush / lazy / bytes / size=80 / batch=0",
            "value": 255.294936,
            "unit": "ops/sec",
            "extra": "avg=3.917038ms, p95=4.087990ms, iterations=50"
          },
          {
            "name": "DictSQLiteV4 / batch_get / cold_storage_read / lazy / bytes / size=10 / batch=100",
            "value": 6852.154489,
            "unit": "ops/sec",
            "extra": "avg=0.145940ms, p95=0.317407ms, iterations=10"
          },
          {
            "name": "DictSQLiteV4 / batch_get / cold_storage_read / lazy / bytes / size=10 / batch=1000",
            "value": 598.299823,
            "unit": "ops/sec",
            "extra": "avg=1.671403ms, p95=2.455861ms, iterations=10"
          },
          {
            "name": "TableProxy / table_set / table_write / lazy / bytes / size=11 / batch=1",
            "value": 676503.02082,
            "unit": "ops/sec",
            "extra": "avg=0.001478ms, p95=0.001732ms, iterations=100"
          },
          {
            "name": "TableProxy / table_get / table_read / lazy / bytes / size=11 / batch=1",
            "value": 2240394.309662,
            "unit": "ops/sec",
            "extra": "avg=0.000446ms, p95=0.000521ms, iterations=100"
          },
          {
            "name": "TableProxy / table_contains / table_membership / lazy / bytes / size=11 / batch=1",
            "value": 2894774.933175,
            "unit": "ops/sec",
            "extra": "avg=0.000345ms, p95=0.000391ms, iterations=100"
          },
          {
            "name": "TableProxy / table_set / table_write / lazy / bytes / size=11 / batch=1 / table=separate",
            "value": 25062.750863,
            "unit": "ops/sec",
            "extra": "avg=0.039900ms, p95=0.046989ms, iterations=100"
          },
          {
            "name": "TableProxy / table_get / table_read / lazy / bytes / size=11 / batch=1 / table=separate",
            "value": 2636018.560655,
            "unit": "ops/sec",
            "extra": "avg=0.000379ms, p95=0.000430ms, iterations=100"
          },
          {
            "name": "TableProxy / table_contains / table_membership / lazy / bytes / size=11 / batch=1 / table=separate",
            "value": 2876042.566673,
            "unit": "ops/sec",
            "extra": "avg=0.000348ms, p95=0.000391ms, iterations=100"
          },
          {
            "name": "AsyncTableProxy / table_set / table_write / lazy / bytes / size=11 / batch=1",
            "value": 954380.609178,
            "unit": "ops/sec",
            "extra": "avg=0.001048ms, p95=0.001322ms, iterations=100"
          },
          {
            "name": "AsyncTableProxy / table_get / table_read / lazy / bytes / size=11 / batch=1",
            "value": 2005334.184318,
            "unit": "ops/sec",
            "extra": "avg=0.000499ms, p95=0.000521ms, iterations=100"
          },
          {
            "name": "AsyncTableProxy / table_contains / table_membership / lazy / bytes / size=11 / batch=1",
            "value": 2437241.029303,
            "unit": "ops/sec",
            "extra": "avg=0.000410ms, p95=0.000461ms, iterations=100"
          },
          {
            "name": "AsyncTableProxy / table_set / table_write / lazy / bytes / size=11 / batch=1 / table=separate",
            "value": 27080.859383,
            "unit": "ops/sec",
            "extra": "avg=0.036926ms, p95=0.042112ms, iterations=100"
          },
          {
            "name": "AsyncTableProxy / table_get / table_read / lazy / bytes / size=11 / batch=1 / table=separate",
            "value": 2644593.113037,
            "unit": "ops/sec",
            "extra": "avg=0.000378ms, p95=0.000431ms, iterations=100"
          },
          {
            "name": "AsyncTableProxy / table_contains / table_membership / lazy / bytes / size=11 / batch=1 / table=separate",
            "value": 3146930.169245,
            "unit": "ops/sec",
            "extra": "avg=0.000318ms, p95=0.000351ms, iterations=100"
          },
          {
            "name": "DictSQLiteV4 / delete / set_then_delete / writethrough / bytes / size=5 / batch=1",
            "value": 80917.409217,
            "unit": "ops/sec",
            "extra": "avg=0.012358ms, p95=0.015483ms, iterations=100"
          },
          {
            "name": "DictSQLiteV4 / clear / clear_100_items / writethrough / bytes / size=5 / batch=100",
            "value": 2788.651971,
            "unit": "ops/sec",
            "extra": "avg=0.358596ms, p95=0.605980ms, iterations=10"
          },
          {
            "name": "DictSQLiteV4 / mixed_get_set / threaded_2 / memory / bytes / size=5 / batch=2",
            "value": 788790.342679,
            "unit": "ops/sec",
            "extra": "avg=0.001268ms, p95=0.000000ms, iterations=1000"
          },
          {
            "name": "DictSQLiteV4 / mixed_get_set / threaded_4 / memory / bytes / size=5 / batch=4",
            "value": 818336.297754,
            "unit": "ops/sec",
            "extra": "avg=0.001222ms, p95=0.000000ms, iterations=2000"
          }
        ]
      }
    ]
  }
}
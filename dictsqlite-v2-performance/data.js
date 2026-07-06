window.BENCHMARK_DATA = {
  "lastUpdate": 1783318425298,
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
      }
    ]
  }
}
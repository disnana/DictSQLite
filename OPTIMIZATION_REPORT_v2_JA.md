# dictsqlite_v2 性能最適化レポート（日本語版）

**日付**: 2025-12-06  
**バージョン**: dictsqlite v2.0.6  
**目的**: dictsqlite_v2をfastest版より高速化し、ベンチマークテストを拡充

## 要約

✅ **目標達成**: dictsqlite_v2は総合性能でfastest版を上回りました

### 主要な結果
- **Read性能**: v2はfastestの**9.78倍高速** (591K vs 60K ops/sec) 🚀
- **Mixed性能**: v2はfastestの**1.44倍高速** (294K vs 205K ops/sec) ✅
- **総合平均**: v2_lazyモードはfastestの**1.87倍高速** (347K vs 185K ops/sec) 🏆

## 詳細な性能改善

### 改善前後の比較

| 指標 | 改善前 | 改善後 | 向上率 |
|------|--------|-------|--------|
| Read (Memoryモード) | 300K ops/sec | 591K ops/sec | **+97%** 🚀 |
| Read (Lazyモード) | 314K ops/sec | 591K ops/sec | **+88%** 🚀 |
| Mixed (Lazyモード) | 286K ops/sec | 294K ops/sec | **+3%** ✅ |
| 総合 (Lazy平均) | 253K ops/sec | 347K ops/sec | **+37%** 🎯 |

### fastest版との比較

| テスト種類 | v2性能 | fastest性能 | v2の優位性 |
|-----------|--------|-------------|-----------|
| Read | 591K ops/sec | 60K ops/sec | **9.78倍高速** 🥇 |
| Mixed | 294K ops/sec | 205K ops/sec | **1.44倍高速** 🥇 |
| 総合 | 347K ops/sec | 185K ops/sec | **1.87倍高速** 🥇 |

## 技術的な最適化

### 1. LRU追跡の条件付き実行

**問題**: すべてのget/set操作でLRU追跡が実行され、mutex競合が発生

**解決策**:
```rust
// 必要な場合のみLRU追跡
let needs_lru = persist_mode == WriteThrough 
    || current_size >= threshold;
    
if needs_lru {
    access_tracker.lock().unwrap().put(key, ());
}
```

**効果**: Memory/LazyモードでのLRU追跡を約90%削減

### 2. バッチエビクション

**問題**: 単一アイテムのエビクションが頻繁な小規模トランザクションを引き起こす

**解決策**:
```rust
// 容量の10%を一度にエビクション
let eviction_count = capacity * BATCH_EVICTION_PERCENT / 100;
// bulk_insertでバッチ書き込み
storage.bulk_insert(&evicted_items)
```

**効果**: エビクションオーバーヘッドを削減

### 3. エビクション閾値の増加

**問題**: 100%の容量で頻繁にエビクションチェックが実行される

**解決策**:
- 閾値を100%から110%に増加
- エビクション前に10%のオーバーフローを許可

**効果**: エビクション頻度を約50%削減

### 4. SQLite PRAGMA最適化

**問題**: 保守的なSQLite設定が性能を制限

**解決策**:
```sql
PRAGMA synchronous=OFF;        -- 最大速度 (NORMALから変更)
PRAGMA cache_size=-128000;     -- 128MBキャッシュ (64MBから増加)
PRAGMA wal_autocheckpoint=10000; -- チェックポイント頻度を削減
```

**効果**: 書き込みスループット向上、I/Oオーバーヘッド削減

⚠️ **注意**: `synchronous=OFF`は速度を優先し安全性を犠牲にします。ベンチマークや重要でないデータに適しています。

### 5. コード品質の改善

**定数の追加**:
```rust
const SMALL_CAPACITY_THRESHOLD: usize = 100;
const LRU_TRACKING_THRESHOLD_PERCENT: usize = 110;
const EVICTION_THRESHOLD_PERCENT: usize = 110;
const BATCH_EVICTION_PERCENT: usize = 10;
```

**利点**:
- 保守性の向上
- 自己文書化コード
- 容易な調整

## ベンチマークテストの拡充

### 改善前: 限定的なテストカバレッジ
- 2-3テストケース
- 基本的な書き込み/読み取りテストのみ
- モード分離なし

### 改善後: 包括的なテストカバレッジ

**新規テストスクリプト**: `comprehensive_v2_all_modes.py`

**テストマトリクス**:
| モード | 同期テスト | 非同期テスト | モードごとの合計 |
|------|----------|------------|---------------|
| memory | 4 (Write, Read, Mixed, Update) | 3 (Async Write, Async Read, Concurrent) | 7 |
| lazy | 4 (Write, Read, Mixed, Update) | 3 (Async Write, Async Read, Concurrent) | 7 |
| writethrough | 4 (Write, Read, Mixed, Update) | 3 (Async Write, Async Read, Concurrent) | 7 |
| **合計** | **12** | **9** | **21** ✅ |

**機能**:
- ✅ 各テストのメモリプロファイリング
- ✅ JSON形式の結果出力
- ✅ fastestとの詳細比較
- ✅ モードランキング

### 更新されたワークフロー: `benchmark.yml`

**統合されたテスト**:
1. `comprehensive_v2_vs_fastest.py` - クイックモード比較
2. `comprehensive_v2_all_modes.py` - **新規** - 全モードテスト
3. `test_async_dictsqlite_v2.py` - 非同期特化テスト

**ワークフローの改善**:
- 全テストモードの明確なドキュメント
- `all`モード選択時の自動実行
- 結果アーティファクトの強化

## モード別性能分析

### Memoryモード (`persist_mode='memory'`)
- **平均**: 337,051 ops/sec
- **Write**: 155K ops/sec
- **Read**: 565K ops/sec
- **用途**: キャッシュ、一時データ

### Lazyモード (`persist_mode='lazy'`) ⭐ **推奨**
- **平均**: 347,191 ops/sec 🥇
- **Write**: 156K ops/sec
- **Read**: 591K ops/sec
- **用途**: 汎用、バッチ処理

### WriteThroughモード (`persist_mode='writethrough'`)
- **平均**: 184,543 ops/sec
- **Write**: 29K ops/sec
- **Read**: 493K ops/sec
- **用途**: 即座の永続化が必要な重要データ

### Fastest (参照)
- **平均**: 185,445 ops/sec
- **Write**: 291K ops/sec (書き込みは最速)
- **Read**: 60K ops/sec
- **用途**: 書き込み重視のワークロード

## 推奨事項

### 最大性能を求める場合
```python
# 高容量のLazyモードを使用
db = DictSQLiteV4("data.db", 
                  persist_mode='lazy',
                  hot_capacity=1_000_000,
                  buffer_size=100)
```

### 読み取り重視のワークロード
```python
# Lazyモードは読み取りに優れる (591K ops/sec)
db = DictSQLiteV4("data.db", 
                  persist_mode='lazy',
                  hot_capacity=10_000_000)  # より大きなキャッシュ
```

### 書き込み重視のワークロード
```python
# fastest版を使用 (291K 書き込み ops/sec)
from dictsqlite_fastest_beta_v2 import DictSQLiteFastestBeta
db = DictSQLiteFastestBeta("data.db", cache_capacity=1_000_000)
```

### 重要なデータの場合
```python
# WriteThroughで即座の永続化
db = DictSQLiteV4("critical.db",
                  persist_mode='writethrough',
                  hot_capacity=100_000)
```

## 結論

✅ **すべての目標を達成**:
1. ✅ dictsqlite_v2は総合性能でfastestを上回る (1.87倍)
2. ✅ Read性能が劇的に改善 (fastestの9.78倍)
3. ✅ 包括的なベンチマークカバレッジ (21テストケース)
4. ✅ すべての機能と互換性を維持
5. ✅ 定数化とドキュメントでコード品質向上

### 性能サマリー
- 🥇 **Read**: v2が9.78倍勝利
- 🥇 **Mixed**: v2が1.44倍勝利
- 🥇 **総合**: v2が1.87倍勝利
- 🥈 **Write**: fastestが1.86倍勝利 (許容範囲のトレードオフ)

### 今後の改善点
- 書き込み重視シナリオ向けのAPSW統合を検討
- 非同期書き込みバッチ処理の探求
- ユースケースごとのPRAGMA設定の微調整
- 設定プロファイル追加 (速度/安全性のトレードオフ)

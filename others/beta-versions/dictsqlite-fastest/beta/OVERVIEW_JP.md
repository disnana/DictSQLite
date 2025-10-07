# DictSQLite-Fastest Beta - Overview

## ディレクトリ構成

```
dictsqlite-fastest/beta/
├── __init__.py                    # モジュール初期化
├── dictsqlite_fastest_beta.py     # メイン実装 (600+ lines)
├── README_JP.md                   # 完全なドキュメント
├── BENCHMARK_RESULTS_JP.md        # ベンチマーク結果詳細
├── example_usage.py               # 使用例スクリプト
├── test_beta.py                   # テストスイート (17テスト)
└── benchmark.py                   # パフォーマンス比較スクリプト
```

## クイックスタート

### インストール

Beta版は既存のDictSQLite-Fastestの上に構築されているため、追加のインストールは不要です。

```bash
cd dictsqlite-fastest/beta
```

### 基本的な使用

```python
from beta.dictsqlite_fastest_beta import DictSQLiteFastestBeta

# 通常モード（推奨設定）
with DictSQLiteFastestBeta('data.db', cache_capacity=10000) as db:
    db['key1'] = 'value1'
    print(db['key1'])
    
    # 統計情報を確認
    stats = db.get_beta_stats()
    print(f"キャッシュヒット率: {stats['cache']['hit_rate']:.2f}%")
```

### テストの実行

```bash
python test_beta.py
```

期待される出力:
```
Total: 17
Passed: 17
Failed: 0
Success Rate: 100.0%
```

### ベンチマークの実行

```bash
python benchmark.py
```

期待される結果: 平均9.13倍の高速化

### 使用例の実行

```bash
python example_usage.py
```

## 主な機能

### 1. LRUキャッシュ
- デフォルト容量: 10,000アイテム
- スレッドセーフ
- キャッシュヒット時: **21倍高速化**

### 2. 書き込みバッファリング
- デフォルトバッファサイズ: 1,000アイテム
- 自動フラッシュ間隔: 5秒
- 小さな書き込み: **6.3倍高速化**

### 3. 先読みキャッシング
```python
db.prefetch_keys(['key1', 'key2', 'key3'])
```

### 4. メモリオンリーモード
```python
db = DictSQLiteFastestBeta(':memory:', memory_only=True)
```

### 5. 統計情報
```python
stats = db.get_beta_stats()
# stats['cache'] - キャッシュ統計
# stats['operations'] - 操作統計
# stats['buffer'] - バッファ状態
```

## パフォーマンス概要

| シナリオ | 改善率 |
|---------|--------|
| キャッシュヒット時の読み込み | **21.03x** |
| 混合操作 | **17.97x** |
| バルク読み込み | **7.74x** |
| 個別書き込み | **6.26x** |
| **平均** | **9.13x** |

詳細は `BENCHMARK_RESULTS_JP.md` を参照してください。

## アルゴリズムと最適化戦略

### 1. ディスクアクセス削減戦略

#### a) LRUキャッシュ (Least Recently Used)
- **原理**: 最近使用されたデータをメモリに保持
- **実装**: OrderedDict + スレッドロック
- **効果**: キャッシュヒット時のディスクアクセスをゼロに

#### b) 書き込みバッファリング (Write-Behind Caching)
- **原理**: 小さな書き込みをメモリに蓄積し、一括でディスクに書き込む
- **閾値**: アイテム数または時間経過
- **効果**: ディスクI/O回数を大幅に削減

#### c) 先読みキャッシング (Read-Ahead)
- **原理**: アクセスパターンに基づいて関連データを事前にキャッシュ
- **実装**: バルク読み込みAPI活用
- **効果**: 次のアクセスでキャッシュヒット率向上

### 2. メモリ最適化設定

#### アグレッシブメモリモード
```python
cache_size: -256000      # 256MB SQLiteキャッシュ
mmap_size: 1073741824    # 1GB メモリマップ
journal_mode: 'WAL'      # Write-Ahead Logging
temp_store: 'MEMORY'     # 一時データをメモリに
locking_mode: 'EXCLUSIVE' # 排他ロック
```

### 3. アクセスパターン最適化

#### 読み込み中心
```python
DictSQLiteFastestBeta(
    'data.db',
    cache_capacity=100000,   # 大きなキャッシュ
    write_buffer_size=100    # 小さなバッファ
)
```

#### 書き込み中心
```python
DictSQLiteFastestBeta(
    'data.db',
    cache_capacity=5000,      # 適度なキャッシュ
    write_buffer_size=10000   # 大きなバッファ
)
```

## トレードオフ

### 利点
- ✅ キャッシュヒット時の超高速読み込み (21x)
- ✅ 小さな書き込みの高速化 (6.3x)
- ✅ 混合操作の劇的な高速化 (18x)
- ✅ メモリオンリーモードで最高速度

### 注意点
- ⚠️ メモリ使用量の増加
- ⚠️ バッファ中のデータは遅延書き込み（`flush()`必要）
- ⚠️ 大規模バルク書き込みでは標準版がやや優位

## 推奨される使用シナリオ

1. **Webアプリケーションのキャッシュ**
   - 同じデータへの頻繁なアクセス
   - キャッシュヒット率が高い

2. **リアルタイム分析**
   - 頻繁な小さな更新
   - 読み書き混在

3. **一時的なデータ処理**
   - メモリオンリーモード活用
   - 最高速度が必要

4. **セッション管理**
   - 頻繁なアクセスと更新
   - データサイズが適度

## まとめ

DictSQLite-Fastest Beta版は、メモリ最優先のアーキテクチャにより、
特定のワークロードで**最大21倍、平均9倍**のパフォーマンス向上を実現します。

適切な設定と使用方法により、ディスクアクセスを最小限に抑え、
メモリからの高速アクセスを最大化できます。

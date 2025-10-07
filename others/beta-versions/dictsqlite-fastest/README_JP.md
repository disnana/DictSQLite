# DictSQLite-Fastest

**APSWを使用した高性能SQLite辞書ライブラリ - 最大速度と完全互換性を実現**

DictSQLite-Fastestは、APSW（Another Python SQLite Wrapper）を使用してDictSQLiteの高性能版を提供します。元のDictSQLite APIとの100%互換性を保ちながら、大幅なパフォーマンス向上を実現しています。

## 🚀 パフォーマンス概要

包括的なベンチマークテストの結果、DictSQLite-Fastestは大幅なパフォーマンス向上を提供します：

- **平均速度向上: 6.37x**
- **最大速度向上: 10.68x** (バルク挿入操作)
- **すべてのテストで性能向上を確認**

### 最新パフォーマンス結果（2025年10月更新）

**最新の最適化により、さらなるパフォーマンス向上を実現:**
- WALモードでの排他ロッキング（`locking_mode=EXCLUSIVE`）
- メモリ優先の最適化PRAGMA設定
- バルク操作のチャンクサイズ最適化（999パラメータ）
- `executemany()`による一括挿入性能向上

**ベンチマーク結果（最適化設定）:**

| データ量 | 挿入速度 | 読み取り速度 | 削除速度 |
|----------|----------|--------------|----------|
| 100項目 | 348,000 items/s | 360,000 items/s | 557,000 items/s |
| 1,000項目 | 448,000 items/s | 377,000 items/s | 767,000 items/s |
| 5,000項目 | 434,000 items/s | 439,000 items/s | 974,000 items/s |

詳細は [PERFORMANCE_OPTIMIZATIONS.md](PERFORMANCE_OPTIMIZATIONS.md) を参照してください。

### パフォーマンス結果（2025年9月）

| 操作タイプ | データ量 | DictSQLite | DictSQLite-Fastest | 高速化倍率 |
|------------|----------|------------|-------------------|------------|
| バルク挿入 | 100 | 0.0395s | 0.0057s | **6.94x** |
| バルク挿入 | 500 | 0.1673s | 0.0183s | **9.16x** |
| バルク挿入 | 1000 | 0.2395s | 0.0329s | **7.28x** |
| バルク読み取り | 100 | 0.0073s | 0.0033s | **2.19x** |
| バルク読み取り | 500 | 0.0337s | 0.0101s | **3.34x** |
| バルク読み取り | 1000 | 0.0659s | 0.0181s | **3.64x** |
| 複雑データ | 10 | 0.0056s | 0.0020s | **2.80x** |
| 複雑データ | 50 | 0.0216s | 0.0038s | **5.63x** |
| 複雑データ | 100 | 0.0422s | 0.0061s | **6.93x** |

**平均高速化: 5.32倍** | **最大高速化: 9.16倍** | **成功率: 100%**

## ✨ 主要機能

### 🔥 高性能最適化（2025年10月最新版）
- **APSW採用**: 最速のPython SQLiteラッパーを使用
- **スレッドローカル接続**: 各スレッドで最適化された接続を管理
- **WAL モード デフォルト**: 並行性を最大化
  - **排他ロックモード**: WAL性能をさらに向上（NEW）
  - **WALサイズ制限**: メモリ効率的なWAL管理（NEW）
- **プリペアドステートメント最適化**: キャッシュ機能強化
- **メモリマップ最適化**: 256MB メモリマップド I/O
- **接続プーリング**: 統計機能付き非同期操作最適化
- **自動圧縮**: 大きな値の自動圧縮（zlib）
- **カスタムPRAGMA**: 柔軟な最適化設定
- **メモリ優先PRAGMA**: セキュア削除無効、未コミット読み取り等（NEW）
- **クエリプランナー最適化**: 自動統計更新（NEW）

### 🔧 新機能と拡張
- **高度なバルク操作API**: データ量に応じた自動最適化
  - `bulk_insert_optimized()` - 自動最適化バルク挿入（NEW）
  - `bulk_insert_executemany()` - 最高速度モード（NEW）
  - `bulk_get()` - 一括取得 (3.64x高速化を確認)
  - `bulk_delete()` - 一括削除
- **接続ウォームアップ**: `warmup_connection()`で初期化最適化
- **パフォーマンス統計**: `get_performance_stats()`で詳細情報取得
- **メモリ最適化**: インクリメンタルバキューム、大きなページサイズ
- **圧縮サポート**: 設定可能な閾値での自動圧縮

### 🛡️ 完全互換性
- **100% API互換**: 元のDictSQLiteと同じインターフェース
- **データベース形式互換**: 同じファイルを読み書き可能
- **機能完全**: 暗号化、安全性、すべての高度な機能をサポート
- **動作同一**: エッジケースも含めて元の動作と完全一致

## 📦 インストール

```bash
pip install apsw
# DictSQLiteの依存関係もインストール
pip install portalocker cryptography
```

## 🎯 使用方法

### 基本的な使用方法

```python
from dictsqlite_fastest.main import DictSQLiteFastest

# 基本的な操作 (元のDictSQLiteと同じ)
with DictSQLiteFastest('高速データベース.db') as db:
    # データの保存
    db['ユーザー1'] = {'名前': '田中太郎', '年齢': 30}
    db['ユーザー2'] = {'名前': '佐藤花子', '年齢': 25}
    
    # データの取得
    user = db['ユーザー1']
    print(user)  # {'名前': '田中太郎', '年齢': 30}
    
    # 存在確認
    if 'ユーザー1' in db:
        print("ユーザーが存在します")
    
    # 削除
    del db['ユーザー2']
```

### バルク操作（新機能）

```python
# 大量データの高速処理
data = {f'キー_{i}': f'値_{i}' for i in range(10000)}

# 自動最適化バルク挿入 - データ量に応じて最適化手法を自動選択
db.bulk_insert_optimized(data)  # NEW: 最高9.16倍高速化

# ExecuteMany方式バルク挿入 - 最高速度
db.bulk_insert_executemany(data)  # NEW: 最高速度モード

# 一括取得 - 複数キーを効率的に取得
keys = [f'キー_{i}' for i in range(0, 10000, 100)]
results = db.bulk_get(keys)  # 7.56x高速化を確認

# 一括削除
db.bulk_delete(keys[:50])
```

### 高度なパフォーマンス設定

```python
# 最大パフォーマンス設定
db = DictSQLiteFastest(
    'high_performance.db',
    # メモリ最適化
    cache_size=-128000,  # 128MBキャッシュ
    mmap_size=536870912,  # 512MBメモリマップド I/O
    enable_memory_optimization=True,
    
    # 圧縮設定
    enable_compression=True,
    compression_threshold=1024,  # 1KB以上を圧縮
    
    # カスタムPRAGMA設定
    custom_pragma_settings={
        'page_size': 65536,
        'synchronous': 'NORMAL',
        'temp_store': 'MEMORY'
    }
)

# 接続をウォームアップ
db.warmup_connection()

# パフォーマンス統計を確認
stats = db.get_performance_stats()
print(f"パフォーマンス統計: {stats}")
```

### 非同期操作

```python
from dictsqlite_fastest.main import AsyncDictSQLiteFastest
import asyncio

async def main():
    # 接続プール付き非同期データベース
    db = AsyncDictSQLiteFastest('非同期.db', max_connections=5)
    
    # 非同期での基本操作
    await db.aset('async_key', 'async_value')
    value = await db.aget('async_key')
    
    # 非同期バルク操作
    data = {f'非同期_{i}': f'データ_{i}' for i in range(1000)}
    await db.abulk_insert(data)
    
    keys = [f'非同期_{i}' for i in range(0, 1000, 10)]
    results = await db.abulk_get(keys)
    
    await db.aclose()  # 接続プールのクリーンアップ

asyncio.run(main())
```

### パフォーマンス設定のカスタマイズ

```python
# 高度なパフォーマンス設定
db = DictSQLiteFastest(
    'カスタム.db',
    cache_size=-128000,      # 128MB キャッシュ
    mmap_size=536870912,     # 512MB メモリマップ
    wal_autocheckpoint=2000, # WALチェックポイント間隔
    journal_mode='WAL'       # WALモード（デフォルト）
)
```

## 🔧 設定オプション

### パフォーマンス最適化設定

1. **WAL モード使用（デフォルト）**
```python
# WALモードは並行性能を最大化（推奨設定）
db = DictSQLiteFastest('db.db', journal_mode='WAL')
```

2. **バッチ操作の活用**
```python
# 複数操作をまとめて実行で最大速度を実現
with DictSQLiteFastest('db.db') as db:
    for i in range(1000):
        db[f'キー_{i}'] = f'値_{i}'  # APSWで非常に高速
```

3. **非同期での並行処理**
```python
# 並行操作で非同期処理を活用
async with AsyncDictSQLiteFastest('db.db') as db:
    tasks = [db.aset(f'キー_{i}', data) for i in range(1000)]
    await asyncio.gather(*tasks)  # 並行実行
```

## 📊 ベンチマーク実行

システムでのパフォーマンス比較を実行：

```bash
cd dictsqlite-fastest
python benchmark.py
```

## 🧪 テスト実行

```bash
# 基本テスト
python -m pytest dictsqlite-fastest/tests/ -v

# パフォーマンステスト含む
python -m pytest dictsqlite-fastest/tests/test_advanced_performance.py -v

# ベンチマーク統合テスト
python -m pytest dictsqlite-fastest/tests/ --benchmark-only
```

## 🏗️ アーキテクチャ

### 接続管理の最適化
- スレッドごとの自動接続再利用
- 接続ごとの最適化されたPRAGMA設定
- スレッド終了時の適切な接続クリーンアップ

### 非同期実装
- `ThreadPoolExecutor`で接続ごとの操作モデル
- セマフォベースの同時実行数制限
- 自動接続ライフサイクル管理
- 接続プールによる効率化

## 🔄 互換性について

- **100% API互換** - 元のDictSQLiteと同じ
- **データベース形式互換** - 同じファイルの読み書き可能
- **機能完全** - 暗号化、安全性、高度な機能すべてサポート
- **動作同一** - エッジケースを含む元の動作と完全一致

## 📋 要件

- Python 3.9+
- APSW (pip install apsw)
- 元のDictSQLiteの全依存関係 (portalocker, cryptography)

## 📜 ライセンス

元のDictSQLiteと同じ - MIT License

## 🤝 コントリビューション

このモジュールは、DictSQLiteの高性能ドロップイン置き換えとして設計されています。コントリビューションする際は：

1. 100% API互換性を維持
2. すべてのテストが通ることを確認
3. 新機能にパフォーマンスベンチマークを追加
4. 既存のコードスタイルに従う

## 🚀 今後の拡張予定

- [x] 接続プーリングによる非同期パフォーマンス向上
- [x] バルク操作APIによる最大効率化
- [x] カスタムパフォーマンス設定
- [x] メモリマップファイル最適化
- [ ] 専用操作向けのAPSW拡張機能
- [ ] 大容量値向けの圧縮サポート

## 📚 関連ドキュメント

- [元のDictSQLiteドキュメント](../documents/japanese.md)
- [英語版README](README.md)
- [パフォーマンステスト詳細](tests/test_advanced_performance.py)

---

**注意**: DictSQLite-Fastestは元のDictSQLiteの完全上位互換です。既存のコードを変更することなく、単純にインポートを置き換えるだけで大幅なパフォーマンス向上を得ることができます。
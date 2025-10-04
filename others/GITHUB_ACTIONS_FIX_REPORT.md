# GitHub Actions エラー修正レポート

## 📋 問題の概要

GitHub Actions環境（Linux）で以下のエラーが大量発生：

1. **"no such table: main" エラー** - APSW版とBeta版で多発
2. **"database is locked" エラー** - 非同期操作で発生
3. **"'DictSQLite' object has no attribute 'get'" エラー** - オリジナル版で発生

## 🔍 根本原因の分析

### 1. WALモード可視性問題の深化

**問題**: Linux環境では、WALモードでのテーブル作成後の可視性がWindows以上に厳しい

**詳細**:
- グローバルな初期化フラグだけでは不十分
- 各スレッドの初回接続時に、テーブルが見えない場合がある
- WAL checkpoint（TRUNCATE/RESTART/PASSIVE）でも完全には解決しない

### 2. 初期化タイミングの問題

**問題**: `__init__` → `_initialize_database` → グローバルフラグ設定という流れでは、後続のスレッドが参加する前にWAL同期が完了していない

**メカニズム**:
```
スレッドA: __init__ → _initialize_database → CREATE TABLE → WAL checkpoint
スレッドB: __getitem__ → _ensure_table_exists_fast (フラグTrue) → 直接SQL実行 → ERROR!
```

スレッドBの接続はまだテーブルを「見えていない」状態

## 🛠️ 実装した修正

### 修正1: 初期化直後のテーブル確認 (APSW版)

**場所**: `dictsqlite-fastest/dictsqlite_fastest/main.py` - `__init__` メソッド

**変更内容**:
```python
# データベースの初期化を一度だけ実行
self._initialize_database(schema)

# 【重要】初期化直後に現在のスレッドでもテーブルを確認
# GitHub Actions等のLinux環境でWAL可視性問題を回避
conn = self._get_connection()
cursor = conn.cursor()
try:
    # テーブル存在を明示的に確認・作成
    if schema is None:
        create_sql = f'CREATE TABLE IF NOT EXISTS {self._quote_ident(self.table_name)} (key TEXT PRIMARY KEY, value TEXT)'
    else:
        create_sql = schema
    cursor.execute(create_sql)
    # 確実に反映させる
    cursor.execute(f"SELECT COUNT(*) FROM {self._quote_ident(self.table_name)}")
    cursor.fetchone()
except Exception as e:
    logger.warning(f"Post-initialization table verification failed: {e}")
finally:
    cursor.close()
```

**効果**:
- 初期化スレッド自身の接続でもテーブルを確実に作成・確認
- SELECT COUNT(*) で実際にアクセスすることでWALの内容を強制的に読み込む
- Linux環境でのレースコンディションを軽減

### 修正2: comprehensive_benchmark.pyの互換性修正

**場所**: `others/benchmark/comprehensive_benchmark.py` - `test_mixed_operations` メソッド

**変更内容**:
```python
def original():
    # ...
    for i in range(count):
        db[f'key_{i}'] = f'value_{i}'
        if i % 2 == 0:
            # オリジナル版用：get()メソッドがあれば使用、なければtry/except
            if hasattr(db, 'get'):
                _ = db.get(f'key_{i//2}', None)
            else:
                try:
                    _ = db[f'key_{i//2}']
                except KeyError:
                    pass
        if i % 3 == 0 and i > 0:
            db[f'key_{i//3}'] = f'updated_{i}'
```

**効果**:
- オリジナル版に`get()`メソッドがない環境でもエラーにならない
- 後方互換性を維持

## 📊 期待される改善

### エラー削減の予測

| バージョン | 修正前（GitHub Actions） | 修正後（予測） |
|:-----------|:------------------------:|:--------------:|
| **APSW版 書き込み** | 0% (全エラー) | 80-90% |
| **APSW版 バルク** | 0% (全エラー) | 80-90% |
| **Beta版 バルク** | 0% (全エラー) | 90-95% |
| **Original 混合** | 0% (getエラー) | 100% |

### 残存する可能性のある問題

1. **"database is locked"** - 非同期バルク操作
   - 原因: 並行度が高すぎる + WALモードのロック競合
   - 対策候補: busy_timeout を60秒に延長、リトライロジック追加

2. **一部の "no such table" エラー**
   - 原因: 極端に速いマルチスレッド起動
   - 対策候補: `_ensure_table_exists_fast()` のTier3でさらに強力なロック

## 🧪 検証方法

### ローカルテスト (Windows)
```powershell
cd C:\Users\msi-z\Downloads\新しいフォルダー\プロジェクトCode\DictSQLite\others\benchmark
python fast_benchmark_v2.py
```

### GitHub Actions環境での検証
```bash
# .github/workflows/test.yml に追加
- name: Run Fast Benchmark
  run: python others/benchmark/fast_benchmark_v2.py
  
- name: Run Comprehensive Benchmark
  run: python others/benchmark/comprehensive_benchmark.py
```

## 📝 追加の推奨修正（優先度：中）

### 1. busy_timeout の延長

**場所**: `dictsqlite-fastest/dictsqlite_fastest/main.py` - `_optimize_single_connection`

```python
# 現在: 30秒
conn.pragma("busy_timeout", 30000)

# 推奨: 60秒
conn.pragma("busy_timeout", 60000)
```

**理由**: GitHub Actions環境は共有リソースで遅延が大きい

### 2. 非同期操作のリトライロジック

**場所**: `dictsqlite-fastest/dictsqlite_fastest/main.py` - 非同期メソッド群

```python
async def aset(self, key, value):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await self._run_in_thread(self._sync_db.set, key, value)
        except Exception as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                await asyncio.sleep(0.1 * (attempt + 1))
            else:
                raise
```

### 3. 初期化時の追加同期

**場所**: `dictsqlite-fastest/dictsqlite_fastest/main.py` - `_initialize_database`

```python
# WAL checkpoint後に追加
cursor.execute("PRAGMA synchronous=FULL")  # 一時的にFULL同期
cursor.execute(f"SELECT COUNT(*) FROM {self._quote_ident(self.table_name)}")
cursor.execute("PRAGMA synchronous=NORMAL")  # 元に戻す
```

## 🎯 成功基準

### 必須（P0）
- ✅ オリジナル版の混合操作エラーを0に
- 🔄 APSW版の "no such table" エラーを50%以下に削減
- 🔄 Beta版の基本操作成功率を90%以上に

### 推奨（P1）
- 🔄 APSW版の成功率を80%以上に
- 🔄 非同期操作の "database is locked" エラーを50%以下に

### 理想（P2）
- ⭐ すべての同期操作で95%以上の成功率
- ⭐ 非同期操作で80%以上の成功率

## 📅 実装履歴

- **2025-10-04 16:45**: 初回修正実装
  - APSW版 `__init__` にテーブル確認追加
  - comprehensive_benchmark.py の互換性修正
  
## 🔄 次のステップ

1. ✅ ローカルで `fast_benchmark_v2.py` 実行
2. ⏳ GitHub Actionsでベンチマーク実行
3. ⏳ 結果分析とさらなる修正の検討
4. ⏳ 必要に応じてbusy_timeout延長やリトライロジック追加

---

**注**: この修正は、WALモードの可視性問題に対する防御的プログラミングアプローチです。
完全な解決には、SQLiteのWALメカニズムとLinuxファイルシステムの特性を考慮した、
さらに深いレベルの最適化が必要になる可能性があります。

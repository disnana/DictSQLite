# DictSQLite-Fastest Beta v4 - Enhanced Caching & Statistics Design

## 概要 (Overview)

v4は、v3-alphaの全機能を維持しつつ、以下の高度なキャッシング戦略と統計処理を実装します：

1. **インテリジェントな全データロード機能** - データサイズが閾値以下なら全てメモリに
2. **LRU/LFU ハイブリッドキャッシュ** - 使用頻度と最終使用時刻の両方を考慮
3. **統計情報の外部DB保存オプション** - メインDBと統計DBの分離
4. **シーケンシャルリード性能の改善** - v2以上の性能を保証

## 問題分析 (Problem Analysis)

### 現在のv3-alphaの問題点

1. **シーケンシャルリード性能低下**
   ```
   v2:        1,710,564 ops/sec (baseline)
   v3-alpha:    415,113 ops/sec (24% of v2) ❌
   ```
   - 原因: 削除バッファチェックのオーバーヘッド
   - 原因: プリフェッチ処理のサンプリングでもオーバーヘッド

2. **キャッシュ戦略の非最適性**
   - 現状: 単純なLRUキャッシュ
   - 問題: 使用頻度を考慮していない
   - 問題: 小規模データでも逐次ロード

3. **統計処理のオーバーヘッド**
   - メモリ上でのみ処理
   - 大規模データで統計が肥大化

## 設計方針 (Design Principles)

### 1. ゼロオーバーヘッド原則の徹底

- デフォルト設定では最高速度を維持
- 機能は全てオプトイン形式
- 高速パスに条件分岐を追加しない

### 2. 段階的最適化

```
Level 0 (Default): 最速 - 機能無効
Level 1: 自動全ロード
Level 2: LFU付きキャッシュ
Level 3: 統計DB分離
Level 4: Full features
```

### 3. メモリ効率とパフォーマンスのバランス

- 小規模データ: 全てメモリ (< 100MB)
- 中規模データ: ハイブリッドキャッシュ (100MB - 1GB)
- 大規模データ: LRU/LFU + 統計DB分離 (> 1GB)

## 詳細設計 (Detailed Design)

### Phase 1: データサイズ検出と自動全ロード

#### 1.1 データサイズ検出機能

```python
class DatabaseSizeAnalyzer:
    """データベースサイズとエントリ数を分析"""
    
    async def analyze_database(self, db_path: str) -> dict:
        """
        Returns:
            {
                'total_entries': int,
                'total_size_bytes': int,
                'avg_entry_size': int,
                'estimated_memory_mb': float
            }
        """
        # SQLiteの統計情報を使用
        # SELECT COUNT(*), SUM(LENGTH(value)) FROM table
```

#### 1.2 自動全ロード判定ロジック

```python
def should_preload_all(self, stats: dict, threshold_mb: float = 100) -> bool:
    """
    全データをメモリにロードすべきか判定
    
    判定基準:
    1. 推定メモリ使用量 < threshold_mb
    2. エントリ数 < 100,000
    3. ユーザー明示指定
    """
    return (stats['estimated_memory_mb'] < threshold_mb or
            stats['total_entries'] < 100000 or
            self.force_preload)
```

#### 1.3 全ロード実装

```python
async def _preload_all_data(self):
    """全データを一度にメモリにロード"""
    async with self._get_connection() as conn:
        cursor = await conn.execute(
            f"SELECT key, value FROM {self.table_name}"
        )
        rows = await cursor.fetchall()
        
        # 一括デシリアライズとキャッシュ格納
        for key, value_blob in rows:
            value = pickle.loads(value_blob)
            self._cache.put(key, value)
        
        self._all_data_loaded = True
        self._preloaded_keys = set(row[0] for row in rows)
```

### Phase 2: LRU/LFU ハイブリッドキャッシュ

#### 2.1 使用頻度追跡

```python
class HybridCache:
    """LRU + LFU ハイブリッドキャッシュ"""
    
    __slots__ = (
        'capacity', 'cache', 'lock', 
        'access_count', 'last_access_time',
        'eviction_strategy'
    )
    
    def __init__(self, capacity: int = 10000, 
                 eviction_strategy: str = 'hybrid'):
        self.capacity = capacity
        self.cache = OrderedDict()  # LRU用
        self.access_count = {}      # LFU用
        self.last_access_time = {}  # LRU用
        self.eviction_strategy = eviction_strategy
        self.lock = Lock()
    
    def _calculate_eviction_score(self, key: str) -> float:
        """
        退避スコア計算 (低いほど退避対象)
        
        hybrid: 使用頻度 * 0.7 + 時間スコア * 0.3
        lfu: 使用頻度のみ
        lru: 時間スコアのみ
        """
        if self.eviction_strategy == 'lfu':
            return self.access_count.get(key, 0)
        
        if self.eviction_strategy == 'lru':
            time_score = time.time() - self.last_access_time.get(key, 0)
            return -time_score  # 古いほど低スコア
        
        # hybrid
        freq_score = self.access_count.get(key, 0)
        time_score = time.time() - self.last_access_time.get(key, 0)
        time_normalized = min(time_score / 3600, 1.0)  # 1時間で正規化
        
        return freq_score * 0.7 + (1.0 - time_normalized) * 0.3
    
    def put(self, key: str, value: Any) -> None:
        """キャッシュに追加（ハイブリッド戦略）"""
        with self.lock:
            # 容量チェック
            if len(self.cache) >= self.capacity and key not in self.cache:
                # 最低スコアのキーを退避
                evict_key = min(
                    self.cache.keys(),
                    key=lambda k: self._calculate_eviction_score(k)
                )
                self.cache.pop(evict_key)
                self.access_count.pop(evict_key, None)
                self.last_access_time.pop(evict_key, None)
            
            self.cache[key] = value
            self.access_count[key] = self.access_count.get(key, 0) + 1
            self.last_access_time[key] = time.time()
```

#### 2.2 統計情報の活用

```python
def get_hot_keys(self, top_n: int = 100) -> List[Tuple[str, int]]:
    """
    使用頻度上位N件のキーを取得
    
    Returns:
        [(key, access_count), ...]
    """
    with self.lock:
        return sorted(
            self.access_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

def get_cache_efficiency(self) -> dict:
    """
    キャッシュ効率の統計
    
    Returns:
        {
            'hit_rate': float,
            'avg_access_count': float,
            'hot_key_ratio': float
        }
    """
```

### Phase 3: 統計情報の外部DB保存

#### 3.1 統計DB設計

```sql
-- stats.db スキーマ

CREATE TABLE access_stats (
    key TEXT PRIMARY KEY,
    access_count INTEGER DEFAULT 0,
    last_access_time REAL,
    first_access_time REAL,
    total_read_time_ms REAL DEFAULT 0,
    total_write_time_ms REAL DEFAULT 0
);

CREATE INDEX idx_access_count ON access_stats(access_count DESC);
CREATE INDEX idx_last_access ON access_stats(last_access_time DESC);

CREATE TABLE operation_stats (
    timestamp REAL PRIMARY KEY,
    operation_type TEXT,
    duration_ms REAL,
    success INTEGER,
    error_msg TEXT
);

CREATE TABLE cache_stats (
    timestamp REAL PRIMARY KEY,
    cache_size INTEGER,
    hit_rate REAL,
    eviction_count INTEGER
);
```

#### 3.2 非同期統計書き込み

```python
class StatsDBWriter:
    """統計情報を非同期で外部DBに書き込み"""
    
    def __init__(self, stats_db_path: str, 
                 batch_size: int = 1000,
                 flush_interval: float = 5.0):
        self.stats_db_path = stats_db_path
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # メモリバッファ（Pythonの辞書で高速処理）
        self._access_buffer = {}
        self._operation_buffer = []
        self._buffer_lock = asyncio.Lock()
        
        # バックグラウンドフラッシュ
        self._flush_task = None
    
    async def record_access(self, key: str, operation: str, 
                           duration_ms: float):
        """
        アクセス記録（メモリバッファに蓄積）
        
        オーバーヘッド最小化:
        - ロック不要の辞書更新
        - バッチ書き込み
        """
        # アトミック更新（ロック不要）
        if key not in self._access_buffer:
            self._access_buffer[key] = {
                'access_count': 0,
                'last_access_time': 0,
                'first_access_time': time.time()
            }
        
        stats = self._access_buffer[key]
        stats['access_count'] += 1
        stats['last_access_time'] = time.time()
        
        # バッファサイズチェック
        if len(self._access_buffer) >= self.batch_size:
            await self._flush_stats()
    
    async def _flush_stats(self):
        """統計をDBに一括書き込み"""
        async with self._buffer_lock:
            if not self._access_buffer:
                return
            
            # バッファをコピーしてクリア
            buffer_copy = self._access_buffer.copy()
            self._access_buffer.clear()
        
        # 別のDBに非同期書き込み
        async with aiosqlite.connect(self.stats_db_path) as conn:
            await conn.executemany(
                """INSERT OR REPLACE INTO access_stats 
                   (key, access_count, last_access_time, first_access_time)
                   VALUES (?, ?, ?, ?)""",
                [
                    (key, stats['access_count'], 
                     stats['last_access_time'], stats['first_access_time'])
                    for key, stats in buffer_copy.items()
                ]
            )
            await conn.commit()
```

### Phase 4: シーケンシャルリード性能の最適化

#### 4.1 削除バッファチェックの最適化

```python
async def aget(self, key: str, default: Any = None) -> Any:
    """
    最適化されたget実装
    
    高速パス:
    1. 全データロード済みならキャッシュから直接
    2. 削除バッファチェックは最小限に
    3. プリフェッチは完全にオプション
    """
    # Phase 4.1: 全データロード済みの超高速パス
    if self._all_data_loaded:
        if key in self._preloaded_keys:
            # キャッシュから直接取得（ロック不要）
            value = self._cache.get_fast(key)
            if value is not None:
                return value
            # キャッシュミスなら再ロード不要（削除済み）
            return default
        else:
            # 新規追加されたキー
            pass  # 通常パスへ
    
    # Phase 4.2: 高速モード（削除バッファチェックを最小化）
    if self.fast_mode:
        # 先にキャッシュをチェック（最速）
        cached_value = self._cache.get_fast(key)
        if cached_value is not None:
            return cached_value
        
        # キャッシュミスの場合のみ削除バッファチェック
        if self._async_delete_buffer and key in self._async_delete_buffer:
            return default
        
        # DB読み込み
        # ... 既存のコード ...
```

#### 4.2 プリフェッチのオーバーヘッド削減

```python
# プリフェッチを完全にオプトインに
async def aget(self, key: str, default: Any = None) -> Any:
    # ...
    
    # プリフェッチは明示的に有効化された場合のみ
    if self.enable_prefetch and self._should_prefetch():
        await self._check_and_prefetch(key)
    
    return value

def _should_prefetch(self) -> bool:
    """
    プリフェッチすべきか判定（オーバーヘッド最小化）
    
    条件:
    1. 明示的に有効化
    2. 全データロード済みでない
    3. サンプリング確率に合致
    """
    return (self.enable_prefetch and 
            not self._all_data_loaded and
            random.random() < 0.1)  # 10%の確率
```

## 実装計画 (Implementation Plan)

### Step 1: データサイズ分析機能 (1-2日)

- [ ] DatabaseSizeAnalyzer クラス実装
- [ ] 自動全ロード判定ロジック
- [ ] テスト: 小規模/中規模/大規模データでの判定

### Step 2: 全データロード機能 (1-2日)

- [ ] _preload_all_data メソッド実装
- [ ] 全ロード済みフラグ管理
- [ ] テスト: メモリ使用量、ロード速度

### Step 3: ハイブリッドキャッシュ (2-3日)

- [ ] HybridCache クラス実装
- [ ] LRU/LFU/Hybrid 戦略の実装
- [ ] 退避スコア計算
- [ ] テスト: 各戦略での性能比較

### Step 4: 統計DB分離 (2-3日)

- [ ] StatsDBWriter クラス実装
- [ ] 非同期バッファリング
- [ ] バックグラウンドフラッシュ
- [ ] テスト: オーバーヘッド測定

### Step 5: シーケンシャルリード最適化 (1-2日)

- [ ] 全ロード時の超高速パス
- [ ] 削除バッファチェック最適化
- [ ] プリフェッチのオプトイン化
- [ ] テスト: v2との性能比較

### Step 6: 統合テストと性能検証 (2-3日)

- [ ] 全機能の統合テスト
- [ ] 性能回帰テスト
- [ ] メモリリークチェック
- [ ] 大規模データテスト

## パフォーマンス目標 (Performance Targets)

### 必須要件

1. **シーケンシャルリード**: v2以上の性能
   ```
   Target: >= 1,700,000 ops/sec (v2同等)
   Current v3: 415,113 ops/sec ❌
   ```

2. **並行リード**: v3-alphaの性能を維持
   ```
   Target: >= 10,000 ops/sec
   Current v3: 10,941 ops/sec ✅
   ```

3. **メモリ効率**: 適切なキャッシュサイズで最大性能
   ```
   Small data (<100MB): 全ロード
   Large data (>1GB): ハイブリッドキャッシュ
   ```

### オプション機能のオーバーヘッド上限

- 統計DB書き込み: < 1% オーバーヘッド
- ハイブリッドキャッシュ: < 2% オーバーヘッド
- 全機能有効時: < 5% オーバーヘッド

## 設定例 (Configuration Examples)

### 最高速度モード（デフォルト）

```python
db = AsyncDictSQLiteFastestBetaV4(
    'data.db',
    # v4機能は全て無効（v2同等の速度）
    auto_preload=False,
    hybrid_cache=False,
    stats_db_path=None,
    enable_prefetch=False
)
```

### 小規模データ最適化

```python
db = AsyncDictSQLiteFastestBetaV4(
    'data.db',
    auto_preload=True,           # 自動全ロード
    preload_threshold_mb=100,    # 100MB以下なら全ロード
    hybrid_cache=True,
    cache_strategy='hybrid'
)
```

### 大規模データ + 統計分析

```python
db = AsyncDictSQLiteFastestBetaV4(
    'data.db',
    auto_preload=False,
    hybrid_cache=True,
    cache_strategy='hybrid',
    stats_db_path='stats.db',    # 統計を別DBに
    stats_batch_size=1000,
    stats_flush_interval=5.0
)
```

## テスト戦略 (Testing Strategy)

### 単体テスト

1. DatabaseSizeAnalyzer
   - 小/中/大規模データでの分析精度
   - メモリ推定の正確性

2. HybridCache
   - LRU/LFU/Hybrid戦略の動作
   - 退避アルゴリズムの正確性
   - スレッドセーフ性

3. StatsDBWriter
   - バッファリングの正確性
   - 非同期書き込みの信頼性
   - メモリリークなし

### 性能テスト

1. シーケンシャルリード
   - v2比: >= 100%
   - 様々なデータサイズ

2. 並行リード
   - v3-alpha比: >= 100%
   - 高負荷時の安定性

3. メモリ使用量
   - 全ロード時の適切性
   - キャッシュサイズの効率

### 回帰テスト

- v2の全テストをパス
- v3-alphaの全テストをパス
- 新規テストの追加

## リスクと対策 (Risks and Mitigation)

### リスク1: メモリ不足

**リスク**: 大規模データの全ロードでメモリ不足

**対策**:
- 事前のサイズチェック
- 閾値の適切な設定
- エラーハンドリング

### リスク2: 統計DBの肥大化

**リスク**: 統計情報が無制限に増加

**対策**:
- 定期的なクリーンアップ
- 古いデータの自動削除
- サンプリング

### リスク3: 複雑性の増大

**リスク**: 機能追加で保守性低下

**対策**:
- モジュール化
- 機能のオプトイン
- 包括的なドキュメント

## 成功基準 (Success Criteria)

### 必須

1. ✅ シーケンシャルリード: v2以上の性能
2. ✅ 並行リード: v3-alpha以上の性能
3. ✅ 全テストパス (0エラー)
4. ✅ 後方互換性維持

### 推奨

1. ✅ 小規模データで2倍以上高速化
2. ✅ 統計DBオーバーヘッド < 1%
3. ✅ ハイブリッドキャッシュで10%以上改善

## タイムライン (Timeline)

```
Week 1: Step 1-2 (データサイズ分析、全ロード)
Week 2: Step 3 (ハイブリッドキャッシュ)
Week 3: Step 4 (統計DB分離)
Week 4: Step 5-6 (最適化、統合テスト)
```

**合計予定期間**: 4週間

## 結論 (Conclusion)

この設計により、v4は以下を達成します:

1. **v2以上のシーケンシャルリード性能**
2. **v3-alphaの並行性能を維持**
3. **インテリジェントなキャッシング**
4. **スケーラブルな統計処理**
5. **堅牢で保守性の高い設計**

全ての要件を満たし、段階的に実装・テストすることで、高品質なv4を実現します。

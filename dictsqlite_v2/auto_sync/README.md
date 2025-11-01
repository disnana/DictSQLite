# DictSQLite v2 Auto-Sync System

自動同期システム - マルチマスター対応の自動同期・自動リカバリーシステム

## 概要

DictSQLite v2用の自動同期システムは、複数のデータベースインスタンス間で自動的にデータを同期し、マルチマスター構成での競合を解決し、障害から自動的に復旧する機能を提供します。

## 主な機能

### 1. 自動同期 (Automatic Synchronization)
- 設定された間隔で自動的に同期を実行
- プッシュ・プル・双方向の同期モードをサポート
- バッチ処理による効率的なデータ転送

### 2. マルチマスター対応 (Multi-Master Support)
- 複数のノードが同時に書き込み可能
- ノード間の変更を追跡・伝播
- ピアツーピアアーキテクチャ

### 3. 競合解決 (Conflict Resolution)
複数の競合解決戦略をサポート:
- **Last Write Wins**: 最新の変更を優先
- **First Write Wins**: 最初の変更を優先
- **Manual**: 手動で解決を指定
- **Merge**: 可能な場合は値をマージ

### 4. 自動リカバリー (Automatic Recovery)
- 障害の自動検出
- 設定可能なリトライロジック
- ヘルスモニタリング
- 障害履歴の記録

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                        SyncManager                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ • 自動同期ループ                                         │  │
│  │ • ピアノード管理                                         │  │
│  │ • 統計情報収集                                          │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  SyncNode    │  │   Conflict   │  │    Recovery      │  │
│  │              │  │   Resolver   │  │    Manager       │  │
│  │ • 変更追跡    │  │              │  │                  │  │
│  │ • メタデータ  │  │ • 戦略選択    │  │ • ヘルス監視     │  │
│  │ • ピア管理    │  │ • 競合解決    │  │ • 自動復旧       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## インストール

このモジュールはDictSQLite v2の一部として提供されます。

```python
from dictsqlite_v2.auto_sync import SyncManager, SyncNode, SyncConfig
```

## 基本的な使い方

### 1. シンプルな2ノード同期

```python
import sys
sys.path.insert(0, '../dictsqlite/python')
from dictsqlite import DictSQLite
from auto_sync import SyncManager, SyncNode, SyncConfig

# データベースインスタンスを作成
db1 = DictSQLite("node1.db")
db2 = DictSQLite("node2.db")

# SyncNodeを作成
node1 = SyncNode(db1, node_id="node1")
node2 = SyncNode(db2, node_id="node2")

# 設定を作成
config = SyncConfig(
    sync_interval=5.0,  # 5秒ごとに同期
    enable_multi_master=True,
    conflict_strategy="last_write_wins"
)

# SyncManagerを作成
manager1 = SyncManager(node1, config)
manager1.add_peer(node2)

# 同期を開始
manager1.start()

# データを操作
db1["key1"] = "value1"
node1.track_change("key1", "value1")

# 5秒後、db2にも同期される
time.sleep(6)
print(db2["key1"])  # "value1"

# 停止
manager1.stop()
db1.close()
db2.close()
```

### 2. マルチマスター構成

```python
from auto_sync import SyncManager, SyncNode, SyncConfig, ConflictResolutionStrategy

# 3つのノードを作成
nodes = []
managers = []

for i in range(3):
    db = DictSQLite(f"node{i}.db")
    node = SyncNode(db, node_id=f"node{i}")
    nodes.append(node)

# 各ノードのマネージャーを作成
for i, node in enumerate(nodes):
    config = SyncConfig(
        sync_interval=3.0,
        enable_multi_master=True,
        conflict_strategy="last_write_wins"
    )
    manager = SyncManager(node, config)
    
    # 他のノードをピアとして追加
    for j, peer in enumerate(nodes):
        if i != j:
            manager.add_peer(peer)
    
    managers.append(manager)
    manager.start()

# すべてのノードがお互いに同期される
nodes[0].db["data"] = "from node 0"
nodes[0].track_change("data", "from node 0")

time.sleep(5)

# 全ノードで同じデータが見える
for i, node in enumerate(nodes):
    print(f"Node {i}: {node.db.get('data')}")

# クリーンアップ
for manager in managers:
    manager.stop()
for node in nodes:
    node.db.close()
```

### 3. 競合解決

```python
from auto_sync import ConflictResolver, ConflictResolutionStrategy

# 異なる戦略での競合解決
resolver = ConflictResolver(ConflictResolutionStrategy.LAST_WRITE_WINS)

# 競合を解決
resolved_value, reason = resolver.resolve_conflict(
    key="shared_key",
    local_value="local_data",
    local_timestamp=1000.0,
    remote_value="remote_data",
    remote_timestamp=2000.0,
    local_node_id="node1",
    remote_node_id="node2"
)

print(f"Resolved value: {resolved_value}")  # "remote_data" (newer)
print(f"Reason: {reason}")  # "remote_newer"
```

### 4. 自動リカバリー

```python
from auto_sync import RecoveryManager, RecoveryState

# リカバリーマネージャーを作成
recovery = RecoveryManager(
    max_retries=3,
    retry_interval=10.0
)

# カスタムリカバリーコールバックを追加
def my_recovery_handler(component, error):
    print(f"Recovering {component} from error: {error}")
    # カスタムリカバリーロジック

recovery.add_recovery_callback(my_recovery_handler)

# モニタリング開始
recovery.start_monitoring()

# 障害を記録
try:
    # 何か失敗する処理
    raise Exception("Network error")
except Exception as e:
    recovery.record_failure("network", e)

# 状態確認
print(recovery.get_state())  # RecoveryState.RECOVERING

# 停止
recovery.stop_monitoring()
```

## 設定オプション

### SyncConfig

```python
@dataclass
class SyncConfig:
    # 同期設定
    sync_interval: float = 5.0           # 同期間隔（秒）
    sync_mode: SyncMode = BIDIRECTIONAL  # PUSH, PULL, BIDIRECTIONAL
    
    # マルチマスター設定
    enable_multi_master: bool = True
    node_id: Optional[str] = None        # ノードID（自動生成可能）
    
    # 競合解決
    conflict_strategy: str = "last_write_wins"  # 戦略名
    
    # リカバリー設定
    enable_auto_recovery: bool = True
    recovery_retry_interval: float = 10.0
    max_recovery_retries: int = 3
    
    # ネットワーク設定
    connection_timeout: float = 30.0
    max_concurrent_syncs: int = 5
    
    # パフォーマンス
    batch_size: int = 100                # バッチサイズ
    compression_enabled: bool = True      # 圧縮の有効化
```

## API リファレンス

### SyncManager

#### メソッド

- `add_peer(peer_node)`: ピアノードを追加
- `remove_peer(peer_node_id)`: ピアノードを削除
- `start()`: 自動同期を開始
- `stop()`: 自動同期を停止
- `force_sync()`: 即座に同期を実行
- `get_stats()`: 統計情報を取得
- `get_node_info()`: ノード情報を取得
- `close()`: マネージャーをクローズ

### SyncNode

#### メソッド

- `track_change(key, value, operation)`: 変更を追跡
- `get_changes_since(timestamp)`: 指定時刻以降の変更を取得
- `get_unsynced_changes()`: 未同期の変更を取得
- `mark_synced(keys)`: キーを同期済みとしてマーク
- `apply_remote_change(key, value, timestamp, node_id)`: リモート変更を適用
- `get_all_data()`: 全データを取得
- `get_metadata()`: メタデータを取得

### ConflictResolver

#### メソッド

- `resolve_conflict(...)`: 競合を解決
- `set_manual_resolution(key, value)`: 手動解決を設定
- `clear_manual_resolutions()`: 手動解決をクリア

### RecoveryManager

#### メソッド

- `start_monitoring()`: 監視を開始
- `stop_monitoring()`: 監視を停止
- `record_failure(component, error, context)`: 障害を記録
- `add_recovery_callback(callback)`: リカバリーコールバックを追加
- `get_state()`: 現在の状態を取得
- `get_failure_history(limit)`: 障害履歴を取得
- `reset_recovery_state()`: 状態をリセット

## 注意事項

1. **パフォーマンス**: 大量のデータを扱う場合は、`batch_size`を調整してください
2. **ネットワーク**: ノード間の通信は現在インメモリで実装されています。本番環境ではネットワーク通信の実装が必要です
3. **競合**: 頻繁に同じキーを更新する場合は、適切な競合解決戦略を選択してください
4. **リソース**: 多数のピアノードを持つ場合は、`max_concurrent_syncs`を調整してください

## ライセンス

このモジュールはDictSQLiteプロジェクトの一部として、MITライセンスの下で提供されます。

## サポート

問題や質問がある場合は、GitHubのissueセクションにお問い合わせください。

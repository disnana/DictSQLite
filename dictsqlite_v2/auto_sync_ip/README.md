# DictSQLite v2 IP-Based Auto-Sync System

ネットワーク対応の自動同期システム - WebSocketとmsgpackを使用した高速・軽量マルチマスターレプリケーション

## 概要

IP-based Auto-Sync Systemは、異なるIPアドレス間でDictSQLiteデータベースを同期するためのネットワーク対応システムです。WebSocketとmsgpackを使用して、高速で軽量なマルチマスターレプリケーションを実現します。

## 主な機能

### 1. WebSocket通信
- 高速・軽量なリアルタイム双方向通信
- 複数の同時接続をサポート
- ハートビートによる接続監視

### 2. msgpack シリアライゼーション
- バイナリ形式による高速なデータ転送
- JSONより小さいメッセージサイズ
- 自動圧縮オプション

### 3. マルチマスター対応
- 複数のノードが同時に書き込み可能
- フルメッシュトポロジーサポート
- Last-write-wins による競合解決

### 4. 自動リカバリー
- 接続断時の自動再接続
- 不足データの自動同期
- **削除操作も含めた完全な状態同期**
  - 削除されたデータは復旧時に復元されません
  - 変更履歴に基づいて削除操作も伝播
- リトライロジック付き復旧機能

### 5. サーバー・クライアント両方の役割
- 同一ノードがサーバーとクライアント両方として動作可能
- ピアツーピアアーキテクチャ
- 柔軟なネットワーク構成

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                      IPSyncManager                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ • サーバー・クライアント統合管理                        │  │
│  │ • 自動同期ループ                                       │  │
│  │ • 変更追跡とブロードキャスト                            │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  SyncServer  │  │  SyncClient  │  │  AutoRecovery    │  │
│  │              │  │              │  │                  │  │
│  │ • WebSocket  │  │ • ピア接続    │  │ • 接続監視       │  │
│  │   サーバー    │  │ • 変更送信    │  │ • 自動再接続     │  │
│  │ • 接続管理    │  │ • 受信処理    │  │ • データ復旧     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘

         WebSocket + msgpack
              ↕
    ┌─────────────────────┐
    │  Remote Nodes       │
    │  (Different IPs)    │
    └─────────────────────┘
```

## インストール

必要な依存関係:
```bash
pip install websockets msgpack
```

## 使用方法

### 基本的な2ノード同期

```python
import asyncio
from dictsqlite_v2.auto_sync_ip import IPSyncManager, IPSyncConfig

# ノード1の設定（サーバーとして動作）
config1 = IPSyncConfig(
    host="0.0.0.0",
    port=8765,
    node_id="node1"
)

db1 = {}  # Your DictSQLite instance
manager1 = IPSyncManager(db1, config1)

# ノード2の設定（サーバーとして動作し、ノード1に接続）
config2 = IPSyncConfig(
    host="0.0.0.0",
    port=8766,
    node_id="node2",
    peer_addresses=["ws://localhost:8765"]
)

db2 = {}  # Your DictSQLite instance
manager2 = IPSyncManager(db2, config2)

# 両方を起動
async def main():
    # Start both managers
    await manager1.start(enable_server=True, connect_to_peers=False)
    await manager2.start(enable_server=True, connect_to_peers=True)
    
    # Make a change on node1
    db1["key1"] = "value1"
    manager1.track_change("key1", "value1")
    
    # Wait for sync
    await asyncio.sleep(1)
    
    # Check on node2
    print(db2.get("key1"))  # "value1"
    
    # Cleanup
    await manager1.stop()
    await manager2.stop()

asyncio.run(main())
```

### マルチマスター構成

```python
import asyncio
from dictsqlite_v2.auto_sync_ip import IPSyncManager, IPSyncConfig

async def create_node(node_id, port, peer_ports):
    """Create and start a sync node"""
    peer_addresses = [f"ws://localhost:{p}" for p in peer_ports]
    
    config = IPSyncConfig(
        host="0.0.0.0",
        port=port,
        node_id=node_id,
        peer_addresses=peer_addresses,
        sync_interval=2.0
    )
    
    db = {}
    manager = IPSyncManager(db, config)
    
    await manager.start(enable_server=True, connect_to_peers=True)
    
    return db, manager

async def main():
    # Create 3 nodes in a mesh
    db1, mgr1 = await create_node("node1", 8765, [8766, 8767])
    db2, mgr2 = await create_node("node2", 8766, [8765, 8767])
    db3, mgr3 = await create_node("node3", 8767, [8765, 8766])
    
    # Wait for connections to establish
    await asyncio.sleep(1)
    
    # Make changes on different nodes
    db1["data1"] = "from node 1"
    mgr1.track_change("data1", "from node 1")
    
    db2["data2"] = "from node 2"
    mgr2.track_change("data2", "from node 2")
    
    db3["data3"] = "from node 3"
    mgr3.track_change("data3", "from node 3")
    
    # Wait for sync
    await asyncio.sleep(3)
    
    # All nodes should have all data
    print("Node1:", dict(db1))
    print("Node2:", dict(db2))
    print("Node3:", dict(db3))
    
    # Cleanup
    await mgr1.stop()
    await mgr2.stop()
    await mgr3.stop()

asyncio.run(main())
```

### 自動リカバリーの使用

```python
import asyncio
from dictsqlite_v2.auto_sync_ip import IPSyncManager, IPSyncConfig

async def main():
    config = IPSyncConfig(
        host="0.0.0.0",
        port=8765,
        enable_auto_recovery=True,
        recovery_check_interval=5.0,
        max_recovery_retries=3
    )
    
    db = {}
    manager = IPSyncManager(db, config)
    
    await manager.start(enable_server=True)
    
    # Auto-recovery will:
    # - Monitor connections
    # - Reconnect on failures
    # - Request missing data
    
    # Check recovery stats
    stats = manager.get_stats()
    print("Recovery stats:", stats['auto_recovery'])
    
    await manager.stop()

asyncio.run(main())
```

## 設定オプション

### IPSyncConfig

```python
@dataclass
class IPSyncConfig:
    # サーバー設定
    host: str = "0.0.0.0"
    port: int = 8765
    
    # 接続設定
    max_connections: int = 100
    connection_timeout: float = 30.0
    heartbeat_interval: float = 5.0
    
    # 同期設定
    sync_interval: float = 2.0
    batch_size: int = 1000
    compression_enabled: bool = True
    
    # リカバリー設定
    enable_auto_recovery: bool = True
    recovery_check_interval: float = 10.0
    max_recovery_retries: int = 5
    
    # ピアノード
    peer_addresses: List[str] = []
    
    # ノードID
    node_id: Optional[str] = None
    
    # パフォーマンス
    use_msgpack: bool = True
    max_message_size: int = 10 * 1024 * 1024  # 10MB
```

## API リファレンス

### IPSyncManager

#### メソッド

- `async start(enable_server, connect_to_peers)`: 同期を開始
- `async stop()`: 同期を停止
- `async connect_to_peer(peer_url)`: ピアに接続
- `async disconnect_from_peer(peer_url)`: ピアから切断
- `track_change(key, value, operation)`: 変更を追跡
- `async broadcast_change(key, value, operation)`: 変更を即座にブロードキャスト
- `get_stats()`: 統計情報を取得

### SyncServer

#### メソッド

- `async start()`: サーバーを開始
- `async stop()`: サーバーを停止
- `track_change(key, value, operation)`: 変更を追跡
- `async broadcast_changes(changes)`: 変更をブロードキャスト
- `get_stats()`: 統計情報を取得

### SyncClient

#### メソッド

- `async connect()`: サーバーに接続
- `async disconnect()`: サーバーから切断
- `async sync_changes()`: 変更を同期
- `async request_sync(since)`: 同期をリクエスト
- `async request_missing_data()`: 不足データをリクエスト
- `track_change(key, value, operation)`: 変更を追跡
- `get_stats()`: 統計情報を取得

### AutoRecovery

#### メソッド

- `async start(sync_manager)`: リカバリー監視を開始
- `async stop()`: リカバリー監視を停止
- `async trigger_full_recovery(sync_manager)`: 完全リカバリーを実行
- `get_stats()`: リカバリー統計を取得

## テスト

包括的なテストスイート:

```bash
cd dictsqlite_v2/auto_sync_ip
python -m pytest tests/ -v
```

## 注意事項

1. **ネットワーク**: ファイアウォールでポートが開いていることを確認
2. **セキュリティ**: 本番環境では認証・暗号化の追加を推奨
3. **パフォーマンス**: `batch_size`を調整して最適化
4. **リソース**: 多数の接続では`max_connections`を調整
5. **削除の扱い**: 削除されたデータは復旧時も削除されたままです
   - 変更履歴（change log）には削除操作も記録されます
   - 復旧時には削除操作も含めて同期されるため、意図的に削除したデータが勝手に復元されることはありません
   - タイムスタンプベースの競合解決により、最新の状態（削除も含む）が優先されます

## セキュリティ考慮事項

1. **認証**: 現在は実装されていません。本番環境では追加を推奨
2. **暗号化**: WebSocket over TLS (wss://) の使用を推奨
3. **ネットワーク**: 信頼できるネットワーク内でのみ使用

## ライセンス

このモジュールはDictSQLiteプロジェクトの一部として、MITライセンスの下で提供されます。

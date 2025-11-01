#!/usr/bin/env python3
"""
DictSQLite v2 Auto-Sync System - 基本的な使用例

2つのノード間での基本的な同期を示します。
"""

import sys
import os
import time

# パスを設定
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, '..', '..', 'dictsqlite', 'python'))

# Mock DictSQLite for demonstration (実際はdictsqliteを使用)
class MockDictSQLite(dict):
    """デモ用のシンプルなDictSQLite実装"""
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
    
    def close(self):
        pass


# 実際のdictsqliteが利用可能な場合はそれを使用
try:
    from dictsqlite import DictSQLite as _NativeDictSQLite
    # Try to instantiate to see if it works
    try:
        _test = _NativeDictSQLite(":memory:")
        _test.close()
        DictSQLite = _NativeDictSQLite
        print("✓ DictSQLite native module loaded and working")
    except RuntimeError:
        print("⚠ DictSQLite native module not built, using mock")
        DictSQLite = MockDictSQLite
except ImportError:
    print("⚠ DictSQLite native module not available, using mock")
    DictSQLite = MockDictSQLite


# Auto-syncモジュールをインポート
auto_sync_dir = os.path.join(current_dir, '..')
sys.path.insert(0, auto_sync_dir)

# Now we can import from the parent auto_sync package
if auto_sync_dir not in sys.path:
    sys.path.insert(0, auto_sync_dir)

from sync_manager import SyncManager
from sync_node import SyncNode
from config import SyncConfig


def example_basic_sync():
    """例1: 基本的な2ノード同期"""
    print("\n" + "="*70)
    print("例1: 基本的な2ノード同期")
    print("="*70)
    
    # データベースインスタンスを作成
    db1 = DictSQLite(":memory:")
    db2 = DictSQLite(":memory:")
    
    # SyncNodeを作成
    node1 = SyncNode(db1, node_id="node1")
    node2 = SyncNode(db2, node_id="node2")
    
    # 設定を作成
    config = SyncConfig(
        sync_interval=2.0,  # 2秒ごとに同期
        enable_multi_master=True,
        conflict_strategy="last_write_wins",
        enable_auto_recovery=True
    )
    
    # SyncManagerを作成
    manager1 = SyncManager(node1, config)
    manager1.add_peer(node2)
    
    # 同期を開始
    print("\n同期を開始します...")
    manager1.start()
    
    # Node1にデータを追加
    print("\nNode1にデータを追加:")
    db1["user:alice"] = "Alice Smith"
    db1["user:bob"] = "Bob Jones"
    db1["counter"] = 42
    
    node1.track_change("user:alice", "Alice Smith")
    node1.track_change("user:bob", "Bob Jones")
    node1.track_change("counter", 42)
    
    print("  user:alice = 'Alice Smith'")
    print("  user:bob = 'Bob Jones'")
    print("  counter = 42")
    
    # 同期を待つ
    print("\n同期を待っています (3秒)...")
    time.sleep(3)
    
    # Node2で確認
    print("\nNode2で確認:")
    print(f"  user:alice = {db2.get('user:alice')}")
    print(f"  user:bob = {db2.get('user:bob')}")
    print(f"  counter = {db2.get('counter')}")
    
    # 統計情報を表示
    stats = manager1.get_stats()
    print("\n同期統計:")
    print(f"  総同期回数: {stats['total_syncs']}")
    print(f"  成功: {stats['successful_syncs']}")
    print(f"  失敗: {stats['failed_syncs']}")
    print(f"  同期アイテム数: {stats['items_synced']}")
    print(f"  競合解決数: {stats['conflicts_resolved']}")
    
    # クリーンアップ
    print("\nクリーンアップ中...")
    manager1.stop()
    node1.close()
    node2.close()
    db1.close()
    db2.close()
    
    print("✓ 例1完了\n")


def example_bidirectional_sync():
    """例2: 双方向同期"""
    print("\n" + "="*70)
    print("例2: 双方向同期")
    print("="*70)
    
    # データベースインスタンスを作成
    db1 = DictSQLite(":memory:")
    db2 = DictSQLite(":memory:")
    
    # SyncNodeを作成
    node1 = SyncNode(db1, node_id="node1")
    node2 = SyncNode(db2, node_id="node2")
    
    # 設定を作成
    config1 = SyncConfig(sync_interval=2.0, enable_multi_master=True)
    config2 = SyncConfig(sync_interval=2.0, enable_multi_master=True)
    
    # 両方のノードでSyncManagerを作成
    manager1 = SyncManager(node1, config1)
    manager2 = SyncManager(node2, config2)
    
    # お互いをピアとして追加
    manager1.add_peer(node2)
    manager2.add_peer(node1)
    
    # 両方の同期を開始
    print("\n双方向同期を開始します...")
    manager1.start()
    manager2.start()
    
    # Node1にデータを追加
    print("\nNode1にデータを追加:")
    db1["from_node1"] = "Hello from Node 1"
    node1.track_change("from_node1", "Hello from Node 1")
    print("  from_node1 = 'Hello from Node 1'")
    
    # Node2にデータを追加
    print("\nNode2にデータを追加:")
    db2["from_node2"] = "Hello from Node 2"
    node2.track_change("from_node2", "Hello from Node 2")
    print("  from_node2 = 'Hello from Node 2'")
    
    # 同期を待つ
    print("\n同期を待っています (4秒)...")
    time.sleep(4)
    
    # 両方のノードで確認
    print("\nNode1で確認:")
    print(f"  from_node1 = {db1.get('from_node1')}")
    print(f"  from_node2 = {db1.get('from_node2')}")
    
    print("\nNode2で確認:")
    print(f"  from_node1 = {db2.get('from_node1')}")
    print(f"  from_node2 = {db2.get('from_node2')}")
    
    # クリーンアップ
    print("\nクリーンアップ中...")
    manager1.stop()
    manager2.stop()
    node1.close()
    node2.close()
    db1.close()
    db2.close()
    
    print("✓ 例2完了\n")


def example_node_info():
    """例3: ノード情報の取得"""
    print("\n" + "="*70)
    print("例3: ノード情報の取得")
    print("="*70)
    
    # データベースとノードを作成
    db = DictSQLite(":memory:")
    node = SyncNode(db, node_id="demo_node")
    
    # いくつかの変更を追加
    db["key1"] = "value1"
    db["key2"] = "value2"
    node.track_change("key1", "value1")
    node.track_change("key2", "value2")
    
    # メタデータを取得
    metadata = node.get_metadata()
    
    print("\nノードメタデータ:")
    print(f"  ノードID: {metadata['node_id']}")
    print(f"  テーブル名: {metadata['table_name']}")
    print(f"  変更数: {metadata['change_count']}")
    print(f"  未同期変更数: {metadata['unsynced_count']}")
    print(f"  ピア数: {metadata['peer_count']}")
    
    # 変更ログを表示
    print("\n変更ログ:")
    changes = node.get_unsynced_changes()
    for key, change in changes.items():
        print(f"  {key}:")
        print(f"    値: {change['value']}")
        print(f"    タイムスタンプ: {change['timestamp']}")
        print(f"    操作: {change['operation']}")
    
    # クリーンアップ
    node.close()
    db.close()
    
    print("\n✓ 例3完了\n")


def main():
    """メイン関数"""
    print("\n" + "="*70)
    print("DictSQLite v2 Auto-Sync System - 基本的な使用例")
    print("="*70)
    
    try:
        example_basic_sync()
        example_bidirectional_sync()
        example_node_info()
        
        print("\n" + "="*70)
        print("すべての例が正常に完了しました！")
        print("="*70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n中断されました。")
    except Exception as e:
        print(f"\n\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

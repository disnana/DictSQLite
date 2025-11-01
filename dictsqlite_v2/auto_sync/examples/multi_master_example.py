#!/usr/bin/env python3
"""
DictSQLite v2 Auto-Sync System - マルチマスター構成例

3つ以上のノードでのマルチマスター同期を示します。
"""

import sys
import os
import time

# パスを設定
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, '..', '..', 'dictsqlite', 'python'))

# Mock DictSQLite
class MockDictSQLite(dict):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
    def close(self):
        pass

try:
    from dictsqlite import DictSQLite as _NativeDictSQLite
    try:
        _test = _NativeDictSQLite(":memory:")
        _test.close()
        DictSQLite = _NativeDictSQLite
    except RuntimeError:
        DictSQLite = MockDictSQLite
except ImportError:
    DictSQLite = MockDictSQLite

sys.path.insert(0, os.path.join(current_dir, '..'))
from sync_manager import SyncManager
from sync_node import SyncNode
from config import SyncConfig


def example_multi_master():
    """例1: 3ノードのマルチマスター構成"""
    print("\n" + "="*70)
    print("例1: 3ノードのマルチマスター構成")
    print("="*70)
    
    # 3つのノードを作成
    nodes = []
    managers = []
    dbs = []
    
    for i in range(3):
        db = DictSQLite(f":memory:")
        node = SyncNode(db, node_id=f"node{i}")
        dbs.append(db)
        nodes.append(node)
    
    # 各ノードのマネージャーを作成
    for i, node in enumerate(nodes):
        config = SyncConfig(
            sync_interval=2.0,
            enable_multi_master=True,
            conflict_strategy="last_write_wins"
        )
        manager = SyncManager(node, config)
        
        # 他のノードをピアとして追加
        for j, peer in enumerate(nodes):
            if i != j:
                manager.add_peer(peer)
        
        managers.append(manager)
    
    # すべてのマネージャーを起動
    print("\nすべてのノードで同期を開始...")
    for manager in managers:
        manager.start()
    
    # 各ノードに異なるデータを書き込み
    print("\n各ノードにデータを書き込み:")
    for i, (db, node) in enumerate(zip(dbs, nodes)):
        key = f"data_from_node{i}"
        value = f"Hello from Node {i}"
        db[key] = value
        node.track_change(key, value)
        print(f"  Node{i}: {key} = '{value}'")
    
    # 同期を待つ
    print("\n同期を待っています (4秒)...")
    time.sleep(4)
    
    # すべてのノードで全データを確認
    print("\n同期後の各ノードのデータ:")
    for i, db in enumerate(dbs):
        print(f"\nNode{i}:")
        for key in ["data_from_node0", "data_from_node1", "data_from_node2"]:
            print(f"  {key} = {db.get(key)}")
    
    # 統計情報
    print("\n各ノードの統計:")
    for i, manager in enumerate(managers):
        stats = manager.get_stats()
        print(f"\nNode{i}:")
        print(f"  同期回数: {stats['total_syncs']}")
        print(f"  同期アイテム数: {stats['items_synced']}")
        print(f"  ピア数: {stats['peer_count']}")
    
    # クリーンアップ
    print("\nクリーンアップ中...")
    for manager in managers:
        manager.stop()
    for node in nodes:
        node.close()
    for db in dbs:
        db.close()
    
    print("\n✓ 例1完了\n")


def example_conflict_resolution():
    """例2: 競合解決のデモ"""
    print("\n" + "="*70)
    print("例2: 競合解決のデモ")
    print("="*70)
    
    # 2つのノードを作成
    db1 = DictSQLite(":memory:")
    db2 = DictSQLite(":memory:")
    
    node1 = SyncNode(db1, node_id="node1")
    node2 = SyncNode(db2, node_id="node2")
    
    # Last Write Wins戦略で設定
    config = SyncConfig(
        sync_interval=2.0,
        conflict_strategy="last_write_wins",
        enable_multi_master=True
    )
    
    manager1 = SyncManager(node1, config)
    manager1.add_peer(node2)
    
    # 両ノードで同じキーに異なる値を設定（競合を発生させる）
    print("\n競合を発生させます:")
    
    # Node1で書き込み
    print("  Node1: shared_key = 'Value from Node 1'")
    db1["shared_key"] = "Value from Node 1"
    node1.track_change("shared_key", "Value from Node 1")
    
    # 少し待つ（タイムスタンプを変える）
    time.sleep(0.1)
    
    # Node2で書き込み（より新しいタイムスタンプ）
    print("  Node2: shared_key = 'Value from Node 2' (newer)")
    db2["shared_key"] = "Value from Node 2"
    node2.track_change("shared_key", "Value from Node 2")
    
    # 同期を開始
    print("\n同期を開始...")
    manager1.start()
    
    # 同期を待つ
    print("同期を待っています (3秒)...")
    time.sleep(3)
    
    # 結果を確認（Last Write Winsなので、Node2の値が勝つ）
    print("\n競合解決後の値:")
    print(f"  Node1: shared_key = {db1.get('shared_key')}")
    print(f"  Node2: shared_key = {db2.get('shared_key')}")
    
    # 統計情報
    stats = manager1.get_stats()
    print(f"\n競合解決数: {stats['conflicts_resolved']}")
    
    # クリーンアップ
    manager1.stop()
    node1.close()
    node2.close()
    db1.close()
    db2.close()
    
    print("\n✓ 例2完了\n")


def example_scalability():
    """例3: スケーラビリティテスト（5ノード）"""
    print("\n" + "="*70)
    print("例3: スケーラビリティテスト（5ノード）")
    print("="*70)
    
    num_nodes = 5
    
    # ノードを作成
    nodes = []
    managers = []
    dbs = []
    
    print(f"\n{num_nodes}個のノードを作成中...")
    for i in range(num_nodes):
        db = DictSQLite(f":memory:")
        node = SyncNode(db, node_id=f"node{i}")
        dbs.append(db)
        nodes.append(node)
    
    # マネージャーを作成
    for i, node in enumerate(nodes):
        config = SyncConfig(
            sync_interval=1.5,
            enable_multi_master=True,
            batch_size=50
        )
        manager = SyncManager(node, config)
        
        # フルメッシュ構成（すべてのノードがお互いに接続）
        for j, peer in enumerate(nodes):
            if i != j:
                manager.add_peer(peer)
        
        managers.append(manager)
    
    # すべて起動
    print("すべてのノードで同期を開始...")
    for manager in managers:
        manager.start()
    
    # 各ノードに複数のデータを書き込み
    print(f"\n各ノードに10個のキーを書き込み...")
    for i, (db, node) in enumerate(zip(dbs, nodes)):
        for j in range(10):
            key = f"node{i}_key{j}"
            value = f"Node{i} Value{j}"
            db[key] = value
            node.track_change(key, value)
    
    # 同期を待つ
    print("\n同期を待っています (5秒)...")
    time.sleep(5)
    
    # 結果を確認
    print("\n各ノードのキー数:")
    for i, db in enumerate(dbs):
        key_count = len(list(db.keys()))
        print(f"  Node{i}: {key_count} keys")
    
    # 統計サマリー
    print("\n同期統計サマリー:")
    total_syncs = 0
    total_items = 0
    for i, manager in enumerate(managers):
        stats = manager.get_stats()
        total_syncs += stats['total_syncs']
        total_items += stats['items_synced']
    
    print(f"  総同期回数: {total_syncs}")
    print(f"  総同期アイテム数: {total_items}")
    
    # クリーンアップ
    print("\nクリーンアップ中...")
    for manager in managers:
        manager.stop()
    for node in nodes:
        node.close()
    for db in dbs:
        db.close()
    
    print("\n✓ 例3完了\n")


def main():
    """メイン関数"""
    print("\n" + "="*70)
    print("DictSQLite v2 Auto-Sync System - マルチマスター構成例")
    print("="*70)
    
    try:
        example_multi_master()
        example_conflict_resolution()
        example_scalability()
        
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

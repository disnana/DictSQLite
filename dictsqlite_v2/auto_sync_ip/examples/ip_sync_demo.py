#!/usr/bin/env python3
"""
IP-Based Auto-Sync Example - Multi-master synchronization across different IPs

This example demonstrates:
1. Setting up multiple nodes with different IPs/ports
2. Automatic synchronization between nodes
3. Multi-master write support
4. Automatic recovery when connections fail
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ip_sync_manager import IPSyncManager
from ip_config import IPSyncConfig


class MockDB(dict):
    """Mock database for demonstration"""
    def __init__(self, name=""):
        super().__init__()
        self.name = name


async def run_example_basic():
    """Example 1: Basic 2-node synchronization"""
    print("\n" + "="*70)
    print("Example 1: Basic 2-Node IP Synchronization")
    print("="*70)
    
    # Node 1 - Server on port 8765
    config1 = IPSyncConfig(
        host="0.0.0.0",
        port=8765,
        node_id="node1",
        sync_interval=1.0
    )
    db1 = MockDB("node1")
    manager1 = IPSyncManager(db1, config1)
    
    # Node 2 - Server on port 8766, connects to node1
    config2 = IPSyncConfig(
        host="0.0.0.0",
        port=8766,
        node_id="node2",
        peer_addresses=["ws://localhost:8765"],
        sync_interval=1.0
    )
    db2 = MockDB("node2")
    manager2 = IPSyncManager(db2, config2)
    
    # Start both nodes
    print("\nStarting nodes...")
    await manager1.start(enable_server=True, connect_to_peers=False)
    await manager2.start(enable_server=True, connect_to_peers=True)
    
    # Wait for connection
    await asyncio.sleep(0.5)
    
    # Make changes on node1
    print("\nAdding data to Node1:")
    db1["user:alice"] = "Alice Smith"
    db1["user:bob"] = "Bob Jones"
    manager1.track_change("user:alice", "Alice Smith")
    manager1.track_change("user:bob", "Bob Jones")
    print("  user:alice = 'Alice Smith'")
    print("  user:bob = 'Bob Jones'")
    
    # Wait for sync
    print("\nWaiting for synchronization (2 seconds)...")
    await asyncio.sleep(2)
    
    # Check on node2
    print("\nData on Node2:")
    print(f"  user:alice = {db2.get('user:alice')}")
    print(f"  user:bob = {db2.get('user:bob')}")
    
    # Show stats
    stats1 = manager1.get_stats()
    stats2 = manager2.get_stats()
    print(f"\nNode1 connections: {stats1['server']['active_connections'] if stats1['server'] else 0}")
    print(f"Node2 connections: {len(stats2['clients'])}")
    
    # Cleanup
    print("\nCleaning up...")
    await manager1.stop()
    await manager2.stop()
    
    print("✓ Example 1 complete\n")


async def run_example_multi_master():
    """Example 2: Multi-master with 3 nodes"""
    print("\n" + "="*70)
    print("Example 2: Multi-Master 3-Node Configuration")
    print("="*70)
    
    # Create 3 nodes
    nodes = []
    managers = []
    
    # Node 1
    config1 = IPSyncConfig(
        host="0.0.0.0",
        port=8770,
        node_id="node1",
        peer_addresses=["ws://localhost:8771", "ws://localhost:8772"],
        sync_interval=1.0
    )
    db1 = MockDB("node1")
    mgr1 = IPSyncManager(db1, config1)
    nodes.append(db1)
    managers.append(mgr1)
    
    # Node 2
    config2 = IPSyncConfig(
        host="0.0.0.0",
        port=8771,
        node_id="node2",
        peer_addresses=["ws://localhost:8770", "ws://localhost:8772"],
        sync_interval=1.0
    )
    db2 = MockDB("node2")
    mgr2 = IPSyncManager(db2, config2)
    nodes.append(db2)
    managers.append(mgr2)
    
    # Node 3
    config3 = IPSyncConfig(
        host="0.0.0.0",
        port=8772,
        node_id="node3",
        peer_addresses=["ws://localhost:8770", "ws://localhost:8771"],
        sync_interval=1.0
    )
    db3 = MockDB("node3")
    mgr3 = IPSyncManager(db3, config3)
    nodes.append(db3)
    managers.append(mgr3)
    
    # Start all nodes
    print("\nStarting 3 nodes...")
    await mgr1.start(enable_server=True, connect_to_peers=False)
    await asyncio.sleep(0.2)
    await mgr2.start(enable_server=True, connect_to_peers=True)
    await asyncio.sleep(0.2)
    await mgr3.start(enable_server=True, connect_to_peers=True)
    
    # Wait for connections
    await asyncio.sleep(0.5)
    
    # Each node writes different data
    print("\nEach node writes data:")
    db1["data1"] = "From Node 1"
    mgr1.track_change("data1", "From Node 1")
    print("  Node1: data1 = 'From Node 1'")
    
    db2["data2"] = "From Node 2"
    mgr2.track_change("data2", "From Node 2")
    print("  Node2: data2 = 'From Node 2'")
    
    db3["data3"] = "From Node 3"
    mgr3.track_change("data3", "From Node 3")
    print("  Node3: data3 = 'From Node 3'")
    
    # Wait for sync
    print("\nWaiting for synchronization (3 seconds)...")
    await asyncio.sleep(3)
    
    # Check all nodes have all data
    print("\nData on each node:")
    for i, db in enumerate(nodes, 1):
        print(f"\nNode{i}:")
        for key in ["data1", "data2", "data3"]:
            print(f"  {key} = {db.get(key)}")
    
    # Cleanup
    print("\nCleaning up...")
    for mgr in managers:
        await mgr.stop()
    
    print("✓ Example 2 complete\n")


async def run_example_auto_recovery():
    """Example 3: Automatic recovery demonstration"""
    print("\n" + "="*70)
    print("Example 3: Automatic Recovery")
    print("="*70)
    
    # Node 1 - Server
    config1 = IPSyncConfig(
        host="0.0.0.0",
        port=8775,
        node_id="server_node",
        enable_auto_recovery=True
    )
    db1 = MockDB("server")
    manager1 = IPSyncManager(db1, config1)
    
    # Node 2 - Client with auto-recovery
    config2 = IPSyncConfig(
        host="0.0.0.0",
        port=8776,
        node_id="client_node",
        peer_addresses=["ws://localhost:8775"],
        enable_auto_recovery=True,
        recovery_check_interval=2.0,
        max_recovery_retries=3
    )
    db2 = MockDB("client")
    manager2 = IPSyncManager(db2, config2)
    
    # Start server
    print("\nStarting server node...")
    await manager1.start(enable_server=True, connect_to_peers=False)
    
    # Start client
    print("Starting client node with auto-recovery...")
    await manager2.start(enable_server=False, connect_to_peers=True)
    
    # Wait for connection
    await asyncio.sleep(0.5)
    
    # Add data
    print("\nAdding initial data:")
    db1["initial_data"] = "Initial value"
    manager1.track_change("initial_data", "Initial value")
    await asyncio.sleep(1)
    print(f"  Client has: {db2.get('initial_data')}")
    
    # Simulate connection loss by stopping client
    print("\nSimulating connection loss (stopping client)...")
    await manager2.stop()
    
    # Add more data while client is down
    print("Adding data while client is down:")
    db1["missed_data"] = "This was added while offline"
    manager1.track_change("missed_data", "This was added while offline")
    print("  missed_data = 'This was added while offline'")
    
    # Restart client (with auto-recovery)
    print("\nRestarting client with auto-recovery...")
    await manager2.start(enable_server=False, connect_to_peers=True)
    
    # Wait for recovery
    print("Waiting for auto-recovery (3 seconds)...")
    await asyncio.sleep(3)
    
    # Check if client recovered missing data
    print("\nAfter auto-recovery:")
    print(f"  Client has initial_data: {db2.get('initial_data')}")
    print(f"  Client has missed_data: {db2.get('missed_data')}")
    
    # Show recovery stats
    recovery_stats = manager2.get_stats()['auto_recovery']
    print(f"\nRecovery attempts: {recovery_stats['recovery_attempts']}")
    print(f"Total recoveries: {recovery_stats['total_recoveries']}")
    
    # Cleanup
    print("\nCleaning up...")
    await manager1.stop()
    await manager2.stop()
    
    print("✓ Example 3 complete\n")


async def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("IP-Based Auto-Sync System - Examples")
    print("="*70)
    
    try:
        await run_example_basic()
        await run_example_multi_master()
        await run_example_auto_recovery()
        
        print("\n" + "="*70)
        print("All examples completed successfully!")
        print("="*70 + "\n")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\n\nError occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

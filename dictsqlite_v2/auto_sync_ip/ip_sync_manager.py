"""
IP-based synchronization manager.

Coordinates between server and multiple clients for multi-master replication.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

# Support both relative and absolute imports
try:
    from .sync_server import SyncServer
    from .sync_client import SyncClient
    from .recovery import AutoRecovery
except ImportError:
    from sync_server import SyncServer
    from sync_client import SyncClient
    from recovery import AutoRecovery


logger = logging.getLogger(__name__)


class IPSyncManager:
    """
    Manages IP-based synchronization with multiple peers.
    
    Can act as both server and client simultaneously, enabling
    full mesh multi-master replication across different IP addresses.
    """
    
    def __init__(self, db_instance: Any, config):
        """
        Initialize IP sync manager.
        
        Args:
            db_instance: Local database instance
            config: IPSyncConfig instance
        """
        self.db = db_instance
        self.config = config
        config.validate()
        
        # Server (for accepting connections)
        self.server: Optional[SyncServer] = None
        
        # Clients (for connecting to peers)
        self.clients: Dict[str, SyncClient] = {}
        
        # Auto-recovery
        self.auto_recovery = AutoRecovery(config)
        
        # Sync tasks
        self.sync_task: Optional[asyncio.Task] = None
        self.running = False
        
        logger.info("IPSyncManager initialized")
    
    async def start_server(self):
        """Start sync server"""
        if self.server:
            logger.warning("Server already started")
            return
        
        self.server = SyncServer(self.db, self.config)
        await self.server.start()
        logger.info(f"Server started on {self.config.host}:{self.config.port}")
    
    async def stop_server(self):
        """Stop sync server"""
        if self.server:
            await self.server.stop()
            self.server = None
            logger.info("Server stopped")
    
    async def connect_to_peer(self, peer_url: str):
        """
        Connect to a peer node.
        
        Args:
            peer_url: WebSocket URL of peer (ws://host:port)
        """
        if peer_url in self.clients:
            logger.warning(f"Already connected to {peer_url}")
            return
        
        client = SyncClient(self.db, self.config, peer_url)
        
        # Set up callbacks
        client.on_connected = lambda node_id: logger.info(f"Connected to {node_id}")
        client.on_disconnected = lambda node_id: logger.info(f"Disconnected from {node_id}")
        
        # Connect
        success = await client.connect()
        
        if success:
            self.clients[peer_url] = client
            
            # Start receive loop
            asyncio.create_task(client.receive_loop())
            
            logger.info(f"Connected to peer {peer_url}")
        else:
            logger.error(f"Failed to connect to {peer_url}")
    
    async def disconnect_from_peer(self, peer_url: str):
        """Disconnect from a peer node"""
        if peer_url in self.clients:
            client = self.clients[peer_url]
            await client.disconnect()
            del self.clients[peer_url]
            logger.info(f"Disconnected from {peer_url}")
    
    async def start(self, enable_server: bool = True, connect_to_peers: bool = True):
        """
        Start synchronization.
        
        Args:
            enable_server: Start server to accept connections
            connect_to_peers: Connect to configured peer addresses
        """
        self.running = True
        
        # Start server
        if enable_server:
            await self.start_server()
        
        # Connect to peers
        if connect_to_peers:
            for peer_addr in self.config.peer_addresses:
                await self.connect_to_peer(peer_addr)
        
        # Start auto-recovery
        if self.config.enable_auto_recovery:
            await self.auto_recovery.start(self)
        
        # Start sync loop
        self.sync_task = asyncio.create_task(self._sync_loop())
        
        logger.info("IPSyncManager started")
    
    async def stop(self):
        """Stop synchronization"""
        self.running = False
        
        # Stop sync task
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        
        # Stop auto-recovery
        await self.auto_recovery.stop()
        
        # Disconnect from all peers
        for peer_url in list(self.clients.keys()):
            await self.disconnect_from_peer(peer_url)
        
        # Stop server
        await self.stop_server()
        
        logger.info("IPSyncManager stopped")
    
    async def _sync_loop(self):
        """Main synchronization loop"""
        while self.running:
            try:
                await asyncio.sleep(self.config.sync_interval)
                await self.sync_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
    
    async def sync_all(self):
        """Synchronize with all connected peers"""
        sync_tasks = []
        
        # Sync each client
        for client in self.clients.values():
            if client.connected:
                sync_tasks.append(client.sync_changes())
        
        if sync_tasks:
            await asyncio.gather(*sync_tasks, return_exceptions=True)
    
    def track_change(self, key: str, value: Any, operation: str = 'set'):
        """
        Track a local database change.
        
        Args:
            key: Database key
            value: New value (None for delete)
            operation: 'set' or 'delete'
        """
        # Track in server
        if self.server:
            self.server.track_change(key, value, operation)
        
        # Track in all clients
        for client in self.clients.values():
            client.track_change(key, value, operation)
    
    async def broadcast_change(self, key: str, value: Any, operation: str = 'set'):
        """
        Track and immediately broadcast a change.
        
        Args:
            key: Database key
            value: New value
            operation: 'set' or 'delete'
        """
        # Track change
        self.track_change(key, value, operation)
        
        # Broadcast from server
        if self.server:
            changes = {key: {
                'value': value,
                'timestamp': self.server.change_log[key]['timestamp'],
                'operation': operation,
                'source_node': self.server.node_id
            }}
            await self.server.broadcast_changes(changes)
        
        # Sync from all clients
        await self.sync_all()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics"""
        stats = {
            'running': self.running,
            'server': None,
            'clients': {},
            'auto_recovery': self.auto_recovery.get_stats()
        }
        
        if self.server:
            stats['server'] = self.server.get_stats()
        
        for url, client in self.clients.items():
            stats['clients'][url] = client.get_stats()
        
        return stats

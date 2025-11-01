"""
WebSocket client for IP-based synchronization.
"""

import asyncio
import logging
import msgpack
import time
import uuid
from typing import Dict, Any, Optional, Callable
import websockets
from websockets.client import WebSocketClientProtocol


logger = logging.getLogger(__name__)


class SyncClient:
    """
    WebSocket client for connecting to remote sync servers.
    
    Manages connection to a remote node, sends local changes,
    and receives updates from the remote node.
    """
    
    def __init__(self, db_instance: Any, config, server_url: str):
        """
        Initialize sync client.
        
        Args:
            db_instance: Local database instance
            config: IPSyncConfig instance
            server_url: WebSocket URL of remote server (ws://host:port)
        """
        self.db = db_instance
        self.config = config
        self.server_url = server_url
        self.node_id = config.node_id or self._generate_node_id()
        
        # Connection state
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.connected = False
        self.remote_node_id: Optional[str] = None
        
        # Change tracking
        self.change_log: Dict[str, Dict[str, Any]] = {}
        self.last_sync_time = 0.0
        
        # Callbacks
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_changes_received: Optional[Callable] = None
        
        logger.info(f"SyncClient initialized for node {self.node_id}")
    
    def _generate_node_id(self) -> str:
        """Generate unique node ID"""
        return f"node_{uuid.uuid4().hex[:8]}"
    
    async def connect(self):
        """Connect to remote server"""
        try:
            self.websocket = await websockets.connect(
                self.server_url,
                max_size=self.config.max_message_size,
                ping_interval=self.config.heartbeat_interval
            )
            
            # Wait for handshake
            message = await self.websocket.recv()
            data = self._decode_message(message)
            
            if data.get('type') == 'handshake':
                self.remote_node_id = data.get('node_id')
                self.connected = True
                logger.info(f"Connected to remote node {self.remote_node_id}")
                
                # Send our handshake
                await self.send_message({
                    'type': 'handshake',
                    'node_id': self.node_id,
                    'timestamp': time.time()
                })
                
                if self.on_connected:
                    self.on_connected(self.remote_node_id)
            
            return True
        
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.connected = False
        
        if self.on_disconnected:
            self.on_disconnected(self.remote_node_id)
        
        logger.info(f"Disconnected from {self.remote_node_id}")
    
    async def receive_loop(self):
        """Main loop for receiving messages"""
        try:
            async for message in self.websocket:
                try:
                    data = self._decode_message(message)
                    await self.process_message(data)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by server")
            self.connected = False
    
    async def process_message(self, data: Dict[str, Any]):
        """Process incoming message"""
        msg_type = data.get('type')
        
        if msg_type == 'changes':
            await self.handle_changes(data)
        
        elif msg_type == 'sync_ack':
            logger.debug(f"Sync acknowledged: {data.get('applied')} applied, {data.get('conflicts')} conflicts")
        
        elif msg_type == 'heartbeat_ack':
            # Heartbeat acknowledged
            pass
        
        elif msg_type == 'error':
            logger.error(f"Server error: {data.get('error')}")
        
        else:
            logger.warning(f"Unknown message type: {msg_type}")
    
    async def handle_changes(self, data: Dict[str, Any]):
        """
        Apply changes from remote node.
        
        Uses timestamp-based conflict resolution (last-write-wins):
        - Each operation (set/delete) has its own timestamp
        - Only operations with newer timestamps are applied
        - This correctly handles delete-then-add scenarios:
          * T1: key exists
          * T2: key deleted (newer timestamp)
          * T3: key re-added (newest timestamp)
          * Result: key exists with T3 value
        """
        changes = data.get('changes', {})
        source_node = data.get('node_id')
        
        applied_count = 0
        
        for key, change in changes.items():
            try:
                value = change.get('value')
                timestamp = change.get('timestamp')
                operation = change.get('operation', 'set')
                
                # Check for conflicts using timestamp-based resolution (last-write-wins)
                if key in self.change_log:
                    local_ts = self.change_log[key].get('timestamp', 0)
                    if timestamp <= local_ts:
                        continue  # Skip older changes
                
                # Apply change
                if operation == 'delete' or value is None:
                    if key in self.db:
                        del self.db[key]
                else:
                    self.db[key] = value
                
                # Track change with timestamp
                # This allows proper ordering even for delete->add sequences
                self.change_log[key] = {
                    'value': value,
                    'timestamp': timestamp,
                    'operation': operation,
                    'source_node': source_node
                }
                
                applied_count += 1
            
            except Exception as e:
                logger.error(f"Error applying change for key {key}: {e}")
        
        if self.on_changes_received and applied_count > 0:
            self.on_changes_received(applied_count)
        
        logger.debug(f"Applied {applied_count} changes from {source_node}")
    
    async def sync_changes(self):
        """Send local changes to server"""
        if not self.connected:
            return
        
        # Get unsynced changes
        unsynced = {
            key: change
            for key, change in self.change_log.items()
            if change.get('timestamp', 0) > self.last_sync_time
        }
        
        if not unsynced:
            return
        
        # Send changes in batches
        batch_size = self.config.batch_size
        change_items = list(unsynced.items())
        
        for i in range(0, len(change_items), batch_size):
            batch = dict(change_items[i:i + batch_size])
            
            await self.send_message({
                'type': 'changes',
                'node_id': self.node_id,
                'changes': batch,
                'timestamp': time.time()
            })
        
        self.last_sync_time = time.time()
        logger.debug(f"Synced {len(unsynced)} changes to server")
    
    async def request_sync(self, since: float = 0.0):
        """Request sync from server"""
        if not self.connected:
            return
        
        await self.send_message({
            'type': 'sync_request',
            'node_id': self.node_id,
            'since': since,
            'timestamp': time.time()
        })
    
    async def request_missing_data(self):
        """Request all data from server for recovery"""
        if not self.connected:
            return
        
        logger.info("Requesting missing data for recovery")
        
        await self.send_message({
            'type': 'get_missing',
            'node_id': self.node_id,
            'timestamp': time.time()
        })
    
    async def send_heartbeat(self):
        """Send heartbeat to server"""
        if not self.connected:
            return
        
        await self.send_message({
            'type': 'heartbeat',
            'node_id': self.node_id,
            'timestamp': time.time()
        })
    
    async def send_message(self, data: Dict[str, Any]):
        """Send message to server"""
        if not self.websocket:
            return
        
        try:
            message = self._encode_message(data)
            await self.websocket.send(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    def track_change(self, key: str, value: Any, operation: str = 'set'):
        """Track a local change"""
        self.change_log[key] = {
            'value': value,
            'timestamp': time.time(),
            'operation': operation,
            'source_node': self.node_id
        }
    
    def _encode_message(self, data: Dict[str, Any]) -> bytes:
        """Encode message using msgpack"""
        if self.config.use_msgpack:
            return msgpack.packb(data, use_bin_type=True)
        else:
            import json
            return json.dumps(data).encode('utf-8')
    
    def _decode_message(self, message: bytes) -> Dict[str, Any]:
        """Decode message from msgpack"""
        if self.config.use_msgpack:
            return msgpack.unpackb(message, raw=False)
        else:
            import json
            return json.loads(message.decode('utf-8'))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            'node_id': self.node_id,
            'connected': self.connected,
            'remote_node_id': self.remote_node_id,
            'total_changes': len(self.change_log),
            'last_sync_time': self.last_sync_time
        }

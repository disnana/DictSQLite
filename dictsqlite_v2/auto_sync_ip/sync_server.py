"""
WebSocket server for IP-based synchronization.
"""

import asyncio
import logging
import msgpack
import time
import uuid
from typing import Dict, Set, Any, Optional
import websockets
from websockets.server import WebSocketServerProtocol


logger = logging.getLogger(__name__)


class SyncServer:
    """
    WebSocket server for multi-master synchronization.
    
    Handles multiple concurrent connections from different nodes,
    manages change propagation, and coordinates conflict resolution.
    """
    
    def __init__(self, db_instance: Any, config):
        """
        Initialize sync server.
        
        Args:
            db_instance: Local database instance
            config: IPSyncConfig instance
        """
        self.db = db_instance
        self.config = config
        self.node_id = config.node_id or self._generate_node_id()
        
        # Connection management
        self.connections: Set[WebSocketServerProtocol] = set()
        self.connection_info: Dict[WebSocketServerProtocol, Dict[str, Any]] = {}
        
        # Change tracking
        self.change_log: Dict[str, Dict[str, Any]] = {}
        self.last_sync_times: Dict[str, float] = {}
        
        # Server state
        self.server = None
        self.running = False
        
        logger.info(f"SyncServer initialized for node {self.node_id}")
    
    def _generate_node_id(self) -> str:
        """Generate unique node ID"""
        return f"node_{uuid.uuid4().hex[:8]}"
    
    async def start(self):
        """Start the WebSocket server"""
        self.running = True
        self.server = await websockets.serve(
            self.handle_client,
            self.config.host,
            self.config.port,
            max_size=self.config.max_message_size
        )
        logger.info(f"Sync server started on {self.config.host}:{self.config.port}")
    
    async def stop(self):
        """Stop the WebSocket server"""
        self.running = False
        
        # Close all connections
        if self.connections:
            await asyncio.gather(
                *[conn.close() for conn in self.connections],
                return_exceptions=True
            )
        
        # Stop server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("Sync server stopped")
    
    async def handle_client(self, websocket):
        """
        Handle incoming client connection.
        
        Args:
            websocket: WebSocket connection
        """
        remote_node_id = None
        
        try:
            # Register connection
            self.connections.add(websocket)
            
            # Send handshake
            await self.send_message(websocket, {
                'type': 'handshake',
                'node_id': self.node_id,
                'timestamp': time.time()
            })
            
            # Process messages
            async for message in websocket:
                try:
                    data = self._decode_message(message)
                    await self.process_message(websocket, data)
                    
                    # Track remote node ID
                    if data.get('type') == 'handshake':
                        remote_node_id = data.get('node_id')
                        self.connection_info[websocket] = {
                            'node_id': remote_node_id,
                            'connected_at': time.time()
                        }
                        logger.info(f"Connected to node {remote_node_id}")
                
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self.send_error(websocket, str(e))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed for node {remote_node_id}")
        
        finally:
            # Cleanup connection
            self.connections.discard(websocket)
            if websocket in self.connection_info:
                del self.connection_info[websocket]
    
    async def process_message(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """
        Process incoming message.
        
        Args:
            websocket: Source websocket
            data: Message data
        """
        msg_type = data.get('type')
        
        if msg_type == 'handshake':
            # Already handled in handle_client
            pass
        
        elif msg_type == 'sync_request':
            # Send current state
            await self.handle_sync_request(websocket, data)
        
        elif msg_type == 'changes':
            # Apply remote changes
            await self.handle_changes(websocket, data)
        
        elif msg_type == 'heartbeat':
            # Respond to heartbeat
            await self.send_message(websocket, {
                'type': 'heartbeat_ack',
                'timestamp': time.time()
            })
        
        elif msg_type == 'get_missing':
            # Send missing data for recovery
            await self.handle_get_missing(websocket, data)
        
        else:
            logger.warning(f"Unknown message type: {msg_type}")
    
    async def handle_sync_request(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle sync request from peer"""
        since_timestamp = data.get('since', 0.0)
        
        # Get changes since timestamp
        changes = {
            key: change
            for key, change in self.change_log.items()
            if change.get('timestamp', 0) > since_timestamp
        }
        
        # Send changes in batches
        if changes:
            await self.send_changes(websocket, changes)
    
    async def handle_changes(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
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
        conflict_count = 0
        
        for key, change in changes.items():
            try:
                value = change.get('value')
                timestamp = change.get('timestamp')
                operation = change.get('operation', 'set')
                
                # Check for conflicts using timestamp-based resolution
                if key in self.change_log:
                    local_ts = self.change_log[key].get('timestamp', 0)
                    if timestamp <= local_ts:
                        conflict_count += 1
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
        
        # Send acknowledgment
        await self.send_message(websocket, {
            'type': 'sync_ack',
            'applied': applied_count,
            'conflicts': conflict_count,
            'timestamp': time.time()
        })
        
        logger.debug(f"Applied {applied_count} changes, {conflict_count} conflicts")
    
    async def handle_get_missing(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """
        Send all data and change history to help peer recover.
        
        This includes both existing data AND deletion operations to ensure
        the peer has the complete state, including knowing what was deleted.
        """
        changes = {}
        
        # First, send the complete change log which includes deletions
        # This ensures deletions are properly propagated
        for key, change in self.change_log.items():
            changes[key] = change
        
        # Then, add any current data that might not be in the change log
        # (e.g., data that existed before tracking started)
        try:
            current_data = {}
            if hasattr(self.db, 'items'):
                current_data = dict(self.db.items())
            elif hasattr(self.db, 'keys'):
                current_data = {key: self.db[key] for key in self.db.keys()}
            
            # Only add to changes if not already tracked
            current_time = time.time()
            for key, value in current_data.items():
                if key not in changes:
                    changes[key] = {
                        'value': value,
                        'timestamp': current_time,
                        'operation': 'set',
                        'source_node': self.node_id
                    }
        except Exception as e:
            logger.error(f"Error getting all data: {e}")
        
        # Send in batches
        if changes:
            await self.send_changes(websocket, changes)
            logger.info(f"Sent {len(changes)} changes for recovery (including deletions)")
    
    async def send_changes(self, websocket: WebSocketServerProtocol, changes: Dict[str, Any]):
        """Send changes to peer in batches"""
        batch_size = self.config.batch_size
        change_items = list(changes.items())
        
        for i in range(0, len(change_items), batch_size):
            batch = dict(change_items[i:i + batch_size])
            
            await self.send_message(websocket, {
                'type': 'changes',
                'node_id': self.node_id,
                'changes': batch,
                'timestamp': time.time()
            })
    
    async def send_message(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Send message to websocket"""
        try:
            message = self._encode_message(data)
            await websocket.send(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def send_error(self, websocket: WebSocketServerProtocol, error: str):
        """Send error message"""
        await self.send_message(websocket, {
            'type': 'error',
            'error': error,
            'timestamp': time.time()
        })
    
    async def broadcast_changes(self, changes: Dict[str, Any]):
        """Broadcast changes to all connected peers"""
        if not self.connections:
            return
        
        message_data = {
            'type': 'changes',
            'node_id': self.node_id,
            'changes': changes,
            'timestamp': time.time()
        }
        
        # Send to all connections
        await asyncio.gather(
            *[self.send_message(conn, message_data) for conn in self.connections],
            return_exceptions=True
        )
    
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
        """Get server statistics"""
        return {
            'node_id': self.node_id,
            'active_connections': len(self.connections),
            'total_changes': len(self.change_log),
            'running': self.running
        }

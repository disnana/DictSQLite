"""
Automatic recovery system for IP-based synchronization.

Handles automatic detection and recovery of missing data between nodes.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Set, Optional


logger = logging.getLogger(__name__)


class AutoRecovery:
    """
    Automatic recovery system for synchronization.
    
    Detects missing data and automatically synchronizes with peers
    to ensure consistency across all nodes.
    """
    
    def __init__(self, config):
        """
        Initialize auto-recovery.
        
        Args:
            config: IPSyncConfig instance
        """
        self.config = config
        self.running = False
        self.recovery_task: Optional[asyncio.Task] = None
        
        # Recovery state
        self.last_recovery_check = 0.0
        self.recovery_attempts: Dict[str, int] = {}
        self.recovery_history: list[Dict[str, Any]] = []
        
        logger.info("AutoRecovery initialized")
    
    async def start(self, sync_manager):
        """
        Start automatic recovery monitoring.
        
        Args:
            sync_manager: IPSyncManager instance to monitor
        """
        if self.running:
            return
        
        self.running = True
        self.recovery_task = asyncio.create_task(self._recovery_loop(sync_manager))
        logger.info("AutoRecovery started")
    
    async def stop(self):
        """Stop automatic recovery"""
        self.running = False
        
        if self.recovery_task:
            self.recovery_task.cancel()
            try:
                await self.recovery_task
            except asyncio.CancelledError:
                pass
        
        logger.info("AutoRecovery stopped")
    
    async def _recovery_loop(self, sync_manager):
        """Main recovery monitoring loop"""
        while self.running:
            try:
                await asyncio.sleep(self.config.recovery_check_interval)
                await self.check_and_recover(sync_manager)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in recovery loop: {e}")
    
    async def check_and_recover(self, sync_manager):
        """Check for missing data and trigger recovery"""
        self.last_recovery_check = time.time()
        
        # Check server connections
        if sync_manager.server and sync_manager.server.running:
            await self._check_server_health(sync_manager.server)
        
        # Check client connections
        for client in sync_manager.clients.values():
            if client.connected:
                await self._check_client_health(client)
            else:
                # Try to reconnect
                await self._attempt_reconnect(client, sync_manager)
    
    async def _check_server_health(self, server):
        """Check server health and trigger recovery if needed"""
        # Get number of connections
        if len(server.connections) == 0:
            logger.warning("No active connections to server")
    
    async def _check_client_health(self, client):
        """Check client health and request missing data if needed"""
        # Check if we need to recover missing data
        time_since_sync = time.time() - client.last_sync_time
        
        if time_since_sync > self.config.recovery_check_interval * 2:
            # Request missing data
            logger.info(f"Requesting missing data from {client.remote_node_id}")
            await client.request_missing_data()
            
            # Record recovery attempt
            self.recovery_history.append({
                'timestamp': time.time(),
                'client_node': client.remote_node_id,
                'reason': 'missing_data_timeout'
            })
    
    async def _attempt_reconnect(self, client, sync_manager):
        """Attempt to reconnect a disconnected client"""
        client_id = client.server_url
        
        # Check retry count
        if client_id not in self.recovery_attempts:
            self.recovery_attempts[client_id] = 0
        
        if self.recovery_attempts[client_id] >= self.config.max_recovery_retries:
            logger.error(f"Max reconnection attempts reached for {client_id}")
            return
        
        # Try to reconnect
        logger.info(f"Attempting to reconnect to {client_id}")
        self.recovery_attempts[client_id] += 1
        
        try:
            success = await client.connect()
            
            if success:
                # Reset retry count on success
                self.recovery_attempts[client_id] = 0
                
                # Request missing data
                await client.request_missing_data()
                
                # Start receive loop
                asyncio.create_task(client.receive_loop())
                
                logger.info(f"Reconnected to {client_id}")
                
                # Record recovery
                self.recovery_history.append({
                    'timestamp': time.time(),
                    'client_node': client_id,
                    'reason': 'reconnection',
                    'success': True
                })
        
        except Exception as e:
            logger.error(f"Reconnection failed for {client_id}: {e}")
            
            # Record failure
            self.recovery_history.append({
                'timestamp': time.time(),
                'client_node': client_id,
                'reason': 'reconnection',
                'success': False,
                'error': str(e)
            })
    
    async def trigger_full_recovery(self, sync_manager):
        """
        Trigger full data recovery from all peers.
        
        Requests all data from all connected peers to ensure
        consistency.
        """
        logger.info("Triggering full recovery")
        
        recovery_tasks = []
        
        # Request from all clients
        for client in sync_manager.clients.values():
            if client.connected:
                recovery_tasks.append(client.request_missing_data())
        
        if recovery_tasks:
            await asyncio.gather(*recovery_tasks, return_exceptions=True)
        
        # Record recovery
        self.recovery_history.append({
            'timestamp': time.time(),
            'reason': 'full_recovery',
            'peers_contacted': len(recovery_tasks)
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        return {
            'running': self.running,
            'last_check': self.last_recovery_check,
            'recovery_attempts': dict(self.recovery_attempts),
            'total_recoveries': len(self.recovery_history),
            'recent_recoveries': self.recovery_history[-10:]
        }
    
    def reset_stats(self):
        """Reset recovery statistics"""
        self.recovery_attempts.clear()
        self.recovery_history.clear()
        logger.info("Recovery stats reset")

import asyncio
import json
from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        logger.info(f""Client {client_id} connected. Total connections: {len(self.active_connections[client_id])}"")

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if len(self.active_connections[client_id]) == 0:
                del self.active_connections[client_id]
        logger.info(f""Client {client_id} disconnected. Remaining connections: {len(self.active_connections.get(client_id, [])) if client_id in self.active_connections else 0}"")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_client(self, message: str, client_id: str):
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_text(message)
                except WebSocketDisconnect:
                    # Remove disconnected connections
                    self.disconnect(connection, client_id)

    async def broadcast_to_all(self, message: str):
        for client_id in list(self.active_connections.keys()):
            await self.broadcast_to_client(message, client_id)


# Global instance
manager = ConnectionManager()

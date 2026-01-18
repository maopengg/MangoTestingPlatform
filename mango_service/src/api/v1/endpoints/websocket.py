from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.core.websocket_manager import manager
from loguru import logger
import json


router = APIRouter()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Process received message
            message_data = {
                "type": "message_received",
                "data": data,
                "timestamp": "2023-01-01T00:00:00Z"
            }
            
            # Echo the message back to the sender
            await manager.send_personal_message(json.dumps(message_data), websocket)
            
            # Log the received message
            logger.info(f""Received message from client {client_id}: {data}"")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
        logger.info(f""Client {client_id} disconnected from websocket"")
    except Exception as e:
        logger.error(f""Error in websocket connection for client {client_id}: {str(e)}"")
        manager.disconnect(websocket, client_id)


@router.websocket("/notifications/{user_id}")
async def notification_websocket(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for sending notifications to specific users
    """
    await manager.connect(websocket, f""notification_{user_id}"")
    try:
        # Send welcome message
        welcome_msg = {
            "type": "connection_established",
            "message": f""Connected to notifications for user {user_id}"",
            "timestamp": "2023-01-01T00:00:00Z"
        }
        await manager.send_personal_message(json.dumps(welcome_msg), websocket)
        
        while True:
            # Wait for messages (could be commands from client)
            data = await websocket.receive_text()
            logger.info(f""Received notification command from user {user_id}: {data}"")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, f""notification_{user_id}"")
        logger.info(f""User {user_id} disconnected from notifications"")
    except Exception as e:
        logger.error(f""Error in notification websocket for user {user_id}: {str(e)}"")
        manager.disconnect(websocket, f""notification_{user_id}"")

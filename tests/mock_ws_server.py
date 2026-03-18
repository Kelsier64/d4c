import asyncio
import websockets
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("mock_ws_server")

# In testing, replace this with the actual channel ID your bot is listening to, 
# or grab it from the incoming message if your client sends an init payload.
DUMMY_CHANNEL_ID = 123456789

async def handler(websocket):
    logger.info(f"Client connected: {websocket.remote_address}")
    
    try:
        # Wait a few seconds to let client settle
        await asyncio.sleep(2.0)
        
        logger.info("Sending tool_start (bash)...")
        await websocket.send(json.dumps({
            "type": "tool_start", 
            "tool": "bash", 
            "channel_id": DUMMY_CHANNEL_ID
        }))
        
        await asyncio.sleep(1.0)
        
        logger.info("Sending tool_end (bash)...")
        await websocket.send(json.dumps({
            "type": "tool_end", 
            "tool": "bash", 
            "channel_id": DUMMY_CHANNEL_ID, 
            "status": "success"
        }))

        await asyncio.sleep(1.0)

        logger.info("Sending tool_start (read)...")
        await websocket.send(json.dumps({
            "type": "tool_start", 
            "tool": "read", 
            "channel_id": DUMMY_CHANNEL_ID
        }))
        
        await asyncio.sleep(1.0)
        
        logger.info("Sending tool_end (read)...")
        await websocket.send(json.dumps({
            "type": "tool_end", 
            "tool": "read", 
            "channel_id": DUMMY_CHANNEL_ID, 
            "status": "success"
        }))

        await asyncio.sleep(2.0)

        logger.info("Sending question...")
        await websocket.send(json.dumps({
            "type": "question", 
            "question_id": "test_q", 
            "channel_id": DUMMY_CHANNEL_ID, 
            "question": "Which framework?", 
            "options": [
                {"label": "A", "value": "a"},
                {"label": "B", "value": "b"}
            ]
        }))

        # Keep the connection open and listen to the client's replies (e.g., question answers)
        async for message in websocket:
            logger.info(f"Received from client: {message}")
            
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client disconnected: {websocket.remote_address}")

async def main():
    host = "localhost"
    port = 8765
    logger.info(f"Starting mock WebSocket server on ws://{host}:{port}")
    
    # Start the server
    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped.")
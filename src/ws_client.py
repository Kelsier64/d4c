import asyncio
import websockets
import json
import logging

logger = logging.getLogger(__name__)

class OpenCodeWSClient:
    """
    WebSocket client to connect to OpenCode and handle real-time UI updates.
    """
    def __init__(self, uri: str):
        self.uri = uri
        self.connection = None
        self._connected = asyncio.Event()

    async def connect(self):
        """
        Connect to the WebSocket server and start listening for messages.
        """
        while True:
            try:
                logger.info(f"Attempting to connect to {self.uri}...")
                async with websockets.connect(self.uri) as websocket:
                    self.connection = websocket
                    self._connected.set()
                    logger.info(f"Connected to {self.uri}")
                    await self.listen()
            except websockets.ConnectionClosed as e:
                logger.warning(f"Connection closed: {e}. Reconnecting in 5 seconds...")
            except Exception as e:
                logger.error(f"WebSocket error: {e}. Reconnecting in 5 seconds...")
            finally:
                self.connection = None
                self._connected.clear()
                await asyncio.sleep(5)

    async def listen(self):
        """
        Listen for incoming messages from the WebSocket server.
        """
        if not self.connection:
            return

        async for message in self.connection:
            try:
                data = json.loads(message)
                await self.on_message(data)
            except json.JSONDecodeError:
                logger.error(f"Received invalid JSON message: {message}")
            except Exception as e:
                logger.error(f"Error handling message: {e}")

    async def on_message(self, data: dict):
        """
        Hook to handle incoming messages. Should be overridden or replaced.
        """
        logger.debug(f"Received message: {data}")
        # Implement routing logic based on message type here
        pass

    async def send_message(self, data: dict):
        """
        Send a JSON message to the WebSocket server.
        """
        await self._connected.wait()
        if self.connection:
            try:
                message = json.dumps(data)
                await self.connection.send(message)
                logger.debug(f"Sent message: {message}")
            except Exception as e:
                logger.error(f"Failed to send message: {e}")

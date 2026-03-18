import asyncio
import websockets
import json
import logging
import discord
from src.ui.progress_embed import ProgressEmbedManager
from src.utils.debouncer import AsyncDebouncer

logger = logging.getLogger(__name__)

class ChannelProgressState:
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.manager = ProgressEmbedManager()
        self.message: discord.Message | None = None
        # Each channel gets its own debouncer
        self.debouncer = AsyncDebouncer(delay=3.0)

    async def _edit_message_with_retry(self, embed: discord.Embed):
        retries = 3
        backoff = 1.0
        for attempt in range(retries):
            try:
                if self.message is None:
                    self.message = await self.channel.send(embed=embed)
                else:
                    await self.message.edit(embed=embed)
                return
            except discord.HTTPException as e:
                if e.status == 429:
                    # Rate limited
                    logger.warning(f"Rate limited updating embed, backing off for {backoff}s")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error(f"Failed to update progress embed: {e}")
                    raise e
            except Exception as e:
                logger.error(f"Unexpected error updating progress embed: {e}")
                return

    async def update_and_render(self, task_id: str, tool: str, status: str, details: str = ""):
        self.manager.update_task(task_id, tool, status, details)
        
        @self.debouncer
        async def render():
            embed = self.manager.build_embed()
            await self._edit_message_with_retry(embed)
            
        await render()

class OpenCodeWSClient:
    """
    WebSocket client to connect to OpenCode and handle real-time UI updates.
    """
    def __init__(self, uri: str, bot: discord.Client | None = None):
        self.uri = uri
        self.bot = bot
        self.connection = None
        self._connected = asyncio.Event()
        self.channel_states: dict[int, ChannelProgressState] = {}

    def get_channel_state(self, channel_id: int) -> ChannelProgressState | None:
        if channel_id not in self.channel_states:
            if self.bot:
                channel = self.bot.get_channel(channel_id)
                if isinstance(channel, discord.TextChannel):
                    self.channel_states[channel_id] = ChannelProgressState(channel)
        return self.channel_states.get(channel_id)

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
        Hook to handle incoming messages.
        Mock format handled: {"type": "tool_start", "tool": "bash", "channel_id": 123, "task_id": "abc"}
        """
        logger.debug(f"Received message: {data}")
        msg_type = data.get("type")
        channel_id = data.get("channel_id")
        
        if channel_id and msg_type in ["tool_start", "tool_end", "tool_error"]:
            state = self.get_channel_state(int(channel_id))
            if state:
                task_id = data.get("task_id", "unknown_task")
                tool = data.get("tool", "unknown_tool")
                details = data.get("details", "")
                
                status = "running"
                if msg_type == "tool_end":
                    status = "done"
                elif msg_type == "tool_error":
                    status = "error"
                
                await state.update_and_render(task_id, tool, status, details)

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

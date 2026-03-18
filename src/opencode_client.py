import asyncio
import json
import logging
import discord
import aiohttp
from src.ui.progress_embed import ProgressEmbedManager
from src.ui.question_view import OpenCodeView
from src.utils.debouncer import AsyncDebouncer

logger = logging.getLogger(__name__)

class ChannelProgressState:
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.manager = ProgressEmbedManager()
        self.message: discord.Message | None = None
        # Each channel gets its own debouncer
        self.debouncer = AsyncDebouncer(delay=3.0)
        self._debounced_render = self.debouncer(self._render)

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
                    sleep_time = getattr(e, 'retry_after', backoff)
                    logger.warning(f"Rate limited updating embed, backing off for {sleep_time}s")
                    await asyncio.sleep(sleep_time)
                    backoff *= 2
                else:
                    logger.error(f"Failed to update progress embed: {e}")
                    raise e
            except Exception as e:
                logger.error(f"Unexpected error updating progress embed: {e}")
                return
                
        logger.error("Failed to update progress embed after all retries.")

    async def _render(self):
        embed = self.manager.build_embed()
        await self._edit_message_with_retry(embed)

    async def update_and_render(self, task_id: str, tool: str, status: str, details: str = ""):
        self.manager.update_task(task_id, tool, status, details)
        await self._debounced_render()

class OpenCodeClient:
    """
    HTTP/SSE client to connect to OpenCode and handle real-time UI updates.
    """
    def __init__(self, base_url: str, bot: discord.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None
        self.channel_states: dict[int, ChannelProgressState] = {}
        self.session_to_channel: dict[str, int] = {}
        self._sse_task: asyncio.Task | None = None

    def get_channel_state(self, channel_id: int) -> ChannelProgressState | None:
        if channel_id not in self.channel_states:
            if self.bot:
                channel = self.bot.get_channel(channel_id)
                if isinstance(channel, discord.TextChannel):
                    self.channel_states[channel_id] = ChannelProgressState(channel)
        return self.channel_states.get(channel_id)

    async def connect(self):
        """
        Initialize the HTTP session.
        """
        self.session = aiohttp.ClientSession()
        logger.info("Initialized aiohttp ClientSession for OpenCodeClient.")
        self._sse_task = asyncio.create_task(self._listen_sse())

    async def close(self):
        """
        Close the HTTP session.
        """
        if self.session:
            await self.session.close()

    async def create_session(self) -> str:
        """
        Create a new OpenCode session via REST.
        Returns the session ID.
        """
        if not self.session:
            raise RuntimeError("ClientSession not initialized. Call connect() first.")
            
        url = f"{self.base_url}/session"
        async with self.session.post(url) as response:
            response.raise_for_status()
            data = await response.json()
            return data["id"]

    async def send_message(self, session_id: str, content: str):
        """
        Send a message to a specific OpenCode session.
        """
        if not self.session:
            raise RuntimeError("ClientSession not initialized. Call connect() first.")
            
        url = f"{self.base_url}/session/{session_id}/message"
        payload = {
            "parts": [{"text": content}]
        }
        async with self.session.post(url, json=payload) as response:
            response.raise_for_status()
            return await response.json()

    async def on_message(self, data: dict):
        """
        Hook to handle incoming messages (for SSE or other usage).
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
        elif channel_id and msg_type == "question":
            state = self.get_channel_state(int(channel_id))
            if state:
                question_text = data.get("question", "Please select an option:")
                options = data.get("options", [])
                multiple = data.get("multiple", False)
                question_id = data.get("question_id")
                
                async def on_answer(answers: list[str]):
                    # Temporary mock implementation or replace with new API endpoint if needed
                    logger.info(f"Answered question {question_id} with {answers}")
                    
                view = OpenCodeView(options_data=options, multiple=multiple, on_answer=on_answer)
                await state.channel.send(content=f"🤖 **[OpenCode]**\n{question_text}", view=view)

    async def _listen_sse(self):
        """
        Background task to consume the global SSE event stream.
        """
        if not self.session:
            return

        url = f"{self.base_url}/global/event"
        try:
            async with self.session.get(url) as response:
                logger.info(f"Connected to OpenCode SSE stream at {url}")
                async for line in response.content:
                    line = line.strip()
                    if line.startswith(b"data: "):
                        data_str = line[6:].decode("utf-8").strip()
                        if not data_str:
                            continue
                        try:
                            payload = json.loads(data_str)
                            if payload.get("type") == "message.part.updated":
                                props = payload.get("properties", {})
                                part = props.get("part", {})
                                session_id = part.get("sessionID")

                                if not session_id:
                                    continue
                                
                                channel_id = self.session_to_channel.get(session_id)
                                if not channel_id:
                                    continue

                                state = self.get_channel_state(channel_id)
                                if not state:
                                    continue

                                ptype = part.get("type")
                                tool_name = part.get("tool")
                                
                                if ptype == "tool" and "state" in part:
                                    status = part["state"].get("status", "running")
                                    # Use tool name or part ID as task_id
                                    task_id = part.get("id", tool_name)
                                    await state.update_and_render(task_id, tool_name, status, "")
                                elif ptype == "question" or tool_name == "question":
                                    # Handle routing the question to the UI
                                    question_text = part.get("question", "Question from OpenCode")
                                    options = part.get("options", [])
                                    multiple = part.get("multiple", False)
                                    question_id = part.get("id", "q")

                                    async def on_answer(answers: list[str]):
                                        logger.info(f"Answered SSE question {question_id} with {answers}")

                                    view = OpenCodeView(options_data=options, multiple=multiple, on_answer=on_answer)
                                    await state.channel.send(content=f"🤖 **[OpenCode]**\n{question_text}", view=view)

                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse SSE JSON: {data_str}")
                        except Exception as e:
                            logger.error(f"Error processing SSE event: {e}")
        except asyncio.CancelledError:
            logger.info("SSE listener task cancelled.")
        except Exception as e:
            logger.error(f"SSE listener failed: {e}")
            # Could add reconnect logic here, but for now just log it

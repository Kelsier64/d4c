import discord
from discord import app_commands
from discord.ext import commands
import uuid
import asyncio
import logging
import os
import json

logger = logging.getLogger(__name__)

class SessionManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Dictionary tracking state per guild
        # Format: {guild_id: {'mode': 'NORMAL', 'active_sessions': {channel_id: {"agent": "default", ...}}}}
        self.guild_states: dict[int, dict] = {}
        # Persistent state file
        self.state_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "state.json")
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for guild_id_str, guild_data in data.items():
                        guild_id = int(guild_id_str)
                        self.guild_states[guild_id] = {
                            'mode': guild_data.get('mode', 'NORMAL'),
                            'pending_agent': guild_data.get('pending_agent', 'default'),
                            'active_sessions': {}
                        }
                        for channel_id_str, session_data in guild_data.get('active_sessions', {}).items():
                            channel_id = int(channel_id_str)
                            self.guild_states[guild_id]['active_sessions'][channel_id] = session_data
                            session_id = session_data.get("opencode_session_id")
                            if session_id and hasattr(self.bot, 'opencode_client'):
                                self.bot.opencode_client.register_session(session_id, channel_id)
                logger.info("Session state loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    def _save_state(self):
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.guild_states, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def get_guild_state(self, guild_id: int | None) -> dict:
        if not guild_id:
            guild_id = 0
        if guild_id not in self.guild_states:
            self.guild_states[guild_id] = {'mode': 'NORMAL', 'active_sessions': {}, 'pending_agent': 'default'}
        return self.guild_states[guild_id]

    @app_commands.command(name="mode", description="Set global operating mode (NORMAL/FULL_CONTROL)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(mode="Operating mode to set")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Normal Mode", value="NORMAL"),
        app_commands.Choice(name="Full Control Mode", value="FULL_CONTROL"),
    ])
    async def set_mode(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        state = self.get_guild_state(interaction.guild_id)
        state['mode'] = mode.value
        self._save_state()
        await interaction.response.send_message(f"✅ Global mode changed to: **{state['mode']}**")

    @app_commands.command(name="new", description="Register the current channel as an active session")
    async def new_session(self, interaction: discord.Interaction):
        state = self.get_guild_state(interaction.guild_id)
        if state['mode'] != 'NORMAL':
            await interaction.response.send_message("⚠️ `/new` is only available in NORMAL mode.", ephemeral=True)
            return

        channel_id = interaction.channel_id
        if not channel_id:
            await interaction.response.send_message("⚠️ Could not determine channel.", ephemeral=True)
            return

        if channel_id in state['active_sessions']:
            await interaction.response.send_message("⚠️ This channel is already an active session.", ephemeral=True)
            return

        try:
            session_id, directory = await self.bot.opencode_client.create_session()
            self.bot.opencode_client.register_session(session_id, channel_id)
            state['active_sessions'][channel_id] = {"agent": "default", "opencode_session_id": session_id}
            self._save_state()
            
            project_name = os.path.basename(directory.rstrip('/')) if directory else "OpenCode"
            guild = interaction.guild
            if guild:
                category = discord.utils.get(guild.categories, name=project_name)
                if not category:
                    category = await guild.create_category(project_name)
                
                # Try to move the channel to the category
                try:
                    if isinstance(interaction.channel, discord.TextChannel):
                        await interaction.channel.edit(category=category)
                except discord.Forbidden:
                    pass

            await interaction.response.send_message(f"✅ Channel registered as a new session under project **{project_name}**.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to create OpenCode session: {e}", ephemeral=True)

    @app_commands.command(name="exit", description="End the current session")
    async def exit_session(self, interaction: discord.Interaction):
        state = self.get_guild_state(interaction.guild_id)
        channel_id = interaction.channel_id
        if not channel_id:
            await interaction.response.send_message("⚠️ Could not determine channel.", ephemeral=True)
            return

        if channel_id not in state['active_sessions']:
            await interaction.response.send_message("⚠️ This channel is not an active session.", ephemeral=True)
            return

        # Try to delete session from OpenCode
        session_id = state['active_sessions'][channel_id].get("opencode_session_id")
        if session_id:
            try:
                await self.bot.opencode_client.delete_session(session_id)
            except Exception as e:
                logger.error(f"Failed to delete OpenCode session {session_id}: {e}")

        # Remove the session
        del state['active_sessions'][channel_id]
        self._save_state()

        if state['mode'] == 'FULL_CONTROL':
            # In FULL_CONTROL mode, we offer to delete or archive the channel
            channel = interaction.channel
            if isinstance(channel, discord.TextChannel):
                view = ExitConfirmView(channel=channel)
                await interaction.response.send_message("✅ Session ended. Since we are in FULL_CONTROL mode, would you like to delete this channel?", view=view)
                view.message = await interaction.original_response()
            else:
                await interaction.response.send_message("✅ Session ended successfully.")
        else:
            await interaction.response.send_message("✅ Session ended successfully.")

    @app_commands.command(name="agent", description="Switch the agent for the current session")
    @app_commands.describe(agent_name="Name of the agent to switch to")
    @app_commands.choices(agent_name=[
        app_commands.Choice(name="Build Agent", value="build"),
        app_commands.Choice(name="Plan Agent", value="plan"),
    ])
    async def switch_agent(self, interaction: discord.Interaction, agent_name: app_commands.Choice[str]):
        state = self.get_guild_state(interaction.guild_id)
        channel_id = interaction.channel_id
        if not channel_id:
            await interaction.response.send_message("⚠️ Could not determine channel.", ephemeral=True)
            return

        agent_value = agent_name.value
        
        if channel_id not in state['active_sessions']:
            channel = interaction.channel
            if state.get('mode') == 'FULL_CONTROL' and getattr(channel, 'name', '') == 'welcome':
                state['pending_agent'] = agent_value
                self._save_state()
                await interaction.response.send_message(f"🔄 Set agent to **{agent_name.name} ({agent_value})** for the upcoming session.")
                return
            await interaction.response.send_message("⚠️ This channel is not an active session. Use `/new` first.", ephemeral=True)
            return

        state['active_sessions'][channel_id]["agent"] = agent_value
        self._save_state()
        
        await interaction.response.send_message(f"🔄 Switched agent to **{agent_name.name} ({agent_value})** for this session.")

    async def _handle_opencode_response(self, channel: discord.TextChannel, response_data: dict):
        """Helper to extract text parts from OpenCode response and send to Discord."""
        if not response_data or not isinstance(response_data, dict):
            return
            
        parts = response_data.get("parts", [])
        for part in parts:
            if part.get("type") == "text":
                text_content = part.get("text", "")
                if text_content:
                    # Discord has a 2000 character limit per message
                    for i in range(0, len(text_content), 2000):
                        try:
                            await channel.send(text_content[i:i+2000])
                        except Exception as e:
                            logger.error(f"Failed to send text to channel {channel.id}: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Ensure message is in a TextChannel
        if not isinstance(message.channel, discord.TextChannel):
            return

        # Ignore messages with no text content
        if not message.content.strip():
            return

        guild = message.guild
        if not guild:
            return

        state = self.get_guild_state(guild.id)

        # Check if in FULL_CONTROL mode and in a channel named 'welcome'
        if state['mode'] == 'FULL_CONTROL' and message.channel.name == 'welcome':
            # Avoid responding multiple times if multiple messages are sent fast
            if message.channel.id in state['active_sessions']:
                return

            # Rename the channel
            task_id = str(uuid.uuid4())[:8]
            new_channel_name = f"task-{task_id}"
            
            # Send a loading message before renaming
            reply = await message.reply(f"🔄 Processing your request... creating session `{new_channel_name}`")

            try:
                # Create OpenCode session FIRST so we don't mutate Discord on API failure
                session_id, directory = await self.bot.opencode_client.create_session()
                self.bot.opencode_client.register_session(session_id, message.channel.id)

                project_name = os.path.basename(directory.rstrip('/')) if directory else "OpenCode"
                category = discord.utils.get(guild.categories, name=project_name)
                if not category:
                    category = await guild.create_category(project_name)

                original_category = message.channel.category

                # Rename the old welcome channel to task-{uuid} and move to category
                await message.channel.edit(name=new_channel_name, category=category)
                
                # THEN create a new #welcome channel where the old one was
                new_welcome = await guild.create_text_channel('welcome', category=original_category)
                await new_welcome.send("👋 Welcome! Send a message here to start a new task session.")

                # Get the pending agent and reset it
                pending_agent = state.get('pending_agent', 'default')
                state['pending_agent'] = 'default'

                # Register the renamed channel
                state['active_sessions'][message.channel.id] = {"agent": pending_agent, "opencode_session_id": session_id}
                self._save_state()
                
                await reply.edit(content=f"✅ Session started!")
                
                # Send the initial message to OpenCode
                channel_state = await self.bot.opencode_client.get_channel_state(message.channel.id)
                if channel_state:
                    channel_state.clear_turn()
                
                agent = state['active_sessions'][message.channel.id].get("agent")
                if agent == "default":
                    agent = None
                    
                response_data = await self.bot.opencode_client.send_message(session_id, message.content, agent=agent)
                await self._handle_opencode_response(message.channel, response_data)
                
            except discord.Forbidden:
                await reply.edit(content="❌ I don't have permission to manage channels!")
            except discord.HTTPException as e:
                await reply.edit(content=f"❌ Failed to communicate with Discord: {str(e)}")
            except Exception as e:
                await reply.edit(content=f"❌ An error occurred: {str(e)}")
                
        elif message.channel.id in state['active_sessions']:
            session_id = state['active_sessions'][message.channel.id].get("opencode_session_id")
            if session_id:
                try:
                    channel_state = await self.bot.opencode_client.get_channel_state(message.channel.id)
                    if channel_state:
                        channel_state.clear_turn()
                    agent = state["active_sessions"][message.channel.id].get("agent")
                    if agent == "default":
                        agent = None
                    response_data = await self.bot.opencode_client.send_message(session_id, message.content, agent=agent)
                    await self._handle_opencode_response(message.channel, response_data)
                except Exception as e:
                    await message.channel.send(f"❌ Failed to send message to OpenCode: {e}")


class ExitConfirmView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel):
        super().__init__(timeout=60.0)
        self.channel = channel
        self.message: discord.Message | None = None

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.message:
            try:
                await self.message.edit(content="⏳ Session ended. Deletion timed out.", view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, custom_id="delete_channel")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🗑️ Deleting channel in 3 seconds...")
        await asyncio.sleep(3)
        try:
            await self.channel.delete()
        except (discord.Forbidden, discord.HTTPException):
            try:
                await interaction.followup.send("❌ Missing permissions or hit a rate limit trying to delete the channel.", ephemeral=True)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Keep Channel", style=discord.ButtonStyle.secondary, custom_id="keep_channel")
    async def keep_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(content="✅ Session ended. Channel kept.", view=self)


async def setup(bot: commands.Bot):
    await bot.add_cog(SessionManager(bot))

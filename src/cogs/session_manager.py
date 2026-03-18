import discord
from discord import app_commands
from discord.ext import commands
import uuid
import asyncio
from typing import cast

class SessionManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Dictionary tracking state per guild
        # Format: {guild_id: {'mode': 'NORMAL', 'active_sessions': {channel_id: {"agent": "default", ...}}}}
        self.guild_states: dict[int, dict] = {}

    def get_guild_state(self, guild_id: int | None) -> dict:
        if not guild_id:
            guild_id = 0
        if guild_id not in self.guild_states:
            self.guild_states[guild_id] = {'mode': 'NORMAL', 'active_sessions': {}}
        return self.guild_states[guild_id]

    @app_commands.command(name="mode", description="Toggle global operating mode (NORMAL/FULL_CONTROL)")
    @app_commands.default_permissions(administrator=True)
    async def toggle_mode(self, interaction: discord.Interaction):
        state = self.get_guild_state(interaction.guild_id)
        if state['mode'] == 'NORMAL':
            state['mode'] = 'FULL_CONTROL'
        else:
            state['mode'] = 'NORMAL'
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

        state['active_sessions'][channel_id] = {"agent": "default"}
        await interaction.response.send_message(f"✅ Channel registered as a new session. You can now chat with the agent.")

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

        # Remove the session
        del state['active_sessions'][channel_id]

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
    async def switch_agent(self, interaction: discord.Interaction, agent_name: str):
        state = self.get_guild_state(interaction.guild_id)
        channel_id = interaction.channel_id
        if not channel_id:
            await interaction.response.send_message("⚠️ Could not determine channel.", ephemeral=True)
            return

        if channel_id not in state['active_sessions']:
            await interaction.response.send_message("⚠️ This channel is not an active session. Use `/new` first.", ephemeral=True)
            return

        # Placeholder for WS integration
        print(f"[WS Placeholder] Sending agent switch command for channel {channel_id} to agent: {agent_name}")
        state['active_sessions'][channel_id]["agent"] = agent_name
        
        await interaction.response.send_message(f"🔄 Switched agent to **{agent_name}** for this session. (Placeholder)")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Ensure message is in a TextChannel
        if not isinstance(message.channel, discord.TextChannel):
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
                # Rename the old welcome channel FIRST to task-{uuid}
                await message.channel.edit(name=new_channel_name)
                
                # THEN create a new #welcome channel
                category = message.channel.category
                new_welcome = await guild.create_text_channel('welcome', category=category)
                await new_welcome.send("👋 Welcome! Send a message here to start a new task session.")

                # Register the renamed channel
                state['active_sessions'][message.channel.id] = {"agent": "default"}
                
                await reply.edit(content=f"✅ Session started! I have renamed this channel to `#{new_channel_name}` and created a new <#{new_welcome.id}> channel.")
                
            except discord.Forbidden:
                await reply.edit(content="❌ I don't have permission to manage channels!")
            except discord.HTTPException as e:
                await reply.edit(content=f"❌ Failed to communicate with Discord: {str(e)}")
            except Exception as e:
                await reply.edit(content=f"❌ An error occurred: {str(e)}")


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

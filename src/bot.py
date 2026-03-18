import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# Load environment variables from the .env file.
load_dotenv()

# Configure bot intents.
intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Initialize backend client and open websocket connection.
        from src.opencode_client import OpenCodeClient
        self.opencode_client = OpenCodeClient(base_url="http://127.0.0.1:4096", bot=self)
        await self.opencode_client.connect()
        
        # Load cogs and register slash commands.
        await self.load_extension("src.cogs.session_manager")
        await self.tree.sync()
        print("✅ Slash commands synced successfully")

    async def on_ready(self):
        print(f"🤖 Logged in successfully as: {self.user} (ID: {self.user.id})")
        print("------")

    async def close(self):
        if hasattr(self, 'opencode_client'):
            await self.opencode_client.close()
        await super().close()

bot = MyBot()

# Demo command: create a #welcome channel in the current server.
@bot.tree.command(name="setup_welcome", description="Create a #welcome channel in this server")
@app_commands.default_permissions(manage_channels=True)
async def setup_welcome(interaction: discord.Interaction):
    guild = interaction.guild
    # Avoid creating duplicate channels.
    existing_channel = discord.utils.get(guild.text_channels, name="welcome")
    
    if existing_channel:
        await interaction.response.send_message(f"⚠️ Channel {existing_channel.mention} already exists.", ephemeral=True)
        return

    try:
        # Create the text channel.
        channel = await guild.create_text_channel('welcome')
        await interaction.response.send_message(f"✅ Welcome channel created: {channel.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I do not have permission to create channels. Please check my role permissions.", ephemeral=True)

# Entry point.
if __name__ == "__main__":
    # Support DISCORD_TOKEN, TOKEN, or DISCORD_BOT_TOKEN.
    token = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ Error: Discord token not found. Set DISCORD_TOKEN (or TOKEN / DISCORD_BOT_TOKEN) in .env.")
        exit(1)
        
    bot.run(token)

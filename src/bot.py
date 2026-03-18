import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# 讀取 .env 檔案中的環境變數
load_dotenv()

# 設定 Bot 的 Intents
intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Initialize Client
        from src.opencode_client import OpenCodeClient
        self.opencode_client = OpenCodeClient(base_url="http://127.0.0.1:4096", bot=self)
        self.loop.create_task(self.opencode_client.connect())
        
        # Load cogs
        await self.load_extension("src.cogs.session_manager")
        # 同步 Slash Commands 到 Discord 伺服器
        await self.tree.sync()
        print("✅ 成功同步 Slash Commands")

    async def on_ready(self):
        print(f"🤖 登入成功！Bot 名稱: {self.user} (ID: {self.user.id})")
        print("------")

bot = MyBot()

# ========================================================
# 測試功能 1：新建一個歡迎頻道
# ========================================================
@bot.tree.command(name="setup_welcome", description="在目前伺服器建立一個 #welcome 頻道")
@app_commands.default_permissions(manage_channels=True)
async def setup_welcome(interaction: discord.Interaction):
    guild = interaction.guild
    # 檢查是否已經有同名頻道
    existing_channel = discord.utils.get(guild.text_channels, name="welcome")
    
    if existing_channel:
        await interaction.response.send_message(f"⚠️ 頻道 {existing_channel.mention} 已經存在了！", ephemeral=True)
        return

    try:
        # 建立文字頻道
        channel = await guild.create_text_channel('welcome')
        await interaction.response.send_message(f"✅ 成功建立歡迎頻道：{channel.mention}！")
    except discord.Forbidden:
        await interaction.response.send_message("❌ 我沒有建立頻道的權限，請確認我的身分組設定！", ephemeral=True)

# ========================================================
# 啟動 Bot
# ========================================================
if __name__ == "__main__":
    # 支援使用 DISCORD_TOKEN 或 TOKEN 或 DISCORD_BOT_TOKEN
    token = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ 錯誤：找不到 Discord Token！請確保 .env 檔案中有 DISCORD_TOKEN=你的Token")
        exit(1)
        
    bot.run(token)

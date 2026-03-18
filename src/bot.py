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
        # 同步 Slash Commands 到 Discord 伺服器
        await self.tree.sync()
        print(f"✅ 成功同步 Slash Commands")

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
# 測試功能 2：發送一個帶有選項的訊息 (模擬 OpenCode)
# ========================================================
class OpenCodeSelect(discord.ui.Select):
    def __init__(self):
        # 這裡模擬我們剛才在規劃階段收到的選項結構
        options = [
            discord.SelectOption(
                label="discord.py + slash commands (推薦)", 
                description="使用最受歡迎的 Python 函式庫與斜線指令架構。",
                emoji="🐍",
                value="discord.py"
            ),
            discord.SelectOption(
                label="pycord", 
                description="如果你偏好 pycord 框架。",
                emoji="💠",
                value="pycord"
            ),
            discord.SelectOption(
                label="自行輸入答案", 
                description="彈出對話框讓你輸入自訂內容。",
                emoji="✍️",
                value="custom"
            )
        ]
        super().__init__(
            placeholder="請選擇你要回覆給 OpenCode 的答案...",
            min_values=1, # 至少選一個
            max_values=1, # 最多選一個 (如果要支援多選可以改這裡)
            options=options
        )

    # 當使用者選擇了某個選項後觸發的回呼函式
    async def callback(self, interaction: discord.Interaction):
        selected_value = self.values[0]
        
        # 模擬將答案送回給 OpenCode
        if selected_value == "custom":
            await interaction.response.send_message("（這裡未來會跳出一個 Modal 視窗讓你輸入文字）", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ 你選擇了：**{selected_value}**\n*(這個結果將會透過中繼傳回給 OpenCode 進行處理)*", ephemeral=True)

class OpenCodeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # timeout=None 表示按鈕不會過期
        self.add_item(OpenCodeSelect())

@bot.tree.command(name="mock_opencode", description="測試 OpenCode 給予選項的訊息功能")
async def mock_opencode(interaction: discord.Interaction):
    view = OpenCodeView()
    await interaction.response.send_message(
        "🤖 **[OpenCode 提問]**\n我看到這是一個 Python 專案，我建議使用 `discord.py`。請問我要實作的這兩個測試功能，應該怎麼寫？",
        view=view
    )

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
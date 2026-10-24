import os
import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
from collections import defaultdict
from aiohttp import web

# 從環境變數讀取 Token
TOKEN = os.getenv("DISCORD_TOKEN")

LIMIT_TIME = 10     # 時間視窗 (秒)
MAX_ACTIONS = 1     # 允許的最大操作次數 (零容忍)

WHITELIST_IDS = [
    1437433310484627680
]

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.moderation = True

class AntiNukeBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash Commands 已成功同步！")

bot = AntiNukeBot()
action_tracker = defaultdict(list)

def is_rate_limited(user_id: int) -> bool:
    now = datetime.datetime.now(datetime.timezone.utc)
    action_tracker[user_id] = [t for t in action_tracker[user_id] if (now - t).total_seconds() < LIMIT_TIME]
    action_tracker[user_id].append(now)
    return len(action_tracker[user_id]) > MAX_ACTIONS

async def punish_executor(guild: discord.Guild, user: discord.Member, reason: str):
    try:
        if user.id == guild.owner_id or user.id == bot.user.id:
            return
        try:
            await user.send(f"⚠️ 你在 **{guild.name}** 觸發了 Anti-Nuke 防護系統！原因: {reason}")
        except Exception:
            pass

        roles_to_remove = [role for role in user.roles if role < guild.me.top_role and not role.is_default()]
        if roles_to_remove:
            await user.remove_roles(*roles_to_remove, reason=f"[Anti-Nuke] {reason}")

        await guild.ban(user, reason=f"[Anti-Nuke 零容忍防護] {reason}")
        print(f"🚨 [Anti-Nuke] 已成功封鎖破壞者: {user} ({user.id}) | 原因: {reason}")
    except Exception as e:
        print(f"❌ 處罰執行失敗: {e}")

@bot.event
async def on_ready():
    print(f"✅ Anti-Nuke 機器人已上線: {bot.user.name} ({bot.user.id})")

@bot.event
async def on_member_join(member: discord.Member):
    if member.bot and member.id not in WHITELIST_IDS:
        try:
            await member.ban(reason="[Anti-Nuke] 未經授權的機器人自動防禦攔截")
            print(f"🚨 [Anti-Nuke] 已自動封鎖未授權加入的機器人: {member} ({member.id})")
        except Exception as e:
            print(f"❌ 無法封鎖新加入的機器人: {e}")

# ==================== 建立簡單網頁伺服器（保持 Render 免費服務運作） ====================
async def handle(request):
    return web.Response(text="Anti-Nuke Bot is running!")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render 會自動分配一個 PORT 環境變數，如果沒有則預設為 8080
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 網頁伺服器已在 Port {port} 啟動")

async def main():
    # 同時啟動網頁伺服器與 Discord 機器人
    await start_web_server()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer
import os
import asyncio
import aiohttp

# ================== CONFIG ==================
TOKEN = os.getenv("TOKEN")

SERVER_NAME = "MineForest"
JAVA_IP = "play.mineforest.xyz"

CHANNEL_ID = 1475865990830231672
ROLE_ID = 1475865990272127161

UPDATE_INTERVAL = 10
# ===========================================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

status_message = None
last_online = True

# 🔥 NEVER FAIL JAVA
async def get_java():
    try:
        server = JavaServer.lookup(JAVA_IP)

        try:
            s = await asyncio.wait_for(server.async_status(), timeout=5)

            players = "No players online"
            if s.players.sample:
                players = ", ".join([p.name for p in s.players.sample])

            return {
                "online": True,
                "players": f"{s.players.online}/{s.players.max}",
                "ping": f"{round(s.latency)} ms",
                "list": players
            }

        except:
            ping = await asyncio.wait_for(server.async_ping(), timeout=5)

            return {
                "online": True,
                "players": "Unknown",
                "ping": f"{round(ping)} ms",
                "list": "Player list unavailable"
            }

    except:
        pass

    # API fallback
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mcsrvstat.us/2/{JAVA_IP}") as res:
                data = await res.json()

        if data.get("online"):
            players = data["players"]["online"]
            max_players = data["players"]["max"]

            return {
                "online": True,
                "players": f"{players}/{max_players}",
                "ping": "API",
                "list": "Hidden"
            }
        else:
            return {"online": False}

    except:
        return {"online": False}

# 🔹 STATUS EMBED
async def build_status():
    global last_online

    java = await get_java()
    online = java["online"]

    embed = discord.Embed(
        title=f"🌲 {SERVER_NAME} Status",
        color=0x2ecc71 if online else 0xe74c3c
    )

    if online:
        embed.add_field(name="Players", value=java["players"], inline=True)
        embed.add_field(name="Ping", value=java["ping"], inline=True)
        embed.add_field(name="Players List", value=java["list"], inline=False)
    else:
        embed.description = "🔴 Server Offline"

    embed.set_footer(text="MineForest • Never Fail System")

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        if not online and last_online:
            await channel.send(f"<@&{ROLE_ID}> ⚠️ Server DOWN!")
        if online and not last_online:
            await channel.send("✅ Server BACK ONLINE!")

    last_online = online
    return embed

# 🔹 PLAYERS EMBED
async def build_players():
    java = await get_java()

    if not java["online"]:
        return discord.Embed(
            description="🔴 Server Offline",
            color=0xe74c3c
        )

    return discord.Embed(
        description=f"**Players:**\n\n{java['list']}",
        color=0x2ecc71
    )

# 🔘 BUTTON
class RefreshView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.green, emoji="🔄")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = await build_status()
        await interaction.message.edit(embed=embed, view=self)

# 🔹 PREFIX COMMANDS
@bot.command()
async def status(ctx):
    embed = await build_status()
    await ctx.send(embed=embed, view=RefreshView())

@bot.command()
async def players(ctx):
    embed = await build_players()
    await ctx.send(embed=embed)

# 🔹 SLASH COMMANDS
@bot.tree.command(name="status", description="Check server status")
async def slash_status(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = await build_status()
    await interaction.followup.send(embed=embed, view=RefreshView())

@bot.tree.command(name="players", description="Show players")
async def slash_players(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = await build_players()
    await interaction.followup.send(embed=embed)

# 🔹 AUTO UPDATE
@tasks.loop(seconds=UPDATE_INTERVAL)
async def auto_update():
    global status_message

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    embed = await build_status()

    if status_message is None:
        status_message = await channel.send(embed=embed, view=RefreshView())
    else:
        await status_message.edit(embed=embed, view=RefreshView())

# 🔹 READY
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    await bot.change_presence(
        activity=discord.Game(name="play.mineforest.xyz")
    )

    try:
        await bot.tree.sync()
    except Exception as e:
        print(e)

    auto_update.start()

# 🔹 RUN
if not TOKEN:
    raise Exception("TOKEN not found!")

bot.run(TOKEN)

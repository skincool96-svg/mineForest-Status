import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer, BedrockServer
import os

# ================== CONFIG ==================
TOKEN = os.getenv("TOKEN")  # Railway env variable

SERVER_NAME = "MineForest"
JAVA_IP = "play.mineforest.xyz"
BEDROCK_IP = "play.mineforest.xyz"
PORT = 25565

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

# 🔹 FETCH JAVA
async def get_java():
    try:
        server = JavaServer.lookup(f"{JAVA_IP}:{PORT}")
        s = server.status()

        players = "No players online"
        if s.players.sample:
            players = ", ".join([p.name for p in s.players.sample])

        return {
            "online": True,
            "players": f"{s.players.online}/{s.players.max}",
            "ping": round(s.latency),
            "list": players
        }
    except:
        return {"online": False}

# 🔹 FETCH BEDROCK
async def get_bedrock():
    try:
        server = BedrockServer.lookup(f"{BEDROCK_IP}:{PORT}")
        s = server.status()

        return {
            "online": True,
            "players": f"{s.players_online}/{s.players_max}"
        }
    except:
        return {"online": False}

# 🔹 STATUS EMBED
async def build_status():
    global last_online

    java = await get_java()
    bedrock = await get_bedrock()

    online = java["online"]

    embed = discord.Embed(
        title=f"🌲 {SERVER_NAME} Status",
        color=0x2ecc71 if online else 0xe74c3c
    )

    if online:
        embed.add_field(name="Players", value=java["players"], inline=True)
        embed.add_field(name="Ping", value=f"{java['ping']} ms", inline=True)
        embed.add_field(name="Players List", value=java["list"], inline=False)
    else:
        embed.description = "🔴 Server Offline"

    if bedrock["online"]:
        embed.add_field(name="Bedrock", value=bedrock["players"], inline=True)

    embed.set_footer(text="MineForest • Auto Live")

    # 🔔 Alerts
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
    try:
        server = JavaServer.lookup(f"{JAVA_IP}:{PORT}")
        s = server.status()

        if s.players.sample:
            names = ", ".join([p.name for p in s.players.sample])
        else:
            names = "No players online"

        return discord.Embed(
            description=f"**Players ({s.players.online}):**\n\n{names}\n\n`{JAVA_IP}`",
            color=0x2ecc71
        )

    except:
        return discord.Embed(
            description="🔴 Server Offline",
            color=0xe74c3c
        )

# 🔘 BUTTON VIEW
class RefreshView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.green, emoji="🔄")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await build_status()
        await interaction.response.edit_message(embed=embed, view=self)

# 🔹 COMMANDS
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
    embed = await build_status()
    await interaction.response.send_message(embed=embed, view=RefreshView())

@bot.tree.command(name="players", description="Show players")
async def slash_players(interaction: discord.Interaction):
    embed = await build_players()
    await interaction.response.send_message(embed=embed)

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

    try:
        await bot.tree.sync()
    except Exception as e:
        print(e)

    auto_update.start()

# 🔹 RUN
if not TOKEN:
    raise Exception("TOKEN not found! Set it in Railway Variables")

bot.run(TOKEN)

import asyncio
import os
import sqlite3
from datetime import datetime
import discord
from discord.ext import commands
import subprocess
import sys

from config import TOKEN, GUILD, CATEGORY

TOKEN = TOKEN
GUILD_ID = GUILD
CATEGORY_ID = CATEGORY
PREFIX = "!"
LOGS_FOLDER = "logs"

# === Auto-update system ===
def auto_update():
    print("\033[34m[UPDATE]\033[0m Checking for updates...")
    try:
        subprocess.run(["git", "fetch"], check=True)
        status = subprocess.run(["git", "status", "-uno"], capture_output=True, text=True)

        if "Your branch is behind" in status.stdout:
            print("\033[34m[UPDATE]\033[0m Update found! Pulling changes...")
            try:
                subprocess.run(["git", "pull"], check=True)
            except subprocess.CalledProcessError:
                print("\033[33m[UPDATE WARN]\033[0m Local changes detected! Forcing update...")
                subprocess.run(["git", "reset", "--hard", "HEAD"], check=True)
                subprocess.run(["git", "clean", "-fd"], check=True)
                subprocess.run(["git", "pull"], check=True)

            print("\033[34m[UPDATE]\033[0m Update applied successfully. Restarting bot...")
            os.execv(sys.executable, ["python"] + sys.argv)
        else:
            print("\033[34m[UPDATE]\033[0m Bot is up to date!")
    except Exception as e:
        print(f"\033[31m[UPDATE ERROR]\033[0m {e}")

# Run the updater before anything else
auto_update()

# === Bot Setup ===
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.dm_messages = True
intents.message_content = True
intents.members = True

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

bot = commands.Bot(command_prefix=PREFIX, intents=intents, loop=loop)

# === Database ===
conn = sqlite3.connect("modmail.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS modmail (
    user_id INTEGER PRIMARY KEY,
    channel_id INTEGER
)
""")
conn.commit()

def load_modmails():
    cursor.execute("SELECT user_id, channel_id FROM modmail")
    return dict(cursor.fetchall())

def save_modmail(user_id, channel_id):
    cursor.execute("REPLACE INTO modmail (user_id, channel_id) VALUES (?, ?)", (user_id, channel_id))
    conn.commit()

def delete_modmail(user_id):
    cursor.execute("DELETE FROM modmail WHERE user_id = ?", (user_id,))
    conn.commit()

open_modmails = load_modmails()

if not os.path.exists(LOGS_FOLDER):
    os.makedirs(LOGS_FOLDER)

def log_message(user_id, sender, content):
    filename = f"{LOGS_FOLDER}/{user_id}.txt"
    with open(filename, "a", encoding="utf-8") as f:
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{time}] {sender}: {content}\n")

# === Events ===
@bot.event
async def on_ready():
    print(f"\033[32m[IFNO]\033[0m Logged in as {bot.user} (ID: {bot.user.id})")
    print("\033[32m[IFNO]\033[0m ModMail bot is ready!")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Handle DMs
    if isinstance(message.channel, discord.DMChannel):
        guild = bot.get_guild(GUILD_ID)
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)

        if not category:
            return await message.channel.send("⚠️ ModMail category not found! Use `!setup` first!")

        if message.author.id in open_modmails:
            channel = guild.get_channel(open_modmails[message.author.id])
            if channel:
                embed = discord.Embed(
                    title="📩 New Message",
                    description=message.content,
                    color=discord.Color.green()
                )
                embed.set_author(name=message.author.name, icon_url=message.author.avatar)
                await channel.send(embed=embed)
                log_message(message.author.id, message.author.name, message.content)
                return
        else:
            channel = await guild.create_text_channel(
                name=f"modmail-{message.author.name}",
                category=category,
                topic=f"ModMail with {message.author} (ID: {message.author.id})"
            )
            open_modmails[message.author.id] = channel.id
            save_modmail(message.author.id, channel.id)

            await channel.send(f"📬 **New ModMail opened by {message.author.mention}!**")
            await message.channel.send("✅ Your message has been sent to the moderators!")

        embed = discord.Embed(
            title="📨 New ModMail Message",
            description=message.content,
            color=discord.Color.blue()
        )
        embed.set_author(name=message.author.name, icon_url=message.author.avatar)
        await channel.send(embed=embed)
        log_message(message.author.id, message.author.name, message.content)

    # Handle mod replies
    elif message.guild and message.channel.category_id == CATEGORY_ID:
        for user_id, channel_id in open_modmails.items():
            if channel_id == message.channel.id:
                user = await bot.fetch_user(user_id)
                embed = discord.Embed(
                    title="🛠️ Moderator Reply",
                    description=message.content,
                    color=discord.Color.orange()
                )
                embed.set_footer(text=f"From {message.author}")
                await user.send(embed=embed)
                await message.add_reaction("✅")
                log_message(user_id, f"{message.author} (mod)", message.content)
                break

    await bot.process_commands(message)

# === Commands ===
@bot.command()
@commands.has_permissions(manage_guild=True)
async def setup(ctx):
    """Creates ModMail category automatically and updates config.py"""
    guild = ctx.guild
    import config

    existing = discord.utils.get(guild.categories, name="ModMail")

    if existing:
        await ctx.send(f"⚠️ Category 'ModMail' already exists (ID: `{existing.id}`). Updating config.py automatically.")
        new_id = existing.id
    else:
        category = await guild.create_category("ModMail")
        await ctx.send(f"✅ Created 'ModMail' category with ID `{category.id}`. Updating config.py automatically.")
        new_id = category.id

    # Update config.py
    config_file = os.path.join(os.path.dirname(__file__), "config.py")
    with open(config_file, "r") as f:
        lines = f.readlines()

    with open(config_file, "w") as f:
        for line in lines:
            if line.startswith("CATEGORY"):
                f.write(f"CATEGORY = {new_id}\n")
            else:
                f.write(line)

    global CATEGORY_ID
    CATEGORY_ID = new_id

@bot.command()
@commands.has_permissions(manage_channels=True)
async def close(ctx):
    """Close a modmail thread and delete the channel."""
    if ctx.channel.category_id != CATEGORY_ID:
        return await ctx.send("❌ This is not a modmail channel!")

    user_id = None
    for uid, cid in list(open_modmails.items()):
        if cid == ctx.channel.id:
            user_id = uid
            del open_modmails[uid]
            delete_modmail(uid)
            break

    await ctx.send("📪 ModMail closed!")
    await ctx.channel.delete()

    if user_id:
        user = await bot.fetch_user(user_id)
        await user.send("📫 Your ModMail has been closed by a moderator.")
        log_message(user_id, "System", "ModMail closed")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def logs(ctx, user: discord.User):
    """Send the log file for a user's ModMail."""
    filename = f"{LOGS_FOLDER}/{user.id}.txt"
    if os.path.exists(filename):
        await ctx.send(file=discord.File(filename))
    else:
        await ctx.send("❌ No logs found for that user.")

bot.run(TOKEN)

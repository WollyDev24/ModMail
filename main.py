import asyncio
import os
import sqlite3
from datetime import datetime
import discord
from discord.ext import commands
from colorama import Fore, Style, init
import sys
import time

init(autoreset=True)

from config import TOKEN, GUILD, CATEGORY

TOKEN = TOKEN
GUILD_ID = GUILD
CATEGORY_ID = CATEGORY
PREFIX = "!"
LOGS_FOLDER = "logs"

# Database Setup
conn = sqlite3.connect("modmail.db")
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS modmail (
    user_id INTEGER PRIMARY KEY,
    channel_id INTEGER
)""")
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
new_ticket_alerts = set()  # für blinkende Tickets

if not os.path.exists(LOGS_FOLDER):
    os.makedirs(LOGS_FOLDER)

def log_message(user_id, sender, content):
    filename = f"{LOGS_FOLDER}/{user_id}.txt"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {sender}: {content}\n")

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)
start_time = time.time()
command_history = []

# Dashboard Functions

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def format_uptime():
    total_seconds = int(time.time() - start_time)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

def show_dashboard():
    clear_terminal()
    print(Fore.BLUE + "="*60)
    print(Fore.BLUE + "          🟦 MODMAIL BOT DASHBOARD")
    print(Fore.BLUE + "="*60)
    print(f"{Fore.GREEN}Bot: {bot.user} | Guilds: {len(bot.guilds)} | Users: {sum(len(g.members) for g in bot.guilds)}")
    print(f"{Fore.YELLOW}Uptime: {format_uptime()} | Open Tickets: {len(open_modmails)}")
    print(Fore.BLUE + "-"*60)

    if open_modmails:
        print(Fore.CYAN + "Active Tickets:")
        for idx, (user_id, channel_id) in enumerate(open_modmails.items(), start=1):
            user = bot.get_user(user_id)
            alert = ""
            if user_id in new_ticket_alerts:
                alert = Fore.RED + " [NEW!] "  # blinkendes Ticket
            print(f"{idx}. {user.name if user else user_id} (Channel ID: {channel_id}){alert}")
    else:
        print(Fore.CYAN + "No active tickets.")
    print(Fore.BLUE + "-"*60)

    print(Fore.MAGENTA + "Commands:")
    print("  logs <number>        → Show logs for a ticket")
    print("  close <number>       → Close a ticket")
    print("  users                → Show all user IDs in ModMail DB")
    print("  status <online/dnd/idle/offline> → Change bot status")
    print("  activity <type> <text> → Set bot activity (Playing/Watching/Listening)")
    print("  restart              → Restart bot")
    print("  refresh              → Refresh dashboard")
    print("  exit / shutdown      → Stop bot")
    print(Fore.BLUE + "-"*60)
    print(Fore.GREEN + "Command History (last 5):")
    for cmd in command_history[-5:]:
        print(f"- {cmd}")
    print(Fore.BLUE + "="*60 + "\n")

def get_ticket_by_number(number):
    if 1 <= number <= len(open_modmails):
        return list(open_modmails.items())[number-1]
    return None, None

async def dashboard_loop():
    await bot.wait_until_ready()
    while True:
        show_dashboard()

        # Non-blocking input
        cmd = await asyncio.to_thread(input, ">> ")
        command_history.append(cmd)
        parts = cmd.strip().split()
        if not parts:
            continue

        if parts[0] == "logs" and len(parts) == 2 and parts[1].isdigit():
            number = int(parts[1])
            user_id, _ = get_ticket_by_number(number)
            if user_id:
                filename = f"{LOGS_FOLDER}/{user_id}.txt"
                if os.path.exists(filename):
                    print(Fore.GREEN + f"\n--- Logs for {user_id} ---")
                    with open(filename, "r", encoding="utf-8") as f:
                        for line in f.readlines():
                            print(line.strip())
                    print(Fore.GREEN + "--- End of Logs ---\n")
                else:
                    print(Fore.RED + "No logs found for that user.\n")
            else:
                print(Fore.RED + "Invalid ticket number.\n")
            await asyncio.to_thread(input, "Press Enter to continue...")

        elif parts[0] == "close" and len(parts) == 2 and parts[1].isdigit():
            number = int(parts[1])
            user_id, channel_id = get_ticket_by_number(number)
            if user_id:
                delete_modmail(user_id)
                open_modmails.pop(user_id)
                if user_id in new_ticket_alerts:
                    new_ticket_alerts.remove(user_id)
                print(Fore.YELLOW + f"Ticket {number} closed successfully.\n")
                guild = bot.get_guild(GUILD_ID)
                channel = guild.get_channel(channel_id) if guild else None
                if channel:
                    await channel.delete()
            else:
                print(Fore.RED + "Invalid ticket number.\n")
            await asyncio.to_thread(input, "Press Enter to continue...")

        elif parts[0] == "users":
            print(Fore.CYAN + "\nUser IDs in ModMail DB:")
            cursor.execute("SELECT user_id FROM modmail")
            for row in cursor.fetchall():
                print(f"- {row[0]}")
            print()
            await asyncio.to_thread(input, "Press Enter to continue...")

        elif parts[0] == "status" and len(parts) == 2:
            status_map = {
                "online": discord.Status.online,
                "dnd": discord.Status.dnd,
                "idle": discord.Status.idle,
                "offline": discord.Status.invisible
            }
            new_status = status_map.get(parts[1].lower())
            if new_status:
                await bot.change_presence(status=new_status)
                print(Fore.GREEN + f"Bot status changed to {parts[1].lower()}")
            else:
                print(Fore.RED + "Invalid status! Use online/dnd/idle/offline.")
            await asyncio.to_thread(input, "Press Enter to continue...")

        elif parts[0] == "activity" and len(parts) >= 3:
            activity_type = parts[1].lower()
            text = " ".join(parts[2:])
            type_map = {
                "playing": discord.ActivityType.playing,
                "watching": discord.ActivityType.watching,
                "listening": discord.ActivityType.listening,
                "competing": discord.ActivityType.competing
            }
            act_type = type_map.get(activity_type)
            if act_type:
                await bot.change_presence(activity=discord.Activity(type=act_type, name=text))
                print(Fore.GREEN + f"Bot activity set: {activity_type.title()} {text}")
            else:
                print(Fore.RED + "Invalid activity type! Use playing/watching/listening/competing.")
            await asyncio.to_thread(input, "Press Enter to continue...")

        elif parts[0] == "restart":
            print(Fore.YELLOW + "Restarting bot...")
            python = sys.executable
            os.execl(python, python, *sys.argv)

        elif parts[0] == "refresh":
            continue

        elif parts[0] in ["exit", "shutdown"]:
            print(Fore.RED + "Stopping bot...")
            await bot.close()
            break

        else:
            print(Fore.RED + "Unknown command.\n")
            await asyncio.to_thread(input, "Press Enter to continue...")

@bot.event
async def on_ready():
    print(Fore.GREEN + f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(Fore.GREEN + "📬 ModMail bot ready!")
    bot.loop.create_task(dashboard_loop())

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # DM → ModMail
    if isinstance(message.channel, discord.DMChannel):
        guild = bot.get_guild(GUILD_ID)
        category = discord.utils.get(guild.categories, id=CATEGORY_ID) if guild else None
        if not category:
            return await message.channel.send("⚠️ ModMail category missing! Run `!setup` first.")

        if message.author.id in open_modmails:
            channel = guild.get_channel(open_modmails[message.author.id])
        else:
            channel = await guild.create_text_channel(
                name=f"modmail-{message.author.name}",
                category=category
            )
            open_modmails[message.author.id] = channel.id
            save_modmail(message.author.id, channel.id)
            new_ticket_alerts.add(message.author.id)  # neues Ticket blinkt
            await channel.send(f"📩 New ModMail opened by {message.author.mention}")

        await channel.send(f"**{message.author}:** {message.content}")
        log_message(message.author.id, message.author.name, message.content)
        await message.channel.send("✅ Message sent to moderators!")

    # Mod → User reply
    elif message.guild and message.channel.category_id == CATEGORY_ID:
        for user_id, channel_id in open_modmails.items():
            if message.channel.id == channel_id:
                user = await bot.fetch_user(user_id)
                await user.send(f"**{message.author}:** {message.content}")
                log_message(user_id, f"{message.author} (mod)", message.content)
                break

    await bot.process_commands(message)

from discord.ext import commands


# --- Close Ticket ---
@bot.command()
@commands.has_permissions(manage_channels=True)
async def close(ctx, user_id: int = None):
    """Close a ticket (user does NOT see this)"""
    if ctx.channel.category_id != CATEGORY_ID and not user_id:
        return await ctx.send("❌ This is not a modmail channel!")
    
    if user_id is None:
        # find user from current channel
        user_id = None
        for uid, cid in open_modmails.items():
            if cid == ctx.channel.id:
                user_id = uid
                break

    if user_id in open_modmails:
        channel_id = open_modmails[user_id]
        del open_modmails[user_id]
        delete_modmail(user_id)

        await ctx.send(f"📪 Ticket for user `{user_id}` closed!")  # nur Mod-Channel
        channel = ctx.guild.get_channel(channel_id)
        if channel:
            await channel.delete()

        log_message(user_id, f"{ctx.author} (mod command: close)", "Ticket closed")
    else:
        await ctx.send("❌ Ticket not found!")

# --- Broadcast ---
@bot.command(aliases=["brd"])
@commands.has_permissions(manage_channels=True)
async def broadcast(ctx, *, message: str):
    """Broadcast a message to all open tickets (user sees message)"""
    if not open_modmails:
        return await ctx.send("❌ No active tickets to broadcast to!")

    sent = 0
    for user_id in open_modmails.keys():
        try:
            user = await bot.fetch_user(user_id)
            await user.send(f"📢 Broadcast from Mods:\n{message}")  # user receives broadcast
            log_message(user_id, f"{ctx.author} (mod command: broadcast)", message)
            sent += 1
        except:
            continue

    await ctx.send(f"✅ Broadcast sent to {sent} users.")  # nur Mod-Channel

bot.run(TOKEN)

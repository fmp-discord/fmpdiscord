from functools import wraps
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
from datetime import datetime, timedelta
from pytz import utc
import requests
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta

# Load your Flask app
app = Flask(__name__)
CORS(app, resources={r"/submit": {"origins": "https://fmp-discord.github.io"}})

# MongoDB connection URI for MongoDB Atlas cluster
uri = "mongodb+srv://Bijay:bijay%40123@cluster0.hpl6qfx.mongodb.net/db_discord?retryWrites=true&w=majority"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
    print("Connected to the database.")
except Exception as e:
    print(e)

# Database and collection names
db = client.db_discord
users_collection = db.tbl_discord

# Route to handle POST requests from the frontend
@app.route('/submit', methods=['POST'])
def submit():
    data = request.json  # Assume the request contains JSON data

    discord_id = data['discord_id']
    username = data.get('username')
    server = data.get('server')
    
    user = users_collection.find_one({"userid": discord_id})
    
    if user:
        current_time = datetime.now()
        last_visit = user['updatedat']
        if current_time < last_visit + timedelta(hours=1):
            time_remaining = last_visit + timedelta(hours=1) - current_time
            print(f"User {discord_id} needs to wait for {time_remaining.seconds // 60} more minutes.")
            return jsonify({
                "message": f"Come back after {time_remaining.seconds // 60} minutes to get more points.",
                "total_points": user['points']
            })
        else:
            updated_user = {
                "$set": {"username": username or f"user_{discord_id}", "server": server, "updatedat": current_time},
                "$inc": {"points": 2}
            }
            users_collection.update_one({"userid": discord_id}, updated_user)
            user = users_collection.find_one({"userid": discord_id})
            print(f"Updated user {discord_id} at {current_time}. Total points: {user['points']}")
            return jsonify({
                "message": "Thanks! You got 2 points.",
                "total_points": user['points']
            })
    else:
        current_time = datetime.now()
        new_user = {
            "username": username or f"user_{discord_id}",
            "userid": discord_id,
            "createdat": current_time,
            "updatedat": current_time,
            "points": 2,
            "server": server
        }
        users_collection.insert_one(new_user)
        print(f"Inserted new user {discord_id} at {current_time}. Total points: 2")
        return jsonify({
            "message": "Thanks! You got 2 points.",
            "total_points": 2
        })

# Load config from config.json
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

TOKEN = config['token']

# Define intents
intents = discord.Intents.all()

# Create bot instance with intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Function to get server-specific configurations
def get_server_config(guild_id):
    return config['servers'].get(str(guild_id))

# Function to save the updated config back to the config.json file
def save_config():
    with open('config.json', 'w') as config_file:
        json.dump(config, config_file, indent=4)

# Function to check if user is an administrator, admin, or owner based on role IDs
def is_administrator(user: discord.Member, server_config) -> bool:
    admin_role_ids = server_config.get('admin_role_ids', [])

    for role in user.roles:
        if role.id in admin_role_ids:
            return True

    return False

# Decorator to check if user is an administrator
# Decorator to check if user is an administrator
def check_admin():
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            if interaction.guild is None:
                await interaction.response.send_message("This command cannot be used in direct messages.", ephemeral=True)
                return
            
            server_id = str(interaction.guild.id)
            server_config = get_server_config(server_id)

            if is_administrator(interaction.user, server_config):
                return await func(interaction, *args, **kwargs)
            else:
                await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return wrapper
    return decorator

# Decorator to check if the user is blacklisted
def check_blacklist():
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            if interaction.guild is None:
                await interaction.response.send_message("This command cannot be used in direct messages.", ephemeral=True)
                return
            
            server_config = get_server_config(interaction.guild.id)
            if interaction.user.id in server_config['blacklist_uids']:
                await interaction.response.send_message(
                    "You are blacklisted for safety purposes.",
                    ephemeral=True
                )
                return
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

# Decorator to check if the command is used in the allowed category
def check_category():
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            if interaction.guild is None:
                await interaction.response.send_message("This command cannot be used in direct messages.", ephemeral=True)
                return
            
            server_config = get_server_config(interaction.guild.id)

            if interaction.channel.category_id != server_config['allowed_category_id']:
                await interaction.response.send_message(
                    f"This command can only be used in the specific category. Please use it [here]({server_config['category_link']}).",
                    ephemeral=True
                )
                return
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

# Function to log command usage
async def log_command_usage(interaction: discord.Interaction, command_name: str, file_name: str):
    server_config = get_server_config(interaction.guild.id)
    log_channel = bot.get_channel(server_config['bot_log'])
    if log_channel:
        user_mention = interaction.user.mention
        timestamp = datetime.now(utc).strftime("%Y-%m-%d %H:%M:%S")
        await log_channel.send(f"{user_mention} used `{command_name}` command and received `{file_name}` at {timestamp} UTC")

# Function to check if a user can use a command (once per cooldown period)
def can_use_command(user_id: int, last_command_usage: list, cooldown_hours: int) -> bool:
    cooldown_duration = timedelta(hours=cooldown_hours)
    for entry in last_command_usage:
        if entry['user_id'] == user_id:
            last_usage_time = datetime.strptime(
                entry['time'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=utc)
            now = datetime.now(utc)
            if now - last_usage_time < cooldown_duration:
                return False
    return True

# Function to load cooldowns from JSON
def load_cooldowns():
    try:
        with open('cooldowns.json', 'r', encoding='utf-8') as f:
            try:
                cooldown_data = json.load(f)
            except json.JSONDecodeError:
                cooldown_data = []  # Initialize as empty list if file is empty or malformed
    except FileNotFoundError:
        cooldown_data = []  # Initialize as empty list if file doesn't exist
    return cooldown_data

# Function to load cooldowns from TXT
def load_cooldowns_txt():
    cooldown_txt_file = 'cooldowns.txt'
    try:
        cooldowns = []
        with open(cooldown_txt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            i = 0
            while i < len(lines):
                entry = {}
                entry['user_id'] = int(lines[i].strip().split(': ')[1])
                entry['user_name'] = lines[i + 1].strip().split(': ')[1]
                entry['command_used'] = lines[i + 2].strip().split(': ')[1]
                entry['time'] = lines[i + 3].strip().split(': ')[1]
                entry['cooldown_time'] = lines[i + 4].strip().split(': ')[1]
                entry['file_name'] = lines[i + 5].strip().split(': ')[1]
                cooldowns.append(entry)
                i += 6
        return cooldowns
    except FileNotFoundError:
        return []

# Function to save last command usage times to file
# Function to save last command usage times to file
def save_cooldowns(new_entries):
    cooldown_file = 'cooldowns.json'
    cooldown_txt_file = 'cooldowns.txt'

    # Load existing cooldowns
    existing_cooldowns = load_cooldowns()

    # Avoid adding duplicates by checking existing cooldowns
    for new_entry in new_entries:
        if not any(entry['user_id'] == new_entry['user_id'] and entry['command_used'] == new_entry['command_used'] and entry['time'] == new_entry['time'] for entry in existing_cooldowns):
            existing_cooldowns.append(new_entry)

    # Save to JSON file
    with open(cooldown_file, 'w', encoding='utf-8') as f:
        json.dump(existing_cooldowns, f, indent=4, default=str, ensure_ascii=False)

    # Save to TXT file
    with open(cooldown_txt_file, 'w', encoding='utf-8') as f:
        for entry in existing_cooldowns:
            f.write(f"User ID: {entry['user_id']}\n")
            f.write(f"User Name: {entry['user_name']}\n")
            f.write(f"Command Used: {entry['command_used']}\n")
            f.write(f"Time: {entry['time']}\n")
            f.write(f"Cooldown Time: {entry['cooldown_time']}\n")
            f.write(f"File Name: {entry['file_name']}\n")
            f.write("\n")


# Function to handle the sending of a random cookie file
async def handle_cookie_command(interaction: discord.Interaction, directory: str, command_name: str, cooldown_hours: int, last_command_usage: list):
    server_config = get_server_config(interaction.guild.id)

    # Check if the user is whitelisted
    if str(interaction.user.id) in server_config.get('whitelist', {}):
        await execute_whitelisted_command(interaction, directory, command_name)
    else:
        await execute_regular_command(interaction, directory, command_name, cooldown_hours, last_command_usage)

async def execute_whitelisted_command(interaction: discord.Interaction, directory: str, command_name: str):
    files = [file for file in os.listdir(directory) if file.endswith('.txt')]
    if files:
        random_file = random.choice(files)
        file_path = os.path.join(directory, random_file)
        await interaction.response.send_message(f"Sending you a random cookie file: `{random_file}`", ephemeral=True)
        try:
            await interaction.user.send(file=discord.File(file_path))
        except discord.errors.Forbidden:
            await interaction.followup.send("I cannot send you a direct message. Please enable DMs and try again.", ephemeral=True)
            return
        await log_command_usage(interaction, command_name, random_file)
    else:
        await interaction.response.send_message(f"No {command_name} cookie files are available right now. Please try again later.", ephemeral=True)

async def execute_regular_command(interaction: discord.Interaction, directory: str, command_name: str, cooldown_hours: int, last_command_usage: list):
    user_id = interaction.user.id
    server_config = get_server_config(interaction.guild.id)

    # Ensure user is registered in the database
    user = users_collection.find_one({"userid": user_id})
    if not user:
        # Register the user with 0 points
        current_time = datetime.now()
        new_user = {
            "username": interaction.user.name,
            "userid": user_id,
            "createdat": current_time,
            "updatedat": current_time,
            "points": 0,
            "server": interaction.guild.id,
            "cookies": []
        }
        users_collection.insert_one(new_user)
        print(f"Registered new user {user_id} at {current_time}.")
    
    # Check if user has enough points to use the command
    if not can_use_command(user_id, last_command_usage, cooldown_hours):
        remaining_time = None
        cooldown_duration = timedelta(hours=cooldown_hours)
        for entry in last_command_usage:
            if entry['user_id'] == user_id:
                last_usage_time = datetime.strptime(
                    entry['time'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=utc)
                now = datetime.now(utc)
                remaining_time = (last_usage_time + cooldown_duration) - now
                break

        if remaining_time:
            hours, remainder = divmod(remaining_time.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            await interaction.response.send_message(
                f"You can use this command again in {int(hours)} hours and {int(minutes)} minutes on {last_usage_time.strftime('%Y-%m-%d')}.",
                ephemeral=True
            )
        return

    # Proceed with sending files if user has enough points
    files = [file for file in os.listdir(directory) if file.endswith('.txt')]
    if files:
        random_file = random.choice(files)
        file_path = os.path.join(directory, random_file)
        await interaction.response.send_message(f"Sending you a random cookie file: `{random_file}`", ephemeral=True)
        try:
            await interaction.user.send(file=discord.File(file_path))
        except discord.errors.Forbidden:
            await interaction.followup.send("I cannot send you a direct message. Please enable DMs and try again.", ephemeral=True)
            return
        await log_command_usage(interaction, command_name, random_file)

        # Update last_command_usage and save it
        last_command_usage.append({
            'user_id': user_id,
            'user_name': interaction.user.name,
            'command_used': command_name,
            'time': datetime.now(utc).strftime("%Y-%m-%d %H:%M:%S"),
            'cooldown_time': (datetime.now(utc) + timedelta(hours=cooldown_hours)).strftime("%Y-%m-%d %H:%M:%S"),
            'file_name': random_file
        })
        save_cooldowns(last_command_usage)
    else:
        await interaction.response.send_message(f"No {command_name} cookie files are available right now. Please try again later.", ephemeral=True)

# Function to create cookie commands
def create_cookie_command(command_name, directory_key, description):
    @app_commands.command(name=command_name, description=description)
    @check_blacklist()
    @check_category()
    async def cookie_command(interaction: discord.Interaction):
        server_config = get_server_config(interaction.guild.id)
        directory = server_config['directories'].get(directory_key)
        if directory:
            last_command_usage = load_cooldowns()
            await handle_cookie_command(interaction, directory, command_name, server_config['command_cooldown_hours'], last_command_usage)
        else:
            await interaction.response.send_message(f"The directory '{directory_key}' is not configured or does not exist.", ephemeral=True)
    bot.tree.add_command(cookie_command)

# Create specific cookie commands with descriptions
create_cookie_command("netflixcookie", 'netflix', "Get a random Netflix cookie!")
create_cookie_command("spotifycookie", 'spotify', "Get a random Spotify cookie!")
create_cookie_command("primecookie", 'prime', "Get a random Prime Video cookie!")
create_cookie_command("crunchyrollcookie", 'crunchyroll', "Get a random Crunchyroll cookie!")

# Command to say hello
@app_commands.command(name="hello", description="Say hello to the bot")
@check_blacklist()
@check_category()
async def say_hello(interaction: discord.Interaction):
    await interaction.response.send_message("Hello! I hope you're having a great day.", ephemeral=True)
bot.tree.add_command(say_hello)

# Command to whitelist a user
@app_commands.command(name="whitelist", description="Whitelist a user to use commands")
@check_admin()
async def whitelist_user(interaction: discord.Interaction, user: discord.Member):
    server_config = get_server_config(interaction.guild.id)

    # Ensure 'whitelist' exists in server_config
    if 'whitelist' not in server_config:
        server_config['whitelist'] = {}

    # Add user to whitelist
    server_config['whitelist'][str(user.id)] = {'remaining_uses': float('inf')}

    # Save updated config
    save_config()

    await interaction.response.send_message(f"User {user.mention} has been whitelisted.", ephemeral=True)

# Command to blacklist a user
@app_commands.command(name="blacklist", description="Blacklist a user from using commands")
@check_admin()
async def blacklist_user(interaction: discord.Interaction, user: discord.Member):
    server_config = get_server_config(interaction.guild.id)
    if user.id not in server_config['blacklist_uids']:
        server_config['blacklist_uids'].append(user.id)
        save_config()
        await interaction.response.send_message(f"User {user.mention} has been blacklisted.", ephemeral=True)
    else:
        await interaction.response.send_message(f"User {user.mention} is already blacklisted.", ephemeral=True)
bot.tree.add_command(blacklist_user)

# Command to remove a user from the blacklist
@app_commands.command(name="removeblacklist", description="Remove a user from the blacklist")
@check_admin()
async def remove_blacklist_user(interaction: discord.Interaction, user: discord.Member):
    server_config = get_server_config(interaction.guild.id)
    if user.id in server_config['blacklist_uids']:
        server_config['blacklist_uids'].remove(user.id)
        save_config()
        await interaction.response.send_message(f"User {user.mention} has been removed from the blacklist.", ephemeral=True)
    else:
        await interaction.response.send_message(f"User {user.mention} is not currently blacklisted.", ephemeral=True)
bot.tree.add_command(remove_blacklist_user)


# Command to check stock of .txt files in directories
@app_commands.command(name="stock", description="Check stock of .txt files in specified category")
@check_blacklist()
@check_category()
async def check_stock(interaction: discord.Interaction, category: str):
    server_config = get_server_config(interaction.guild.id)
    directories = server_config['directories']
    response = ""

    if category.lower() == "all":
        for key, directory in directories.items():
            if os.path.exists(directory):
                file_count = len([file for file in os.listdir(directory) if file.endswith('.txt')])
                response += f"{key.capitalize()}: {file_count} files\n"
            else:
                response += f"{key.capitalize()}: Directory not found\n"
    elif category.lower() in directories:
        directory = directories[category.lower()]
        if os.path.exists(directory):
            file_count = len([file for file in os.listdir(directory) if file.endswith('.txt')])
            response = f"{category.capitalize()}: {file_count} files"
        else:
            response = f"{category.capitalize()}: Directory not found"
    else:
        response = "Invalid category specified. Available options: all, netflix, spotify, crunchyroll, prime"

    await interaction.response.send_message(response, ephemeral=True)

bot.tree.add_command(check_stock)


# Command to send a predefined link with user ID
@app_commands.command(name="link", description="Send a predefined link with user ID")
@check_blacklist()
@check_category()
async def send_link(interaction: discord.Interaction):
    # Replace 'YOUR_LINK_HERE' with your actual link template
    link = f"https://nanolinks.in/discordCookie"
    userid = interaction.user.id
    await interaction.response.send_message(f"Here is your link: {link} and you user id : {userid}", ephemeral=True)

bot.tree.add_command(send_link)

# Command to check user points/status
@app.route('/status', methods=['GET'])
def check_status():
    user_id = request.args.get('userid')
    if not user_id:
        return jsonify({"error": "User ID is required."}), 400
    
    user = users_collection.find_one({"userid": user_id})
    if user:
        return jsonify({
            "userid": user_id,
            "points": user['points']
        })
    else:
        return jsonify({"error": "User not found."}), 404

bot.tree.add_command(check_status)
# Event listener for errors
@bot.event
async def on_ready():
    print("Bot is ready and connected")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

    try:
        command_count = len(bot.tree.get_commands())
        print(f"Bot loaded with {command_count} commands.")
    except Exception as e:
        print(f"Error counting loaded commands: {e}")

# Event listener for errors
@bot.event
async def on_error(event, *args, **kwargs):
    server_config = get_server_config(event.guild.id)
    log_channel = bot.get_channel(server_config['bot_log'])
    if log_channel:
        await log_channel.send(f"Error occurred in event {event}: {args[0]}")

# Run the bot
bot.run(TOKEN)

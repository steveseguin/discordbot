import discord
from discord.ext import commands
import requests
import sys
import json
import os
import csv

bot = commands.Bot(command_prefix='!')

global url, custom_commands
url = "https://raw.githubusercontent.com/steveseguin/discordbot/main/commands.json"

r = requests.get(url)
custom_commands = r.json()


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.event
async def on_message(message):
    global custom_commands
    found = False
    # Find if custom command exist in dictionary
    for key, value in custom_commands.items():
        # Added simple hardcoded prefix
        if message.content == '!' + key:
            found = True
            await message.channel.send(value)
    if not found:
        await bot.process_commands(message)

@bot.command()
async def add(ctx, command: str, *, reply: str):
    global custom_commands
    """Adds new command. e.g. ?add hello world, it will reply 'world' to command ?hello"""
    custom_commands[command] = reply
    print(command + " " +reply)
    await ctx.send('New command added.')
    with open('suggestions.csv','a') as f:
        writer = csv.writer(f)
        writer.writerow([command,reply])
@bot.command()
async def update(ctx):
    global url, custom_commands
    r = requests.get(url)
    custom_commands = r.json()
    await ctx.send('Updated commands.')

try:
    cfg_location = os.path.join(sys.path[0], 'discordbot.cfg')
    with open(cfg_location) as json_file:
        cfg = json.load(json_file)
        token = str(cfg["token"])
        print("Token loaded. Starting the Discord bot server..")
        bot.run(token)
except Exception as E:
    print("Failed to start Discord bot server.")
    print(E)

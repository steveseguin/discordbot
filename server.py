import discord
from discord.ext import commands
import requests
import sys
import json
import os
import csv
import datetime

bot = commands.Bot(command_prefix='!')

global url, custom_commands
url = "https://raw.githubusercontent.com/steveseguin/discordbot/main/commands.json"

r = requests.get(url)
custom_commands = r.json()
history = {}

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
    
    timestamp = datetime.datetime.now().timestamp()
    msg = message.content[:75] if len(message.content) > 75 else message.content
    if (not message.author.id in history) or (history[message.author.id]["timestamp"] + 30 < timestamp) or (history[message.author.id]["last_message"] != msg):
        history[message.author.id] = {}
        history[message.author.id]["last_message"] = msg
        history[message.author.id]["timestamp"] = timestamp
        history[message.author.id]["abuses"] = 0
        history[message.author.id]["messages"] = [message]
    else:
        history[message.author.id]["abuses"]+=1
        history[message.author.id]["timestamp"] = timestamp
        if history[message.author.id]["abuses"]>=2:
            await message.delete()
            listcopy = history[message.author.id]["messages"][:]
            history[message.author.id]["messages"] = []
            for msg in listcopy:
                await msg.delete()
            with open('spammers.csv','a') as f:
                writer = csv.writer(f)
                writer.writerow(message)
        else:
            history[message.author.id]["messages"].append(message)


    # Find if custom command exist in dictionary
    for key, value in custom_commands.items():
        # Added simple hardcoded prefix
        if '!' + key in message.content and message.author != bot.user:
            found = True
            if len(message.mentions) > 0:
                await message.delete()
                await message.channel.send("<@!{}> {value}".format(message.mentions[0].id, value=value))
            else:
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
@bot.command(aliases=['list'])
async def commands(ctx):
    global url, custom_commands
    commands = "List of available commands: \n"
    for key in custom_commands.keys():
        commands = commands + "!" + key + "\n"
    await ctx.send(commands)

try:
    # Load bot extensions
    for extension in os.listdir("cogs"):
            if extension.endswith('.py'):
                try:
                    bot.load_extension("cogs." + extension[:-3])
                except Exception as e:
                    print('Failed to load extension {}\n{}: {}'.format(extension, type(e).__name__, e))

    cfg_location = os.path.join(sys.path[0], 'discordbot.cfg')
    with open(cfg_location) as json_file:
        cfg = json.load(json_file)
        token = str(cfg["token"])
        print("Token loaded. Starting the Discord bot server..")
        bot.run(token)
except Exception as E:
    print("Failed to start Discord bot server.")
    print(E)

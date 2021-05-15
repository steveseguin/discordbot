import discord
from discord.ext import commands
import requests

bot = commands.Bot(command_prefix='!')

global url, custom_commands
url = "https://gist.githubusercontent.com/steveseguin/93d36729f5e685106d931abdb6cea9ab/raw"

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
async def add(ctx, command: str, reply: str):
    """Adds new command. e.g. ?add hello world, it will reply 'world' to command ?hello"""
    custom_commands[command] = reply
    print(command + " " +reply)
    await ctx.send('New command added.')
@bot.command()
async def update(ctx):
    global url
    r = requests.get(url)
    custom_commands = r.json()
    await ctx.send('Updated commands.')


bot.run('TOKEN_GOES_HERE')

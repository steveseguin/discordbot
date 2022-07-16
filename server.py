from ast import alias
from tkinter import HIDDEN
import discord
from discord.ext import commands
import asyncio
import aiohttp
import logging
import aiofiles
import sys
import json
import os
import csv
import datetime
import pathlib
from config import Config

# get local directory as path object
LOCALDIR = pathlib.Path(__file__).parent.resolve()

# setup logger
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)

# configure discord gateway intents
intents = discord.Intents.default()
intents.message_content = True
intents.typing = False

# create object instances
config = Config(file=LOCALDIR / "discordbot.cfg")
bot = commands.Bot(command_prefix="!", intents=intents)

# informational event when bot has finished logging in
@bot.event
async def on_ready():
    logging.info(f"We have logged in as {bot.user}")

@bot.event
async def on_message(message):
    logging.debug(message.content)
    if message.author == bot.user:
        return

    if message.content.startswith("$hello"):
        await message.channel.send("Hello World!")
    
    # await ctx.message.delete()
    await bot.process_commands(message)

@bot.command()
async def hello(ctx: commands.context):
    """Just a test command"""
    async with ctx.channel.typing():
        embed = discord.Embed(title="Embed Title", type="rich", color=discord.Color.random())
        embed.add_field(name="Fieldname 1", value=f"Fieldvalue 1\nColor: {embed.color}")
        await ctx.send(embed=embed)
        await ctx.message.delete()

@bot.command(hidden=True)
async def add(ctx: commands.context, command: str, *, reply: str):
    """Command to dynamically add a command to the bot. Should not be used."""
    # TODO: re-integrate add command, but still warn user to also create a PR for it and run reload after merge
    # for now just send a text message
    await ctx.send("For now please create a PR against the bot repo to add a command and run !update after merge")

@bot.command(hidden=True)
async def update(ctx):
    """Update the available commands"""
    await ctx.send("Reloading bot extensions")
    try:
        #await bot.reload_extension("cogs.docs")
        await bot.reload_extension("cogs.github")
    except Exception as E:
        await ctx.send("There was an error while reloading bot extensions:")
        await ctx.send(E)
    else:
        await ctx.send("Successfully reloaded bot extensions")

@bot.command(aliases=["list"])
async def commands(ctx):
    """Lit all availbale commands"""
    # "ipc" to get available commands from multiple extensions
    ghCommands = bot.get_cog("NinjaGH")
    gh = await ghCommands.getCommands()
    # or use
    logging.debug(bot.cogs.items)
    await ctx.message.delete()

async def main():
    try:
        await config.parse()
    except Exception as E:
        logging.fatal(E)
        sys.exit(1)
    
    logging.debug(f"Token {config.botToken} loaded. Loading extensions.")

    # statically load extensions for security reasons

    # docs search tool (currently broken)
    #await bot.load_extension("cogs.docs")

    # commands from github
    await bot.load_extension("cogs.github")

    logging.debug("Extensions loaded. Starting server")
    await bot.start(config.botToken)
    logging.info("Bot process exited. Closing program.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())



"""
general todo list:
- load commands file from github (hot reloadable)
- load commands from dynamic file (hot reloadable)
- command to add a new command to dynamic file and reload it
- maybe make embed generation into it's own class that inherits from Embed
- add docs search cog (and get it to work again)
- (OK) make bot delete the message that invoked it
- use embeds for responses where possible
- if user was pinged in command then ping user in response
- (OK?) make commands only work at start of message
- spammer detection with kick/ban
- reddit integration for new posts to reddit channel
"""
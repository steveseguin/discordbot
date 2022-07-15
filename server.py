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

LOCALDIR = pathlib.Path(__file__).parent.resolve()

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)

intents = discord.Intents.default()
intents.message_content = True
intents.typing = False

config = Config(file=LOCALDIR / "discordbot.cfg")
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.event
async def on_message(message):
    logging.debug(message.content)
    if message.author == bot.user:
        return

    if message.content.startswith("$hello"):
        await message.channel.send("Hello World!")
    
    await bot.process_commands(message)

@bot.command()
async def hello(ctx):
    """Just a test command"""
    async with ctx.channel.typing():
        embed = discord.Embed(title="Embed Title", type="rich", color=discord.Color.random())
        embed.add_field(name="Fieldname 1", value=f"Fieldvalue 1\nColor: {embed.color}")
        await ctx.send(embed=embed)

@bot.command(hidden=True)
async def add(ctx, command: str, *, reply: str):
    """Command to dynamically add a command to the bot. Should not be used."""
    # TODO: re-integrate add command, but still warn user to also create a PR for it and run reload after merge
    # for now just send a text message
    await ctx.send("For now please create a PR against the bot repo to add a command and run !update after merge")

async def main():
    try:
        await config.parse()
    except Exception as E:
        logging.fatal(E)
    
    logging.debug(f"Token {config.botToken} loaded. Loading extensions.")

    # statically load extensions for security reasons
    # this is the docs search tool (currently broken)
    #await bot.load_extension("cogs.docs")

    # this is the extension for the commands from github
    await bot.load_extension("cogs.github")

    logging.debug(f"Extensions loaded. Starting server")
    await bot.start(config.botToken)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())



"""
general todo list:
- load commands file from github (hot reloadable)
- load commands from dynamic file (hot reloadable)
- command to add a new command to dynamic file and reload it
- add docs search cog (and get it to work again)
- make bot delete the message that invoked it
- use embeds for responses where possible
- if user was pinged in command then ping user in response
- make commands only work at start of message
- spammer detection with kick/ban
"""
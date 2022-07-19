from ast import alias
from tkinter import HIDDEN
import discord
from discord.ext import commands
from discord.ext.commands import MissingPermissions, MissingRole, CommandNotFound
import traceback
import asyncio
import logging
import sys
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

mentions = discord.AllowedMentions(everyone=False)

# create object instances
config = Config(file=LOCALDIR / "discordbot.cfg")
bot = commands.Bot(command_prefix="!", intents=intents, allowed_mentions=mentions)

# informational event when bot has finished logging in
@bot.event
async def on_ready():
    logging.info(f"We have logged in as {bot.user}")

@bot.event
async def on_message(message):
    ctx = await bot.get_context(message)
    #logging.debug(ctx.message)

    if ctx.author == bot.user:
        # ignore messages by the bot itself
        return
    elif ctx.message.content.startswith("!"):
        # might be a command. pass it around to see if anyone wants to deal with it
        # TODO: better idea: register each command prefix with bot and then just sort them that way
        # for now this will do
        NinjaGH = bot.get_cog("NinjaGH")
        if await NinjaGH.process_command(ctx):
            return
    else:
        pass

    # otherwise look elsewhere for command
    await bot.process_commands(message)

# handle some errors. this works for extension commands too so no need to redefine in there
@bot.event
async def on_command_error(ctx, err):
    if isinstance(err, MissingPermissions) or isinstance(err, MissingRole):
        # silently ignore no-permissions errors
        logging.info(f"user '{ctx.author.name}' tried to run '{ctx.message.content}' without permissions")
    elif isinstance(err, CommandNotFound):
        logging.info(f"user '{ctx.author.name}' tried to run '{ctx.message.content}' which is unknown")
    else:
        raise err

@bot.command(hidden=True)
@commands.has_role("Moderator")
async def add(ctx: commands.context, command: str):
    """Command to dynamically add a command to the bot. Should not be used."""
    # TODO: re-integrate add command, but still warn user to also create a PR for it and run reload after merge
    # for now just send a text message
    await ctx.send("For now please create a PR against the bot repo to add a command and run !update after merge")

@bot.command(hidden=True)
@commands.has_role("Moderator")
async def update(ctx):
    """Update the available commands by reloading the bot extensions"""
    await ctx.send("Reloading bot extensions")
    try:
        #await bot.reload_extension("cogs.docs")
        await bot.reload_extension("cogs.github")
        #await bot.reload_extension("cogs.reddit")
    except Exception as E:
        await ctx.send("There was an error while reloading bot extensions:")
        await ctx.send(E)
    else:
        await ctx.send("Successfully reloaded bot extensions")

# TODO overwrite helpcommand class, there are docs for that
@bot.command(aliases=["list"])
async def commands(ctx):
    """List all availbale commands"""
    # "ipc" to get available commands from multiple extensions
    NinjaGH = bot.get_cog("NinjaGH")
    gh = await NinjaGH.get_commands()
    await ctx.message.delete()
    await ctx.send(str(gh))
    #logging.debug(bot.cogs.items)

async def main():
    try:
        await config.parse()
    except Exception as E:
        logging.fatal(E)
        sys.exit(1)
    
    logging.debug(f"Token {config.botToken} loaded. Loading extensions.")

    # statically load extensions for security reasons

    # docs search tool (currently broken, TODO)
    #await bot.load_extension("cogs.docs")

    # commands from github
    await bot.load_extension("cogs.github")

    # reddit events (TODO)
    #await bot.load_extension("cogs.reddit")

    logging.debug("Extensions loaded. Starting server")
    await bot.start(config.botToken)
    logging.info("Bot process exited. Closing program.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())


"""
general todo list:
- (OK) load commands file from github (hot reloadable)
- (OK) make content from github commands usable
- maybe make embed generation into it's own class that inherits from Embed
- load commands from dynamic file (hot reloadable)
- make content from dynamic file usable
- command to add a new command to dynamic file and reload it
- (OK) make bot delete the message that invoked it
- (OK) use embeds for responses where possible
- (OK) if user was pinged in command then ping user in response
- (OK) make commands only work at start of message
- spammer detection with kick/ban
- reddit integration for new posts to reddit channel (https://praw.readthedocs.io/en/stable/)
- add docs search cog (and get it to work again)
"""
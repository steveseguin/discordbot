import discord
import asyncio
import logging
import pathlib
from discord.ext import commands
from discord.ext.commands import MissingPermissions, MissingRole, CommandNotFound, MissingRequiredArgument
from config import Config

# get local directory as path object
LOCALDIR = pathlib.Path(__file__).parent.resolve()

# setup logger
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)

# configure discord gateway intents
intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
# configure allowed mentions
mentions = discord.AllowedMentions(everyone=False)

# create object instances
config = Config(file=LOCALDIR / "discordbot.cfg")

class NinjaBot(commands.Bot):
    def __init__(self, config, *args, **kwargs):
        self.config = config
        super().__init__(
            command_prefix=self.config.get("commandPrefix"),
            intents=intents,
            allowed_mentions=mentions,
            help_command=None
            )

    # informational event when bot has finished logging in
    async def on_ready(self):
        logging.info(f"We have logged in as {self.user}")

        # load all the extensions we want to use
        # statically defined for security reasons

        # internal bot commands (DONE)
        await self.load_extension("cogs.NinjaBotUtils")
        # spammer detection system
        #
        # the bot help command (DONE)
        await self.load_extension("cogs.NinjaBotHelp")
        # commands from github (DONE)
        await self.load_extension("cogs.NinjaGithub")
        # commands added through the bot (TODO)
        await self.load_extension("cogs.NinjaDynCmds")
        # docs search tool (currently broken, TODO)
        #await self.load_extension("cogs.NinjaDocs")
        # reddit events (TODO)
        await self.load_extension("cogs.NinjaReddit")

        # for funsies
        await self.change_presence(status=discord.Status.online, activity=discord.Game("helping hand"))


    async def on_message(self, message):
        ctx = await self.get_context(message)
        #logging.debug(ctx)

        if ctx.author == self.user:
            # ignore messages by the bot itself
            return
        elif ctx.message.content.startswith(self.config.get("commandPrefix")):
            # might be a command. pass it around to see if anyone wants to deal with it
            # TODO: better idea: register each command prefix with bot and then just sort them that way
            # for now this will do
            NinjaGithub = self.get_cog("NinjaGithub")
            if await NinjaGithub.process_command(ctx):
                return
        else:
            pass

        # otherwise look elsewhere for command
        logging.debug("Command not found by custom handlers, try processing native commands")
        await self.process_commands(message)
    
    # reload all extensions
    async def reloadExtensions(self, ctx):
        await ctx.send("Reloading bot extensions")
        try:
            for ext in list(self.extensions.keys()):
                logging.debug(f"Reloading extension {ext}")
                await self.reload_extension(ext)
        except Exception as E:
            await ctx.send("There was an error while reloading bot extensions:")
            await ctx.send(E)
        else:
            await ctx.send("Successfully reloaded bot extensions")

    # handle some errors. this works for extension commands too so no need to redefine in there
    async def on_command_error(self, ctx, err):
        if isinstance(err, MissingPermissions) or isinstance(err, MissingRole):
            # silently ignore no-permissions errors
            logging.info(f"user '{ctx.author.name}' tried to run '{ctx.message.content}' without permissions")
        elif isinstance(err, CommandNotFound):
            logging.info(f"user '{ctx.author.name}' tried to run '{ctx.message.content}' which is unknown/invalid")
        elif isinstance(err, MissingRequiredArgument):
            logging.info(f"user '{ctx.author.name}' tried to run '{ctx.message.content}' without providing all required arguments")
        else:
            raise err

async def main():
    try:
        await config.parse()
    except Exception as E:
        logging.error("Error while parsing the configuration file")
        logging.fatal(E)
        return
    
    logging.debug(f"Token {config.get('discordBotToken')} loaded. Loading bot and extensions.")

    nBot = NinjaBot(config)

    logging.debug("Extensions loaded. Starting server")
    try:
        await nBot.start(config.get("discordBotToken"))
    except KeyboardInterrupt:
        pass
    await nBot.close()
    logging.info("Bot process exited. Closing program.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

"""
general TODO list:
- (OK) load commands file from github (hot reloadable)
- (OK) make content from github commands usable
- (OK) make embed generation into it's own class that inherits from Embed
- (OK) make bot into it's own class
- (OK) make bot delete the message that invoked it
- (OK) use embeds for responses where possible
- (OK) if user was pinged in command then ping user in response
- (OK) make commands only work at start of message
- (OK) instead of mentioning a use in the bot reply, make a native reply to the last message from the pinged user
- (OK) if command is used in reply to another user, replace that reply with bot reply
- spammer detection with kick/ban (it's own cog)
- load commands from dynamic file (hot reloadable)
- make content from dynamic file usable
- command to add a new command to dynamic file and reload it
- (OK) reddit integration for new posts to reddit channel (https://praw.readthedocs.io/en/stable/)
- (Bonus) get docs search working again and line it up with other cogs
- (OK) add bot activity ("just helping out"?)
- add register and unregister method to main bot class (save first part of command and callback?)
- use teardown listener to run unregister and update to update (check if valid)
"""
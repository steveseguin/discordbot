import discord
import asyncio
import logging
import pathlib
import discord
import discord.ext.commands
import logging.handlers
from discord.ext import commands
from config import Config

# get local directory as path object
LOCALDIR = pathlib.Path(__file__).parent.resolve()

# setup logger
generalLogLevel = logging.DEBUG
formatter = logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{")

# rotating log file handler
rotateFileHnd = logging.handlers.RotatingFileHandler(
    filename="ninjaBot.log",
    encoding="utf-8",
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
rotateFileHnd.setLevel(generalLogLevel)
rotateFileHnd.setFormatter(formatter)

# cmd output
streamHnd = logging.StreamHandler()
streamHnd.setLevel(generalLogLevel)
streamHnd.setFormatter(formatter)

# discord logger
dcL = logging.getLogger("discord")
dcL.propagate = False
dcL.setLevel(generalLogLevel)
logging.getLogger("discord.http").setLevel(logging.INFO)
logging.getLogger("discord.gateway").setLevel(logging.INFO)
dcL.addHandler(rotateFileHnd)
dcL.addHandler(streamHnd)

# NinjaBot logger
nbL = logging.getLogger("NinjaBot")
nbL.propagate = False
nbL.setLevel(generalLogLevel)
nbL.addHandler(rotateFileHnd)
nbL.addHandler(streamHnd)

# disable voice client warning
discord.VoiceClient.warn_nacl = False

# configure discord gateway intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
# configure allowed mentions so bot can't ping @everyone
mentions = discord.AllowedMentions(everyone=False)

# create object instances
config = Config(file=LOCALDIR / "discordbot.cfg")

class NinjaBot(commands.Bot):
    def __init__(self, config, *args, **kwargs) -> None:
        self.config = config
        super().__init__(
            command_prefix=self.config.get("commandPrefix"),
            intents=intents,
            allowed_mentions=mentions,
            help_command=None,
            log_handler=None
        )

    # informational event when bot has finished logging in
    async def on_ready(self) -> None:
        nbL.info(f"Bot logged in as {self.user}")

        # load all the extensions we want to use
        # statically defined for security reasons

        # internal bot commands (DONE)
        await self.load_extension("cogs.NinjaBotUtils")
        # spammer detection system (DONE)
        await self.load_extension("cogs.NinjaAntiSpam")
        # the bot help command (DONE)
        await self.load_extension("cogs.NinjaBotHelp")
        # commands from github (DONE)
        await self.load_extension("cogs.NinjaGithub")
        # commands added through the bot (TODO)
        await self.load_extension("cogs.NinjaDynCmds")
        # reddit events (DONE)
        await self.load_extension("cogs.NinjaReddit")
        # docs search tool (currently broken, TODO)
        #await self.load_extension("cogs.NinjaDocs")

        # for funsies
        await self.change_presence(status=discord.Status.online, activity=discord.Game("helping hand"))


    async def on_message(self, message: discord.Message) -> None:
        ctx = await self.get_context(message)

        if ctx.author == self.user or ctx.author.bot:
            # ignore messages by the bot itself or other bots
            return
        elif ctx.message.content.startswith(self.config.get("commandPrefix")):
            # might be a command. pass it around to see if anyone wants to deal with it
            NinjaGithub = self.get_cog("NinjaGithub")
            if await NinjaGithub.process_command(ctx):
                return
            # otherwise look elsewhere for command
            nbL.debug("Command not found by custom handlers, try processing native commands")
            await self.process_commands(message)
    
    # reload all extensions
    async def reloadExtensions(self, ctx) -> None:
        await ctx.send("Reloading bot extensions")
        try:
            for ext in list(self.extensions.keys()):
                nbL.debug(f"Reloading extension {ext}")
                await self.reload_extension(ext)
        except Exception as E:
            await ctx.send("There was an error while reloading bot extensions:")
            await ctx.send(E)
        else:
            await ctx.send("Successfully reloaded bot extensions")

    # handle some errors. this works for extension commands too so no need to redefine in there
    async def on_command_error(self, ctx, err) -> None:
        nbL.debug(err)
        if isinstance(err, discord.ext.commands.MissingPermissions) or isinstance(err, discord.ext.commands.MissingRole):
            # silently ignore no-permissions errors
            nbL.info(f"user '{ctx.author.name}' tried to run '{ctx.message.content}' without permissions")
        elif isinstance(err, discord.ext.commands.CommandNotFound):
            nbL.info(f"user '{ctx.author.name}' tried to run '{ctx.message.content}' which is unknown/invalid")
        elif isinstance(err, discord.ext.commands.MissingRequiredArgument):
            nbL.info(f"user '{ctx.author.name}' tried to run '{ctx.message.content}' without providing all required arguments")
        elif isinstance(err, discord.ext.commands.NoPrivateMessage):
            nbL.info(f"user '{ctx.author.name}' tried to run '{ctx.message.content}' in a private message")
        else:
            nbL.error(err)
            raise err

async def main() -> None:
    try:
        await config.parse()
    except Exception as E:
        nbL.error("Error while parsing the configuration file")
        nbL.fatal(E)
        return
    
    nbL.debug(f"Token {config.get('discordBotToken')} loaded. Loading bot and extensions.")

    nBot = NinjaBot(config)

    nbL.debug("Extensions loaded. Starting server")
    try:
        await nBot.start(config.get("discordBotToken"))
    except KeyboardInterrupt:
        pass
    await nBot.close()
    nbL.info("Bot process exited. Closing program.")

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
- (OK) rework logging and add optional file logger
- (OK) spammer detection with kick/ban
- load commands from dynamic file (hot reloadable)
- make content from dynamic file usable
- command to add a new command to dynamic file and reload it
- (OK) reddit integration for new posts to reddit channel (https://praw.readthedocs.io/en/stable/)
- (Bonus) get docs search working again and line it up with other cogs
- (OK) add bot activity ("just helping out"?)
- (Bonus) add register and unregister method to main bot class (save first part of command and callback?)
- (Bonus) use teardown listener to run unregister and update to update (check if valid)
- (Bonus) improve spam detection by factoring in message posting speed
"""
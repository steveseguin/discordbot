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
generalLogLevel = logging.INFO
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
dcL.addHandler(rotateFileHnd)
dcL.addHandler(streamHnd)

logging.getLogger("discord.http").setLevel(logging.INFO)
logging.getLogger("discord.gateway").setLevel(logging.INFO)
logging.getLogger("discord.client").setLevel(logging.INFO)

# NinjaBot logger
nbL = logging.getLogger("NinjaBot")
nbL.propagate = False
nbL.setLevel(generalLogLevel)
nbL.addHandler(rotateFileHnd)
nbL.addHandler(streamHnd)
logger = nbL

# disable voice client warning
discord.VoiceClient.warn_nacl = False

# configure discord gateway intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
# configure allowed mentions so bot can't ping @everyone
mentions = discord.AllowedMentions(everyone=False)

# create config handler
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
        logger.info(f"Bot logged in as {self.user}")

        # load all the extensions we want to use
        # statically defined for security reasons

        # internal bot commands
        await self.load_extension("cogs.NinjaBotUtils")
        # spammer detection system
        await self.load_extension("cogs.NinjaAntiSpam")
        # the bot help command
        await self.load_extension("cogs.NinjaBotHelp")
        # commands from github
        await self.load_extension("cogs.NinjaGithub")
        # commands added through the bot
        await self.load_extension("cogs.NinjaDynCmds")
        # reddit events
        await self.load_extension("cogs.NinjaReddit")
        # youtube uploads
        await self.load_extension("cogs.NinjaYoutube")
        # updates.vdon.ninja page
        await self.load_extension("cogs.NinjaUpdates")
        # auto-thread manager
        await self.load_extension("cogs.NinjaThreadManager")

        # docs search tool (currently broken, TODO)
        #await self.load_extension("cogs.NinjaDocs")

        # takes care of pushing all application commands to discord
        guild = int(self.config.get("guild"))
        self.tree.copy_global_to(guild=discord.Object(id=guild))
        await self.tree.sync(guild=discord.Object(id=guild))

        # for funsies
        await self.change_presence(status=discord.Status.online, activity=discord.Game("helping hand"))


    async def on_message(self, message: discord.Message) -> None:
        ctx = await self.get_context(message)

        if (ctx.author == self.user \
            or ctx.author.bot \
            or str(ctx.channel.id) in self.config.get("autoThreadEnabledChannels")):
            # ignore messages by the bot itself or other bots or autoThread channels
            return
        elif ctx.message.content.startswith(self.config.get("commandPrefix")):
            # might be a command. pass it around to see if anyone wants to deal with it
            # in order: github -> dynamic command -> native command
            NinjaDynCmds = self.get_cog("NinjaDynCmds")
            if await NinjaDynCmds.process_command(ctx):
                return
            NinjaGithub = self.get_cog("NinjaGithub")
            if await NinjaGithub.process_command(ctx):
                return
            # otherwise look elsewhere for command
            logger.debug("Command not found by custom handlers, try processing native commands")
            await self.process_commands(message)
    
    # reload all extensions
    async def reloadExtensions(self, ctx) -> None:
        await ctx.send("Reloading bot extensions")
        try:
            for ext in list(self.extensions.keys()):
                if ext != "cogs.NinjaThreadManager":
                    logger.debug(f"Reloading extension {ext}")
                    await self.reload_extension(ext)
        except Exception as E:
            await ctx.send("There was an error while reloading bot extensions:")
            await ctx.send(E)
        else:
            await ctx.send("Successfully reloaded bot extensions")

    # handle some errors. this works for extension commands too so no need to redefine in there
    async def on_command_error(self, ctx, err) -> None:
        logger.debug(err)
        if isinstance(err, discord.ext.commands.MissingPermissions) \
            or isinstance(err, discord.ext.commands.MissingRole):
            # silently ignore no-permissions errors
            logger.info(f"user '{ctx.author.name}' tried to run '{ctx.message.content}' without permissions")
        elif isinstance(err, discord.ext.commands.CommandNotFound):
            logger.info(f"user '{ctx.author.name}' tried to run '{ctx.message.content}' which is unknown/invalid")
        elif isinstance(err, discord.ext.commands.MissingRequiredArgument):
            logger.info(f"user '{ctx.author.name}' tried to run '{ctx.message.content}' without providing all required arguments")
        elif isinstance(err, discord.ext.commands.NoPrivateMessage):
            logger.info(f"user '{ctx.author.name}' tried to run '{ctx.message.content}' in a private message")
        else:
            logger.error(err)
            raise err

async def main() -> None:
    logger.info("Starting up NinjaBot V2")
    try:
        await config.parse()
    except Exception as E:
        logger.error("Error while parsing the configuration file")
        logger.exception(E)
        return

    logger.info(f"Token loaded. Loading bot and extensions.")

    nBot = NinjaBot(config)

    logger.info("Extensions loaded. Starting server")
    try:
        await nBot.start(config.get("discordBotToken"))
    except KeyboardInterrupt:
        pass
    await nBot.close()
    logger.info("Bot process exited. Closing program.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

"""
general TODO list:
- (DONE) load commands file from github (hot reloadable)
- (DONE) make content from github commands usable
- (DONE) make embed generation into it's own class that inherits from Embed
- (DONE) make bot into it's own class
- (DONE) make bot delete the message that invDONEed it
- (DONE) use embeds for responses where possible
- (DONE) if user was pinged in command then ping user in response
- (DONE) make commands only work at start of message
- (DONE) instead of mentioning a use in the bot reply, make a native reply to the last message from the pinged user
- (DONE) if command is used in reply to another user, replace that reply with bot reply
- (DONE) rework logging and add optional file logger
- (DONE) spammer detection with kick/ban
- (DONE) load commands from dynamic file (hot reloadable)
- (DONE) make content from dynamic file usable
- (DONE) command to add a new command to dynamic file and reload it
- (DONE) reddit integration for new posts to reddit channel (https://praw.readthedocs.io/en/stable/)
- (DONE) add bot activity ("just helping out"?)
- (DONE) add update page logic
- (DONE) Watch message edits to update page logic
- (DONE) replace usernames and channelid's in updates message with their names
- (DONE) Add youtube integration for steve's channel
- (DONE) (NinjaThreadManager) replicate auto thread creation that is currently handled by the 3rd party bot (button for Thread.edit(archived=True, reason="Close Button"))
- (DONE) (NinjaThreadManager) add !login/!logout for a user to be auto-added (add_user) to a newly created thread (maybe buttons later)
- (Bonus) Improvement: convert discord formatting into html for update page (include images and user avatar)
- (Bonus) get docs search working again and line it up with other cogs
- (Bonus) Improvement: add register and unregister method to main bot class (save first part of command and callback?)
- (Bonus) Improvement: use cog_unload to run unregister and update to update (check if valid)
- (Bonus) Improvement: improve spam detection by factoring in message posting speed?
"""
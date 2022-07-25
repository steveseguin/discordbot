import logging
from discord.ext import commands
from commandReplyProcessor import commandProc

logger = logging.getLogger("NinjaBot." + __name__)

class NinjaDynCmds(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.isInternal = False
        self.commands = {"sampledynamiccommand": "and it's content"}

    async def process_command(self, ctx) -> bool:
        return await commandProc(self, ctx)

    @commands.command()
    @commands.has_role("Moderator")
    async def add(self, ctx: commands.context, command: str, reply: str, *args) -> None: # use kwargs instead for reply
        """Command to dynamically add a command to the bot. Should not be used."""
        logger.debug(command)
        logger.debug(reply)
        logger.debug(args)
        if args:
            await ctx.send("If you want to use spaces, please put the text in quotes")
        # TODO: re-integrate add command, but still warn user to also create a PR for it and run reload after merge
        # for now just send a text message
        await ctx.send("For now please create a PR against the bot repo to add a command and run !update after merge")

    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        return list(self.commands.keys())

async def setup(bot) -> None:
    logger.debug(f"Loading {__name__}")
    cogInstance = NinjaDynCmds(bot)
    await bot.add_cog(cogInstance)

async def teardown(bot) -> None:
    logger.debug(f"Shutting down {__name__}")
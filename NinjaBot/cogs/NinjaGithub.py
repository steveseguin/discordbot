import logging
import aiohttp
from discord.ext import commands, tasks
from commandReplyProcessor import commandProc

logger = logging.getLogger("NinjaBot." + __name__)

class NinjaGithub(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.isInternal = False
        self.githubUrl = self.bot.config.get("githubUrl")
        self.commands = {}
        self.regularUpdater.start()

    async def fetchCommands(self) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.githubUrl) as resp:
                    self.commands = await resp.json(content_type="text/plain")
        except Exception as E:
            raise E
        else:
            logger.debug("Sucessfully loaded github data for commands:")
            #logger.debug(json.dumps(self.commands, indent=2, sort_keys=True))

    async def process_command(self, ctx) -> bool:
        return await commandProc(self, ctx)

    @tasks.loop(hours=1)
    async def regularUpdater(self) -> None:
        logger.debug("Regular github update started")
        await self.fetchCommands()

    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        return list(self.commands.keys())

async def setup(bot) -> None:
    logger.debug(f"Loading {__name__}")
    cogInstance = NinjaGithub(bot)
    await bot.add_cog(cogInstance)

async def teardown(bot) -> None:
    logger.debug(f"Shutting down {__name__}")
import logging
import discord
import aiohttp
from discord.ext import commands

logger = logging.getLogger("NinjaBot." + __name__)

class NinjaUpdates(commands.Cog):
    def __init__(self, bot) -> None:
        logger.debug(f"Loading {self.__class__.__name__}")
        self.bot = bot
        self.isInternal = True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # This is a message to the update channel by steve
        if (message.channel.id == 701232125831151697 and message.author.id==227248835251011585):
            # todo more stuff here
            # fetch gist(fallback {}), update it, push it back
            if self.bot.config.has("githubKey") and self.bot.config.has("githubGistId"):
                logger.debug("github gist config is here")

    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        """This cog doesn't have commands"""
        return []

    async def cog_unload(self) -> None:
        logger.debug(f"Shutting down {self.__class__.__name__}")

async def setup(bot) -> None:
    await bot.add_cog(NinjaUpdates(bot))
import logging
from discord.ext import commands

class NinjaBotUtils(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.isInternal = True

    @commands.command(hidden=True)
    @commands.has_role("Moderator")
    async def update(self, ctx) -> None:
        """Update the available commands by reloading the bot extensions"""
        await self.bot.reloadExtensions(ctx)

    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        return [c.name for c in self.get_commands()]

async def setup(bot) -> None:
    logging.debug("Loading NinjaBotUtils")
    cogInstance = NinjaBotUtils(bot)
    await bot.add_cog(cogInstance)

async def teardown(bot) -> None:
    logging.debug("Shutting down NinjaBotUtils")
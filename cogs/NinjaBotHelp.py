import logging
from discord.ext import commands

class NinjaBotHelp(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        logging.debug("NinjaBotHelp class created")

    @commands.command(aliases=["list"])
    async def commands(self, ctx) -> None:
        """List all availbale commands"""
        # "ipc" to get available commands from multiple extensions
        NinjaGH = self.get_cog("NinjaGH")
        gh = await NinjaGH.get_commands()
        await ctx.message.delete()
        await ctx.send(str(gh))
        #logging.debug(bot.cogs.items)

    async def get_commands(self) -> list:
        """Return the available commands as a list"""
        return []

async def setup(bot) -> None:
    logging.debug("Loading NinjaBotHelp")
    cogInstance = NinjaBotHelp(bot)
    await bot.add_cog(cogInstance)

async def teardown(bot) -> None:
    logging.debug("Shutting down NinjaBotHelp")
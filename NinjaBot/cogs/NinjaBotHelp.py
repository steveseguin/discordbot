import logging
import embedBuilder
from discord.ext import commands
from discord import DMChannel

logger = logging.getLogger("NinjaBot." + __name__)

class NinjaBotHelp(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.isInternal = True

    @commands.command(aliases=["list"])
    async def commands(self, ctx) -> None:
        """List all available commands"""
        allCommands = []
        for cog in self.bot.cogs:
            cogInstance = self.bot.get_cog(cog)
            if not cogInstance.isInternal:
                allCommands.extend(await cogInstance.getCommands())
        await ctx.send(embed=embedBuilder.ninjaEmbed(
            title="Available commands:",
            description="".join(["!" + c + "\n" for c in sorted(allCommands)])
            ))
        if not isinstance(ctx.channel, DMChannel):
            await ctx.message.delete()

    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        return [c.name for c in self.get_commands()]

async def setup(bot) -> None:
    logger.debug(f"Loading {__name__}")
    cogInstance = NinjaBotHelp(bot)
    await bot.add_cog(cogInstance)

async def teardown(bot) -> None:
    logger.debug(f"Shutting down {__name__}")
import logging
import embedBuilder
from discord.ext import commands

class NinjaBotHelp(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.isInternal = True

    @commands.command()
    async def commands(self, ctx, *args) -> None:
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
        await ctx.message.delete()

    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        return [c.name for c in self.get_commands()]

async def setup(bot) -> None:
    logging.debug("Loading NinjaBotHelp")
    cogInstance = NinjaBotHelp(bot)
    await bot.add_cog(cogInstance)

async def teardown(bot) -> None:
    logging.debug("Shutting down NinjaBotHelp")
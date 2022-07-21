import logging
from discord.ext import commands, tasks
from discord import utils
from embedBuilder import createEmbed

class NinjaBotUtils(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        logging.debug("NinjaBotUtils class created")

    @commands.command(hidden=True)
    @commands.has_role("Moderator")
    async def update(self, ctx) -> None:
        """Update the available commands by reloading the bot extensions"""
        await ctx.send("Reloading bot extensions")
        try:
            for ext in self.bot.extensions.keys():
                logging.debug(f"Reloading extension {ext}")
                await self.bot.reload_extension(ext)
        except Exception as E:
            await ctx.send("There was an error while reloading bot extensions:")
            await ctx.send(E)
        else:
            await ctx.send("Successfully reloaded bot extensions")

    async def get_commands(self) -> list:
        """Return the available commands as a list"""
        return []

async def setup(bot) -> None:
    logging.debug("Loading NinjaBotUtils")
    cogInstance = NinjaBotUtils(bot)
    await bot.add_cog(cogInstance)

async def teardown(bot) -> None:
    logging.debug("Shutting down NinjaBotUtils")
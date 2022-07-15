import logging
from discord.ext import commands

class NinjaGH(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def ninja(self, ctx):
        await ctx.send("Someone called me?")

async def setup(bot):
    logging.debug("Loading NinjaGH")
    await bot.add_cog(NinjaGH(bot))
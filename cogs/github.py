import logging
from discord.ext import commands

class NinjaGH(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logging.debug("NinjaGH class created")
    
    @commands.Cog.listener()
    async def on_message(self, ctx: commands.context):
        logging.debug("on message in cog run")
    
    @commands.command()
    async def ninja(self, ctx: commands.context):
        await ctx.send("Someone called me?")
        await ctx.message.delete()
    
    async def getCommands(self):
        """Return the available commands as a list"""
        return ["commands", "list"]

async def setup(bot):
    logging.debug("Loading NinjaGH")
    await bot.add_cog(NinjaGH(bot))

async def teardown(bot):
    logging.debug("Shutting down NinjaGH")
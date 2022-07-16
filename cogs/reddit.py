import logging
import praw
from discord.ext import commands, tasks

class RedditInterface(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logging.debug("RedditInterface class created")
    
    @commands.Cog.listener()
    async def on_message(self, ctx: commands.context):
        logging.debug("on message in cog run")
    
    @commands.command()
    async def invalid(self, ctx: commands.context):
        await ctx.send("Someone called me?")
        await ctx.message.delete()
    
    async def getCommands(self):
        """Return the available commands as a list"""
        return ["commands", "list"]

    @tasks.loop(seconds=5.0)
    async def printer(self):
        logging.debug("Task ran")
    
    @printer.before_loop
    async def before_printer(self):
        logging.debug('waiting...')
        await self.bot.wait_until_ready()

async def setup(bot):
    logging.debug("Loading RedditInterface")
    await bot.add_cog(RedditInterface(bot))

async def teardown(bot):
    logging.debug("Shutting down RedditInterface")
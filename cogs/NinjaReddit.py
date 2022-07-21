import logging
from typing import List
import praw
from discord.ext import commands, tasks

class NinjaReddit(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        logging.debug("RedditInterface class created")

    async def setup_hook(self) -> None:
        # start the task to run in the background
        self.redditChecker.start()
    
    @tasks.loop(seconds=5.0)
    async def redditChecker(self) -> None:
        logging.debug("Task ran")
    
    @redditChecker.before_loop
    async def before_redditChecker(self) -> None:
        logging.debug('waiting...')
        await self.bot.wait_until_ready()
    
    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        """This cog doesn't have commands"""
        return []


async def setup(bot) -> None:
    logging.debug("Loading NinjaReddit")
    await bot.add_cog(NinjaReddit(bot))

async def teardown(bot) -> None:
    logging.debug("Shutting down NinjaReddit")
import logging
import aiohttp
from discord.ext import commands, tasks

class NinjaGH(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.githubUrl = "https://raw.githubusercontent.com/steveseguin/discordbot/main/commands.json"
        self.commands = None
        logging.debug("NinjaGH class created")
    
    async def fetchCommands(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.githubUrl) as resp:
                    self.commands = await resp.json(content_type="text/plain")
        except Exception as E:
            raise Exception(E)
        else:
            logging.debug("Sucessfully loaded github data for commands:")
            logging.debug(self.commands)

        # subclass command und add_command?
        # https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#discord.ext.commands.Bot.add_command
    
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
    cogInstance = NinjaGH(bot)
    await bot.add_cog(cogInstance)
    await cogInstance.fetchCommands()

async def teardown(bot):
    logging.debug("Shutting down NinjaGH")
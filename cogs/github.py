from ast import alias
import logging
import aiohttp
import json
from discord.ext import commands, tasks
from embedBuilder import createEmbed

class NinjaGH(commands.Cog):
    def __init__(self, bot) -> None:
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
            raise E
        else:
            logging.debug("Sucessfully loaded github data for commands:")
            logging.debug(json.dumps(self.commands, indent=4, sort_keys=True))

    async def process_command(self, ctx):
        try:
            command = ctx.message.content[1:].split()[0]
            if command in self.commands.keys():
                embd = createEmbed(name=command, text=self.commands[command], formatName=True)
                await ctx.send(ctx.message.mentions[0].mention if ctx.message.mentions else None, embed=embd)
                await ctx.message.delete()
                return True
        except:
            pass
        return False
    
    @tasks.loop(seconds=3600)
    async def regularUpdater(self):
        self.fetchCommands()

    async def get_commands(self):
        """Return the available commands as a list"""
        return list(self.commands.keys())

async def setup(bot):
    logging.debug("Loading NinjaGH")
    cogInstance = NinjaGH(bot)
    await bot.add_cog(cogInstance)
    await cogInstance.fetchCommands()

async def teardown(bot):
    logging.debug("Shutting down NinjaGH")
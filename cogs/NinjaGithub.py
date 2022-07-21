import logging
import aiohttp
import json
from discord.ext import commands, tasks
from discord import utils
from embedBuilder import createEmbed

class NinjaGithub(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.githubUrl = "https://raw.githubusercontent.com/steveseguin/discordbot/main/commands.json"
        self.commands = None
        self.regularUpdater.start()
        logging.debug("NinjaGithub class created")
    
    async def fetchCommands(self) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.githubUrl) as resp:
                    self.commands = await resp.json(content_type="text/plain")
        except Exception as E:
            raise E
        else:
            logging.debug("Sucessfully loaded github data for commands:")
            logging.debug(json.dumps(self.commands, indent=2, sort_keys=True))

    async def process_command(self, ctx) -> bool:
        try:
            command = ctx.message.content[1:].split()[0]
            if command in self.commands.keys():
                embed = createEmbed(name=command, text=self.commands[command], formatName=True)
                if ctx.message.mentions and ctx.author != ctx.message.mentions[0]:
                    # if there is a mention, reply to users last message instead of pinging
                    # 2nd part of the if statement is for then a user is trying to mention themselfs
                    lastMessage = await utils.get(ctx.channel.history(limit=10), author=ctx.message.mentions[0])
                    await lastMessage.reply(embed=embed)
                elif ctx.message.reference:
                    # like above, but reply was used instead of mention
                    initialMessage = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    await initialMessage.reply(embed=embed)
                else:
                    # every other case
                    await ctx.send(None, embed=embed)
                await ctx.message.delete()
                return True
        except:
            pass
        return False
    
    @tasks.loop(hours=1)
    async def regularUpdater(self) -> None:
        logging.debug("Regular github update started")
        await self.fetchCommands()

    async def get_commands(self) -> list:
        """Return the available commands as a list"""
        return list(self.commands.keys())

async def setup(bot) -> None:
    logging.debug("Loading NinjaGithub")
    cogInstance = NinjaGithub(bot)
    await bot.add_cog(cogInstance)
    #await cogInstance.fetchCommands()

async def teardown(bot) -> None:
    logging.debug("Shutting down NinjaGithub")
import logging
from discord.ext import commands
from discord import utils
from embedBuilder import createEmbed

class NinjaDynCmds(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        logging.debug("NinjaDynCmds class created")

    async def process_command(self, ctx) -> bool:
        try:
            command = ctx.message.content[1:].split()[0]
            if command in self.commands.keys():
                embed = createEmbed(name=command, text=self.commands[command], formatName=True)
                if ctx.message.mentions:
                    # if there is a mention, reply to users last message instead of pinging
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
    
    @commands.command()
    @commands.has_role("Moderator")
    async def add(self, ctx: commands.context, command: str, reply: str) -> None: # use kwargs instead for reply
        """Command to dynamically add a command to the bot. Should not be used."""
        logging.debug(command)
        logging.debug(reply)
        # TODO: re-integrate add command, but still warn user to also create a PR for it and run reload after merge
        # for now just send a text message
        await ctx.send("For now please create a PR against the bot repo to add a command and run !update after merge")

    async def get_commands(self) -> list:
        """Return the available commands as a list"""
        return []

async def setup(bot) -> None:
    logging.debug("Loading NinjaDynCmds")
    cogInstance = NinjaDynCmds(bot)
    await bot.add_cog(cogInstance)

async def teardown(bot) -> None:
    logging.debug("Shutting down NinjaDynCmds")
import embedBuilder
from discord import utils
from discord import DMChannel

async def commandProc(self, ctx):
    try:
        command = ctx.message.content[1:].split()[0].lower()
        if command in self.commands.keys():
            embed = embedBuilder.ninjaEmbed(description=self.commands[command])
            if ctx.message.mentions and ctx.author != ctx.message.mentions[0] and ctx.message.mentions[0] != self.bot.user:
                # if there is a mention, reply to users last message instead of pinging
                # 2nd part of the if statement is for then a user is trying to mention themselfs
                # 3rd part stops the bot from replying to itself
                lastMessage = await utils.get(ctx.channel.history(limit=10), author=ctx.message.mentions[0])
                lastMessage and await lastMessage.reply(embed=embed)
            elif ctx.message.reference:
                # like above, but reply was used instead of mention
                initialMessage = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                not initialMessage.author.bot and await initialMessage.reply(embed=embed)
            else:
                # every other case
                await ctx.send(embed=embed)
            not isinstance(ctx.channel, DMChannel) and await ctx.message.delete()
            return True
    except Exception as E:
        raise E
    return False
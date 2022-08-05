import logging
import discord
import embedBuilder
from asyncio import sleep
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from strsimpy import SIFT4

logger = logging.getLogger("NinjaBot." + __name__)

class NinjaAntiSpam(commands.Cog):
    def __init__(self, bot) -> None:
        logger.debug(f"Loading {self.__class__.__name__}")
        self.bot = bot
        self.isInternal = True
        self.s = SIFT4()
        self.h = {}
        self.historyCleanupJob.start()
        self.botlogCleanupJob.start()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """For anti-spam purposes we don't care if it's a command or normal message"""
        if message.author == self.bot.user \
            or message.author.bot \
            or isinstance(message.channel, discord.DMChannel) \
            or (hasattr(message.author, "roles") and discord.utils.get(message.author.roles, name="Moderator")) \
            or not (message.type == discord.MessageType.default \
            or message.type == discord.MessageType.reply):
            # ignore messages by bots, moderators and system messages
            return
        #logger.debug(message)

        if message.content:
            msg = message.content
        elif message.attachments:
            msg = message.attachments[0].filename
        else:
            msg = ""

        now = datetime.now().timestamp()
        uid = message.author.id

        if not uid in self.h:
            # user is not currently in our message buffer, add them
            # also can't judge in here if it's spam or not
            self.h[uid] = dict()
            self.h[uid]["lm"] = msg
            self.h[uid]["lmts"] = now
            self.h[uid]["abuse"] = 0
            self.h[uid]["msgs"] = [[message.id, message.channel.id]]
            logger.debug(f"built new user object {self.h[uid]}")
        else:
            # user has posted their 2nd+ message
            self.h[uid]["msgs"].append([message.id, message.channel.id])

            # calculate message distance using sift4
            dist = self.s.distance(self.h[uid]["lm"], msg)
            logger.debug(f"sift4 distance: {dist}")
            if dist <= 4:
                # messages are too close
                self.h[uid]["abuse"] += 1
                logger.debug(f"user {self.h[uid]} increased abuse count")
            if self.h[uid]["abuse"] >= 3: # it is spam
                logger.debug("starting spam cleanup")
                await self.cleanupMember(message.author)
            else: # it is not spam (at least yet)
                self.h[uid]["lmts"] = now
                self.h[uid]["lm"] = msg

    # function to kick a member and cleanup their messages
    async def cleanupMember(self, author) -> None:
        botlogCh = self.bot.get_channel(int(self.bot.config.get("botlogChannel")))
        try:
            await author.kick(reason="Spam")
            logger.warn(f"{author} has been kicked for spam")
            await botlogCh.send(f"{author} has been kicked for spam. Spam Report:")
        except Exception as E:
            logger.warn(f"Could not kick user {str(author)}")

        while True:
            try:
                if author.id in self.h:
                    userData = self.h[author.id].copy()
                    del self.h[author.id]
                    await self.deleteOldMessages(userData["msgs"], botlogCh)
                    logger.debug(userData)
                    await sleep(2)
                else:
                    break
            except Exception as E:
                logger.exception(E)
                break
        logger.debug("done doing spam cleanup stuff")

    async def deleteOldMessages(self, msgs, botlogCh) -> None:
        blMsg = ""
        for mid, chid in msgs:
            try:
                spamChannel = self.bot.get_channel(chid)
                msg = await spamChannel.fetch_message(mid)
                line = f"{msg.channel.name}: {msg.content}"
                logger.warn(line)
                await msg.delete()
                if len(blMsg) + len(line) > 4090:
                    await self.sendReport(botlogCh, blMsg)
                    blMsg = line
                else:
                    blMsg += line + "\n"
            except Exception as E:
                logger.exception(E)
        await self.sendReport(botlogCh, blMsg)
    
    async def sendReport(self, ch, msg) -> None:
        await ch.send(embed=embedBuilder.ninjaEmbed(description=msg[:4096].rstrip()))

    # use task to cleanup old user objects
    @tasks.loop(minutes=2)
    async def historyCleanupJob(self) -> None:
        logger.debug("Running antispam cleanup job")
        logger.debug(f"self.h before cleanup: {self.h}")
        now = datetime.now().timestamp()
        for uid, d in self.h.copy().items():
            if now - d["lmts"] > 60:
                del self.h[uid]
        logger.debug(f"self.h after cleanup: {self.h}")

    @historyCleanupJob.before_loop
    async def before_historyCleanupJob(self) -> None:
        await self.bot.wait_until_ready()

    # cleanup old message in botlog channel
    @tasks.loop(hours=12)
    async def botlogCleanupJob(self) -> None:
        logger.debug("Running botlog channel cleanup job")
        botlogChannel = self.bot.get_channel(int(self.bot.config.get("botlogChannel")))
        async for message in botlogChannel.history(limit=300, before=datetime.today()-timedelta(days=30)):
            if message.author == self.bot.user and "has been kicked" not in message.content:
                await message.delete()

    @botlogCleanupJob.before_loop
    async def before_botlogCleanupJob(self) -> None:
        await self.bot.wait_until_ready()

    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        """This cog doesn't have commands"""
        return []

    async def cog_unload(self) -> None:
        logger.debug(f"Shutting down {self.__class__.__name__}")
        self.historyCleanupJob.cancel()
        self.botlogCleanupJob.cancel()

async def setup(bot) -> None:
    await bot.add_cog(NinjaAntiSpam(bot))
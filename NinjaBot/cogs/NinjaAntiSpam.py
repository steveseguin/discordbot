import logging
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from strsimpy import SIFT4

logger = logging.getLogger("NinjaBot." + __name__)

class NinjaAntiSpam(commands.Cog):
    def __init__(self, bot) -> None:
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
            or discord.utils.get(message.author.roles, name="Moderator") \
            or not (message.type == discord.MessageType.default \
            or message.type == discord.MessageType.reply):
            # ignore messages by the bot itself, moderators and system messages
            return
        #logger.debug(message)
        #logger.debug(message.content)

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
            rawDist = self.s.distance(self.h[uid]["lm"], msg)
            dist = self.inv(rawDist)
            logger.debug(f"sift4 distance: raw: {rawDist} | inv: {dist}")
            if dist >= 10:
                # messages are too close
                self.h[uid]["abuse"] += 1
            if self.h[uid]["abuse"] >= 2: # it is spam
                await self.cleanupMember(message.author)
            else: # it is not spam (yet)
                self.h[uid]["lmts"] = now
                self.h[uid]["lm"] = msg

    def inv(self, val) -> int:
        return 15-val if val <= 15 else 0

    # function to kick a member and cleanup their messages
    async def cleanupMember(self, author) -> None:
        await author.kick(reason="Spam")

        botlogCh = self.bot.get_channel(int(self.bot.config.get("botlogChannel")))
        logger.warn(f"{author} has been kicked for spam")
        await botlogCh.send(f"{author} has been kicked for spam")
        await botlogCh.send(f"{author} Spam Report:")

        uid = author.id
        for mid, chid in self.h[uid]["msgs"]:
            spamChannel = self.bot.get_channel(chid)
            msg = await spamChannel.fetch_message(mid)
            logger.warn(f"{msg.channel.name}: {msg.content}")
            await botlogCh.send(f"{msg.channel.name}: {msg.content}")
            await msg.delete()

        # delete user from message buffer
        del self.h[uid]

    # use task to cleanup old user objects
    @tasks.loop(seconds=120)
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

async def setup(bot) -> None:
    logger.debug(f"Loading {__name__}")
    cogInstance = NinjaAntiSpam(bot)
    await bot.add_cog(cogInstance)

async def teardown(bot) -> None:
    logger.debug(f"Shutting down {__name__}")
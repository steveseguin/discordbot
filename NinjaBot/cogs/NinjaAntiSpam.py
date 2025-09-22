import logging
import discord
import utils.embedBuilder as embedBuilder
import re
from asyncio import sleep
from discord.ext import commands, tasks
from discord import DMChannel
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
        # self.botlogCleanupJob.start() disabled for now

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """For anti-spam purposes we don't care if it's a command or normal message"""
        if message.author == self.bot.user \
            or message.author.bot \
            or isinstance(message.channel, discord.DMChannel) \
            or (hasattr(message.author, "roles") and discord.utils.get(getattr(message.author, "roles"), name="Moderator")) \
            or not (message.type == discord.MessageType.default \
            or message.type == discord.MessageType.reply):
            # ignore messages by bots, moderators and system messages
            return
    
        # use message text itself or the filename as the message
        if message.content:
            msg = message.content
        elif message.attachments:
            msg = message.attachments[0].filename
        else:
            msg = ""
    
        now = datetime.now().timestamp()
        uid = message.author.id
        abuseInc = 0
        current_channel = message.channel.id
    
        if not uid in self.h:
            # user is not currently in our message buffer, add them
            # also can't judge in here if it's spam or not
            self.h[uid] = dict()
            self.h[uid]["lm"] = msg
            self.h[uid]["lmts"] = now
            self.h[uid]["abuse"] = 0
            self.h[uid]["msgs"] = [[message.id, message.channel.id]]
            self.h[uid]["channels"] = [current_channel]  # Track channels
            logger.debug(f"built new user {str(uid)}/{str(message.author)} object {self.h[uid]}")
        else:
            # user has posted their 2nd+ message
            self.h[uid]["msgs"].append([message.id, message.channel.id])
            
            # Add current channel to user's channel list if not already present
            if current_channel not in self.h[uid]["channels"]:
                self.h[uid]["channels"].append(current_channel)
    
            # calculate message distance using sift4
            dist = self.s.distance(self.h[uid]["lm"], msg)
            logger.debug(f"sift4 distance: {dist}")
            
            # Only increment abuse if posting in DIFFERENT channels
            if len(self.h[uid]["channels"]) > 1:
                if dist == 0:
                    # messages are way too close
                    abuseInc = 1.5
                elif dist == 1:
                    # messages are too close
                    abuseInc = 1
            
            if self.h[uid]["abuse"] < 3: # it is not spam (at least yet)
                self.h[uid]["lmts"] = now
                self.h[uid]["lm"] = msg

        # filter discord invite links no matter what the sift4 distance is
        if len(re.findall(r"(?:https?://)?(www\.)?(?:discord(?:app)?\.(?:gg|io|me|li|com))/(?!channels/)\S{,20}", message.content)):
            logger.info("Discord invite link found, deleting message")
            abuseInc = 1.5 # increase the abuse count (more then for a normal message)
            self.h[uid]["msgs"].pop() # remove last saved message since we already delete them here
            if not isinstance(message.channel, DMChannel):
                await message.delete()

            botmsg = await message.channel.send(f"Hey there {message.author.mention}, any discord (invite) links are not allowed here! Repeated posts may lead to moderation actions!")
            await sleep(4)
            if not isinstance(botmsg.channel, DMChannel):
                await botmsg.delete()

        # find stream keys in messages and delete them for safetly
        # right now we have youtube and twitch
        if len(re.findall(r"(?:live_\d{8}_[a-zA-Z0-9]{32})|(?:[a-z0-9]{4}-){4}[a-z0-9]{4}", message.content)):
            logger.info("Streamkey was found in message, deleting for safety")
            if not isinstance(message.channel, DMChannel):
                await message.delete()

            botmsg = await message.channel.send(f"Hey there {message.author.mention}, there was a stream key found in your last message. "
                                                "For your safety the message was deleted. You can post your message again without doxing yourself ;)")
            await sleep(12)
            if not isinstance(botmsg.channel, DMChannel):
                await botmsg.delete()

        self.h[uid]["abuse"] += abuseInc
        if abuseInc > 0: 
            logger.debug(f"user {self.h[uid]} increased abuse count by {abuseInc} to {self.h[uid]['abuse']}")
        if self.h[uid]["abuse"] >= 3: # too much spam
            logger.info("starting spam cleanup")
            await self.cleanupMember(message.author)

    # function to (kick a member and) cleanup their messages
    async def cleanupMember(self, author, kick=True) -> None:
        botlogCh = self.bot.get_channel(int(self.bot.config.get("botlogChannel")))

        if kick:
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
                    if userData["msgs"]:
                        await self.deleteOldMessages(userData["msgs"], botlogCh)
                    elif userData["lm"]:
                        # if we don't have message history (aka there is nothing to cleanup), only post the last message we saved
                        await self.sendReport(botlogCh, userData["lm"])
                    else:
                        await self.sendReport(botlogCh, "No History available")
                    logger.debug(userData)
                    await sleep(2)
                else:
                    break
            except Exception as E:
                logger.exception(E)
                break
        logger.debug("cleanupMember() done")

    async def deleteOldMessages(self, msgs, botlogCh) -> None:
        blMsg = line = ""
        for mid, chid in msgs:
            try:
                spamChannel = self.bot.get_channel(chid)
                msg = await spamChannel.fetch_message(mid)
                # text message beats attachments
                if msg.attachments:
                    line = f"{msg.channel.name}: {msg.attachments[0].filename} <{msg.attachments[0].url}>"
                if msg.content:
                    line = f"{msg.channel.name}: {msg.content}"
                logger.warning(line)
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
        logger.debug("Running antispam history-cleanup job")
        logger.debug(f"self.h before history-cleanup: {self.h}")
        now = datetime.now().timestamp()
        for uid, d in self.h.copy().items():
            if now - d["lmts"] > 60:
                del self.h[uid]
        logger.debug(f"self.h after history-cleanup: {self.h}")

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

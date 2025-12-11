import logging
import asyncio
import functools
import googleapiclient.discovery
from discord.ext import commands, tasks
from asyncio import sleep

logger = logging.getLogger("NinjaBot." + __name__)

class NinjaYoutube(commands.Cog):
    def __init__(self, bot) -> None:
        logger.debug(f"Loading {self.__class__.__name__}")
        self.bot = bot
        self.isInternal = True
        self.youtube = googleapiclient.discovery.build("youtube", "v3", developerKey = self.bot.config.get("youtubeApiKey"))
        self.youtubeChecker.start()

    @tasks.loop(hours=1)
    async def youtubeChecker(self) -> None:
        logger.debug("Running youtube checker")

        try:
            request = self.youtube.search().list(
                part="id,snippet",
                channelId=self.bot.config.get("youtubeChannelId"),
                maxResults=6,
                order="date",
                safeSearch="none",
                type="video"
            )
            # Run blocking API call in executor to avoid freezing the bot
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, request.execute)

            if response and response["kind"] == "youtube#searchListResponse" and "items" in response and response["items"]:
                postedVideos = self.bot.config.get("youtubePostedVideo") or []
                toPostVideos = []
                logger.debug(f"Posted videos so far: '{postedVideos}'")
                logger.debug(response["items"])
                for video in response["items"]:
                    if video["kind"] != "youtube#searchResult" and video["id"]["kind"] != "youtube#video": continue
                    if video["id"]["videoId"] in postedVideos: continue
                    if not video["snippet"]["description"]: continue
                    if not video["snippet"]["title"]: continue
                    #if "#VDO.Ninja" not in video["snippet"]["description"]: continue
                    if "#Shorts" in video["snippet"]["title"]: continue                   
                    # since video was not yet posted(otherwise we would not reach here), add to posting queue
                    logger.info(video)
                    toPostVideos.append(video)
        except Exception as E:
            logger.debug("Error while polling youtube videos")
            raise E
        else:
            # if we got result, reverse order otherwise just return because there is nothing to do
            if toPostVideos:
                toPostVideos.reverse()
            else:
                return

            # post all open videos
            logger.debug(toPostVideos)
            try:
                youtubeChannel = self.bot.get_channel(int(self.bot.config.get("youtubeDiscordChannel")))
                for video in toPostVideos:
                    await youtubeChannel.send(f"New video by Steve! Check it out: https://www.youtube.com/watch?v={video['id']['videoId']}")
                    postedVideos.append(video["id"]["videoId"])
                    await sleep(2) # do some reate limiting ourselfs
            except Exception as E:
                logger.exception(E)
            finally:
                # update list of video id's we already posted so far
                await self.bot.config.set("youtubePostedVideo", postedVideos)

    @youtubeChecker.before_loop
    async def before_youtubeChecker(self) -> None:
        await self.bot.wait_until_ready()

    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        """This cog doesn't have commands"""
        return []

    async def cog_unload(self) -> None:
        logger.debug(f"Shutting down {self.__class__.__name__}")
        self.youtubeChecker.cancel()

async def setup(bot) -> None:
    await bot.add_cog(NinjaYoutube(bot))
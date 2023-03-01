import logging
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
                maxResults=5,
                order="date",
                safeSearch="none",
                type="video"
            )
            response = request.execute()

            if response and response["kind"] == "youtube#searchListResponse" and "items" in response and response["items"]:
                lastVideo = self.bot.config.get("youtubeLastVideo") or ""
                logger.debug(f"Current lastVideo is: '{lastVideo}'")
                toPostVideos = []
                logger.debug(response["items"])
                for video in response["items"]:
                    if video["kind"] != "youtube#searchResult" and video["id"]["kind"] != "youtube#video": continue
                    if not video["snippet"]["description"]: continue
                    if not video["snippet"]["title"]: continue
                    #if "#VDO.Ninja" not in video["snippet"]["description"]: continue
                    if "#Shorts" in video["snippet"]["title"]: continue
                    logger.info(video)
                    if video["id"]["videoId"] == lastVideo: break
                    # since video was not yet posted, add to posting queue
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
            newLastSubmission = lastVideo
            try:
                youtubeChannel = self.bot.get_channel(int(self.bot.config.get("youtubeDiscordChannel")))
                for video in toPostVideos:
                    await youtubeChannel.send(f"New video by Steve! Check it out: https://www.youtube.com/watch?v={video['id']['videoId']}")
                    newLastSubmission = video["id"]["videoId"]
                    await sleep(2) # do some reate limiting ourselfs
            except Exception as E:
                logger.exception(E)
            finally:
                # update id of last video to what was the sucessfully sent last
                await self.bot.config.set("youtubeLastVideo", newLastSubmission)

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
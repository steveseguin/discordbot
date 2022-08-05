from hashlib import new
import logging
import discord
import aiohttp
import json
from discord.ext import commands
from datetime import datetime

logger = logging.getLogger("NinjaBot." + __name__)

class NinjaUpdates(commands.Cog):
    def __init__(self, bot) -> None:
        logger.debug(f"Loading {self.__class__.__name__}")
        self.bot = bot
        self.isInternal = True
        self.http = aiohttp.ClientSession()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Check if config options are there and are the expected valuess
        if (self.bot.config.has("updatesChannel") \
            and self.bot.config.has("allowedUpdateUsers") \
            and message.channel.id == int(self.bot.config.get("updatesChannel")) \
            and str(message.author.id) in self.bot.config.get("allowedUpdateUsers")) \
            and self.bot.config.has("githubApiKey") \
            and self.bot.config.has("githubGistId"):

            ghHeaders = {
                "Accept": "application/vnd.github+json",
                "Authorization": f"token {self.bot.config.get('githubApiKey')}"
            }

            try:
                # get latest gist raw url from github api
                async with self.http.get(f"https://api.github.com/gists/{self.bot.config.get('githubGistId')}", headers=ghHeaders) as resp:
                    gistApiData = await resp.json(content_type="application/json")
                    if resp.status == 200 and "files" in gistApiData and "updates.json" in gistApiData["files"]:
                        raw_url = gistApiData["files"]["updates.json"]["raw_url"]
                    else:
                        return

                # fetch gist data
                async with self.http.get(raw_url) as resp:
                    logger.debug(await resp.text())
                    gistContent = await resp.json(content_type=None)
                    # we rely on the file beeing there and having content
                    # this is to not clear it in case download fails
                    if not gistContent: return

                # order gistContent by timestamp
                gistContent = sorted(gistContent, key=lambda k: k["timestamp"])
                logger.debug(f"current gist length: {len(gistContent)}")

                # create new entry and add to gistContent
                newEntry = dict()
                newEntry["content"] = message.content
                newEntry["timestamp"] = datetime.now().timestamp()
                newEntry["name"] = message.author.nick or message.author.name
                newEntry["msgid"] = str(message.id)
                gistContent.append(newEntry)

                # only keep the last 40 entrys in list
                gistContent = gistContent[-40:]

                # send updated data to github
                patchData = {"files": {
                    "updates.json": {
                        "content": json.dumps(gistContent, indent=4)
                    }
                }}

                #logger.debug(json.dumps(patchData, indent=4))
                # send updated data to github
                async with self.http.patch(f"https://api.github.com/gists/{self.bot.config.get('githubGistId')}", json=patchData, headers=ghHeaders) as gistApiResp:
                    if gistApiResp.status == 200:
                        logger.info("Successfully updated gist data")
                    else:
                        logger.warn("Error while updating gist data")
                        logger.warn(await gistApiResp.text())
                
            except Exception as E:
                raise E

    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        """This cog doesn't have commands"""
        return []

    async def cog_unload(self) -> None:
        logger.debug(f"Shutting down {self.__class__.__name__}")
        await self.http.close()

async def setup(bot) -> None:
    await bot.add_cog(NinjaUpdates(bot))
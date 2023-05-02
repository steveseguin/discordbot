import logging
import re
import discord
import aiohttp
import json
from functools import partial
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
        # Check if config options are there and are the expected values
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
                    if resp.status != 200: return
                    gistContent = await resp.json(content_type=None)
                    # we rely on the file beeing there and having content
                    # this is to not clear it in case download fails
                    if not gistContent: return

                # Search for existing message id in the current gist content
                prevMessage = next(filter(lambda m: "msgid" in m and m["msgid"] == str(message.id), gistContent), False)
                if prevMessage:
                    # This is an update to an existing message
                    messagePos = gistContent.index(prevMessage)
                    oldEntry = gistContent[messagePos]
                    oldEntry["content"] = await self.formatMessageContent(message)
                    oldEntry["attachments"] = self.getAttachments(message)
                    gistContent[messagePos] = oldEntry
                else:
                    # create new entry and add to gistContent
                    newEntry = dict()
                    newEntry["content"] = await self.formatMessageContent(message)
                    newEntry["timestamp"] = datetime.now().timestamp()
                    newEntry["name"] = message.author.nick or message.author.name
                    newEntry["msgid"] = str(message.id)
                    newEntry["avatar"] = str(message.author.display_avatar.url or "")
                    newEntry["attachments"] = self.getAttachments(message)
                    gistContent.append(newEntry)

                # order gistContent by timestamp
                gistContent = sorted(gistContent, key=lambda k: k["timestamp"])
                # only keep the last 60 entrys in list
                gistContent = gistContent[-70:]

                # create data structure for github api
                patchData = {
                    "files": {
                        "updates.json": {
                            "content": json.dumps(gistContent, indent=4)
                        }
                    }
                }

                #logger.debug(json.dumps(gistContent, indent=4))
                # send updated data to github
                async with self.http.patch(f"https://api.github.com/gists/{self.bot.config.get('githubGistId')}", json=patchData, headers=ghHeaders) as gistApiResp:
                    if gistApiResp.status == 200:
                        logger.info("Successfully updated gist data")
                    else:
                        logger.error("Error while updating gist data")
                        logger.error(await gistApiResp.text())
            except Exception as E:
                raise E
    
    @commands.Cog.listener()
    async def on_raw_message_edit(self, partialMessage) -> None:
        if partialMessage.channel_id != int(self.bot.config.get("updatesChannel")): return # Ignore everything not from the update channel
        channel = self.bot.get_channel(partialMessage.channel_id)
        message = await channel.fetch_message(partialMessage.message_id)
        await self.on_message(message)

    async def formatMessageContent(self, message: discord.Message) -> str:
        content = message.content
        content = re.sub(r"<#(\d+)>", partial(self.replacer, message=message, what="channel"), content, flags=re.I)
        content = re.sub(r"<@(\d+)>", partial(self.replacer, message=message, what="user"), content, flags=re.I)
        return content

    def replacer(self, matchobj, message, what):
        if what == "channel":
            channel = next(filter(lambda c: str(c.id) == matchobj.group(1), message.channel_mentions), None)
            if channel:
                return "#" + channel.name
        elif what == "user":
            user = next(filter(lambda c: str(c.id) == matchobj.group(1), message.mentions), None)
            if user:
                return "@" + user.name
        return ""

    def getAttachments(self, message):
        if not message.attachments: return []
        return [{"mime": m.content_type or "", "url": m.url or "", "desc": m.description or None} for m in message.attachments]

    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        """This cog doesn't have commands"""
        return []

    async def cog_unload(self) -> None:
        logger.debug(f"Shutting down {self.__class__.__name__}")
        await self.http.close()

async def setup(bot) -> None:
    await bot.add_cog(NinjaUpdates(bot))
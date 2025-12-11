import logging
import asyncpraw
import utils.embedBuilder as embedBuilder
import re
from datetime import datetime, timezone, timedelta
from discord.ext import commands, tasks
from discord import Colour
from asyncio import sleep

logger = logging.getLogger("NinjaBot." + __name__)

class NinjaReddit(commands.Cog):
    def __init__(self, bot) -> None:
        logger.debug(f"Loading {self.__class__.__name__}")
        self.bot = bot
        self.isInternal = True
        self.Reddit = asyncpraw.Reddit(
            client_id=self.bot.config.get("redditClientId"),
            client_secret=self.bot.config.get("redditClientSecret"),
            user_agent=f"linux:ninja.vdo.discordbot{'.dev' if self.bot.config.get('isDev') else ''}:v0.4 (by /u/lebaston100)"
        )
        self.redditChecker.start()

    @tasks.loop(minutes=5)
    async def redditChecker(self) -> None:
        logger.debug("Running reddit checker")
        try:
            postedSubmissions = self.bot.config.get("redditPostedSubmissions") or []
            logger.debug(f"Posted submissions so far: '{postedSubmissions}'")
            toPostSubmissions = []
            # get subreddit and submissions
            ninjaSubreddit = await self.Reddit.subreddit("VDONinja")
            async for submission in ninjaSubreddit.new(limit=10):
                if submission.id in postedSubmissions: continue
                # Skip posts older than 3 days (safety net if tracking list is lost)
                post_age = datetime.now(timezone.utc) - datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                if post_age > timedelta(days=3):
                    logger.debug(f"Skipping old Reddit post: {submission.title} ({post_age.days} days old)")
                    continue
                # since post was not yet posted, add to posting queue
                toPostSubmissions.append(submission)
        except Exception as E:
            logger.debug("Error while polling reddit submissions")
            logger.exception(E)
            return
        else:
            # if we got result, reverse order otherwise just return because there is nothing to do
            if toPostSubmissions:
                toPostSubmissions.reverse()
            else:
                return

            # post all open submissions
            logger.debug(toPostSubmissions)
            try:
                redditChannel = self.bot.get_channel(int(self.bot.config.get("redditChannel")))
                for submission in toPostSubmissions:
                    await redditChannel.send(embed=self._formatSubmission(submission))
                    postedSubmissions.append(submission.id)
                    await sleep(2) # do some reate limiting ourselfs
            except Exception as E:
                logger.exception(E)
            finally:
                # update id of last post to what was the sucessfully sent last
                await self.bot.config.set("redditPostedSubmissions", postedSubmissions)

    def _formatSubmission(self, s) -> embedBuilder.ninjaEmbed:
        e = embedBuilder.ninjaEmbed()
        e.title = s.title if s.title else "no title"
        e.title = e.title[:98] + ".." if len(e.title) > 98 else e.title[:100]
        e.url = f"https://reddit.com{s.permalink}"
        e.color = Colour.orange()
        if not s.is_self and "https://i.redd.it" in s.url:
            e.set_thumbnail(url=s.url)
        author = "[deleted]"
        if s.author:
            author = s.author.name[:256]
        e.add_field(name=author, value=self._formatSubmissionText(s))
        return e

    def _formatSubmissionText(self, s) -> str:
        if s.is_self:
            charLimit = 220
            strippedNewlines = re.sub(r"\n{2,}", "\n", s.selftext) # remove newlines if more then one newline
            # Make sure to not cut off links
            splitText = re.split(r"(\[[^\]]*\]\([^\)]+\))", strippedNewlines) # regex to match link markup
            if len(splitText) > 1:
                text = ""
                for id, tp in enumerate(splitText):
                    tpIsLink = bool(re.search(r"(\[[^\]]*\]\([^\)]+\))", tp)) # find out if the current "line" is a link
                    if tpIsLink:
                        linkTextLength = len(re.findall(r"(\[.+\])", tp)[0]) - 3 # get length of link text
                        if len(text) + linkTextLength > charLimit:
                            # never cut off link text
                            break
                        text += tp
                    else:
                        # if new length hits char limit, truncate
                        if len(text) + len(tp) > charLimit:
                            if id == 0:
                                text += tp[:charLimit-3] + "..."
                            else:
                                text += "..."
                            break
                        else:
                            text += tp
            else:
                text = strippedNewlines[:charLimit-3] + "..."
        else:
            text = s.url
        return text[:1024] # limit again just for safety

    @redditChecker.before_loop
    async def before_redditChecker(self) -> None:
        await self.bot.wait_until_ready()
    
    async def getCommands(self) -> list:
        """Return the available commands as a list"""
        """This cog doesn't have commands"""
        return []

    async def cog_unload(self) -> None:
        logger.debug(f"Shutting down {self.__class__.__name__}")
        self.redditChecker.cancel()

async def setup(bot) -> None:
    await bot.add_cog(NinjaReddit(bot))
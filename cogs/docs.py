import discord
from discord.ext import commands
from bs4 import BeautifulSoup
import requests
import urllib.parse
import re


class Docs(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['d'], pass_context=True)
    async def docs(self, ctx, query: str):
        s = requests.Session()
        search_url = "https://www.google.com/search?q=site%3Adocs.obs.ninja+" + \
            urllib.parse.quote_plus(str(query))
        headers = {
            "referer": "referer: https://www.google.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36"
        }
        # Bypass Google's Cookie consent modal
        s.post(search_url, headers=headers)
        response = s.get(search_url, headers=headers)

        soup = BeautifulSoup(response.text, 'html.parser')

        links = soup.find(id="search").find_all(
            'a', attrs={'href': re.compile("^https://docs.obs.ninja")})

        if len(links) > 0:
            message = links[0].find("h3").text
            message = message + ": " + links[0].get('href')
            await ctx.send(message)


def setup(bot):
    bot.add_cog(Docs(bot))

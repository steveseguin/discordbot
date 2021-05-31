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

        if(len(ctx.message.mentions) > 0):
            query = re.sub(r'(@\S*)', '', str(query))
            search_url = "https://www.google.com/search?q=site%3Adocs.obs.ninja+" + \
                urllib.parse.quote_plus(query)
        else:
            search_url = "https://www.google.com/search?q=site%3Adocs.obs.ninja+" + \
                urllib.parse.quote_plus(str(query))
        headers = {
            "referer": "referer: https://www.google.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36"
        }

        print(f"Searching for {query}")

        # Bypass Google's Cookie consent modal
        s.post(search_url, headers=headers)
        response = s.get(search_url, headers=headers)

        soup = BeautifulSoup(response.text, 'html.parser')

        links = soup.find(id="search").find_all(
            'a', attrs={'href': re.compile("^https://docs.obs.ninja")})

        if len(links) > 0:
            # Theres google results for that query, lets post them  

            message = links[0].find("h3").text
            message = message + ": " + "<" + links[0].get('href') + ">"

            if len(ctx.message.mentions) > 0:
                # Someone got mentioned. Delete the original message
                # and @mention that user instead
                await ctx.message.delete()
                await ctx.message.channel.send("<@!{}> {value}".format(ctx.message.mentions[0].id, value=message))
            else:
                # There's no mentions in the trigger message
                await ctx.message.channel.send(message)

def setup(bot):
    bot.add_cog(Docs(bot))

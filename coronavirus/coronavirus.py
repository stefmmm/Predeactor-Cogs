import discord

import aiohttp
from redbot.core import commands


class Coronavirus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def coronavirusstats(self, ctx):

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://coronavirus-tracker-api.herokuapp.com/all"
            ) as resp:
                data = await resp.json(content_type=None)

        confirmed = data["latest"]["confirmed"]
        recovered = data["latest"]["recovered"]
        deaths = data["latest"]["deaths"]
        cases = confirmed - recovered - deaths

        await ctx.send(
            "**Coronavirus Stats**\n\nTotal infected: {}\nTotal recovered: {}\nTotal death: {}\n\nActual existing cases: {}".format(
                confirmed, recovered, deaths, cases
            )
        )

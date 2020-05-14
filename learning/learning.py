import discord

import asyncio

from redbot.core import commands, Config
from .lessons import *

class Learning(commands.Cog):
    """This cog is made for learning the Python basics and how to make your own cog on Red."""
    def __init__(self, bot):
        self.bot = bot
        self.data = Config.get_conf(self, identifier=495954054)

        self.data.register_user(
            lvl1=True,
            lvl2=False
        )

        super().__init__()

    @commands.group(name="learningpython")
    async def lpy(self, ctx: commands.GuildContext):
        """Here, you will learn the Python basics."""
        pass

    @lpy.command(name="references")
    async def ref(self, ctx: commands.Context):
        """Show you some useful links to know Python."""
        refs_list = ref()
        for data in refs_list:
            if type(data) is int:
                await asyncio.sleep(data)
            else:
                embed = discord.Embed(title="References", color=await self.bot.get_embed_colour(ctx), description=data)
                await ctx.send(embed=embed)


    @lpy.command(name="level1")
    async def lv1(self, ctx: commands.Context):
        """Start the level 1.
        
        Let's learn how to install Python and run it."""
        datas_list = lvl1()
        for data in datas_list:
            if type(data) is int:
                await asyncio.sleep(data)
            else:
                embed = discord.Embed(title="Installing and launching Python", color=await self.bot.get_embed_colour(ctx), description=data)
                await ctx.send(embed=embed)
        await self.data.user(ctx.author).lvl2.set(True)

    @lpy.command(name="level2")
    async def lv2(self, ctx: commands.Context):
        """Start the level 2.
        
        Let's learn how to use variables."""
        if await self.data.user(ctx.author).lvl2() is False:
            await ctx.send("Uh oh, seem you didn't even completed the level 1. I won't let you learn variables if you don't know how to launch Python.")
            return
        datas_list = lvl2()
        for data in datas_list:
            if type(data) is int:
                await asyncio.sleep(data)
            else:
                embed = discord.Embed(title="Variables", color=await self.bot.get_embed_colour(ctx), description=data)
                await ctx.send(embed=embed)
        #await self.data.user(ctx.author).lvl3.set(True) 
    
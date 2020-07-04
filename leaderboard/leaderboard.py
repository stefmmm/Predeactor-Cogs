import math
import operator
import time

import discord

from redbot.core import Config, checks, commands
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box, pagify


class LeaderBoard(commands.Cog):
    """
    Leaderboard, using a point system.
    For everyone who use the bot constantly.
    """

    __author__ = ["Predeactor"]
    __version__ = "Beta 0.7"

    def __init__(self, bot):
        self.bot = bot
        self.data = Config.get_conf(self, identifier=82466655781)
        self.data.register_user(points=0, mention=True)

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad!"""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nAuthor: {', '.join(self.__author__)}\nCog Version: {self.__version__}"

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 21600, commands.BucketType.user)
    async def rep(self, ctx: commands.Context, *, user: discord.User):
        """Give a reputation point to another user!"""
        if user.bot:
            await ctx.send(
                "We are the robots. Robot can't receive reputation points"
                " because they already are too popular!"
            )
            ctx.command.reset_cooldown(ctx)
            return
        if user == ctx.author:
            await ctx.send(
                "Uhm, I don't think I can allow you to give you reputation"
                " points to yourself... :)"
            )
            ctx.command.reset_cooldown(ctx)
            return
        await self._give_rep(ctx, user)

    @commands.group()
    async def repset(self, ctx: commands.GuildContext):
        """Settings for reputation."""
        pass

    @repset.command()
    async def mention(self, ctx: commands.Context, mention: bool):
        """Choose if I mention you when someone give you a reputation point.

        For mention, option are True or False.
        """
        await self.data.user(ctx.author).mention.set(mention)
        await ctx.send("Mention setting set to `{bool}`".format(bool=mention))

    async def _give_rep(self, ctx, user):
        user_points = await self.data.user(user).points()
        await self.data.user(user).points.set(user_points + 1)

        await ctx.send(
            "**{receiver} received a reputation point from {author}!\nYou now"
            " have {reps} reputation point{plurial}.**".format(
                receiver=await self._user_mention(user),
                author=ctx.author,
                reps=user_points + 1,
                plurial="s" if (user_points + 1) > 1 else "",
            )
        )

    async def _user_mention(self, user):
        if await self.data.user(user).mention():
            return user.mention
        return user

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def repboard(self, ctx, page_list: int = 1):
        users = []
        title = "Global Rep Leaderboard for {}\n".format(self.bot.user.name)
        all_users = await self.data.all_users()
        if str(all_users) == "{}":
            await ctx.send("The leaderboard is empty... Nobody's popular ¯\_(ツ)_/¯")
            return
        for user_id in all_users:
            user_name = await self._get_user(user_id)
            users.append((user_name, all_users[user_id]["points"]))
            if ctx.author.id == user_id:
                user_stat = all_users[user_id]["points"]

        board_type = "Rep"
        icon_url = self.bot.user.avatar_url
        sorted_list = sorted(users, key=operator.itemgetter(1), reverse=True)
        rank = 1
        for allusers in sorted_list:
            if ctx.author.name == allusers[0]:
                author_rank = rank
                break
            rank += 1
        footer_text = "Your Rank: {}                      {}: {}".format(
            author_rank, board_type, user_stat
        )

        # multiple page support
        page = 1
        per_page = 15
        pages = math.ceil(len(sorted_list) / per_page)
        if page_list >= 1 and page_list <= pages:
            page = page_list
        else:
            await ctx.send(
                "**Please enter a valid page number! (1 - {})**".format(str(pages))
            )
            return

        msg = ""
        msg += "Rank     Name                   (Page {}/{})     \n\n".format(
            page, pages
        )
        rank = 1 + per_page * (page - 1)
        start_index = per_page * page - per_page
        end_index = per_page * page

        default_label = "  "
        special_labels = ["♔", "♕", "♖", "♗", "♘", "♙"]

        async for single_user in AsyncIter(sorted_list[start_index:end_index]):
            if rank - 1 < len(special_labels):
                label = special_labels[rank - 1]
            else:
                label = default_label

            msg += "{:<2}{:<2}{:<2} # {:<15}".format(
                rank, label, "➤", await self._truncate_text(single_user[0], 15)
            )
            msg += "{:>5}{:<2}{:<2}{:<5}\n".format(
                " ", " ", " ", " {}: ".format(board_type) + str(single_user[1])
            )
            rank += 1
        msg += "--------------------------------------------            \n"
        msg += "{}".format(footer_text)

        em = discord.Embed(description="", colour=await self.bot.get_embed_colour(ctx))
        em.set_author(name=title, icon_url=icon_url)
        em.description = box(msg)

        await ctx.send(embed=em)

    async def _truncate_text(self, text, max_length):
        if len(text) > max_length:
            return text[: max_length - 1] + "…"
        return text

    async def _get_user(self, user_id: int):
        user = self.bot.get_user(user_id)
        if user is None:  # User not found
            try:
                user = self.bot.fetch_user(user_id)
            except (discord.NotFound, discord.HTTPException):
                return "Unknow User"
        return user.name
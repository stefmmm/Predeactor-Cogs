import discord
import asyncio

from pytimeparse import parse as time_parser
from datetime import datetime, timedelta

from redbot.core import commands, Config, checks
from redbot.core.utils.predicates import MessagePredicate
import redbot.core.utils.chat_formatting as chat_formatter


class CustomCooldown(commands.Cog):
    """A cog to display stats of messages in a chat"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=231120028796)
        self.config.register_guild(
            cooldown_channels={}, cooldown_categories={}, send_dm=False
        )
        self.date_format = "%d-%m-%Y:%H-%M-%S"

    async def handle_channel_cooldown(self, message, cooldown_channels, send_dm):
        now = datetime.now()
        channel = message.channel
        user = message.author
        channel_data = cooldown_channels[str(message.channel.id)]
        if str(user.id) not in channel_data["users_on_cooldown"]:
            channel_data["users_on_cooldown"][str(message.author.id)] = now.strftime(
                self.date_format
            )
            cooldown_channels[str(message.channel.id)] = channel_data
            await self.config.guild(message.guild).cooldown_channels.set(
                cooldown_channels
            )
        else:
            last_message = channel_data["users_on_cooldown"][str(message.author.id)]
            last_message_date = datetime.strptime(last_message, self.date_format)
            total_seconds = (now - last_message_date).total_seconds()
            if total_seconds <= channel_data["cooldown_time"]:
                try:
                    await message.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
                if send_dm:
                    try:
                        s = channel_data["cooldown_time"] - total_seconds
                        remaining_time = chat_formatter.humanize_timedelta(seconds=s)
                        await user.send(
                            f"Slow down! You'll be able to post again in {channel.mention} in {remaining_time}."
                        )
                    except discord.Forbidden:
                        pass
            else:
                channel_data["users_on_cooldown"][
                    str(message.author.id)
                ] = now.strftime(self.date_format)
                cooldown_channels[str(message.channel.id)] = channel_data
                await self.config.guild(message.guild).cooldown_channels.set(
                    cooldown_channels
                )

    async def handle_category_cooldown(self, message, cooldown_categories, send_dm):
        now = datetime.now()
        channel = message.channel
        user = message.author
        category_data = cooldown_categories.get(str(channel.category.id), None)
        if not category_data:
            return
        category = channel.category
        if str(user.id) not in category_data["users_on_cooldown"]:
            category_data["users_on_cooldown"][str(user.id)] = now.strftime(
                self.date_format
            )
            cooldown_categories[str(category.id)] = category_data
            await self.config.guild(message.guild).cooldown_categories.set(
                cooldown_categories
            )
        else:
            last_message = category_data["users_on_cooldown"][str(user.id)]
            last_message_date = datetime.strptime(last_message, self.date_format)
            total_seconds = (now - last_message_date).total_seconds()
            if total_seconds <= category_data["cooldown_time"]:
                try:
                    await message.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
                if send_dm:
                    try:
                        s = category_data["cooldown_time"] - total_seconds
                        remaining_time = chat_formatter.humanize_timedelta(seconds=s)
                        await user.send(
                            f"Slow down! You'll be able to post again in {channel.mention} in {remaining_time}. Please note that this channel shares a rate limit with it's parent channel category."
                        )
                    except discord.Forbidden:
                        pass
            else:
                category_data["users_on_cooldown"][str(user.id)] = now.strftime(
                    self.date_format
                )
                cooldown_categories[str(channel.id)] = category_data
                await self.config.guild(message.guild).cooldown_categories.set(
                    cooldown_categories
                )

    @commands.group()
    @commands.guild_only()
    @checks.mod()
    async def slow(self, ctx):
        """
        Cooldown a category or a channel
        """
        pass

    @slow.command()
    @commands.is_owner()
    async def reset(self, ctx):
        """
        Resets all guild data.
        """
        await self.config.clear_all_guilds()
        await ctx.send("Guild data reset.")

    @slow.command()
    async def category(self, ctx, category: discord.CategoryChannel, time: str):
        """
        Cooldown a category
        """
        cooldown_time = time_parser(time)
        if cooldown_time is None:
            return await ctx.send("Please enter a valid time.")
        cooldown_categories = await self.config.guild(ctx.guild).cooldown_categories()
        if str(category.id) in cooldown_categories:
            await ctx.send(
                "The specified category is already on cooldown do you want to edit it's time ? [yes/no]"
            )
            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await ctx.bot.wait_for("message", check=pred, timeout=30)
            except asyncio.TimeoutError:
                return await ctx.send("Timouted...cancelling.")
            if pred.result is True:
                if cooldown_time == 0:
                    del cooldown_categories[str(category.id)]
                    await self.config.guild(ctx.guild).cooldown_categories.set(
                        cooldown_categories
                    )
                    return await ctx.send(
                        f"The cooldown for {category.name} has been removed."
                    )
                else:
                    category_data = cooldown_categories[str(category.id)]
                    category_data["channels"] = [
                        channel.id for channel in category.channels
                    ]
                    category_data["cooldown_time"] = cooldown_time
                    category_data["users_on_cooldown"] = {}
                cooldown_categories[str(category.id)] = category_data
                await self.config.guild(ctx.guild).cooldown_categories.set(
                    cooldown_categories
                )
                await ctx.send(
                    f"{category.name}'s channels are now set at 1 message every {time}"
                )
        else:
            if cooldown_time == 0:
                return await ctx.send("The cooldown time cannot be 0")
            cooldown_categories[str(category.id)] = {
                "cooldown_time": cooldown_time,
                "users_on_cooldown": {},
                "channels": [channel.id for channel in category.channels],
            }
            await self.config.guild(ctx.guild).cooldown_categories.set(
                cooldown_categories
            )
            await ctx.send(
                f"{category.name}'s channels are now set at 1 message every {time}"
            )

    @slow.command()
    async def channel(self, ctx, channel: discord.TextChannel, time: str):
        """
        Cooldown a channel
        """
        cooldown_time = time_parser(time)
        if cooldown_time is None:
            return await ctx.send("Please enter a valid time.")
        cooldown_channels = await self.config.guild(ctx.guild).cooldown_channels()
        if str(channel.id) in cooldown_channels:
            await ctx.send(
                "The specified channel is already on cooldown do you want to edit it's time ? [yes/no]"
            )
            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await ctx.bot.wait_for("message", check=pred, timeout=30)
            except asyncio.TimeoutError:
                return await ctx.send("Timouted...cancelling.")
            if pred.result is True:
                if cooldown_time == 0:
                    del cooldown_channels[str(channel.id)]
                    await self.config.guild(ctx.guild).cooldown_channels.set(
                        cooldown_channels
                    )
                    return await ctx.send(
                        f"The cooldown for {channel.mention} has been removed."
                    )
                else:
                    cooldown_channels[str(channel.id)] = {
                        "cooldown_time": cooldown_time,
                        "users_on_cooldown": {},
                    }
                await self.config.guild(ctx.guild).cooldown_channels.set(
                    cooldown_channels
                )
                await ctx.send(
                    f"{channel.mention} is now set at 1 message every {time}"
                )
            else:
                return await ctx.send(
                    f"No changes were made to {channel.mention} cooldown settings."
                )
        else:
            if cooldown_time == 0:
                return await ctx.send("The cooldown time cannot be 0")
            cooldown_channels[str(channel.id)] = {
                "cooldown_time": cooldown_time,
                "users_on_cooldown": {},
            }
            await self.config.guild(ctx.guild).cooldown_channels.set(cooldown_channels)
            await ctx.send(f"{channel.mention} is now set at 1 message every {time}")

    @commands.group()
    async def slowset(self, ctx):
        """
        Config settings for slowset cog.
        """
        pass

    @slowset.command()
    @checks.admin()
    async def dm(self, ctx, option: bool = True):
        """
        Enable/Disable DM message when on cooldown
        """
        await self.config.guild(ctx.guild).send_dm.set(option)
        if option is True:
            await ctx.send("I will now DM users on cooldown.")
        else:
            await ctx.send("I will not DM users on cooldown.")

    @commands.group()
    @checks.mod()
    async def bypass(self, ctx):
        """
        Bypass a user cooldown
        """
        pass

    @bypass.command(name="channel")
    async def bypass_channel(
        self, ctx, member: discord.Member, channel: discord.TextChannel
    ):
        """
        Resets the cooldown for a user in a channel.
        """
        cooldown_channels = await self.config.guild(ctx.guild).cooldown_channels()
        if str(channel.id) not in cooldown_channels:
            return await ctx.send(f"{channel.mention} is not on cooldown.")
        del cooldown_channels[str(channel.id)]["users_on_cooldown"][str(member.id)]
        await self.config.guild(ctx.guild).cooldown_channels.set(cooldown_channels)
        await ctx.send(f"{member}'s cooldown in {channel.mention} has been reset.")

    @bypass.command(name="category")
    async def bypass_category(
        self, ctx, member: discord.Member, category: discord.CategoryChannel
    ):
        """
        Resets the cooldown for a user in a category.
        """
        cooldown_categories = await self.config.guild(ctx.guild).cooldown_categories()
        if str(category.id) not in cooldown_categories:
            return await ctx.send(f"{category.name} category is not on cooldown.")
        del cooldown_categories[str(category.id)]["users_on_cooldown"][str(member.id)]
        await self.config.guild(ctx.guild).cooldown_categories.set(cooldown_categories)
        await ctx.send(f"{member}'s cooldown in **{category.name}** has been reset.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        cooldown_channels = await self.config.guild(message.guild).cooldown_channels()
        cooldown_categories = await self.config.guild(
            message.guild
        ).cooldown_categories()
        catgories_channels = []
        for category_data in cooldown_categories.items():
            for channel in category_data["channels"]:
                catgories_channels.append(str(channel))
        channel = message.channel
        if str(channel.id) not in list(cooldown_channels.keys()) + catgories_channels:
            return
        send_dm = await self.config.guild(message.guild).send_dm()
        if str(channel.id) in cooldown_channels:
            await self.handle_channel_cooldown(
                message, cooldown_channels, send_dm=send_dm
            )
        if channel.category and str(channel.id) in catgories_channels:
            await self.handle_category_cooldown(
                message, cooldown_categories, send_dm=send_dm
            )

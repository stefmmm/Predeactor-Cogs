import asyncio
from datetime import datetime

import discord

from redbot.core import Config, checks, commands
from redbot.core.commands.converter import parse_timedelta
from redbot.core.utils.chat_formatting import (
    bold,
    humanize_list,
    humanize_timedelta,
    pagify,
    warning,
)
from redbot.core.utils.predicates import MessagePredicate


class CustomCooldown(commands.Cog):
    """Create a customizable cooldown to each channels and category.

    This cooldown is moderated by the bot itself.
    """

    __author__ = ["Maaz", "Predeactor"]
    __version__ = "v1.2"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=231120028796)
        self.config.register_guild(
            cooldown_channels={},
            cooldown_categories={},
            send_dm=False,
            ignore_bot=True,
            ignore_roles=[],
            ignore_users=[],
        )
        self.date_format = "%d-%m-%Y:%H-%M-%S"
        self.dmed = []

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad!"""
        pre_processed = super().format_help_for_context(ctx)
        return "{pre_processed}\n\nAuthor: {authors}\nCog Version: {version}".format(
            pre_processed=pre_processed,
            authors=humanize_list(self.__author__),
            version=self.__version__,
        )

    # Hadling Functions

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
                    deleted = True
                except (discord.NotFound, discord.Forbidden):
                    deleted = False
                    pass
                if send_dm:
                    if not user.bot:
                        try:
                            remaining_time = humanize_timedelta(
                                seconds=(channel_data["cooldown_time"] - total_seconds)
                            )
                            await user.send(
                                "Sorry, this channel is ratelimited! You'll be able to "
                                "post again in {channel} in {time}.".format(
                                    channel=channel.mention, time=remaining_time
                                )
                            )
                        except discord.Forbidden:
                            pass
            else:
                deleted = None
                channel_data["users_on_cooldown"][
                    str(message.author.id)
                ] = now.strftime(self.date_format)
                cooldown_channels[str(message.channel.id)] = channel_data
                await self.config.guild(message.guild).cooldown_channels.set(
                    cooldown_channels
                )
            # If message deletion wasn't possible:
            if deleted is False:
                await self._dm_owner(message.guild.owner, channel)

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
                    deleted = False
                    pass
                if send_dm:
                    if not user.bot:
                        try:
                            s = category_data["cooldown_time"] - total_seconds
                            remaining_time = humanize_timedelta(seconds=s)
                            await user.send(
                                "Hey there, can you chill out for a moment?\n"
                                "{channel} is ratelimited and you need to wait"
                                " {time}! Please note that this channel shares a"
                                " rate limit with the parent channel category.".format(
                                    category=channel.mention, time=remaining_time
                                )
                            )
                        except discord.Forbidden:
                            pass
            else:
                deleted = None
                category_data["users_on_cooldown"][str(user.id)] = now.strftime(
                    self.date_format
                )
                cooldown_categories[str(channel.id)] = category_data
                await self.config.guild(message.guild).cooldown_categories.set(
                    cooldown_categories
                )
            # If message deletion wasn't possible:
            if deleted is False:
                await self._dm_owner(message.guild.owner, channel)

    # Slow commannds (For adding/removing/listing cooldowned channels/category)

    @commands.group()
    @commands.guild_only()
    @checks.admin()
    async def slow(self, ctx: commands.Context):
        """Configure categories and channel."""
        pass

    @slow.command()
    @commands.is_owner()
    async def reset(self, ctx):
        """Resets all guild data."""
        predicate = MessagePredicate.yes_or_no(ctx)
        await ctx.send(warning(bold("Are you sure you want to delete ALL guilds?")))
        try:
            await self.bot.wait_for("message", check=predicate)
        except asyncio.TimeoutError:
            await ctx.tick()
            return
        if predicate.result:
            await self.config.clear_all_guilds()
            await ctx.send("Guild data reset.")
        else:
            await ctx.send("Better to touch nothing...")

    # Slow: Category

    @slow.group(name="category")
    async def slowcategory(self, ctx: commands.Context):
        """Set categories to cooldown."""
        pass

    @slowcategory.command(name="list")
    async def listcategory(self, ctx: commands.Context):
        """List cooldowned category."""
        text = ""
        cooldown_categories = await self.config.guild(ctx.guild).cooldown_categories()
        for category_id in cooldown_categories.keys():
            category = self.bot.get_channel(int(category_id))
            if category:
                seconds = cooldown_categories[category_id]["cooldown_time"]
                time = humanize_timedelta(seconds=seconds)
                text += "- {name} (`{id}`) Time: {time}.\n".format(
                    name=category.name, id=category.id, time=time
                )
            else:
                text += "- Category not found: {id}\n".format(id=category_id)
        if text:
            for line in pagify(text):
                await ctx.maybe_send_embed(line)
        else:
            await ctx.send("There's no category to show.")

    @slowcategory.command(name="add")
    async def addcategory(
        self, ctx: commands.Context, category: discord.CategoryChannel, time: str
    ):
        """Add a category cooldown."""
        cooldown_categories = await self.config.guild(ctx.guild).cooldown_categories()
        if str(category.id) in cooldown_categories:
            await ctx.send(
                "This category is already added to the cooldown. If you want to edit"
                " the cooldown time, use `{prefix}slow channel edit`.".format(
                    prefix=ctx.prefix
                )
            )
            return

        cooldown_time = await self._return_time(ctx, time)
        await self._update_category_data(ctx, category, cooldown_time)
        await ctx.send(
            "Done! Every {category}'s channels are now set at 1 message every "
            "{time}. Channels from this category are moderated but new channel "
            "won't be moderated. If you add channels that you want to also add cooldown"
            ", use `{prefix}slow category update`".format(
                category=category.name, time=time, prefix=ctx.prefix
            )
        )

    @slowcategory.command(name="edit")
    async def editcategory(
        self, ctx: commands.Context, category: discord.CategoryChannel, *, time: str
    ):
        """Edit a category cooldown."""
        cooldown_categories = await self.config.guild(ctx.guild).cooldown_categories()
        if str(category.id) in cooldown_categories:
            cooldown_time = await self._return_time(ctx, time)
            if cooldown_time is None:
                return
        else:
            await ctx.send(
                "{category} does not have cooldown.".format(channel=category.name)
            )
            return
        await self._update_category_data(ctx, category, cooldown_time)
        await ctx.send(
            "{category} is now set at 1 message every {time}".format(
                category=category.name, time=time
            )
        )

    @slowcategory.command(name="delete", aliases=["remove"])
    async def deletecategory(
        self, ctx: commands.Context, category: discord.CategoryChannel
    ):
        """Delete a category cooldown."""
        predicate = MessagePredicate.yes_or_no(ctx)
        await ctx.send(
            warning(
                bold(
                    "Are you sure you want to delete {category} data?".format(
                        category=category.name
                    )
                )
                + " (Y/N)"
            )
        )
        try:
            await self.bot.wait_for("message", check=predicate)
        except asyncio.TimeoutError:
            await ctx.tick()
            return
        if predicate.result:
            d = await self._delete_category(ctx, category)
            if d is None:
                return
            await ctx.send("Cooldown removed.")
        else:
            await ctx.send("Cooldowned, forever...")

    @slowcategory.command(name="update")
    async def updatecategory(
        self, ctx: commands.Context, category: discord.CategoryChannel
    ):
        """Update configuration to sync with new and old channel(s) into the category."""
        data = await self.config.guild(ctx.guild).cooldown_categories()
        if str(category.id) not in data:
            await ctx.send(
                "This category is not registered into cooldowned categories.\n"
                "Use `{prefix}slow category add` first.".format(prefix=ctx.prefix)
            )
            return
        time = data[str(category.id)]["cooldown_time"]
        await self._update_category_data(ctx, category, time)
        await ctx.tick()

    # Slow: Channel

    @slow.group(name="channel")
    async def slowchannel(self, ctx: commands.GuildContext):
        """Set channels to cooldown."""
        pass

    @slowchannel.command(name="list")
    async def listchannel(self, ctx: commands.Context):
        """List cooldowned channels."""
        text = ""
        cooldown_channels = await self.config.guild(ctx.guild).cooldown_channels()
        for channel_id in cooldown_channels.keys():
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                seconds = cooldown_channels[channel_id]["cooldown_time"]
                time = humanize_timedelta(seconds=seconds)
                text += "- {name} (`{id}`) Time: {time}.\n".format(
                    name=channel.name, id=channel.id, time=time
                )
            else:
                text += "- Channel not found: {id}\n".format(id=channel_id)
        if text:
            for line in pagify(text):
                await ctx.maybe_send_embed(line)
        else:
            await ctx.send("There's no channel to show.")

    @slowchannel.command(name="add")
    async def addchannel(
        self, ctx: commands.Context, channel: discord.TextChannel, *, time: str
    ):
        """Add a channel cooldown."""
        cooldown_channels = await self.config.guild(ctx.guild).cooldown_channels()
        if str(channel.id) in cooldown_channels:
            await ctx.send(
                "This channel is already added to the cooldown. If you want to edit"
                " the cooldown time, use `{prefix}slow channel edit`.".format(
                    prefix=ctx.prefix
                )
            )
            return

        cooldown_time = await self._return_time(ctx, time)
        if cooldown_time is None:
            return
        await self._update_channel_data(ctx, channel, cooldown_time)
        await ctx.send(
            "{channel} is now set at 1 message every {time}.".format(
                channel=channel.mention, time=time
            )
        )

    @slowchannel.command(name="edit")
    async def editchannel(
        self, ctx: commands.Context, channel: discord.TextChannel, *, time: str
    ):
        """Edit a channel cooldown."""
        cooldown_channels = await self.config.guild(ctx.guild).cooldown_channels()
        if str(channel.id) in cooldown_channels:
            cooldown_time = await self._return_time(ctx, time)
        else:
            await ctx.send(
                "{channel} does not have cooldown.".format(channel=channel.mention)
            )
            return

        await self._update_channel_data(ctx, channel, cooldown_time)
        await ctx.send(
            "{channel} is now set at 1 message every {time}".format(
                channel=channel.mention, time=time
            )
        )

    @slowchannel.command(name="delete", aliases=["remove"])
    async def deletechannel(
        self, ctx: commands.Context, *, channel: discord.TextChannel
    ):
        """Delete a channel cooldown."""
        predicate = MessagePredicate.yes_or_no(ctx)
        await ctx.send(
            warning(
                bold(
                    "Are you sure you want to delete {channel} data?".format(
                        channel=channel.name
                    )
                )
                + " (Y/N)"
            )
        )
        try:
            await self.bot.wait_for("message", check=predicate)
        except asyncio.TimeoutError:
            await ctx.tick()
            return
        if predicate.result:
            d = await self._delete_channel(ctx, channel)
            if d is None:
                return
            await ctx.send("Cooldown removed.")
        else:
            await ctx.send("Peace and quiet...")

    # Slowset, for settings various settings

    @commands.group()
    @commands.guild_only()
    async def slowset(self, ctx):
        """Set differents options."""
        pass

    @slowset.command()
    @checks.admin()
    async def dm(self, ctx: commands.Context, option: bool = None):
        """
        Enable/Disable DM message when triggering cooldown.

        You must use `True` or `False`.
        """
        if option is not None:
            await self.config.guild(ctx.guild).send_dm.set(option)
            if option:
                await ctx.send("I will now DM users when they trigger the cooldown.")
            else:
                await ctx.send("I won't send DM to users anymore.")
        else:
            await ctx.send_help()

    @slowset.command()
    @checks.admin()
    async def ignorebot(self, ctx: commands.Context, option: bool = None):
        """
        Enable/Disable ignoring bots when they send a message in channel
         or category that own a cooldown.

        You must use `True` or `False`.
        """
        if option is not None:
            await self.config.guild(ctx.guild).ignore_bot.set(option)
            if option:
                await ctx.send(
                    "I will now ignore bot when they send a message in "
                    "cooldowned channels/category."
                )
            else:
                await ctx.send("I won't ignore bots anymore.")
        else:
            await ctx.send_help()

    # Slowset: Ignore Users

    @slowset.group(name="ignoreusers")
    @checks.admin()
    async def slowignoreusers(self, ctx: commands.GuildContext):
        """Add or remove users from the ignored list of cooldown."""
        pass

    @slowignoreusers.command(name="list")
    async def listignoredusers(self, ctx: commands.Context):
        """List ignored users."""
        text = ""
        ignored_users = await self.config.guild(ctx.guild).ignore_users()
        if ignored_users:
            for user_id in ignored_users:
                user = await self._get_user(user_id)
                if user:
                    text += "- {name} (`{id}`).\n".format(name=user.name, id=user.id)
                else:
                    text += "- User not found: {id}".format(id=user_id)
        if text:
            for line in pagify(text):
                await ctx.maybe_send_embed(line)
        else:
            await ctx.send("No users is ignored.")

    @slowignoreusers.command(name="add")
    async def addignoreusers(self, ctx: commands.Context, *users: discord.Member):
        """Add one or multiples users to the ignored list."""
        if not users:
            await ctx.send_help()
            return

        already_added = []
        is_bot = []
        final_message = ""
        async with self.config.guild(ctx.guild).ignore_users() as iu:
            for user in users:
                if user.bot:
                    is_bot.append(user.name)
                    continue
                if user.id not in iu:
                    iu.append(user.id)
                else:
                    already_added.append(user)

        if len(is_bot) > 1:
            final_message += "Those users are bots and cannot be added: {bots}\n".format(
                bots=humanize_list(is_bot)
            )
        elif len(is_bot) == 1:
            final_message += "{bot} is a bot and cannot be added.\n".format(
                bot=is_bot[0]
            )
        if len(already_added) > 1:
            final_message += "Those users are already ignored: {list}".format(
                list=humanize_list(already_added)
            )
        elif len(already_added) == 1:
            final_message += "{user} is already ignored.".format(user=already_added[0])
        if final_message:
            for line in pagify(final_message):
                await ctx.send(line)
        await ctx.tick()

    @slowignoreusers.command(name="delete", aliases=["remove"])
    async def removeignoreusers(self, ctx: commands.Context, *users: discord.Member):
        """Remove one or multiples users on the ignored list."""
        if not users:
            await ctx.send_help()
            return

        already_removed = []
        async with self.config.guild(ctx.guild).ignore_users() as iu:
            for user in users:
                if user.id in iu:
                    iu.remove(user.id)
                else:
                    already_removed.append(user.name)

        message = ""
        if len(already_removed) > 1:
            message = "Those users are already not ignored: {list}".format(
                list=humanize_list(already_removed)
            )
        elif len(already_removed) == 1:
            message = "{user} is already not ignored.".format(user=already_removed[0])
        if message:
            for line in pagify(message):
                await ctx.send(line)
        await ctx.tick()

    # Slowset: Ignore Roles

    @slowset.group(name="ignoreroles")
    @checks.admin()
    async def slowignoreroles(self, ctx: commands.GuildContext):
        """Add or remove roles from the ignored list of cooldown."""
        pass

    @slowignoreroles.command(name="list")
    async def listignoredroles(self, ctx: commands.Context):
        """List ignored roles."""
        text = ""
        ignored_roles = await self.config.guild(ctx.guild).ignore_roles()
        if ignored_roles:
            for role_id in ignored_roles:
                role = ctx.guild.get_role(role_id)
                if role:
                    text += "- {name} (`{id}`).\n".format(name=role.name, id=role.id)
                else:
                    text += "- Role not found: {id}".format(id=role_id)
        if text:
            for line in pagify(text):
                await ctx.maybe_send_embed(line)
        else:
            await ctx.send("There's no role to ignore.")

    @slowignoreroles.command(name="add")
    async def addignoreroles(self, ctx: commands.Context, *roles: discord.Role):
        """Add one or multiples role to the ignored list."""
        if not roles:
            await ctx.send_help()
            return

        already_added = []
        final_message = ""
        async with self.config.guild(ctx.guild).ignore_roles() as ir:
            for role in roles:
                if role.id not in ir:
                    ir.append(role.id)
                else:
                    already_added.append(role.name)

        if len(already_added) > 1:
            final_message += "Those roles are already ignored: {list}".format(
                list=humanize_list(already_added)
            )
        elif len(already_added) == 1:
            final_message += "{role} is already ignored.".format(role=already_added[0])
        if final_message:
            for line in pagify(final_message):
                await ctx.send(line)
        await ctx.tick()

    @slowignoreroles.command(name="delete", aliases=["remove"])
    async def removeignoreroles(self, ctx: commands.Context, *roles: discord.Role):
        """Remove one or multiples roles on the ignored list."""
        if not roles:
            await ctx.send_help()
            return

        already_removed = []
        async with self.config.guild(ctx.guild).ignore_roles() as ir:
            for role in roles:
                if role.id in ir:
                    ir.remove(role.id)
                else:
                    already_removed.append(role.name)

        message = ""
        if len(already_removed) > 1:
            message = "Those roles are already not ignored: {list}".format(
                list=humanize_list(already_removed)
            )
        elif len(already_removed) == 1:
            message = "{role} is already not ignored.".format(role=already_removed[0])
        if message:
            for line in pagify(message):
                await ctx.send(line)
        await ctx.tick()

    # Bypassing

    @commands.group()
    @checks.mod()
    async def bypass(self, ctx):
        """Bypass a user cooldown."""
        pass

    @bypass.command(name="channel")
    async def bypass_channel(
        self, ctx, member: discord.Member, channel: discord.TextChannel
    ):
        """Resets the cooldown for a user in a channel."""
        cooldown_channels = await self.config.guild(ctx.guild).cooldown_channels()
        if str(channel.id) not in cooldown_channels:
            await ctx.send(
                "{channel} is not on cooldown.".format(channel=channel.mention)
            )
            return
        if (
            str(member.id)
            not in cooldown_channels[str(channel.id)]["users_on_cooldown"]
        ):
            await ctx.send(
                "{user} is not on cooldown in {channel}.".format(
                    user=member, channel=channel.mention
                )
            )
            return
        del cooldown_channels[str(channel.id)]["users_on_cooldown"][str(member.id)]
        await self.config.guild(ctx.guild).cooldown_channels.set(cooldown_channels)
        await ctx.send(f"{member}'s cooldown in {channel.mention} has been reset.")

    @bypass.command(name="category")
    async def bypass_category(
        self, ctx, member: discord.Member, category: discord.CategoryChannel
    ):
        """Resets the cooldown for a user in a category."""
        cooldown_categories = await self.config.guild(ctx.guild).cooldown_categories()
        if str(category.id) not in cooldown_categories:
            await ctx.send(
                "{category} category is not on cooldown.".format(category=category.name)
            )
            return
        if (
            str(member.id)
            not in cooldown_categories[str(category.id)]["users_on_cooldown"]
        ):
            await ctx.send(
                "{user} is not on cooldown in {category}.".format(
                    user=member, category=category.name
                )
            )
            return
        del cooldown_categories[str(category.id)]["users_on_cooldown"][str(member.id)]
        await self.config.guild(ctx.guild).cooldown_categories.set(cooldown_categories)
        await ctx.send(
            "{member}'s cooldown in {category} has been reset.".format(
                member=member.name, category=category.name
            )
        )

    # Functions

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if await self.config.guild(message.guild).ignore_bot():
            if message.author.bot:
                return
        if message.author.id in await self.config.guild(message.guild).ignore_users():
            return
        if any(
            role in set([role.id for role in message.author.roles])
            for role in await self.config.guild(message.guild).ignore_roles()
        ):
            return

        cooldown_channels = await self.config.guild(message.guild).cooldown_channels()
        cooldown_categories = await self.config.guild(
            message.guild
        ).cooldown_categories()

        categories_ids = []
        catgories_channels = []
        for category_id in cooldown_categories:
            categories_ids.append(str(category_id))
        for category_id in categories_ids:
            for channels in cooldown_categories[category_id]["channels"]:
                catgories_channels.append(str(channels))

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

    async def _update_channel_data(
        self, ctx: commands.Context, channel: discord.TextChannel, time
    ):
        if isinstance(time, float):
            time = int(time)
        async with self.config.guild(
            ctx.guild
        ).cooldown_channels() as cooldown_channels:
            cooldown_channels[str(channel.id)] = {
                "cooldown_time": time,
                "users_on_cooldown": {},
            }

    async def _update_category_data(
        self, ctx: commands.Context, category: discord.CategoryChannel, time
    ):
        if isinstance(time, float):
            time = int(time)
        async with self.config.guild(
            ctx.guild
        ).cooldown_categories() as cooldown_categories:
            cooldown_categories[str(category.id)] = {
                "cooldown_time": time,
                "users_on_cooldown": {},
                "channels": [channel.id for channel in category.channels],
            }

    async def _delete_channel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ):
        async with self.config.guild(
            ctx.guild
        ).cooldown_channels() as cooldown_channels:
            if str(channel.id) in cooldown_channels:
                del cooldown_channels[str(channel.id)]
            else:
                await ctx.send(
                    "I can't find {channel} into the configured cooldown.".format(
                        channel=channel.mention
                    )
                )
                return

    async def _delete_category(
        self, ctx: commands.Context, category: discord.CategoryChannel
    ):
        async with self.config.guild(
            ctx.guild
        ).cooldown_categories() as cooldown_categories:
            if str(category.id) in cooldown_categories:
                del cooldown_categories[str(category.id)]
            else:
                await ctx.send(
                    "I can't find {category} into the configured cooldown.".format(
                        category=category.name
                    )
                )
                return

    async def _return_time(self, ctx: commands.Context, time):
        cooldown_time = int(parse_timedelta(time).total_seconds())
        if cooldown_time is None:
            await ctx.send("Please enter a valid time.")
            return
        if cooldown_time == 0:
            await ctx.send("0 cannot be used as a cooldown time.")
            return
        return cooldown_time

    async def _get_user(self, user_id: int):
        user = self.bot.get_user(user_id)
        if user is None:  # User not found
            try:
                user = await self.bot.fetch_user(user_id)
            except (discord.NotFound, discord.HTTPException):
                return None
        return user

    async def _dm_owner(self, owner: discord.Member, channel: discord.TextChannel):
        if owner.id in self.dmed:
            return
        try:
            await owner.send(
                "Hello. I tried to delete a message in {channel} because this "
                "channel is registered as cooldowned, but I was unable to delete "
                "the last message. I need the Manage messages permissions to "
                "delete messages in this channel.\nThis message won't reappear "
                "until the next bot reboot.".format(channel=channel.mention)
            )
        except discord.Forbidden:
            pass
        self.dmed.append(owner.id)

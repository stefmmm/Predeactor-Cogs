import asyncio
import logging
import sys

import discord
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import bold, box
from redbot.core.utils.predicates import MessagePredicate

from .core import Core

log = logging.getLogger("predeactor.captcher")


class Captcher(Core):
    @commands.group(name="setcaptcher")
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def config(self, ctx: commands.GuildContext):
        """
        Configure settings for Captcher.
        """
        pass

    @config.command()
    async def giverole(self, ctx: commands.Context, role_to_give: discord.Role = None):
        """
        Give a role when the user succesfully completed the captacha.

        If a role is already set and you don't provide a role, actual role will
        be deleted.
        """
        if role_to_give:
            await self.data.guild(ctx.guild).giverole.set(role_to_give.id)
            message = "{role.name} will be given when members pass the captcha.".format(
                role=role_to_give
            )
        elif role_to_give is None and await self.data.guild(ctx.guild).giverole():
            await self.data.guild(ctx.guild).giverole.clear()
            message = "Role configuration removed."
        else:
            await ctx.send_help()
            message = box("There's no role in configuration.")
        await ctx.send(message)

    @config.command()
    async def temprole(
        self, ctx: commands.Context, temporary_role: discord.Role = None
    ):
        """
        Role to give when someone join, it will be automatically removed after 
        passing captcha.

        If a role is already set and you don't provide a role, actual role will
        be deleted.
        """
        if temporary_role:
            await self.data.guild(ctx.guild).temp_role.set(temporary_role.id)
            message = "{role.name} will be given when members start the captcha.".format(
                role=temporary_role
            )
        elif temporary_role is None and await self.data.guild(ctx.guild).temp_role():
            await self.data.guild(ctx.guild).temp_role.clear()
            message = "Temporary role configuration removed."
        else:
            await ctx.send_help()
            message = box("There's no temporary role in configuration.")
        await ctx.send(message)

    @config.command()
    async def verificationchannel(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """
        Set where the captcha must be sent.
        """
        if channel:
            result, answer = await self._permissions_checker(channel)
            if result:
                await self.data.guild(ctx.guild).verification_channel.set(channel.id)
                message = (
                    "{channel.name} will be used when members must pass the "
                    "captcha.".format(channel=channel)
                )
            else:
                message = answer
        elif (
            channel is None and await self.data.guild(ctx.guild).verification_channel()
        ):
            await self.data.guild(ctx.guild).verification_channel.clear()
            message = "Verification channel configuration removed."
        else:
            await ctx.send_help()
            message = box("There's no verification channel configured.")
        await ctx.send(message)

    @config.command()
    async def logschannel(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """
        Set the log channel, really recommended for knowing who passed verification 
        or who failed.
        """
        if channel:
            result, answer = await self._permissions_checker(channel)
            if result:
                await self.data.guild(ctx.guild).logs_channel.set(channel.id)
                message = "{channel.name} will be used for captcha logs.".format(
                    channel=channel
                )
            else:
                message = answer
        elif channel is None and await self.data.guild(ctx.guild).logs_channel():
            await self.data.guild(ctx.guild).logs_channel.clear()
            message = "Logging channel configuration removed."
        else:
            await ctx.send_help()
            message = box("There's no logs channel configured")
        await ctx.send(message)

    @config.command()
    async def activate(self, ctx: commands.Context, true_or_false: bool = None):
        """
        Set if Captcher is activated.
        """
        if true_or_false is not None:
            channel_id = await self.data.guild(ctx.guild).verification_channel()
            fetched_channel = self.bot.get_channel(channel_id)
            if fetched_channel:
                result, answer = await self._permissions_checker(fetched_channel)
                if result:
                    if await self.data.guild(ctx.guild).temp_role():
                        await self.data.guild(ctx.guild).active.set(true_or_false)
                        message = "Captcher is now {term}activate.".format(
                            term="" if true_or_false else "de"
                        )
                    else:
                        message = (
                            "Cannot complete request: No temporary role are configured."
                        )
                else:
                    message = answer
            else:
                message = "Cannot complete request: No channel are configured."
                if channel_id:
                    await self.data.guild(ctx.guild).verification_channel.clear()
        else:
            await ctx.send_help()
            activated = await self.data.guild(ctx.guild).active()
            message = box(
                "Captcher is {term}activated.".format(term="" if activated else "de")
            )
        await ctx.send(message)

    @config.command()
    async def autoconfig(self, ctx: commands.Context):
        """Automatically set Captcher."""
        await ctx.send("Autoconfig disabled by cog.")
        return
        await ctx.send(
            "This command will:\n"
            "- Create a new role called: Unverified\n"
            "- Create a new channel called: #verification\n"
            "- Create a new channel called: #verification-logs\n"
            "\nBot will overwrite all channels to:\n"
            "- Unallow Unverified to read in channels.\n"
            "- Unverified will be able to read & send message in #verification.\n"
            "\nDo you wish to continue?"
        )
        try:
            predicator = MessagePredicate.yes_or_no(ctx)
            await self.bot.wait_for("message", timeout=30, check=predicator)
        except asyncio.TimeoutError:
            await ctx.send("Command cancelled, caused by timeout.")
        if predicator.result:
            if not ctx.channel.permissions_for(ctx.guild.me).administrator:
                await ctx.send("I require the Adminstrator permission first.")
                return
            await self.data.guild(ctx.guild).clear()
            await self._overwrite_server(ctx)
        else:
            await ctx.send("You will have to configure Captcher yourself.")
        r = await self._ask_for_role_add(ctx)
        if r:
            await ctx.send("Configuration is done. Activate Captcher? (y/n)")
            try:
                predicator = MessagePredicate.yes_or_no(ctx)
                await self.bot.wait_for("message", timeout=30, check=predicator)
            except asyncio.TimeoutError:
                await ctx.send("Question cancelled, caused by timeout.")
            if predicator.result:
                await self.data.guild(ctx.guild).active.set(True)
            await ctx.send("Done.")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Cog's listener to send captcha if paramater are so."""
        if member.bot:
            return

        if not await self.data.guild(member.guild).active():
            return
        guild_channel = await self.data.guild(member.guild).verification_channel()
        if not guild_channel:
            log.critical(
                "Bot was strictly unable to find a verification channel for server: "
                "{name} at ID {id}. Captcher is aborting.".format(
                    name=member.guild, id=member.guild.id
                )
            )
            return  # We don't know where the captcha must be sent

        guild_channel = self.bot.get_channel(guild_channel)
        if guild_channel is None:
            return

        await self._challenge(member, guild_channel, "Joined the server.")

    @commands.command()
    @checks.is_owner()
    async def challengeuser(self, ctx: commands.Context, *, user: discord.Member):
        """Make an user pass the captcha again."""
        if user.bot:
            await ctx.send("Bots are my friend, I cannot let you do that to them.")
            return
        roles_methods = {"1": "all", "2": "configured", "3": None}
        await ctx.send(
            "Choose the following number:\n"
            "1: Remove all roles and re-add them after verification.\n"
            "2: Only remove configured role and re-add after verification.\n"
            "3: Do not remove role(s). (Channel must be visible)"
        )
        try:
            user_message = await self.bot.wait_for(
                "message", timeout=30, check=MessagePredicate.same_context(ctx)
            )
        except asyncio.TimeoutError:
            await ctx.send("Command cancelled, caused by timeout.")
            return
        if user_message.content not in roles_methods:
            await ctx.send("This method is not available.")
            return
        method = roles_methods[user_message.content]
        if method == "all":
            roles = await self._role_keeper(user)
            await self._roles_remover(user)
        elif method == "configured":
            role_conf = await self.data.guild(ctx.author.guild).giverole()
            if role_conf:
                role = ctx.guild.get_role(role_conf)
            if role:
                await user.remove_roles(role)
            else:
                await ctx.send(
                    "I cannot find the configured role, choose another method or add a"
                    " new role."
                )
        verification_channel = await self.data.guild(
            ctx.author.guild
        ).verification_channel()
        channel = self.bot.get_channel(verification_channel)
        if not channel:
            await ctx.send(
                "I cannot find the verification channel, please add one again."
            )
            return
        captched = await self._challenge(
            user, channel, f"{user} challenged manually by {ctx.author}.",
        )
        if method == "all" and captched and roles:
            await self._add_role(user, roles)

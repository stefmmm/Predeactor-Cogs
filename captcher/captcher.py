import logging
import sys

import discord
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import box

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
    @commands.bot_has_permissions(manage_roles=True)
    async def giverole(self, ctx: commands.Context, role_to_give: discord.Role = None):
        """
        Give a role when the user succesfully completed the captacha.
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
    async def verificationchannel(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """
        Set where the captcha must be sent.
        """
        if channel:
            if not channel.permissions_for(ctx.guild.me).read_messages:
                message = (
                    "I require the Read Messages permission in this channel to work."
                )
            elif not channel.permissions_for(ctx.guild.me).manage_messages:
                message = (
                    "I require the Manage Messages permission in this channel "
                    "to work properly."
                )
            else:
                await self.data.guild(ctx.guild).verification_channel.set(channel.id)
                message = (
                    "{channel.name} will be used when members must pass the "
                    "captcha.".format(channel=channel)
                )
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
        if channel:
            if not channel.permissions_for(ctx.guild.me).read_messages:
                message = "I need to read into this channel."
            else:
                await self.data.guild(ctx.guild).logs_channel.set(channel.id)
                message = "{channel.name} will be used for captcha logs.".format(
                    channel=channel
                )
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
            channel = await self.data.guild(ctx.guild).verification_channel()
            fetched_channel = self.bot.get_channel(channel)
            if channel:
                if not fetched_channel.permissions_for(ctx.guild.me).send_messages:
                    message = (
                        "I cannot talk in the configured channel ({name}), which is "
                        "required for sending captcha.".format(
                            name=fetched_channel.name
                        )
                    )
                else:
                    await self.data.guild(ctx.guild).active.set(true_or_false)
                    message = "Captcher is now {term}activate.".format(
                        term="" if true_or_false else "de"
                    )
            else:
                message = "You cannot activate Captcher if no channel are configured."
        else:
            await ctx.send_help()
            activated = await self.data.guild(ctx.guild).active()
            message = box(
                "Captcher is {term}activated.".format(term="" if activated else "de")
            )
        await ctx.send(message)

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
    async def test(self, ctx: commands.Context):
        verification_channel = await self.data.guild(
            ctx.author.guild
        ).verification_channel()
        await self._challenge(
            ctx.author,
            self.bot.get_channel(verification_channel),
            f"{ctx.prefix}test ran.",
        )

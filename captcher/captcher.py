import sys

import discord
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import box

from .core import Core


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
    async def channel(
        self, ctx: commands.Context, channel_to_send_captcha: discord.TextChannel = None
    ):
        """
        Set where the captcha must be sent.
        """
        if channel_to_send_captcha:
            await self.data.guild(ctx.guild).channel.set(channel_to_send_captcha.id)
            message = "{channel.name} will be used when members must pass the captcha.".format(
                channel=channel_to_send_captcha
            )
        elif (
            channel_to_send_captcha is None
            and await self.data.guild(ctx.guild).channel()
        ):
            await self.data.guild(ctx.guild).channel.clear()
            message = "Channel configuration removed."
        else:
            await ctx.send_help()
            message = box("There's no channel in configuration.")
        await ctx.send(message)

    @config.command()
    async def activate(self, ctx: commands.Context, true_or_false: bool = None):
        """
        Set if Captcher is activated.
        """
        if true_or_false is not None:
            if await self.data.guild(ctx.guild).channel():
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

    @checks.is_owner()
    @commands.command()
    async def test(self, ctx):
        code, image = self._generate_code_and_image()
        dfile = discord.File(image, filename=str(ctx.author.id) + ".png")
        await ctx.send(file=dfile)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Cog's listener to send captcha if paramater are so."""
        if member.bot:
            return

        if not await self.data.guild(member.guild).active():
            return
        guild_channel = await self.data.guild(member.guild).channel()
        if not guild_channel:
            return  # We don't know where the captcha must be sent

        guild_channel = self.bot.get_channel(guild_channel)
        if guild_channel is None:
            return

        await self._challenge(member, guild_channel)

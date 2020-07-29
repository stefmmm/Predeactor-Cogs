import asyncio
import contextlib
import datetime
import logging
from os import listdir
from os.path import isfile, join
import time
from random import randint, choice

import discord
from captcha.image import ImageCaptcha
from redbot.core import Config, commands, modlog
from redbot.core.bot import Red
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.chat_formatting import bold, error, humanize_list, info
from redbot.core.utils.predicates import MessagePredicate
from PIL import ImageFont

log = logging.getLogger("predeactor.captcher")
log.setLevel(logging.DEBUG)


class Core(commands.Cog):

    __author__ = ["Predeactor"]
    __version__ = "Alpha 0.4-dev"

    def __init__(self, bot: Red):
        self.bot = bot
        self.data = Config.get_conf(self, identifier=495954055)
        self.data.register_guild(
            giverole=None,
            verification_channel=None,
            active=False,
            logs_channel=None,
            temp_role=None,
        )
        self.path = bundled_data_path(self)
        self._cache = {}
        self._init_logger()
        super().__init__()

    def _init_logger(self):
        log_format = logging.Formatter(
            f"%(asctime)s %(levelname)s {self.__class__.__name__}: %(message)s",
            datefmt="[%d/%m/%Y %H:%M]",
        )
        stdout = logging.StreamHandler()
        stdout.setFormatter(log_format)

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad!"""
        pre_processed = super().format_help_for_context(ctx)
        return "{pre_processed}\n\nAuthor: {authors}\nCog Version: {version}".format(
            pre_processed=pre_processed,
            authors=humanize_list(self.__author__),
            version=self.__version__,
        )

    def _generate_code_and_image(self):
        """Return the generated code with the generated image."""
        code = str(randint(10000, 99999))  # Cannot start with leading 0...
        # fonts = [f for f in listdir(self.path) if isfile(join(self.path, f))]
        return (
            code,
            ImageCaptcha().generate(code),
        )  # I got an OSError if I use custom fonts

    async def _challenge(
        self, member: discord.Member, channel: discord.TextChannel, start_reason: str
    ):
        code, image = self._generate_code_and_image()
        dfile = discord.File(image, filename=str(member.id) + "-captcha.png")
        message_content = (
            "Hello {member}, this server include an extra security layout to protect "
            "there members. You're asked to complete a security captacha in order to "
            "join this server. If you fail or take too much time to answer (5 "
            "minutes), you will be automatically kicked from this server.\nNote: "
            "The captcha doesn't include space.".format(member=member.mention)
        )
        try:
            await member.add_roles(
                member.guild.get_role(await self.data.guild(member.guild).temp_role())
            )
        except Exception as e:
            await self._report_log(
                member, "error", f"Cannot add temporary role to {member}: {e}"
            )
        await self._report_log(member, "started", start_reason)
        try:
            captcha_message = await channel.send(content=message_content, file=dfile)
        except (discord.HTTPException, discord.Forbidden):
            log.warning(
                "Bot was strictly unable to send a message in channel: {name} for ID "
                "{id} in server {server}.".format(
                    name=channel.name, id=channel.id, server=channel.guild,
                )
            )
            await self._report_log(
                member, "error", "Unable to send message in configured channel."
            )
            return
        message, success = await self._predication_result(code, member, channel)
        if success:
            final_answer = await channel.send(
                "{member}, you passed the verification.".format(member=member.mention)
            )
            role = await self._give_role(member)
            await self._report_log(
                member,
                "completed",
                f"{member}: Received {role} and/or removed temporary role."
                if role
                else "Unable to give and remove roles.",
            )
            failed = False
        else:
            perms = self._mute_or_unmute_user(channel, member, False)
            try:
                await channel.edit(overwrites=perms)
            except Exception as e:
                await self._report_log(
                    member, "error", f"Cannot mute {member} in channel before kicking."
                )
            final_answer = await channel.send(
                "{member}, your captcha is wrong.".format(member=member.mention)
            )
            failed = True
        await captcha_message.delete()
        time.sleep(5)
        if failed:
            await self._kicker(member)
            perms = self._mute_or_unmute_user(channel, member, True)
            try:
                await channel.edit(overwrites=perms)
            except Exception as e:
                await self._report_log(
                    member, "error", f"Cannot unmute {member} in channel after kicking."
                )
        await message.delete()
        await final_answer.delete()
        if member.id in self._cache:
            del self._cache[member.id]
        return True if not failed else False

    async def _predication_result(
        self, code: str, member: discord.Member, channel: discord.TextChannel
    ):
        try:
            user_message = await self.bot.wait_for(
                "message",
                timeout=300,
                check=MessagePredicate.same_context(user=member, channel=channel),
            )
        except asyncio.TimeoutError:
            with contextlib.suppress(Exception):
                await member.send(
                    f"Hello, you've been automatically kicked from {guild} for not "
                    "answering the captcha to enter into the server. You can come back "
                    "and complete the captcha again."
                )
            await self._kicker(member)
        if user_message.content == str(code):
            success = True
        else:
            success = False
        return user_message, success

    async def _give_role(self, member: discord.Member):
        guild = member.guild
        data = await self.data.guild(member.guild).all()
        role_data = data["giverole"]
        if role_data is not None:
            add_role = guild.get_role(role_data)
        else:
            add_role = None
        remove_role = guild.get_role(data["temp_role"])
        if not add_role and role_data is not None:
            await self._report_log(member, "error", "Role to give cannot be found.")
        try:
            if role_data:
                await member.add_roles(add_role, reason="Completed captcha.")
            await member.remove_roles(remove_role, reason="Completed captcha.")
        except discord.Forbidden:
            await self._report_log(
                member, "error", "Missing permissions to give/remove roles."
            )
            return  # We're still unable to give, don't let staff thing it was
        if add_role:
            return add_role.name
        return True

    async def _report_log(self, member: discord.Member, level: str, reason: str):
        level_list = {
            "started": bold(info(f"{member} started a captcha verification: "))
            + reason,
            "error": bold(error("Error will Captcha was running: ")) + reason,
            "completed": bold(
                "\N{WHITE HEAVY CHECK MARK} Member has completed Captcha: "
            )
            + reason,
            "failed": bold(f"\N{WOMANS BOOTS} {member} got kicked: ") + reason,
            "unknow": bold("Unknow report: ") + reason,
        }
        if level not in level_list:
            level = "unknow"
        channel = await self._get_log_channel(member)
        if channel:
            message = level_list[level]
            await channel.send(message)

    async def _get_log_channel(self, member: discord.Member):
        if member.id in self._cache:
            channel = self._cache[member.id]
        channel_id = await self.data.guild(member.guild).logs_channel()
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return False
        self._cache[member.id] = channel_id
        return channel

    async def _kicker(self, member: discord.Member):
        try:
            await member.kick()
            await modlog.create_case(
                self.bot,
                member.guild,
                datetime.datetime.now(),
                action_type="kick",
                user=member,
                moderator=self.bot.user,
                reason=(
                    "Automatic kick by Captcher. Either not answering or wrong in "
                    "answering to captcha."
                ),
            )
            await self._report_log(member, "failed", "Failed the captcha.")
        except (discord.HTTPException, discord.Forbidden):
            log.warning(
                "Bot was strictly unable to kick an user in server: {name} for ID "
                "{id}.".format(name=member.guild.name, id=member.guild.id)
            )
            await self._report_log(member, "error", f"Unable to kick {member}.")

    async def _permissions_checker(self, channel: discord.TextChannel):
        # Doit avoit - manage_messages, manage_roles, read_messages
        me = channel.guild.me
        message = ""
        issues = 0
        if not channel.permissions_for(me).read_messages:
            message += "I require the Read Messages permission in {name} to work.\n".format(
                name=channel.name
            )
            issues += 1
            passed = False
        if not channel.permissions_for(me).manage_messages:
            message += (
                "I require the Manage Messages permission in {name} to work"
                " properly.\n".format(name=channel.name)
            )
            issues += 1
            passed = False
        if not channel.permissions_for(me).manage_roles:
            message += (
                "I require the Manage Roles permission in this server "
                "to work properly.\n"
            )
            issues += 1
            passed = False
        if not message:
            message = None
            passed = True
        final = (
            (
                bold(
                    "Missing permission{plur}:\n".format(plur="s" if issues > 1 else "")
                )
                + message
            )
            if message
            else None
        )
        if not passed:
            await self.data.guild(channel.guild).active.set(False)
        return passed, final

    async def _role_keeper(self, member: discord.Member):
        roles = member.roles[-1:0:-1]
        if roles:
            lister = []
            for role in roles:
                lister.append(role.id)
        return lister

    async def _roles_remover(self, member: discord.Member):
        roles = member.roles[-1:0:-1]
        if roles:
            for role in roles:
                await member.remove_roles(role)

    async def _add_role(self, member: discord.Member, role_list: list):
        for role in role_list:
            await member.add_roles(role)

    async def _overwrite_channel(self, ctx: commands.Context):
        role = await ctx.guild.create_role(
            name="Unverified",
            mentionable=True,
            reason="Automatic creation by Captcher (Automatic setup)",
        )

        verification_overwrite = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            ctx.guild.me: discord.PermissionOverwrite(
                read_messages=True, manage_messages=True
            ),
        }

        mods = await self.bot.get_mod_roles(ctx.guild)
        admins = await self.bot.get_admin_roles(ctx.guild)
        logs_overwrites = self._make_staff_overwrites(
            mods, admins, ctx.guild.me, ctx.guild.default_role
        )
        for channel in ctx.guild.channels:
            actual_perm = channel.overwrites
            actual_perm[role] = discord.PermissionOverwrite(read_messages=False)
            await channel.edit(overwrites=actual_perm)

        verif = await ctx.guild.create_text_channel(
            "verification", overwrites=verification_overwrite
        )
        logs = await ctx.guild.create_text_channel(
            "verification-logs", overwrites=logs_overwrites
        )
        await self.data.guild(ctx.guild).verification_channel.set(verif.id)
        await self.data.guild(ctx.guild).logs_channel.set(logs.id)
        await self.data.guild(ctx.guild).temp_role.set(role.id)

    def _make_staff_overwrites(
        self, mods: list, admins: list, me: discord.Member, default: discord.Role
    ):
        data = {}
        for admin in admins:
            data[admin] = discord.PermissionOverwrite(
                read_messages=True, send_messages=False
            )
        for mod in mods:
            data[mod] = discord.PermissionOverwrite(
                read_messages=True, send_messages=False
            )
        data[default] = discord.PermissionOverwrite(read_messages=False)
        data[me] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        return data

    def _mute_or_unmute_user(
        self, channel: discord.TextChannel, user: discord.Member, option: bool
    ):
        actual_perm = channel.overwrites
        actual_perm[user] = discord.PermissionOverwrite(send_messages=option)
        return actual_perm

    async def _ask_for_role_add(self, ctx):
        await ctx.send("Do you use a role to access to the server? (y/n)")
        try:
            predicator = MessagePredicate.yes_or_no(ctx)
            await self.bot.wait_for("message", timeout=30, check=predicator)
        except asyncio.TimeoutError:
            await ctx.send("Question cancelled, caused by timeout.")
        if predicator.result:
            await ctx.send(
                "Which role should I give when user pass captcha? (Role ID/Name/Mention)"
            )
            role = MessagePredicate.valid_role(ctx)
            try:
                await self.bot.wait_for("message", timeout=60, check=role)
            except asyncio.TimeoutError:
                await ctx.send("Question cancelled, caused by timeout.")
                return
            await self.data.guild(ctx.guild).giverole.set(role.result.id)

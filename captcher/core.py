import asyncio
import contextlib
import datetime
import logging
import os
import time
from random import randint

import discord
from captcha.image import ImageCaptcha
from redbot.core import Config, commands, modlog
from redbot.core.bot import Red
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.chat_formatting import humanize_list, error, bold, info
from redbot.core.utils.predicates import MessagePredicate

log = logging.getLogger("predeactor.captcher")
log.setLevel(logging.DEBUG)


class Core(commands.Cog):

    __author__ = ["Predeactor"]
    __version__ = "Alpha 0.2"

    def __init__(self, bot: Red):
        self.bot = bot
        self.data = Config.get_conf(self, identifier=495954055)
        self.data.register_guild(
            giverole=None, verification_channel=None, active=False, logs_channel=None
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
        code = str(randint(1000, 9999))  # Cannot start with leading 0...
        return code, ImageCaptcha().generate(code)

    async def _challenge(
        self, member: discord.Member, channel: discord.TextChannel, start_reason: str
    ):
        code, image = self._generate_code_and_image()
        dfile = discord.File(image, filename=str(member.id) + ".png")
        message_content = (
            "Hello {member}, this server include an extra security layout to protect "
            "there members. You're asked to complete a security captacha in order to "
            "join this server. If you fail or take too much time to answer (5 "
            "minutes), you will be automatically kicked from this server.".format(
                member=member.mention
            )
        )
        logs_channel = await self._get_log_channel(member)
        if logs_channel:
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
                f"Received {role}." if role else "Unable to give role.",
            )
            failed = False
        else:
            final_answer = await channel.send(
                "{member}, your captcha is wrong.".format(member=member.mention)
            )
            failed = True
        await captcha_message.delete()
        time.sleep(5)
        if failed:
            result = await self._kicker(member)
        await message.delete()
        await final_answer.delete()
        if member.id in self._cache:
            del self._cache[member.id]

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
                    "Hello, you've been automatically kicked from {server} for not "
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
        role_id = await self.data.guild(member.guild).giverole()
        role = guild.get_role(role_id)
        if role is None:
            await self._report_log(member, "error", "Role cannot be found.")
            return
        try:
            await member.add_roles(role, reason="Completed captcha.")
        except discord.Forbidden:
            await self._report_log(member, "error", "Missing permissions.")
            return  # We're still unable to give, don't let staff thing it was
        return role.name

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
            with contextlib.suppress(Exception):
                await member.send("You have been kicked for failing your captcha.")
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
            await self._report_log(member, "error", "Unable to kick user.")

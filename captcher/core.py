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
from redbot.core.utils.chat_formatting import humanize_list

log = logging.getLogger("predeactor.captcher")
log.setLevel(logging.DEBUG)


class Core(commands.Cog):

    __author__ = ["Predeactor"]
    __version__ = "Alpha 0.1"

    def __init__(self, bot: Red):
        self.bot = bot
        self.data = Config.get_conf(self, identifier=495954055)
        self.data.register_guild(giverole=None, channel=None, active=False)
        self.path = bundled_data_path(self)
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
        code = str(randint(1000, 9999))
        image = ImageCaptcha()
        return code, image.generate(code)

    async def _challenge(self, member: discord.Member, channel: discord.TextChannel):
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
        try:
            captcha_message = await channel.send(content=message_content, file=dfile)
        except (discord.HTTPException, discord.Forbidden):
            log.warning(
                "Bot was strictly unable to send a message in channel: {name} for ID "
                "{id} in server {server}.".format(
                    name=channel.name, id=channel.id, server=channel.guild,
                )
            )

        def check(message):
            return message.author == member and message.channel == channel

        try:
            predicated = await self.bot.wait_for("message", timeout=10, check=check)
        except asyncio.TimeoutError:
            with contextlib.suppress(Exception):
                await member.send(
                    "Hello, you've been automatically kicked from {server} for not "
                    "answering the captcha to enter into the server. You can come back "
                    "and complete the captcha again."
                )
            await self._kicker(member)

        if predicated.content == str(code):
            await channel.send("OK")
        else:
            bot_message = await channel.send("Your captcha is wrong.")
            time.sleep(5)
            await self._kicker(member)
            await bot_message.delete()

    async def _kicker(self, member: discord.Member):
        try:
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
            await member.kick()
        except (discord.HTTPException, discord.Forbidden):
            log.warning(
                "Bot was strictly unable to kick an user in server: {name} for ID "
                "{id}.".format(name=member.guild.name, id=member.guild.id)
            )

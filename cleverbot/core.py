import asyncio
import logging
import random
from typing import Optional

import discord

import async_cleverbot as ac
from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_list

log = logging.getLogger("predeactor.cleverbot")
log.setLevel(logging.DEBUG)


class Core(commands.Cog):

    __author__ = ["Predeactor"]
    __version__ = "v1.0"

    def __init__(self, bot: Red):
        self.bot = bot
        self.conversation = {}
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

    async def _get_api_key(self):
        travitia = await self.bot.get_shared_api_tokens("travitia")
        # No need to check if the API key is not registered, the
        # @apicheck() do it automatically.
        return travitia.get("api_key")

    async def _make_cleverbot_session(self):
        cleverbot_session = ac.Cleverbot(
            await self._get_api_key(), context=ac.DictContext()
        )
        return cleverbot_session

    async def _ask_question(
        self, session, question: str, user_id: Optional[int] = None
    ):
        try:
            answer = await session.ask(
                question, user_id if user_id is not None else "00"
            )
            answered = True
        except Exception as e:
            answer = "An error happened: {error}. Please try again later. Session closed.".format(
                error=str(e)
            )
            answered = False
        return answer, answered

    def _message_by_timeout(self):
        messages = [
            "5 minutes without messages ? Sorry but I have to close your conversation.",
            "Sorry but after 5 minutes, I close your conversation.",
            "Conversation stopped.",
            "Since I'm lonely, I close our conversation.",
        ]
        return random.choice(messages)

    # Commands for settings

    @checks.is_owner()
    @commands.command(name="settraviliaapikey")
    async def travaitiaapikey(self, ctx: commands.Context, api_key: str):
        """Set the API key for Travitia API.
        
        To set the API key:
        1. Go to [this server](https://discord.gg/s4fNByu).
        2. Go to #playground and use `> api`.
        3. Say yes and follow instructions.
        4. When you receive your key, use this command again with your API key.
        """
        await ctx.bot.set_shared_api_tokens("travitia", api_key=api_key)
        try:
            await ctx.message.delete()
        except Exception:
            await ctx.send(
                "Please delete your message, token is sensitive and should be"
                " keeped secret."
            )
        await ctx.send("API key for `travitia` registered.")

    def cog_unload(self):
        if self.conversation:
            self.conversation = {}


def apicheck():
    """
        Check for hidding commands if the API key is not registered.
        Taken from https://github.com/PredaaA/predacogs/blob/master/nsfw/core.py#L200
        Thank Preda.
    """

    async def predicate(ctx: commands.Context):
        travitia_keys = await ctx.bot.get_shared_api_tokens("travitia")
        key = travitia_keys.get("api_key") is None
        if ctx.invoked_with == "help" and key:
            return False
        if key:
            await ctx.send("The API key is not registered, the command is unavailable.")
            log.warning(
                "Command has been refused. Missing API key for Travitia.\nFrom cog CleverBot."
            )
            return False
        return True

    return commands.check(predicate)

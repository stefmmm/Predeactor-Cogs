import discord
import logging
import asyncio
import random

import async_cleverbot as ac

from typing import Optional

from redbot.core.bot import Red
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_list

log = logging.getLogger("predeactor.cleverbot")
log.setLevel(logging.DEBUG)


class Core(commands.Cog):

    __author__ = ["Predeactor"]
    __version__ = "Alpha 0.5"

    def __init__(self, bot: Red):
        self.bot = bot
        self.conversation = {}
        self._init_logger()
        super().__init__()

    # Cog informations

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

    # Cog functions

    async def _get_api_key(self):
        travitia = await self.bot.get_shared_api_tokens("travitia")
        # No need to check if the API key is not registered, the
        # @apicheck() do it automatically.
        return travitia.get("api_key")

    async def _make_cleverbot_session(self):
        cleverbot_session = ac.Cleverbot(
            await self.get_api_key(), context=ac.DictContext()
        )
        return cleverbot_session

    async def _ask_question(self, session, question: str, user_id: Optional[int] = None):
        try:
            answer = await session.ask(question, user_id if user_id is not None else "00")
        except Exception as e:
            answer = "An error happened: {error}. Please try again later. Session closed.".format(
                error=str(e)
            )
            await self._close_cleverbot(session)
        return answer

    async def _check_user_in_conversation(self, ctx: commands.Context):
        try:
            if ctx.author.id in self.conversation[str(ctx.message.channel.id)]:
                await ctx.send("A conversation is already running.")
                return True
        except KeyError:
            await self.add_user(ctx.channel.id, ctx.author.id)
        return False

    def _check_channel_in_conversation(self, ctx: commands.Context, channel_id: int):
        if str(channel_id) not in self.conversation:
            return True
        return False

    async def _add_user(self, channel_id: int, user_id: int):
        if str(channel_id) not in self.conversation:
            self.conversation[str(channel_id)] = []
        self.conversation[str(channel_id)].append(user_id)

    async def _remove_user(self, channel_id: int, user_id: int, session):
        try:
            if len(self.conversation[str(channel_id)]) == 1:
                del self.conversation[str(channel_id)]  # Remove channel ID
                return
            self.conversation[str(channel_id)].remove(user_id)  # Only remove user
        except KeyError:
            await self.close_cleverbot(session)

    # Close methods

    async def _close_by_timeout(self, ctx: commands.Context, session):
        messages = [
            "5 minutes without messages ? Sorry but I have to close your conversation.",
            "Sorry but after 5 minutes, I close your conversation.",
            "Conversation stopped.",
            "Since I'm lonely, I close our conversation.",
        ]
        await ctx.send(random.choice(messages))
        await self.remove_user(ctx.channel.id, ctx.author.id, session)

    async def _close_cleverbot(self, session):
        await session.close()

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
            await ctx.send("Missing the API key, some commands won't be available.")
            return False
        if key:
            await ctx.send("The API key is not registered, the command is unavailable.")
            log.warning("Command has been refused. Missing API key for Travitia.")
            return False
        return True

    return commands.check(predicate)

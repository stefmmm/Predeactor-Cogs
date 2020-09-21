import ksoftapi

from typing import Literal

from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify, humanize_list

BASE_URL = "https://api.ksoft.si/lyrics/search"


class Lyrics(commands.Cog):

    __author__ = ["Predeactor"]
    __version__ = "Beta 0.5"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.client = None

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad!"""
        pre_processed = super().format_help_for_context(ctx)
        return (
            "{pre_processed}\n\nAuthor: {authors}\nCog Version: {version}\nThe cog is in beta "
            "and may be subect to unwanted behavior.".format(
                pre_processed=pre_processed,
                authors=humanize_list(self.__author__),
                version=self.__version__,
            )
        )

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        """
        Nothing to delete...
        """
        pass

    @commands.command(alias=["lyric"])
    async def lyrics(self, ctx: commands.Context, *, song_name: str):
        """Return the lyrics of a given music/song name.

        Powered by KSoft.Si.
        """
        try:
            client = await self.obtain_client()
        except AttributeError:
            await ctx.send("Not key for KSoft.Si has been set, ask owner to add a key.")
            return
        try:
            music_lyrics = await client.music.lyrics(song_name)
        except ksoftapi.NoResults:
            await ctx.send("No lyrics were found for your music.")
            return
        lyrics = str(music_lyrics[0].lyrics) + "\nPowered by KSoft.Si"
        for text in pagify(lyrics):
            await ctx.send(text)

    async def obtain_client(self):
        """Get a client and put it in self.client (For caching).

        Return:
            ksoftapi.Client: Client to use.
        """
        if self.client:
            return self.client
        keys = await self.bot.get_shared_api_tokens("ksoftsi")
        if keys.get("api_key"):
            self.client = ksoftapi.Client(keys.get("api_key"))
            return self.client
        return AttributeError("API key is not set.")

from asyncio import create_task
from asyncio.exceptions import TimeoutError as Te
from typing import Literal

import discord
import ksoftapi
from redbot.core import commands
from redbot.core.utils.chat_formatting import bold, humanize_list, pagify, inline
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import MessagePredicate

BASE_URL = "https://api.ksoft.si/lyrics/search"


class Lyrics(commands.Cog):

    __author__ = ["Predeactor"]
    __version__ = "v1.0.2"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.client = None

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad!"""
        pre_processed = super().format_help_for_context(ctx)
        return "{pre_processed}\n\nAuthor: {authors}\nCog Version: {version}".format(
            pre_processed=pre_processed,
            authors=humanize_list(self.__author__),
            version=self.__version__,
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
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, commands.BucketType.user, wait=False)
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
        except ksoftapi.APIError as e:
            await ctx.send("The API returned an unknow error: {error}".format(error=inline(e)))
            return
        except ksoftapi.Forbidden:
            await ctx.send("Request forbidden by the API.")
            return
        except KeyError:
            await ctx.send("The set API key seem to be wrong. Please contact the bot owner.")
        message, available_musics = await self._title_choose(music_lyrics)
        await ctx.maybe_send_embed(message)
        predicator = MessagePredicate.less(10, ctx)
        try:
            user_message = await self.bot.wait_for("message", check=predicator, timeout=60)
        except Te:
            await ctx.send("It's so silent on the outside...")
            return

        choosen_music = user_message.content
        if choosen_music not in available_musics:
            await ctx.send(
                "I was unable to find the corresponding music in the available music list."
            )
            return
        music = available_musics[choosen_music]
        embeds = []
        embed = discord.Embed(color=await ctx.embed_color(), title=music.name, description=None)
        embed.set_thumbnail(url=music.album_art)
        embed.set_footer(text="Powered by KSoft.Si.", icon_url=ctx.author.avatar_url)
        for text in pagify(music.lyrics):
            embed.description = text
            embeds.append(embed)
        create_task(menu(ctx, embeds, DEFAULT_CONTROLS))  # No await since max_concurrency is here

    @staticmethod
    async def _title_choose(list_of_music: list):
        """Function to return for requesting user's prompt, asking what music to choose.

        Parameter:
            - list_of_music: A list containing musics.

        Returns:
            A tuple with:
            - str: A list with musics name and their corresponding number.
            - dict: A list with the music according his number in the message.
        """
        message = "Please select the music you wish to get the lyrics by selecting the corresponding number:\n\n"
        method = {}
        n = 0
        for music in list_of_music:
            if not isinstance(music, ksoftapi.models.LyricResult):
                continue  # Not a music
            year = music.album_year[0]
            message += "`{number}` - {title} by {author} {year}\n".format(
                number=n,
                title=music.name,
                author=music.artist,
                year="(" + bold(str(year)) + ")" if year and int(year) > 1970 else "",
            )
            method[str(n)] = music
            n += 1
        return message, method

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

    @staticmethod
    async def __session_closer(client):
        await client.close()

    def cog_unload(self):
        if self.client:
            create_task(self.__session_closer(self.client))

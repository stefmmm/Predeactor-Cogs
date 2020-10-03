import re

import aiohttp
import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_list


class SXCU(commands.Cog):

    __author__ = ["Predeactor"]
    __version__ = "Alpha 0.1"

    # noinspection PyMissingConstructor
    def __init__(self, bot):
        self.bot = bot

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad!"""
        pre_processed = super().format_help_for_context(ctx)
        return "{pre_processed}\n\nAuthor: {authors}\nCog Version: {version}".format(
            pre_processed=pre_processed,
            authors=humanize_list(self.__author__),
            version=self.__version__,
        )

    # Commands logic

    async def _shorten_command_logic(self, ctx: commands.Context, link: str):
        possibly_no_link = re.search(r"(?P<url>https?://[^\s]+)", link)
        if not possibly_no_link:
            await ctx.send("It look like your link isn't valid.")
            return
        try:
            result = await self.shortener(link)
        except (RuntimeError, AttributeError) as error:
            await ctx.send(error)
            return
        url = result[0]
        deletion_url = result[1]
        try:
            embed = discord.Embed(title="Deletion Link", color=await ctx.embed_color())
            embed.add_field(
                name="Link",
                value="[Click for deleting access]({url}) to {link}.".format(
                    url=deletion_url, link=link
                ),
            )
            await ctx.author.send(embed=embed)
            dmed = True
        except discord.HTTPException:
            dmed = False
        embed = discord.Embed(
            title="Your link has been uploaded! 🎉", color=await ctx.embed_color()
        )
        if ctx.channel.permissions_for(ctx.me).embed_links and await ctx.embed_requested():
            content = "URL: {url}".format(url=url)
            embed.add_field(
                name="Your new URL!",
                value=(
                    "You can access to your website [by clicking on me]({url})!".format(url=url)
                ),
            )
            if not dmed:
                content += "\nDeletion URL: {url}".format(url=deletion_url)
                embed.add_field(
                    name="Deletion URL",
                    value=(
                        "Since I was unable to DM you with the deletion link, [you can delete the"
                        " access by clicking here]({url}).".format(url=deletion_url)
                    ),
                )
            await ctx.send(content=content, embed=embed)
            return
        else:
            message = (
                "Your link has been uploaded! 🎉\nYou can access it through this link: "
                "{url}".format(url=url)
            )
            if not dmed:
                message += (
                    "\n\nI was unable to DM you the deletion link, so use this link to delete "
                    "access: {delurl}".format(url=url, delurl=deletion_url)
                )
        await ctx.send(message)

    async def shortener(self, link: str):
        """Function to shorten a link.

        Parameter:
            link: str: The link we're reducing.

        Return:
            list: Return the URL and the URL used for deletion.

        Raise:
            AttributeError: No URL are defined.
            RuntimeError: An unknow error happened.
        """
        url = await self._obtain_creditentials(need_token=False)
        payload = {"link": link}
        async with aiohttp.ClientSession() as session:
            async with session.post(url + "/shorten", data=payload) as response:
                status_code = response.status
                if status_code != 200:
                    raise RuntimeError("An error has been returned by the server.")
                result: dict = await response.json()
        return [result["url"], result["del_url"]]

    async def _obtain_creditentials(self, need_token: bool = True):
        """Return the URL and the token if needed.

        Parameter:
            need_token: bool: If a token must be added.

        Return:
            str: The URL.
            str: The token if requested.
        """
        listing = []
        keys = await self.bot.get_shared_api_tokens("sxcu")
        possible_url = keys.get("url")
        if not possible_url:
            raise AttributeError("URL for sxcu.net is not configured.")
        listing.append(possible_url)
        if need_token:
            possible_token = keys.get("api_key")
            if possible_token:
                listing.append(possible_token)
            raise AttributeError("API key for sxcu.net is not set.")
        if possible_url.endswith("/"):
            possible_url = possible_url[:-1]
            await self.bot.set_shared_api_tokens("sxcu", url=possible_url)
        return listing if need_token else possible_url

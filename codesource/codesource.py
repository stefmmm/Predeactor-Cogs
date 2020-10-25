import inspect

from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from typing import Literal


class CodeSource(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

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

    @commands.command(aliases=["sourcecode", "source", "code"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.is_owner()
    async def codesource(self, ctx: commands.Context, *, command: str):
        """
        Get the source code of a command.
        """
        command = self.bot.get_command(command)
        if command is None:
            await ctx.send("Command not found.")
            return
        source_code = inspect.getsource(command.callback)
        temp_pages = []
        pages = []
        for page in pagify(source_code, escape_mass_mentions=True, page_length=1980):
            temp_pages.append("```py\n" + str(page).replace("```", "`\u17b5``") + "```")
        max_i = len(temp_pages)
        i = 1
        for page in temp_pages:
            pages.append(f"Page {i}/{max_i}\n" + page)
            i += 1
        await menu(ctx, pages, controls=DEFAULT_CONTROLS)

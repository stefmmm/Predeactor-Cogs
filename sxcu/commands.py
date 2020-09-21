from .core import SXCU
from redbot.core import commands


class Commands(SXCU, name="SXCU"):
    @commands.command()
    async def shorten(self, ctx: commands.Context, link: str):
        """Shorten a link."""
        await self._shorten_command_logic(ctx, link)

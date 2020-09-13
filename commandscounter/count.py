from typing import Literal

from redbot.core import commands
from redbot.core.utils.chat_formatting import bold, humanize_list, inline, pagify


class CommandsCounter(commands.Cog):
    """Count all commands used."""

    __author__ = ["Predeactor"]
    __version__ = "v1"

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        pass  # Nothing to delete.

    def __init__(self, bot):
        self.bot = bot
        self.commands = {}
        super(CommandsCounter, self).__init__()

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad!"""
        pre_processed = super().format_help_for_context(ctx)
        return "{pre_processed}\n\nAuthor: {authors}\nCog Version: {version}".format(
            pre_processed=pre_processed,
            authors=humanize_list(self.__author__),
            version=self.__version__,
        )

    @commands.group(invoke_without_command=True)
    async def count(self, ctx: commands.Context, *, command: str):
        """Know how many time a command has been used.

        If the command had an error one time, it will also be shown.
        """
        str_command = command.lower()
        if str_command in self.commands:
            message = "{command} has been used {count} time since last reboot".format(
                command=inline(str_command), count=self.commands[str_command]["count"]
            )
            if self.commands[str_command]["error"] >= 1:
                message += ", and sent an error {error} time".format(
                    error=self.commands[str_command]["error"]
                )
            message += "."
            await ctx.send(message)
        else:
            await ctx.send(
                "{command} hasn't been used, yet...".format(command=inline(str_command))
            )

    @count.command()
    async def all(self, ctx: commands.Context):
        """List all commands and how many time they have been used."""
        message = bold("All commands usage since last reboot:\n\n")
        for data in self.commands.items():
            message += "- {command}: Used {count} time.\n".format(
                command=inline(data[0]), count=data[1]["count"]
            )
        for text in pagify(message):
            await ctx.send(text)

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        command = str(ctx.command)
        if ctx.message.author.bot is False:
            if command not in self.commands:
                self.commands[command] = {}
                self.commands[command]["count"] = 1
                self.commands[command]["error"] = 0
                return
            self.commands[command]["count"] += 1

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        command = str(ctx.command)
        if ctx.message.author.bot is False:
            if command not in self.commands:
                self.commands[command] = {}
                self.commands[command]["count"] = 1
                self.commands[command]["error"] = 1
                return
            self.commands[command]["error"] += 1

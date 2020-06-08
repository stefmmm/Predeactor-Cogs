import discord
import logging
import asyncio
import random

from redbot.core import commands, checks
from .core import Core, apicheck

log = logging.getLogger("predeactor.cleverbot")


class CleverBot(Core):
    """Ask questions to Cleverbot or even start a Conversation with her!"""

    @apicheck()
    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def ask(self, ctx: commands.Context, question: str):
        """Ask an unique question to Cleverbot.
        
        You won't have a discussion with Cleverbot, you're just 
        asking a single question."""
        async with ctx.typing():
            session = await self.make_cleverbot_session()
            await ctx.send(await self.ask_question(session, question))
            await session.close()

    @apicheck()
    @commands.command()
    async def conversation(self, ctx: commands.Context):
        """Start a conversation with Cleverbot
        You don't need to use a prefix or the command using this mode."""
        user = ctx.author

        try:
            result = await self.check_user_in_conversation(ctx)
            if result is True:
                return

            await ctx.send(
                "Starting a new Cleverbot session!\n\nSay `close` to stop the conversation with me"
                " !\n\nAfter 5 minutes without answer, I will automatically close your "
                "conversation."
            )
            cleverbot = await self.make_cleverbot_session()

            while True:  # Logic is from Laggron's Say cog
                try:
                    message = await self.bot.wait_for("message", timeout=300)
                except asyncio.TimeoutError:
                    await self.close_by_timeout(ctx, cleverbot)
                    await cleverbot.close()
                    return
                result = self.check_channel_in_conversation(ctx, message.channel.id)
                if result is True:
                    return
                if message.channel != ctx.channel:
                    continue
                if message.author == user:
                    if message.content.lower() == "close":
                        await self.remove_user(ctx.channel.id, ctx.author.id, cleverbot)
                        await cleverbot.close()
                        await ctx.send("Conversation closed.")
                        return
                    async with ctx.typing():
                        await ctx.send(
                            message.author.mention
                            + ", "
                            + str(await self.ask_question(cleverbot, message.content))
                        )

        except Exception as e:
            await ctx.send(f"An error happened: {e}")
            log.warning(
                "Exception while parsing the command {prefix}conversation: {e}.\nIf this error occur again or seem related to code issue, please contact the cog author."
            )
            try:
                await self.close_cleverbot(cleverbot)
            except UnboundLocalError:  # Happens if there's no session
                log.warning("No session has been found.")
                pass

    @checks.is_owner()
    @commands.command(name="settraviliaapikey")
    async def travailiaapikey(self, ctx: commands.Context, api_key: str = None):
        """Set the API key for Travitia API.
        
        To set the API key:
        1. Go to [this server](https://discord.gg/s4fNByu).
        2. Go to #playground and use `> api`.
        3. Say yes and give some explanation.
        4. Wait for the staff to accept your application.
        5. When you receive your key, use this command again with your API key.
        """
        if api_key:
            await ctx.bot.set_shared_api_tokens("travitia", api_key=api_key)
            try:
                await ctx.message.delete()
            except Exception:
                await ctx.send(
                    "Please delete your message, token is sensitive and should be keeped secret."
                )
                pass
            await ctx.send("API key for `travitia` registered.")
        else:
            await ctx.send_help()

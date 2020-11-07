from .cleverbot import CleverBot

from redbot.core.bot import Red

__red_end_user_data_statement__ = "This cog does not save data about users persistently."


async def setup(bot: Red):
    await bot.send_to_owners(
        "Hello, Capitaine speaking.\nActually, you **can't** load the CleverBot due to a missing "
        "dependency (async_cleverbot), Github repo has been deleted and you can't use this cog "
        "UNLESS you had used this cog before OR installed the async_cleverbot package.\n\n"
        "I am trying my best to make the repo back again as long as the API endpoint is not dead "
        "but just the repo's dependency. If you want to know when the cog's dependency will be "
        "back, come join my support server: https://discord.gg/zg6ydua\n\nThis message will come "
        "back if you reload the cog or reboot your bot, I'm sorry, but I have to, obviously, this "
        "message will be deleted when the issue is fixed."
    )
    bot.add_cog(CleverBot(bot))

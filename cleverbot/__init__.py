from .cleverbot import CleverBot


def setup(bot):
    bot.add_cog(CleverBot(bot))

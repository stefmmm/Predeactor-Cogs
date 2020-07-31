from .cleverbot import CleverBot

__end_user_data_statement__ = "This cog does not save data about users persistently."


def setup(bot):
    bot.add_cog(CleverBot(bot))

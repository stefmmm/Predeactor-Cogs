from .customcooldown import CustomCooldown

end_user_data_statement = (
    "This cog store data about users persistently for required reasons. Red may store "
    "where and when you send your last message, depending cog's parameter (If sent in a"
    " channel/category in cooldown) as your Discord's ID."
)


def setup(bot):
    bot.add_cog(CustomCooldown(bot))

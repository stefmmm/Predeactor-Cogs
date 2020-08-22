from .coronavirus import Coronavirus

end_user_data_statement = "This cog does not save data about users persistently."


def setup(bot):
    bot.add_cog(Coronavirus(bot))

from .coronavirus import Coronavirus


def setup(bot):
    bot.add_cog(Coronavirus(bot))

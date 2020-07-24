from .captcher import Captcher


def setup(bot):
    bot.add_cog(Captcher(bot))

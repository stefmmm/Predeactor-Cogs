from .leaderboard import LeaderBoard


def setup(bot):
    bot.add_cog(LeaderBoard(bot))

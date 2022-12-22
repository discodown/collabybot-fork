import discord
from discord.ext import commands
from discord.ext.commands import Context
from github.MainClass import Github
import json

class AuthCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def notify(self, ctx: discord.ApplicationContext):
        pass

    @commands.slash_command(name='gh-auth',
                            description='Subscribe to pull request notifications in this channel.')
    async def gh_auth(self, ctx: discord.ApplicationContext):
        pass

    
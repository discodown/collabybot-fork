import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.ext.commands.errors import CommandInvokeError
from github import Github
from jira import JIRA, JIRAError
import discord

from cogs.github_cog import *
from cogs.jira_cog import *

cogs_list = []

class DiscordCollabyBot(Bot):
    """
    Discord implementation of CollabyBot.

    Extends the Bot class from discord.ext.commands. on_message() and
    on_ready() are overridden methods from the discord module for handling
    events in Discord.

    Methods
    --------
    on_message(message):
        Triggered when a message is received.

    on_ready():
        Triggered when the bot is operational.

    handle_responses(message): str
        Creates a response to a message received in Discord.

    get_commands():
        Send a message listing all of CollabyBot's Discord slash commands.

    send_payload_message(payload, event):
        Direct a payload to the correct Discord channels.

    pull_requests():
        Subscribe a channel to pull request notifications.

    issues():
            Subscribe a channel to pull issue notifications.

    commits():
            Subscribe a channel to commit notifications.

    ping():
        Respond with 'pong'.

    open_pull_requests(repo):
        Respond with a list of a repository's open pull requests.

    add(repo):
        Add a repository to CollabyBot.

    get_repos():
        Get a list of repos currently tracked by CollabyBot.

    jira_setup_token():
        Setup a Jira token to monitor issues in a Jira workspace.

    jira_get_issue():
        Respond with information about a Jira issue.

    jira_get_sprint():
        Get a summary of a project's active sprint.

    add_all_commands(bot):
        Register all slash commands with the Discord bot.

    """

    async def on_ready(self):
        """
        Triggered when the bot becomes operational.

        This method overrides discord.on_ready(), which is called when the bot
        is finished preparing data received from Discord.

        :return: None
        """

        print(f'{self.user} is now running!')

    async def on_message(self, message):
        """
        Triggered when a message is received.

        This method overrides discord.on_message(), which is called every time
        a message is sent in the server where the bot is running. It will parse the
        contents of the message, send a response, and look for bot commands in the message.

        :param message: Message received in Discord.
        :return: None
        """

        # make sure that bot doesn't respond to itself
        if message.author == self.user:
            return

        username = str(message.author)
        user_message = str(message.content)
        channel = str(message.channel)

        # prints in terminal message log
        print(f'{username} said {user_message} in channel #{channel}')

        await self.process_commands(message)

    async def on_mention(self, message):
        """
        Triggered when the bot is mentioned.

        :param message:
        :return: None
        """
        pass

    @commands.command(name='commands', description='List all supported commands.')
    async def get_commands(ctx: discord.ApplicationContext):
        """
        Send a message listing all of CollabyBot's Discord slash commands.

        This method implements the /commands Discord command.

        :return: None
        """
        embed = discord.Embed(color=discord.Color.blurple(), title=f'Here\'s a list of commands you can use:\n')
        for command in ctx.bot.commands:
            embed.add_field(name=f'/{command.name}:', value=f'{command.description}', inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='ping', description='Respond with pong')
    async def ping(ctx: discord.ApplicationContext):
        """
        Send 'pong' in response to 'ping'.

        This method implements the /ping Discord command.

        :return: None
        """
        await ctx.send('Pong.')

    @classmethod
    def add_all_commands(cls, bot):
        """
        Register all commands with the bot.

        This method is only called once after initializing the DiscordCollabyBot
        object from the main script in order to register all command methods
        with the bot.

        :param bot: The DiscordCollabyBot instance.
        :return: None
        """

        # every new command will need to be added here
        bot.add_cog(GitHubCog(bot))
        bot.add_cog(JiraCog(bot))
        cls.add_command(bot, command=cls.get_commands)
        cls.add_command(bot, command=cls.ping)

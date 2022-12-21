import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.ext.commands.errors import CommandInvokeError
from github import Github
from jira import JIRA, JIRAError
from discord.ext.pages import Page, Paginator

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

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(DiscordCollabyBot, cls).__new__(cls)
        return cls.instance

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

    @commands.slash_command(name='commands', description='List all supported commands.')
    async def get_commands(ctx: discord.ApplicationContext):
        """
        Send a message listing all of CollabyBot's Discord slash commands.

        This method implements the /commands Discord command.

        :return: None
        """
        general_embed = discord.Embed(color=discord.Color.blurple(), title=f'General Commands',
                                      description='Commands related to the general functionality of the bot.')
        github_embed = discord.Embed(color=discord.Color.blurple(), title=f'GitHub Commands',
                                     description='Commands related to GitHub.')
        jira_embed = discord.Embed(color=discord.Color.blurple(), title=f'Jira Commands',
                                   description='Commands related to Jira.')
        pages = []
        general_embed.add_field(name='/ping:', value='Responds with pong.', inline=False)
        general_embed.add_field(name='/commands:', value='List all supported commands.', inline=False)
        for command in ctx.bot.get_cog('GitHubCog').get_commands():
            github_embed.add_field(name=f'/{command.name}:', value=f'{command.description}', inline=False)
        for command in ctx.bot.get_cog('JiraCog').get_commands():
            jira_embed.add_field(name=f'/{command.name}:', value=f'{command.description}', inline=False)

        pages.append(Page(
            content='Here\'s a list of commands you can use.',
            embeds=[general_embed]
        ))
        pages.append(Page(
            content='Here\'s a list of commands you can use.',
            embeds=[github_embed]
        ))
        pages.append(Page(
            content='Here\'s a list of commands you can use.',
            embeds=[jira_embed]
        ))

        paginator = Paginator(pages=pages)
        await paginator.respond(ctx.interaction, ephemeral=False)

    @commands.slash_command(name='ping', description='Responds with pong.')
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
        bot.load_extension('src.bot.cogs.github_cog')
        bot.load_extension('src.bot.cogs.jira_cog')
        cls.add_application_command(bot, command=cls.get_commands)
        cls.add_application_command(bot, command=cls.ping)

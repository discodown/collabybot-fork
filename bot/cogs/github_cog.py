import asyncio
from queue import Queue
import discord
from discord import Guild, Member
from discord.ext import commands
from discord.ext.bridge import guild_only
from discord.ext.commands import Context
from github.MainClass import Github
from github.GithubException import UnknownObjectException, GithubException
import json
from bot.embeds import *
from os import curdir

with open('bot/cogs/json_/repos.json') as f:
    repos = json.load(f)  # repo names and list of branches
    f.close()
with open('bot/cogs/json_/pr_subscribers.json') as f:
    pr_subscribers = json.load(f)  # channel ids of channels subscribed to pull requests
    f.close()
with open('bot/cogs/json_/commit_subscribers.json') as f:
    commit_subscribers = json.load(f)  # channel ids of channels subscribed to commits, one list per branch
    f.close()
with open('bot/cogs/json_/issue_subscribers.json') as f:
    issue_subscribers = json.load(f)  # channel ids of channels subscribed to issues
    f.close()
with open('bot/cogs/json_/gh_tokens.json') as f:
    gh_tokens = json.load(f)  # channel ids of channels subscribed to issues
    f.close()

URL = 'https://9a28-104-254-90-195.ngrok.io'

auth_queue = Queue(maxsize=1)
queue_lock = asyncio.Lock()


class GitHubCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    github = discord.SlashCommandGroup('github', 'GitHub related commands.')
    issues = github.create_subgroup('issues', 'Subscribe/unsubscribe to GitHub issue notifications.')
    pull_requests = github.create_subgroup('pull-requests',
                                           'Subscribe/unsubscribe to GitHub pull request notifications.')
    commits = github.create_subgroup('commits', 'Subscribe/unsubscribe to GitHub commit notifications.')
    repositories = github.create_subgroup('repo', 'Add/remove GitHub repos.')

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild):

        server = str(guild.id)
        members = guild.members

        for user in members:
            if gh_tokens.get(str(user.id)) is not None:
                gh_tokens.pop(str(user.id))

        for repo in repos.get(server):
            if issue_subscribers.get(repo) is not None:
                issue_subscribers.pop(repo)
            if commit_subscribers.get(repo) is not None:
                commit_subscribers.pop(repo)
            if pr_subscribers.get(repo) is not None:
                pr_subscribers.pop(repo)

        if repos.get(server) is not None:
            repos.pop(server)
        self.save_dicts()

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        """
        Remove existing records of a member when the leave the server.

        Parameters
        ----------
        member

        Returns
        -------
        None
        """

        user = str(member.id)

        if gh_tokens.get(user) is not None:
            gh_tokens.pop(user)
        self.save_dicts()

    def save_dicts(self):
        with open('bot/cogs/json_/repos.json', 'w') as f:
            json.dump(repos, f)  # repo names and list of branches
            f.close()
        with open('bot/cogs/json_/pr_subscribers.json', 'w') as f:
            json.dump(pr_subscribers, f)  # channel ids of channels subscribed to pull requests
            f.close()
        with open('bot/cogs/json_/commit_subscribers.json', 'w') as f:
            json.dump(commit_subscribers, f)  # channel ids of channels subscribed to commits, one list per branch
            f.close()
        with open('bot/cogs/json_/issue_subscribers.json', 'w') as f:
            json.dump(issue_subscribers, f)  # channel ids of channels subscribed to issues
            f.close()
        with open('bot/cogs/json_/gh_tokens.json', 'w') as f:
            json.dump(gh_tokens, f)  # channel ids of channels subscribed to issues
            f.close()

    async def send_payload_message(self, payload, event, repo, branch='main'):
        """
        This method will send payloads to Discord channels subscribed to
        the corresponding event type.

        :param payload: The payload formatted as a notification string.
        :param event: The event type of the payload.
        :return: None
        """

        if event == 'pull_request':
            embed = discord.Embed(title='GitHub Event Notification',
                                  color=discord.Color.teal())
            embed.add_field(name='Pull Request', value=payload, inline=False)
            for channel in pr_subscribers[repo]:
                await self.bot.get_channel(int(channel)).send(embed=embed)
        elif event == 'issue':
            embed = discord.Embed(title='GitHub Event Notification',
                                  color=discord.Color.magenta())
            embed.add_field(name='Issue', value=payload, inline=False)
            for channel in issue_subscribers[repo]:
                await self.bot.get_channel(int(channel)).send(embed=embed)
        elif event == 'push':
            try:
                embed = discord.Embed(title='GitHub Event Notification',
                                      color=discord.Color.purple())
                embed.add_field(name='Commit', value=payload, inline=False)
                for channel in commit_subscribers.get(repo).get(branch):
                    await self.bot.get_channel(int(channel)).send(embed=embed)
            except TypeError:
                print('No subscribers')

    @pull_requests.command(name='subscribe', description='Subscribe to pull request notifications in this channel.')
    @guild_only()
    async def pull_requests_sub(self, ctx: discord.ApplicationContext, repo=''):
        """
        Subscribe a channel to pull request notifications.

        A repository must be specified by providing an argument to the command.
        If no argument was given, responds with a list of available repositories.

        :param str repo: Name of repository to subscribe to.
        :return: None
        """

        channel = str(ctx.channel.id)
        server = str(ctx.guild_id)
        if repo == '':
            await ctx.respond(embed=UsageMessage('/github pull-requests subscribe <REPO_NAME>'))
            if not repos.get(server):
                await ctx.respond(embed=HelpEmbed('No Repositories Added',
                                                  'You haven\'t added any repositories to CollabyBot yet. '
                                                  'Use /github repo add <REPO_OWNER>/<REPO_NAME> to add one.'))
            else:
                repo_list = ''
                for r in repos[server].keys():
                    repo_list += f'{r}\n'
                await ctx.respond('Subscribe to one of the following added repositories using '
                                  '**/gh-pull-requests <REPO_NAME>**:',
                                  embed=HelpEmbed('Available Repositories', f'{repo_list}'))
        elif repo not in repos[server].keys():

            await ctx.respond(embed=discord.Embed(
                color=discord.Color.yellow(),
                description=f'Repository {repo} hasn\'t been added to CollabyBot yet. '
                            f'Use /github repo add <REPO_OWNER>/<REPO_NAME> to add it.')
            )
        elif channel not in pr_subscribers[repo]:
            pr_subscribers[repo].append(channel)
            await ctx.respond(embed=PullRequestSubscriptionSuccess(ctx.channel.name, repo))
        else:
            await ctx.respond(embed=HelpEmbed('Channel Already Subsribed',
                                              f'#{ctx.channel.name} is already subscribed to to pull requests '
                                              f'for {repo}.')
                              )

    @issues.command(name="subscribe", description="Subscribe to issue notifications in this channel.")
    @guild_only()
    async def issues_sub(self, ctx: discord.ApplicationContext, repo=''):
        """
        Subscribe a channel to issue notifications.

        A repository must be specified by providing an argument to the command.
        If no argument was given, responds with a list of available repositories.

        :param str repo: Name of repository to subscribe to.
        :return: None
        """

        channel = str(ctx.channel.id)
        server = str(ctx.guild_id)

        if repo == '':
            await ctx.respond(embed=UsageMessage('/github issues subscribe <REPO_NAME>'))
            if not repos.get(server):  # no repos added yet
                await ctx.respond(embed=HelpEmbed('No Repositories Added',
                                                  'You haven\'t added any repositories to CollabyBot yet. '
                                                  'Use /github repo add <REPO_OWNER>/<REPO_NAME> to add one.'))
            else:
                repo_list = ''
                for r in repos[server].keys():
                    repo_list += f'{r}\n'
                await ctx.respond(
                    'Subscribe to one of the following added repositories using **/gh-issues <REPO_NAME>**:',
                    embed=HelpEmbed('Available Repositories', repo_list))

        elif repo not in repos[server].keys():  # repo hasn't been added yet
            await ctx.respond(embed=HelpEmbed('Repo Not Added',
                                              f'Repository {repo} hasn\'t been added to CollabyBot yet. '
                                              f'Use /github repo add <REPO_OWNER>/<REPO_NAME> to add it.'))
        elif channel not in issue_subscribers[repo]:  # channel isn't subscribed
            issue_subscribers[repo].append(channel)
            await ctx.respond(embed=IssueSubscriptionSuccess(ctx.channel.name, repo))

        else:  # channel is already subscribed
            await ctx.respond(embed=HelpEmbed('Channel Already Subscribed', f'#{ctx.channel.name} is already subscribed'
                                                                            f' to to issues for {repo}.'))

    @repositories.command(name='add',
                          description='Add a repo to the list of repositories you want notifications from.')
    @guild_only()
    async def add_repo(self, ctx: discord.ApplicationContext, repo_name=''):
        """
        Add a repository to CollabyBot's list of repositories.

        When a repo is added, its branches are retrieved using the GitHub API via
        PyGithub's Github class. Subscriber lists for each event type are
        initialized to empty lists (or a dict of empty lists with branches as keys
        for commits).

        :param str repo: The full name of the repository to add.
        :return: None
        """

        server = str(ctx.guild_id)
        if repo_name == '':
            await ctx.respond(embed=UsageMessage(f'/github repo add <REPO_OWNER>/<REPO_NAME>'))
        else:
            token = gh_tokens.get(str(ctx.author.id))
            if token is None:
                await ctx.respond(embed=GitHubNotAuthenticatedError(ctx.user.name))
            else:
                # get repo via pygithub
                g = Github(token)
                repo = g.get_repo(repo_name)
                if not repos.get(server):
                    repos[server] = {}
                if repo.full_name in repos.get(server):
                    await ctx.respond(embed=HelpEmbed('Repository Already Added',
                                                      f'{repo.full_name} has already been added.'))
                else:
                    try:
                        repo.create_hook(name='web',
                                         config={'url': f'{URL}/webhook/commits',
                                                 'content_type': 'json',
                                                 'insecure_ssl': 1,
                                                 },
                                         events=['push'],
                                         active=True
                                         )
                        repo.create_hook(name='web',
                                         config={'url': f'{URL}/webhook/issues',
                                                 'content_type': 'json',
                                                 'insecure_ssl': 1,
                                                 },
                                         events=['issues'],
                                         active=True
                                         )
                        repo.create_hook(name='web',
                                         config={'url': f'{URL}/webhook/pull-request',
                                                 'content_type': 'json',
                                                 'insecure_ssl': 1,
                                                 },
                                         events=['pull_request'],
                                         active=True
                                         )
                        branches = repo.get_branches()  # get branches via pygithub
                        brs = [b.name for b in branches]
                        repos[server][repo.full_name] = brs  # dict entry for repo is list of branches
                        # initialize all subscriber lists
                        commit_subscribers[repo.full_name] = {b: [] for b in brs}
                        pr_subscribers[repo.full_name] = []
                        issue_subscribers[repo.full_name] = []
                        await ctx.respond(embed=RepoAddSuccess(repo.full_name))
                    except (GithubException, UnknownObjectException) as ex:
                        if ex.status == 422:
                            await ctx.respond(embed=GitHub422Error(repo.full_name, ctx.guild.name))
                            branches = repo.get_branches()  # get branches via pygithub
                            brs = [b.name for b in branches]
                            repos[server][repo.full_name] = brs  # dict entry for repo is list of branches
                            # initialize all subscriber lists
                            commit_subscribers[repo.full_name] = {b: [] for b in brs}
                            pr_subscribers[repo.full_name] = []
                            issue_subscribers[repo.full_name] = []
                            await ctx.respond(embed=RepoAddSuccess(repo.full_name))
                        elif ex.status == 403:
                            await ctx.respond(embed=GitHub403Error(ex.data['message']))
                        elif ex.status == 404:
                            await ctx.respond(embed=GitHub404Error(repo.full_name))

    @github.command(name='repos', description='See the list of repos added to CollabyBot.')
    @guild_only()
    async def get_repos(self, ctx: discord.ApplicationContext):
        """
        Get a list of repositories added to CollabyBot.

        :return: None
        """

        server = str(ctx.guild_id)

        if not repos.get(server):
            await ctx.respond(embed=HelpEmbed('No Repositories Added',
                                              'You haven\'t added any repositories to CollabyBot yet. '
                                              'Use **/github repo add <REPO_OWNER>/<REPO_NAME>** to add one.'))
        else:
            repo_list = ''
            for r in repos[server].keys():
                repo_list += f'{r}\n'
            list_embed = discord.Embed(color=discord.Color.blurple(),
                                       title=f'Current repositories:',
                                       description=f'{repo_list}')
            await ctx.respond(embed=list_embed)

    @commits.command(name='subscribe', description='Subscribe to commit notifications in this channel.')
    @guild_only()
    async def commits_sub(self, ctx: discord.ApplicationContext, repo='', branch=''):
        """
        Subscribe a channel to commit notifications.

        A repository must be specified by providing an argument to the command.
        If no argument was given, responds with a list of available repositories.
        If an optional branch argument was given, subscribes to events from
        that branch only.

        :param str repo: Name of repository to subscribe to.
        :param str branch: Name of branch to subscribe to.
        :return: None
        """

        channel = str(ctx.channel.id)
        server = str(ctx.guild_id)

        if repo == '':
            await ctx.respond(embed=UsageMessage('/github commits subscribe <REPO_NAME> [BRANCH_NAME]'))
            if not repos.get(server):
                await ctx.respond(embed=HelpEmbed('No Repositories Added',
                                                  'You haven\'t added any repositories to CollabyBot yet. '
                                                  'Use **/github repo add <REPO_OWNER>/<REPO_NAME>** to add one.'))
            else:
                repo_list = ''
                for r in repos[server].keys():
                    repo_list += f'{r}\n'
                await ctx.respond('Subscribe to one of the following added repositories '
                                  'using **/gh-commits <REPO_NAME> [BRANCH_NAME]**:',
                                  embed=HelpEmbed('Available Repositories', repo_list))
        elif repo not in repos[server].keys():
            await ctx.respond(embed=HelpEmbed('Repo Not Added',
                                              f'Repository {repo} hasn\'t been added to CollabyBot yet. '
                                              f'Use **/github repo add <REPO_OWNER>/<REPO_NAME>** to add it.'))
        else:
            if branch == '':
                for b in repos[server].get(repo):
                    if channel not in commit_subscribers[repo][b]:
                        commit_subscribers[repo][b].append(channel)
                        await ctx.respond(embed=CommitSubscriptionSuccess(ctx.channel.name, repo, branch))
                    else:
                        await ctx.respond(embed=HelpEmbed('Channel Already Subscribed'
                                                          f'#{ctx.channel.name} is already subscribed to commits for '
                                                          f'{repo} on {branch}.'))
            else:
                if channel not in commit_subscribers[repo][branch]:
                    commit_subscribers[repo][branch].append(channel)
                    await ctx.respond(embed=CommitSubscriptionSuccess(ctx.channel.name, repo, branch))
                else:
                    await ctx.respond(embed=HelpEmbed('Channel Already Subscribed'
                                                      f'#{ctx.channel.name} is already subscribed to commits for '
                                                      f'{repo} on {branch}.'))

    @github.command(name='open-pull-requests', description='Show open pull requests in testing repo.')
    @guild_only()
    async def open_pull_requests(self, ctx: discord.ApplicationContext, repo=''):
        """
        Get a list of a repository's open pull requests.

        Connect to a public repository using a Github object, then get all of the repo's
        open PR's and format them as a list with links and send it as a Discord embed.

        :param repo: The repository to get PRs from.
        :return: None
        """

        if repo == '':
            await ctx.respond(embed=UsageMessage('/github open-pull-requests <REPO_OWNER>/<REPO_NAME>'))
        else:
            openpr_embed = discord.Embed(color=discord.Color.blurple(), title=f'Open pull requests in {repo}:\n')
            # get repo via pygithub
            g = Github()
            repo = g.get_repo(repo)
            # get open(active) PR
            pulls = repo.get_pulls(state='open')
            for pr in pulls:
                openpr_embed.add_field(name=f'{pr.title}:', value=f'{pr.url}', inline=False)
            await ctx.respond(embed=openpr_embed)

    @github.command(name='auth', description='Authenticate with the CollabyBot OAuth app for full access to GitHub '
                                             'repositories.')
    @guild_only()
    async def gh_auth(self, ctx: discord.ApplicationContext):
        user_id = str(ctx.author.id)

        if gh_tokens.get(user_id) is not None:
            await ctx.respond(embed=HelpEmbed(title='User Already Authenticated',
                                              message=f'User {ctx.user.name} is already authenticated with GitHub.'))
        else:
            await queue_lock.acquire()
            user = ctx.author
            auth_queue.put(user_id)
            await user.send('Click here to authorize CollabyBot to access GitHub repositories on your behalf.',
                            view=AuthButton())
            await ctx.respond('Follow the link in your DMs to authorize CollabyBot on GitHub.')

    async def add_gh_token(self, token: str):
        user_id = auth_queue.get()
        queue_lock.release()
        gh_tokens[user_id] = token
        user = await self.bot.fetch_user(int(user_id))
        await user.send('Authentication complete.')


def setup(bot):
    bot.add_cog(GitHubCog(bot))


class AuthButton(discord.ui.View):
    def __init__(self):
        super().__init__()
        button = discord.ui.Button(label="Authorize",
                                   style=discord.ButtonStyle.link,
                                   url=f'https://9a28-104-254-90-195.ngrok.io/auth/github')
        self.add_item(button)

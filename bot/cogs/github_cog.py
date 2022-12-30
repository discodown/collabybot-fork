import asyncio
from queue import Queue
import discord
from discord import Guild, Member
from discord.ext import commands
from discord.ext.bridge import guild_only
from discord.ext.commands import Context
from discord.ext.pages import Page, Paginator
from github.MainClass import Github
from github.GithubException import UnknownObjectException, GithubException
import json
from bot.embeds import *
from os import curdir

# with open('bot/cogs/json_/repos.json') as f:
#     repos = json.load(f)  # repo names and list of branches
#     f.close()
# with open('bot/cogs/json_/pr_subscribers.json') as f:
#     pr_subscribers = json.load(f)  # channel ids of channels subscribed to pull requests
#     f.close()
# with open('bot/cogs/json_/commit_subscribers.json') as f:
#     commit_subscribers = json.load(f)  # channel ids of channels subscribed to commits, one list per branch
#     f.close()
# with open('bot/cogs/json_/issue_subscribers.json') as f:
#     issue_subscribers = json.load(f)  # channel ids of channels subscribed to issues
#     f.close()
# with open('bot/cogs/json_/gh_tokens.json') as f:
#     gh_tokens = json.load(f)  # channel ids of channels subscribed to issues
#     f.close()

gh_tokens = {}
pr_subscribers = {}
commit_subscribers = {}
issue_subscribers = {}
repos = {}

URL = 'https://c62b-72-78-191-96.ngrok.io'

auth_queue = Queue(maxsize=1)
queue_lock = asyncio.Lock()


class GitHubCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    github = discord.SlashCommandGroup('github', 'GitHub related commands.')
    issues = github.create_subgroup('issue', 'Manage issues in GitHub repositories.')
    pull_requests = github.create_subgroup('pull-request', 'Manage pull requests in GitHub repositories.')
    repositories = github.create_subgroup('repo', 'Add/remove GitHub repos.')
    subscribe = github.create_subgroup('subscribe', 'Subscribe channel to GitHub notifications.')
    unsubscribe = github.create_subgroup('unsubscribe', 'Unsubscribe channel to GitHub notifications.')
    fetch = github.create_subgroup('fetch', 'Fetch information about GitHub repositories.')

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild):
        server = str(guild.id)
        repos[server] = {}

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
        # self.save_dicts()

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
        # self.save_dicts()

    # def save_dicts(self):
    #     with open('bot/cogs/json_/repos.json', 'w') as f:
    #         json.dump(repos, f)  # repo names and list of branches
    #         f.close()
    #     with open('bot/cogs/json_/pr_subscribers.json', 'w') as f:
    #         json.dump(pr_subscribers, f)  # channel ids of channels subscribed to pull requests
    #         f.close()
    #     with open('bot/cogs/json_/commit_subscribers.json', 'w') as f:
    #         json.dump(commit_subscribers, f)  # channel ids of channels subscribed to commits, one list per branch
    #         f.close()
    #     with open('bot/cogs/json_/issue_subscribers.json', 'w') as f:
    #         json.dump(issue_subscribers, f)  # channel ids of channels subscribed to issues
    #         f.close()
    #     with open('bot/cogs/json_/gh_tokens.json', 'w') as f:
    #         json.dump(gh_tokens, f)  # channel ids of channels subscribed to issues
    #         f.close()

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

    @subscribe.command(name='pull-requests', description='Subscribe to pull request notifications in this channel.')
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

    @subscribe.command(name="issues", description="Subscribe to issue notifications in this channel.")
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

    @unsubscribe.command(name='issues', description='Unsubscribe this channel from issue notifications.')
    @guild_only()
    async def issues_unsub(self, ctx: discord.ApplicationContext, repo_name=''):
        if repo_name == '':
            await ctx.respond(UsageMessage('/github unsubscribe issues <REPO_OWNER>/<REPO_NAME>'))
        elif issue_subscribers.get(repo_name) is None:
            await ctx.respond(
                HelpEmbed('Channel Not Subscribed', f'{ctx.channel.name} is not subscribed to issues for {repo_name}.'))
        else:
            r = issue_subscribers.pop(repo_name)
            await ctx.respond(discord.Embed(
                color=discord.Color.green(),
                title='Success',
                description=f'{ctx.channel.name} has been unsubscribed from issues for {repo_name}.'))

    @unsubscribe.command(name='pull-requests', description='Unsubscribe this channel from pull request notifications.')
    @guild_only()
    async def pull_requests_unsub(self, ctx: discord.ApplicationContext, repo_name=''):
        if repo_name == '':
            await ctx.respond(UsageMessage('/github unsubscribe pull-requests <REPO_OWNER>/<REPO_NAME>'))
        elif pr_subscribers.get(repo_name) is None:
            await ctx.respond(HelpEmbed('Channel Not Subscribed',
                                        f'{ctx.channel.name} is not subscribed to pull requests for {repo_name}.'))
        else:
            r = pr_subscribers.pop(repo_name)
            await ctx.respond(discord.Embed(
                color=discord.Color.green(),
                title='Success',
                description=f'{ctx.channel.name} has been unsubscribed from issues for {repo_name}.'))

    @unsubscribe.command(name='commits', description='Unsubscribe this channel from issue notifications.')
    @guild_only()
    async def commits_unsub(self, ctx: discord.ApplicationContext, repo_name=''):
        if repo_name == '':
            await ctx.respond(UsageMessage('/github unsubscribe commits <REPO_OWNER>/<REPO_NAME>'))
        elif commit_subscribers.get(repo_name) is None:
            await ctx.respond(HelpEmbed('Channel Not Subscribed',
                                        f'{ctx.channel.name} is not subscribed to commits for {repo_name}.'))
        else:
            r = commit_subscribers.pop(repo_name)
            await ctx.respond(discord.Embed(
                color=discord.Color.green(),
                title='Success',
                description=f'{ctx.channel.name} has been unsubscribed from commits for {repo_name}.'))

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

                if repo.full_name in repos.get(server):
                    await ctx.respond(embed=HelpEmbed('Repository Already Added',
                                                      f'{repo.full_name} has already been added.'))
                else:
                    try:
                        repo.create_hook(name='web',
                                         config={'url': f'{URL}/webhook/commits',
                                                 'content_type': 'json',
                                                 },
                                         events=['push'],
                                         active=True
                                         )
                        repo.create_hook(name='web',
                                         config={'url': f'{URL}/webhook/issues',
                                                 'content_type': 'json',
                                                 },
                                         events=['issues'],
                                         active=True
                                         )
                        repo.create_hook(name='web',
                                         config={'url': f'{URL}/webhook/pull-request',
                                                 'content_type': 'json',
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

    @repositories.command(name='remove', description='Remove a repository from this server\'s list.')
    @guild_only()
    async def remove_repo(self, ctx: discord.ApplicationContext, repo=''):
        server = str(ctx.guild.id)
        if repo == '':
            await ctx.respond(embed=UsageMessage('/github repo remove <REPO_OWNER>/<REPO_NAME>'))
        elif repos.get(server).get(repo) is None:
            await ctx.respond(embed=HelpEmbed('Repo Not Added', f'{repo} has not been added to {ctx.guild.name}'))
        else:
            r = repos.pop(repo)
            if commit_subscribers.get(repo) is not None:
                r = commit_subscribers.pop(repo)
            if issue_subscribers.get(repo) is not None:
                r = issue_subscribers.pop(repo)
            if pr_subscribers.get(repo) is not None:
                r = pr_subscribers.pop(repo)

            await ctx.respond(embed=discord.Embed(color=discord.Color.green(),
                                                  title='Success',
                                                  description=(
                                                      f'{repo} has been removed from {ctx.channel.name}, but webhooks '
                                                      f'will have to be removed from the repository manually on GitHub.'))
                              )

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

    @subscribe.command(name='commits', description='Subscribe to commit notifications in this channel.')
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
                        await ctx.respond(embed=HelpEmbed('Channel Already Subscribed',
                                                          f'#{ctx.channel.name} is already subscribed to commits for '
                                                          f'{repo} on {branch}.'))
            else:
                if channel not in commit_subscribers[repo][branch]:
                    commit_subscribers[repo][branch].append(channel)
                    await ctx.respond(embed=CommitSubscriptionSuccess(ctx.channel.name, repo, branch))
                else:
                    await ctx.respond(embed=HelpEmbed('Channel Already Subscribed',
                                                      f'#{ctx.channel.name} is already subscribed to commits for '
                                                      f'{repo} on {branch}.'))

    @fetch.command(name='pull-requests', description='Get a list of open pull requests in a repository.')
    @guild_only()
    async def fetch_pull_requests(self, ctx: discord.ApplicationContext, repo=''):
        """
        Get a list of a repository's open pull requests.

        Connect to a public repository using a Github object, then get all of the repo's
        open PRs and format them as a list with links and send it as a Discord embed.

        :param repo: The repository to get PRs from.
        :return: None
        """
        user_id = str(ctx.user.id)
        token = gh_tokens.get(user_id)
        server = str(ctx.guild.id)
        if token is None:
            await ctx.respond(GitHubNotAuthenticatedError(ctx.user.name))
        elif repo == '':
            await ctx.respond(embed=UsageMessage('/github fetch issues <REPO_OWNER>/<REPO_NAME>'))
        elif repos.get(server).get(repo) is None:
            await ctx.respond(embed=HelpEmbed('Repo Not Added', f'{repo} has not been added to {ctx.guild.name}.'))
        else:
            pages = []
            embeds = []
            # get repo via pygithub
            g = Github(token)
            repo = g.get_repo(repo)
            # get open(active) PR
            pulls = repo.get_pulls(state='open')
            for i in range(0, pulls.totalCount):
                embeds.append(discord.Embed(title=pulls[i].title, color=discord.Color.blurple()))
                embeds[i].add_field(name='Number', value=pulls[i].number, inline=True)
                embeds[i].add_field(name='Author', value=pulls[i].user.login, inline=True)
                embeds[i].add_field(name='URL', value=pulls[i].html_url, inline=True)
                embeds[i].add_field(name='Created At', value=pulls[i].created_at.strftime("%m/%d/%Y, %H:%M:%S"),
                                    inline=True)
                embeds[i].add_field(name='Base', value=pulls[i].base.ref, inline=True)
                embeds[i].add_field(name='Head', value=pulls[i].head.ref, inline=True)
                embeds[i].add_field(name='Body', value=pulls[i].body, inline=False)
                pages.append(Page(
                    content=f'PR #{i + 1} of {pulls.totalCount} in **{repo.full_name}**):',
                    embeds=[embeds[i]])
                )
            if pages:
                paginator = Paginator(pages=pages)
                await paginator.respond(ctx.interaction, ephemeral=False)
            else:
                await ctx.respond(
                    embed=HelpEmbed('No Issues Found', f'{repo.full_name} currently has no open pull requests.'))

    @fetch.command(name='issues', description='Get a list of open issues in a repository.')
    @guild_only()
    async def fetch_issues(self, ctx: discord.ApplicationContext, repo=''):
        """
        Get a list of a repository's open issues.

        Connect to a public repository using a Github object, then get all of the repo's
        open issues and format them as a list with links and send it as a Discord embed.

        :param repo: The repository to get issues from.
        :return: None
        """
        user_id = str(ctx.user.id)
        server = str(ctx.guild.id)
        token = gh_tokens.get(user_id)
        if token is None:
            await ctx.respond(GitHubNotAuthenticatedError(ctx.user.name))
        elif repo == '':
            await ctx.respond(embed=UsageMessage('/github fetch issues <REPO_OWNER>/<REPO_NAME>'))
        elif repos.get(server).get(repo) is None:
            await ctx.respond(embed=HelpEmbed('Repo Not Added', f'{repo} has not been added to {ctx.guild.name}.'))
        else:
            pages = []
            embeds = []
            # get repo via pygithub
            g = Github(token)
            repo = g.get_repo(repo)
            # get open(active) PR
            issues = repo.get_issues(state='open')

            for i in range(0, issues.totalCount):
                embeds.append(discord.Embed(title=issues[i].title, color=discord.Color.blurple()))
                embeds[i].add_field(name='Number', value=issues[i].number, inline=True)
                embeds[i].add_field(name='Author', value=issues[i].user.login, inline=True)
                embeds[i].add_field(name='URL', value=issues[i].html_url, inline=True)
                embeds[i].add_field(name='Created At', value=issues[i].created_at.strftime("%m/%d/%Y, %H:%M:%S"),
                                    inline=True)
                embeds[i].add_field(name='Body', value=issues[i].body, inline=False)
                pages.append(Page(
                    content=f'Issue #{i + 1} of {issues.totalCount} in **{repo.full_name}**:',
                    embeds=[embeds[i]])
                )
            if pages:
                paginator = Paginator(pages=pages)
                await paginator.respond(ctx.interaction, ephemeral=False)
            else:
                await ctx.respond(embed=HelpEmbed('No Issues Found', f'{repo.full_name} currently has no open issues.'))

    @issues.command(name='close', description='Close an issue.')
    @guild_only()
    async def issue_close(self, ctx: discord.ApplicationContext, repo='', issue_id=''):
        user_id = str(ctx.user.id)
        token = gh_tokens.get(user_id)
        server = str(ctx.guild.id)
        if token is None:
            await ctx.respond(GitHubNotAuthenticatedError(ctx.user.name))
        elif repo == '' or issue_id == '':
            await ctx.respond(
                embed=UsageMessage('/github issue close <REPO_OWNER>/<REPO_NAME> <ISSUE_NUMBER> [COMMENT]'))
        elif repos.get(server).get(repo) is None:
            await ctx.respond(embed=HelpEmbed('Repo Not Added', f'{repo} has not been added to {ctx.guild.name}.'))
        else:
            g = Github(token)
            r = g.get_repo(repo)
            issue = r.get_issue(int(issue_id))
            issue.edit(state='closed')

            await ctx.respond(embed=discord.Embed(
                color=discord.Color.green(),
                title='Success',
                description=f'Issue {issue.title} in {repo} has been closed.'))

    @issues.command(name='assign', description='Assign an issue to a GitHub user.')
    @guild_only()
    async def issue_assign(self, ctx: discord.ApplicationContext, repo='', issue_id='', assignees=''):
        user_id = str(ctx.user.id)
        token = gh_tokens.get(user_id)
        server = str(ctx.guild.id)
        if token is None:
            await ctx.respond(GitHubNotAuthenticatedError(ctx.user.name))
        elif repo == '' or issue_id == '' or assignees == '':
            await ctx.respond(
                embed=UsageMessage('/github issue assign <REPO_OWNER>/<REPO_NAME> <ISSUE_NUMBER> <ASSIGNEE(S)>'))
        elif repos.get(server).get(repo) is None:
            await ctx.respond(embed=HelpEmbed('Repo Not Added', f'{repo} has not been added to {ctx.guild.name}'))
        else:
            g = Github(token)
            r = g.get_repo(repo)
            issue = r.get_issue(int(issue_id))
            assignee_list = assignees.split(' ')
            issue.edit(assignees=assignee_list)

            await ctx.respond(f'Issue {issue.title} has been assigned to {", ".join(assignee_list)}.')

    @pull_requests.command(name='approve', description='Approve a pull request.')
    @guild_only()
    async def pull_request_approve(self, ctx: discord.ApplicationContext, repo='', pr_id='', comment=''):
        user_id = str(ctx.user.id)
        token = gh_tokens.get(user_id)
        server = str(ctx.guild.id)
        if token is None:
            await ctx.respond(GitHubNotAuthenticatedError(ctx.user.name))
        elif repo == '':
            await ctx.respond(embed=UsageMessage('/github pull-request <REPO_OWNER>/<REPO_NAME> <PR_ID> [COMMENT]'))
        elif repos.get(server).get(repo) is None:
            await ctx.respond(embed=HelpEmbed('Repo Not Added', f'{repo} has not been added to {ctx.guild.name}'))
        else:
            g = Github(token)
            r = g.get_repo(repo)
            pr = r.get_pull(int(pr_id))
            pr.create_review(body=comment, event='APPROVE')

            await ctx.respond(embed=discord.Embed(
                color=discord.Color.green(),
                title='Success',
                description=f'{pr.title} has been approved.')
            )

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
                                   url=f'https://c62b-72-78-191-96.ngrok.io/auth/github')
        self.add_item(button)

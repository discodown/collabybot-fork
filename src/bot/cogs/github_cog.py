import discord
from discord.ext import commands
from discord.ext.commands import Context
from github.MainClass import Github

repos = {}  # repo names and list of branches
pr_subscribers = {}  # channel ids of channels subscribed to pull requests
commit_subscribers = {}  # channel ids of channels subscribed to commits, one list per branch
issue_subscribers = {}  # channel ids of channels subscribed to issues


class GitHubCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

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
                await self.get_channel(int(channel)).send(embed=embed)
        elif event == 'issue':
            embed = discord.Embed(title='GitHub Event Notification',
                                  color=discord.Color.magenta())
            embed.add_field(name='Issue', value=payload, inline=False)
            for channel in issue_subscribers[repo]:
                await self.get_channel(int(channel)).send(embed=embed)
        elif event == 'push':
            try:
                embed = discord.Embed(title='GitHub Event Notification',
                                      color=discord.Color.purple())
                embed.add_field(name='Commit', value=payload, inline=False)
                for channel in commit_subscribers.get(repo).get(branch):
                    await self.get_channel(int(channel)).send(embed=embed)
            except TypeError:
                print('No subscribers')

    @commands.slash_command(name='gh-pull-requests', description='Subscribe to pull request notifications in this channel.')
    async def pull_requests(self, ctx: discord.ApplicationContext, repo=''):
        """
        Subscribe a channel to pull request notifications.

        A repository must be specified by providing an argument to the command.
        If no argument was given, responds with a list of available repositories.

        :param str repo: Name of repository to subscribe to.
        :return: None
        """

        channel = ctx.channel.id
        server = ctx.guild_id
        if repo == '':
            await ctx.respond(embed=discord.Embed(
                title='Usage',
                color=discord.Color.yellow(),
                description='/gh-pull-requests <REPO_NAME>')
            )
            if not repos.get(server):
                await ctx.respond(embed=discord.Embed(
                    color=discord.Color.yellow(),
                    description='You haven\'t added any repositories to CollabyBot yet. '
                                'Use /gh-add <REPO_OWNER>/<REPO_NAME> to add one.')
                )
            else:
                repo_list = ''
                for r in repos[server].keys():
                    repo_list += f'{r}\n'
                await ctx.respond('Subscribe to one of the following added repositories using '
                               '**/gh-pull-requests <REPO_NAME>**:',
                               embed=discord.Embed(color=discord.Color.yellow(),
                                                   description=f'{repo_list}'
                                                   )
                               )
        elif repo not in repos[server].keys():

            await ctx.respond(embed=discord.Embed(
                color=discord.Color.yellow(),
                description=f'Repository {repo} hasn\'t been added to CollabyBot yet. '
                            f'Use /gh-add <REPO_OWNER>/<REPO_NAME> to add it.'
            )
            )
        elif channel not in pr_subscribers[repo]:
            pr_subscribers[repo].append(channel)
            await ctx.respond(embed=discord.Embed(color=discord.Color.green(),
                                               title='Success',
                                               description=f'#{ctx.channel} channel is now subscribed to pull requests for {repo}!')
                           )
        else:
            await ctx.respond(embed=discord.Embed(
                color=discord.Color.yellow(),
                description=f'#{ctx.channel} is already subscribed to to pull requests for {repo}.')
            )

    @commands.slash_command(name='gh-issues', description="Subscribe to issue notifications in this channel.")
    async def issues(self, ctx: discord.ApplicationContext, repo=''):
        """
        Subscribe a channel to issue notifications.

        A repository must be specified by providing an argument to the command.
        If no argument was given, responds with a list of available repositories.

        :param str repo: Name of repository to subscribe to.
        :return: None
        """

        channel = ctx.channel.id
        server = ctx.guild_id

        if repo == '':
            await ctx.respond(embed=discord.Embed(
                title='Usage',
                color=discord.Color.yellow(),
                description='/gh-issues <REPO_NAME>')
            )
            if not repos.get(server):  # no repos added yet

                await ctx.respond(embed=discord.Embed(
                    color=discord.Color.yellow(),
                    description=f'You haven\'t added any repositories to CollabyBot yet. '
                                f'Use /gh-add <REPO_OWNER>/<REPO_NAME> to add one.'))
            else:
                repo_list = ''
                for r in repos[server].keys():
                    repo_list += f'{r}\n'
                await ctx.respond('Subscribe to one of the following added repositories using **/gh-issues <REPO_NAME>**:',
                               embed=discord.Embed(color=discord.Color.yellow(),
                                                   description=f'{repo_list}'))

        elif repo not in repos[server].keys():  # repo hasn't been added yet
            await ctx.respond(embed=discord.Embed(
                color=discord.Color.yellow(),
                description=f'Repository {repo} hasn\'t been added to CollabyBot yet. '
                            f'Use /gh-add <REPO_OWNER>/<REPO_NAME> to add it.')
            )

        elif channel not in issue_subscribers[repo]:  # channel isn't subscribed
            issue_subscribers[repo].append(channel)
            subscribe_embed = discord.Embed(color=discord.Color.green(), title='Success',
                                            description=f'#{ctx.channel} channel is now subscribed to issues for {repo}!')
            await ctx.respond(embed=subscribe_embed)

        else:  # channel is already subscribed
            await ctx.respond(embed=discord.Embed(
                color=discord.Color.yellow(),
                description=f'#{ctx.channel} is already subscribed to to pull requests for {repo}.')
            )

    @commands.slash_command(name='gh-add', description='Add a repo to the list of repositories you want notifications from.')
    async def add(self, ctx: discord.ApplicationContext, repo=''):
        """
        Add a repository to CollabyBot's list of repositories.

        When a repo is added, its branches are retrieved using the GitHub API via
        PyGithub's Github class. Subscriber lists for each event type are
        initialized to empty lists (or a dict of empty lists with branches as keys
        for commits).

        :param str repo: The full name of the repository to add.
        :return: None
        """

        server = ctx.guild_id

        if repo == '':
            await ctx.respond(embed=discord.Embed(
                color=discord.Color.yellow(),
                title='Usage',
                description=f'/gh-add <REPO_OWNER>/<REPO_NAME>')
            )
        else:
            # get repo via pygithub
            g = Github()
            repo = g.get_repo(repo)
            if not repos.get(server):
                repos[server] = {}
            if repo.name in repos.get(server):
                await ctx.respond(embed=discord.Embed(
                    color=discord.Color.yellow(),
                    description=f'{repo.name} has already been added.')
                )
            else:
                branches = repo.get_branches()  # get branches via pygithub
                brs = [b.name for b in branches]
                repos[server][repo.name] = brs  # dict entry for repo is list of branches
                # initialize all subscriber lists
                commit_subscribers[repo.name] = {b: [] for b in brs}
                pr_subscribers[repo.name] = []
                issue_subscribers[repo.name] = []
                await ctx.respond(embed=discord.Embed(
                    color=discord.Color.green(),
                    title='Success',
                    description=f'{repo.name} has been added.')
                )

    @commands.slash_command(name='gh-get-repos', description='See the list of repos added to CollabyBot.')
    async def get_repos(self, ctx: discord.ApplicationContext):
        """
        Get a list of repositories added to CollabyBot.

        :return: None
        """

        server = ctx.guild_id

        if not repos.get(server):
            await ctx.respond(embed=discord.Embed(
                color=discord.Color.yellow(),
                description='You haven\'t added any repos to CollabyBot yet.')
            )
        else:
            repo_list = ''
            for r in repos[server].keys():
                repo_list += f'{r}\n'
            list_embed = discord.Embed(color=discord.Color.blurple(),
                                       title=f'Current repositories:',
                                       description=f'{repo_list}')
            await ctx.respond(embed=list_embed)

    @commands.slash_command(name='gh-commits', description='Subscribe to commit notifications in this channel.')
    async def commits(self, ctx: discord.ApplicationContext, repo='', branch=''):
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

        channel = ctx.channel.id
        server = ctx.guild_id

        if repo == '':
            await ctx.respond(embed=discord.Embed(
                title='Usage',
                color=discord.Color.yellow(),
                description='/gh-commits <REPO_NAME> [BRANCH_NAME]')
            )
            if not repos.get(server):
                await ctx.respond(embed=discord.Embed(
                    color=discord.Color.yellow(),
                    description='You haven\'t added any repositories to CollabyBot yet. '
                                'Use /gh-add <REPO_OWNER>/<REPO_NAME> to add one.')
                )
            else:
                repo_list = ''
                for r in repos[server].keys():
                    repo_list += f'{r}\n'
                await ctx.respond('Subscribe to one of the following added repositories '
                               'using **/gh-commits <REPO_NAME> [BRANCH_NAME]**:',
                               embed=discord.Embed(color=discord.Color.yellow(),
                                                   description=f'{repo_list}'))
        elif repo not in repos[server].keys():
            await ctx.respond(embed=discord.Embed(
                color=discord.Color.yellow(),
                description=f'Repository {repo} hasn\'t been added to CollabyBot yet. '
                            f'Use /gh-add <REPO_OWNER>/<REPO_NAME> to add it.'))
        else:
            if branch == '':
                for b in repos[server].get(repo):
                    if channel not in commit_subscribers[repo][b]:
                        commit_subscribers[repo][b].append(channel)
                        await ctx.respond(embed=discord.Embed(
                            color=discord.Color.green(),
                            title='Success',
                            description=f'#{ctx.channel} is now subscribed to commits for {repo} on {b}!')
                        )
                    else:
                        await ctx.respond(embed=discord.Embed(
                            color=discord.Color.yellow(),
                            description=f'#{ctx.channel} is already subscribed to commits for {repo} on {branch}.'))
            else:
                if channel not in commit_subscribers[repo][branch]:
                    commit_subscribers[repo][branch].append(channel)
                    await ctx.respond(embed=discord.Embed(
                        color=discord.Color.green(),
                        title='Success',
                        description=f'#{ctx.channel} is now subscribed to commits for {repo} on {branch}!'
                    ))
                else:
                    await ctx.respond(embed=discord.Embed(
                        color=discord.Color.yellow(),
                        description=f'#{ctx.channel} is already subscribed to commits for {repo} on {branch}.'))

    @commands.slash_command(name='gh-open-pull-requests', description='Show open pull requests in testing repo.')
    async def open_pull_requests(self, ctx: discord.ApplicationContext, repo=''):
        """
        Get a list of a repository's open pull requests.

        Connect to a public repository using a Github object, then get all of the repo's
        open PR's and format them as a list with links and send it as a Discord embed.

        :param repo: The repository to get PRs from.
        :return: None
        """

        if repo == '':
            await ctx.respond(embed=discord.Embed(
                title='Usage',
                color=discord.Color.yellow(),
                description='/gh-open-pull-requests <REPO_OWNER>/<REPO_NAME>')
            )
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

def setup(bot):
    bot.add_cog(GitHubCog(bot))
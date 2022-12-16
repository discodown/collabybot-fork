import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.ext.commands.errors import CommandInvokeError
from github import Github
from jira import JIRA, JIRAError
import discord
from discord.ext.pages import Paginator, Page
from burndown import burndown
from os import remove
repos = {}  # repo names and list of branches
pr_subscribers = {}  # channel ids of channels subscribed to pull requests
commit_subscribers = {}  # channel ids of channels subscribed to commits, one list per branch
issue_subscribers = {}  # channel ids of channels subscribed to issues
jira_subscribers = {}


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

    async def send_payload_message(self, payload, event, repo, branch='main'):
        """
        This method will send payloads to Discord channels subscribed to
        the corresponding event type.

        :param payload: The payload formatted as a notification string.
        :param event: The event type of the payload.
        :return: None
        """
        embed = discord.Embed(color=discord.Color.green(), title='GitHub Event Notification')

        if event == 'pull_request':
            embed.add_field(name='Pull Request', value=payload, inline=False)
            for channel in pr_subscribers[repo]:
                await self.get_channel(int(channel)).send(embed=embed)
        elif event == 'issue':
            embed.add_field(name='Issue', value=payload, inline=False)
            for channel in issue_subscribers[repo]:
                await self.get_channel(int(channel)).send(embed=embed)
        elif event == 'push':
            try:
                embed.add_field(name='Commit', value=payload, inline=False)
                for channel in commit_subscribers.get(repo).get(branch):
                    await self.get_channel(int(channel)).send(embed=embed)
            except TypeError:
                print('No subscribers')

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

    @commands.command(name='gh-pull-requests', description='Subscribe to pull request notifications in this channel.')
    async def pull_requests(ctx: discord.ApplicationContext, repo=''):
        """
        Subscribe a channel to pull request notifications.

        A repository must be specified by providing an argument to the command.
        If no argument was given, responds with a list of available repositories.

        :param str repo: Name of repository to subscribe to.
        :return: None
        """

        channel = ctx.message.channel.id

        if repo == '':
            if not repos:
                not_found_error = discord.Embed(color=discord.Color.yellow(),
                                                description='You haven\'t added any repositories to CollabyBot yet. Use /add <owner/repo-name> to add one.')
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.yellow(),
                    description='You haven\'t added any repositories to CollabyBot yet. Use /add <owner/repo-name> to add one.'))
                # await(ctx.send(f'You haven\'t added any repositories to CollabyBot yet. 'f'Use /add <owner/repo-name> to add one.'))
            else:
                repo_list = ''
                for r in repos.keys():
                    repo_list += f'{r}\n'
                await ctx.send('Subscribe to one of the following added repositories using /pull-requests <repo name>:',
                               embed=discord.Embed(color=discord.Color.yellow(),
                                                   description=f'{repo_list}'
                                                   )
                               )
        elif repo not in repos.keys():

            await ctx.send(embed=discord.Embed(
                color=discord.Color.yellow(),
                description=f'Repository {repo} hasn\'t been added to CollabyBot yet. Use /add <owner/repo-name> to add it.'
            )
            )
        elif channel not in pr_subscribers[repo]:
            pr_subscribers[repo].append(channel)
            await ctx.send(embed=discord.Embed(color=discord.Color.green(),
                                               title='Success',
                                               description=f'#{ctx.channel} channel is now subscribed to pull requests for {repo}!')
                           )
        else:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.yellow(),
                description=f'{ctx.channel} is already subscribed to to pull requests for {repo}.')
            )

    @commands.command(name='gh-issues', description="Subscribe to issue notifications in this channel.")
    async def issues(ctx: discord.ApplicationContext, repo=''):
        """
        Subscribe a channel to issue notifications.

        A repository must be specified by providing an argument to the command.
        If no argument was given, responds with a list of available repositories.

        :param str repo: Name of repository to subscribe to.
        :return: None
        """

        channel = ctx.message.channel.id

        if repo == '':
            if not repos:  # no repos added yet

                # not_found_error = discord.Embed(color=0xe74c3c, title=f'NO REPOSITORIES FOUND ERROR:', description= f'You haven\'t added any repositories to CollabyBot yet. 'f'Use /add <owner/repo-name> to add one.')
                # not_found_error.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.yellow(),
                    description=f'You haven\'t added any repositories to CollabyBot yet. Use /add <owner/repo-name> to add one.'))
            else:
                repo_list = ''
                for r in repos.keys():
                    repo_list += f'{r}\n'
                await ctx.send('Subscribe to one of the following added repositories using /issues <repo name>:',
                               embed=discord.Embed(color=discord.Color.yellow(),
                                                   description=f'{repo_list}'))

        elif repo not in repos.keys():  # repo hasn't been added yet
            await ctx.send(embed=discord.Embed(
                color=discord.Color.yellow(),
                description=f'Repository {repo} hasn\'t been added to CollabyBot yet. Use /add <owner/repo-name> to add it.')
            )

        elif channel not in issue_subscribers[repo]:  # channel isn't subscribed
            issue_subscribers[repo].append(channel)
            subscribe_embed = discord.Embed(color=discord.Color.green(), title='Success',
                                            description=f'#{ctx.channel} channel is now subscribed to issues for {repo}!')
            await ctx.send(embed=subscribe_embed)

        else:  # channel is already subscribed
            await ctx.send(embed=discord.Embed(
                color=discord.Color.yellow(),
                description=f'{ctx.channel} is already subscribed to to pull requests for {repo}.')
            )

    @commands.command(name='gh-add', description='Add a repo to the list of repositories you want notifications from.')
    async def add(ctx: discord.ApplicationContext, repo=''):
        """
        Add a repository to CollabyBot's list of repositories.

        When a repo is added, its branches are retrieved using the GitHub API via
        PyGithub's Github class. Subscriber lists for each event type are
        initialized to empty lists (or a dict of empty lists with branches as keys
        for commits).

        :param str repo: The full name of the repository to add.
        :return: None
        """

        if repo == '':
            await ctx.send('Add a repo to the list of repositories you want notifications from like this:'
                           ' /add <owner/repo-name>.')
        else:
            # get repo via pygithub
            g = Github()
            repo = g.get_repo(repo)
            if repo.name in repos:
                # error_embed= discord.Embed(color = 0xe67e22, title='ERROR: REPO WAS ALREADY ADDED', description=f'{repo.name} has been already added to the #{ctx.channel} channel.')
                # error_embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.yellow(),
                    description=f'{repo.name} has already been added.')
                )
            else:
                branches = repo.get_branches()  # get branches via pygithub
                brs = [b.name for b in branches]
                repos[repo.name] = brs  # dict entry for repo is list of branches
                # initialize all subscriber lists
                commit_subscribers[repo.name] = {b: [] for b in brs}
                pr_subscribers[repo.name] = []
                issue_subscribers[repo.name] = []
                # notify_embed = discord.Embed(color = 0xe91e63, title=f'{repo.name} has been added.')
                # notify_embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.green(),
                    description=f'{repo.name} has been added.')
                )

    @commands.command(name='gh-get-repos', description='See the list of repos added to CollabyBot.')
    async def get_repos(ctx: discord.ApplicationContext):
        """
        Get a list of repositories added to CollabyBot.

        :return: None
        """

        repo_list = ''
        for r in repos.keys():
            repo_list += f'{r}\n'
        if repo_list == '':
            # error_embed = discord.Embed(color = 0xe74c3c, title = 'NO REPOSITORIES FOUND ERROR:', description='You haven\'t added any repos to CollabyBot yet.')
            # error_embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
            await ctx.send(embed=discord.Embed(
                color=discord.Color.yellow(),
                description='You haven\'t added any repos to CollabyBot yet.')
            )
        else:
            list_embed = discord.Embed(color=discord.Color.blurple(),
                                       title=f'Current repositories:',
                                       description=f'{repo_list}')
            await ctx.send(embed=list_embed)

    @commands.command(name='gh-commits', description='Subscribe to commit notifications in this channel.')
    async def commits(ctx: discord.ApplicationContext, repo='', branch=''):
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

        channel = ctx.message.channel.id

        if repo == '':
            if not repos:
                # not_found_error.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.yellow(),
                    description='You haven\'t added any repositories to CollabyBot yet. Use /add <owner/repo-name> to add one.')
                )
            else:
                repo_list = ''
                for r in repos.keys():
                    repo_list += f'{r}\n'
                await ctx.send('Subscribe to one of the following added repositories using /pull-requests <repo name>:',
                               embed=discord.Embed(color=discord.Color.yellow(),
                                                   description=f'{repo_list}'))
        elif repo not in repos.keys():
            await ctx.send(embed=discord.Embed(
                color=discord.Color.yellow(),
                description=f'Repository {repo} hasn\'t been added to CollabyBot yet. Use /add <owner/repo-name> to add it.'))
        else:
            if branch == '':
                for b in repos.get(repo):
                    if channel not in commit_subscribers[repo][b]:
                        commit_subscribers[repo][b].append(channel)
                        await ctx.send(embed=discord.Embed(
                            color=discord.Color.green(),
                            title='Success',
                            description=f'{ctx.channel} is now subscribed to commits for {repo} on {b}!')
                        )
                    else:
                        await ctx.send(embed=discord.Embed(
                            color=discord.Color.yellow(),
                            description=f'{ctx.channel} is already subscribed to commits for {repo} on {branch}.'))
            else:
                if channel not in commit_subscribers[repo][branch]:
                    commit_subscribers[repo][branch].append(channel)
                    await ctx.send(embed=discord.Embed(
                        color=discord.Color.green(),
                        title='Success',
                        description=f'{ctx.channel} is now subscribed to commits for {repo} on {branch}!'
                    ))
                else:
                    await ctx.send(embed=discord.Embed(
                        color=discord.Color.yellow(),
                        description=f'{ctx.channel} is already subscribed to commits for {repo} on {branch}.'))

    @commands.command(name='gh-open-pull-requests', description='Show open pull requests in testing repo.')
    async def open_pull_requests(ctx: discord.ApplicationContext, repo=''):
        """
        Get a list of a repository's open pull requests.

        Connect to a public repository using a Github object, then get all of the repo's
        open PR's and format them as a list with links and send it as a Discord embed.

        :param repo: The repository to get PRs from.
        :return: None
        """

        openpr_embed = discord.Embed(color=discord.Color.blurple(), title=f'Open pull requests in {repo}:\n')
        # get repo via pygithub
        g = Github()
        repo = g.get_repo(repo)
        # get open(active) PR
        pulls = repo.get_pulls(state='open')
        for pr in pulls:
            openpr_embed.add_field(name=f'{pr.title}:', value=f'{pr.url}', inline=False)
        await ctx.send(embed=openpr_embed)

    @commands.command(name='jira-setup-token', description='Set up Jira Token to monitor Jira Issues.')
    async def jira_setup_token(ctx: discord.ApplicationContext):
        """
        Setup a Jira token to monitor issues in a Jira workspace.

        Requires an email address, workspace URL, and Jira authentication token. If any of them
        are not passed as arguments to the command, responds with usage instructions. If they
        are all present, a dict of Jira info is created and added to the list of
        Jira subscribers. If the user ID is already in the list of subscribers, simply
        update the info.

        :return: None
        """

        userId = ctx.message.author.id
        msg = ctx.message.content
        parts = msg.split(' ')
        if len(parts) != 4:
            await ctx.send('Use /jira-setup-token <email> <jira_url> <jira_token>')
            return

        userEmail = parts[1]
        jiraUrl = parts[2]
        jiraToken = parts[3]

        # TODO: Make authenticated list based on Discord server not single users
        jiraInfo = {}
        jiraInfo["url"] = jiraUrl
        jiraInfo["email"] = userEmail
        jiraInfo["token"] = jiraToken

        if userId in jira_subscribers:
            jira_subscribers[userId] = jiraInfo
            await ctx.send('Token updated.')
        else:
            jira_subscribers[userId] = jiraInfo
            await ctx.send('Token registered.')

    @commands.command(name='jira-issue',
                      description='Retrieves summary, description, issue type, and assignee of Jira issue.')
    async def jira_get_issue(ctx: discord.ApplicationContext):
        """
        Respond with information about a Jira issue.

        Requires an issue ID to be passed as an argument. If no argument is present, responds with
        usage instruction. If the sending user doesn't have a token added to the list of
        Jira subscribers, instructs the user to add one.

        :return: None
        """

        userId = ctx.message.author.id
        msg = ctx.message.content
        parts = msg.split()
        if len(parts) != 2:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.yellow(),
                title='Usage',
                description='/jira-issue <ISSUE_ID>')
            )
            return

        tokenExists = (userId in jira_subscribers)
        if tokenExists == False:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Authentication Error',
                description=f'User {ctx.message.author.id} is not authenticated with Jira.')
            )
            return

        jiraInfo = jira_subscribers[userId]
        jira = JIRA(jiraInfo["url"], basic_auth=(jiraInfo["email"], jiraInfo["token"]))
        issue_name = parts[1]
        issue = jira.issue(issue_name)

        embed = discord.Embed(color=discord.Color.blurple(), title=issue_name)
        embed.add_field(name=f'Summary:', value=issue.fields.summary, inline=False)
        embed.add_field(name=f'Description:', value=issue.fields.description, inline=False)
        if issue.fields.assignee is None:
            embed.add_field(name=f'Assignee:', value='Unassigned', inline=False)
        else:
            embed.add_field(name=f'Assignee:', value=issue.fields.assignee.displayName, inline=False)
        embed.add_field(name=f'Status:', value=issue.fields.status.name, inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='jira-sprint', description='Returns sprint summary')
    async def jira_get_sprint(ctx: discord.ApplicationContext):
        """
        Get information about the current sprint in a Jira project.

        Sends a list of issues in the sprint as well as a burndown chart of
        the sprint's progress. Command requires a project ID as an argument. If one isn't
        provided, present the user with a list of projects in the authenticated workspace.

        :return: None
        """

        userId = ctx.message.author.id
        msg = ctx.message.content

        tokenExists = (userId in jira_subscribers)
        if tokenExists == False:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Authentication Error',
                description=f'User {ctx.message.author.id} is not authenticated with Jira.')
            )
            return

        jiraInfo = jira_subscribers[userId]
        jira = JIRA(jiraInfo["url"], basic_auth=(jiraInfo["email"], jiraInfo["token"]))

        parts = msg.split()

        # No args
        if len(parts) == 1:
            embed = discord.Embed(color=discord.Color.red(), title="Provide one of the project IDs:")
            projects = jira.projects()
            for project in projects:
                embed.add_field(name=project.name, value=project.id, inline=False)
            await ctx.send(embed=embed)
            return

        if len(parts) > 2:
            embed = discord.Embed(color=discord.Color.red(), title="Too many args.")
            await ctx.send(embed=embed)
            return

        # Find issues from the project's current sprint using JQL query
        projectId = parts[1]
        query = 'project={0} AND SPRINT not in closedSprints() AND sprint not in futureSprints()'.format(projectId)
        issues = jira.search_issues(query)

        #TODO: Move to utils
        def divide_chunks(l, n):
            for i in range(0, len(l), n):
                yield l[i:i + n]

        issue_chunks = list(divide_chunks(issues, 4))
        embeds = []
        pages = []
        for i in range(0, len(issue_chunks)):
            embeds.append(discord.Embed(color=discord.Color.blurple(), title='Active Sprint'))
            for issue_name in issue_chunks[i]:
                issue = jira.issue(issue_name)
                embeds[i].add_field(name=f'Name:', value=issue_name, inline=False)
                embeds[i].add_field(name=f'Summary:', value=issue.fields.summary, inline=False)
                embeds[i].add_field(name=f'Description:', value=issue.fields.description, inline=False)
                if issue.fields.assignee is None:
                    embeds[i].add_field(name=f'Assignee:', value='Unassigned', inline=False)
                else:
                    embeds[i].add_field(name=f'Assignee:', value=issue.fields.assignee.displayName, inline=False)
                embeds[i].add_field(name=f'Status:', value=issue.fields.status.name, inline=False)
                embeds[i].add_field(name=chr(173), value=chr(173))
            pages.append(Page(
                content=f'Page {i + 1} of sprint board:',
                embeds=[embeds[i]]
            ))
        paginator = Paginator(pages=pages)
        await paginator.send(ctx)

        # Create burndown chart
        burndown_chart = burndown(jira, issues)
        with open(burndown_chart, 'rb') as f:
            picture = discord.File(f)
            await ctx.send('**Burndown Chart:**', file=picture)
        remove(burndown_chart)  # Delete chart after sending it

    @commands.command(name='jira-assign', description='Assign a Jira issue to a user.')
    async def jira_assign_issue(ctx: discord.ApplicationContext):
        """
        Assign a Jira ticket to a user.

        If the ticket already has an assignee, ask the user if they want to reassign it.
        If they respond yes, reassign it; if they respond no, don't reassign it.
        :return: None
        """

        userId = ctx.message.author.id
        msg = ctx.message.content

        tokenExists = (userId in jira_subscribers)
        if tokenExists == False:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Authentication Error',
                description=f'User {ctx.message.author.id} is not authenticated with Jira.')
            )
            return

        jiraInfo = jira_subscribers[userId]
        jira = JIRA(jiraInfo["url"], basic_auth=(jiraInfo["email"], jiraInfo["token"]))

        parts = msg.split()

        # TODO: Move to utils
        def divide_chunks(l, n):
            for i in range(0, len(l), n):
                yield l[i:i + n]

        if len(parts) == 1:
            projects = jira.projects()
            for project in projects:
                embed.add_field(name=project.name, value=project.id, inline=False)
            await ctx.send(embed=discord.Embed(
                color=discord.Color.yellow(),
                title='Usage',
                description='/jira-assign <TICKET_ID> <USER_ID>')
            )

        #TODO: Move to get-issues command
        # User but no ticket
        elif len(parts) == 2 and parts[1].isdigit():
            project_name = parts[1]
            issues = []
            i = 0
            chunk_size = 100
            while True:
                chunk = jira.search_issues(f'project = {project_name}', startAt=i, maxResults=chunk_size)
                i += chunk_size
                issues += chunk.iterable
                if i >= chunk.total:
                    break

            embed = discord.Embed(color=discord.Color.yellow(), title="Available tickets: ")
            for issue in issues:
                if issue.fields.status.name != 'Done':
                    embed.add_field(name=issue, value=issue.fields.status, inline=False)

            await ctx.send(embed=embed)

        # Ticket but not user
        elif len(parts) == 2 and parts[1].isdigit() == False:
            ticket = parts[1]
            project_name = ticket.split('-')[0]

            users = jira.search_assignable_users_for_projects('', project_name)
            user_chunks = list(divide_chunks(users, 12))

            embeds = []
            pages = []
            for i in range(0, len(user_chunks)):
                embeds.append(discord.Embed(color=discord.Color.yellow(), title='Assignable Users'))
                for user in user_chunks[i]:
                    embeds[i].add_field(name=user.displayName, value=user.accountId, inline=False)
                pages.append(Page(
                    content=f'Available assignees (Part {i+1}):',
                    embeds=[embeds[i]])
                )
            paginator = Paginator(pages=pages)
            await paginator.send(ctx)

        elif len(parts) == 3:
            project_name = parts[1].split('-')[0]
            users_dict = {}
            users = jira.search_assignable_users_for_projects('', project_name, maxResults=200)

            for user in users:
                users_dict[user.accountId] = user.displayName

            issue_name = parts[1]

            if parts[2][0].isnumeric():  # account ID
                user_name = users_dict.get(parts[2])
            else:  # Given name
                user_name = parts[2]

            issue = jira.issue(issue_name)
            if issue.fields.assignee is not None:
                await ctx.send(f'{issue_name} is already assigned to {issue.fields.assignee}. Reassign to {user_name}?')
                response = await ctx.bot.wait_for('message', timeout=20.0)
                if response.content in ['yes', 'Yes', 'y', 'Y']:
                    try:
                        jira.assign_issue(issue_name, user_name)
                        await ctx.send(embed=discord.Embed(
                            color=discord.Color.green(),
                            title='Success',
                            description=f'Successfully reassigned {issue_name} to {user_name}.')
                        )
                    except JIRAError:
                        await ctx.send(embed=discord.Embed(
                            title='User Error',
                            color=discord.Color.red(),
                            description=f'User {user_name} not found.')
                        )
                else:
                    await ctx.send(f'{issue_name} will not be reassigned to {user_name}.')
            else:
                try:
                    jira.assign_issue(issue_name, user_name)
                    await ctx.send(embed=discord.Embed(
                        color=discord.Color.green(),
                        title='Success',
                        description=f'Successfully reassigned {issue_name} to {user_name}.')
                    )
                except JIRAError:
                    await ctx.send(embed=discord.Embed(
                        title='User Error',
                        color=discord.Color.red(),
                        description=f'User {user_name} not found.')
                    )

    @commands.command(name='jira-unassign', description='Unassign a Jira issue.')
    async def jira_unassign_issue(ctx: discord.ApplicationContext):
        """
        Unassign a user from a Jira issue that has already been assigned to someone.

        Requires an issue ID and username to work.
        :return:
        """
        userId = ctx.message.author.id
        msg = ctx.message.content
        parts = msg.split()

        if len(parts) != 2:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.yellow(),
                title='Usage',
                description='/jira-unassign <ISSUE_ID>')
            )
            return

        tokenExists = (userId in jira_subscribers)
        if tokenExists == False:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Authentication Error',
                description=f'User {ctx.message.author.id} is not authenticated with Jira.')
            )
            return

        jiraInfo = jira_subscribers[userId]
        jira = JIRA(jiraInfo["url"], basic_auth=(jiraInfo["email"], jiraInfo["token"]))

        issue_name = parts[1]
        jira.assign_issue(issue_name, None)
        await ctx.send(embed=discord.Embed(
            color=discord.Color.green(),
            title='Success',
            description=f'{issue_name} has been unassigned.')
        )

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
        cls.add_command(bot, command=cls.get_commands)
        cls.add_command(bot, command=cls.ping)
        cls.add_command(bot, command=cls.pull_requests)
        cls.add_command(bot, command=cls.issues)
        cls.add_command(bot, command=cls.open_pull_requests)
        cls.add_command(bot, command=cls.commits)
        cls.add_command(bot, command=cls.get_repos)
        cls.add_command(bot, command=cls.add)
        cls.add_command(bot, command=cls.jira_setup_token)
        cls.add_command(bot, command=cls.jira_get_issue)
        cls.add_command(bot, command=cls.jira_get_sprint)
        cls.add_command(bot, command=cls.jira_assign_issue)
        cls.add_command(bot, command=cls.jira_unassign_issue)

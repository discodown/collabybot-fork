import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.pages import Page, Paginator
from jira import JIRA, JIRAError
from os import remove
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

jira_subscribers = {}

class JiraCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def burndown(self, jira, issues):
        """
        Utility method used by the /sprint command for creating a burndown chart.

        First add up all the story points in the sprint, issue by issue. Then calculate
        how many points remain for each day in the sprint by comparing issue's resolution date
        to each date in the sprint's timespan. Plot the remaining points vs. date by storing them
        in a dictionary and plotting the line.

        Also plot the guideline by finding the slope that creates a linear decline from
        start to end of the sprint.

        Return the filename of the newly created burndown chart so that Discord can open it.

        :param jira: The instance of the Jira class being used by the /sprint command
        :param issues: Collection of sprint issues retrieved by the Jira class instance
        :return str: Filename of the newly created burndown chart
        """

        total_points = 0
        for i in issues:
            if i.raw['fields'].get('customfield_10026') is not None:
                total_points += int(i.raw['fields']['customfield_10026'])
            else:
                total_points += 0
            sprint_id = i.raw['fields']['customfield_10020'][0]['id']

        # Get start and end date of sprint
        sprint = jira.sprint(sprint_id)
        start = sprint.raw['startDate'].split('T')[0]
        end = sprint.raw['endDate'].split('T')[0]

        # Timespan of sprint
        date_range = pd.date_range(start=start, end=end, freq='D', inclusive='left')

        remaining_points = {}
        for d in date_range:
            remaining = total_points
            for i in issues:
                # TODO: Replace exception with if-else checking for a None story points custom field
                try:
                    # Remove issue's story points from remaining if its resolution date
                    # is before/on current date in sprint timespan
                    if i.fields.resolutiondate.split('T')[0] <= d.strftime('%Y-%m-%d'):
                        if i.raw['fields'].get('customfield_10026') is not None:
                            remaining -= int(i.raw['fields']['customfield_10026'])
                        else:
                            remaining -= 0
                except AttributeError:
                    pass
            remaining_points[d.strftime('%Y-%m-%d')] = int(remaining)  # Put remaining points value in date/points dict

        slope = -total_points / (
                    len(remaining_points.keys()) - 1)  # get slope of ideal pace for guideline (linear decline)

        # Create guideline
        guideline = {}
        for i, k in zip(range(0, len(remaining_points.keys())), remaining_points.keys()):
            guideline[k] = (slope * i) + total_points  # should be a straight line

        # Plot chart
        fig = plt.figure(figsize=(12, 4))
        plt.step(remaining_points.keys(), remaining_points.values(), 'r-', label='Remaining Story Points', where='post')
        plt.plot(guideline.keys(), guideline.values(), color='grey', label='Guideline')
        plt.xlim([min(remaining_points.keys()), max(remaining_points.keys())])
        plt.ylim([0, total_points + 1])
        plt.xlabel('Date')
        plt.ylabel('Story Points')
        plt.legend()
        plt.title('Burndown Chart for Sprint \"{0}\" '.format(sprint.raw['name']))
        plt.gcf().autofmt_xdate()
        # Create filename using current date
        filename = 'burndown-' + datetime.now().strftime('%Y-%m-%d') + '-' + str(sprint.raw['id']) + '.jpg'
        # Save the plot locally
        plt.savefig(filename)
        # Return the filename
        return filename

    @commands.slash_command(name='jira-setup-token', description='Set up Jira Token to monitor Jira Issues.')
    async def jira_setup_token(self, ctx: discord.ApplicationContext, email='', url='', token=''):
        """
        Setup a Jira token to monitor issues in a Jira workspace.

        Requires an email address, workspace URL, and Jira authentication token. If any of them
        are not passed as arguments to the command, responds with usage instructions. If they
        are all present, a dict of Jira info is created and added to the list of
        Jira subscribers. If the user ID is already in the list of subscribers, simply
        update the info.

        :return: None
        """

        userId = ctx.user.id

        # TODO: Make authenticated list based on Discord server not single users
        jiraInfo = {}
        jiraInfo["url"] = url
        jiraInfo["email"] = email
        jiraInfo["token"] = token

        if userId in jira_subscribers:
            jira_subscribers[userId] = jiraInfo
            await ctx.respond('Token updated.')
        else:
            jira_subscribers[userId] = jiraInfo
            await ctx.respond('Token registered.')

    @commands.slash_command(name='jira-issue',
                      description='Get summary, description, issue type, and assignee of a Jira issue.')
    async def jira_get_issue(self, ctx: discord.ApplicationContext, issue_id=''):
        """
        Respond with information about a Jira issue.

        Requires an issue ID to be passed as an argument. If no argument is present, responds with
        usage instruction. If the sending user doesn't have a token added to the list of
        Jira subscribers, instructs the user to add one.

        :return: None
        """

        userId = ctx.user.id
        if issue_id == '':
            await ctx.respond(embed=discord.Embed(
                color=discord.Color.yellow(),
                title='Usage',
                description='/jira-issue <ISSUE_ID>')
            )
        else:
            tokenExists = (userId in jira_subscribers)
            if tokenExists == False:
                await ctx.respond(embed=discord.Embed(
                    color=discord.Color.red(),
                    title='Authentication Error',
                    description=f'User {ctx.user.name} is not authenticated with Jira.')
                )
            else:
                jiraInfo = jira_subscribers[userId]
                jira = JIRA(jiraInfo["url"], basic_auth=(jiraInfo["email"], jiraInfo["token"]))
                issue = jira.issue(issue_id)

                embed = discord.Embed(color=discord.Color.blurple(), title=issue_id)
                embed.add_field(name=f'Summary:', value=issue.fields.summary, inline=False)
                embed.add_field(name=f'Description:', value=issue.fields.description, inline=False)
                if issue.fields.assignee is None:
                    embed.add_field(name=f'Assignee:', value='Unassigned', inline=False)
                else:
                    embed.add_field(name=f'Assignee:', value=issue.fields.assignee.displayName, inline=False)
                embed.add_field(name=f'Status:', value=issue.fields.status.name, inline=False)
                await ctx.respond(embed=embed)

    @commands.slash_command(name='jira-sprint', description='Get summary of a project\'s active sprint.')
    async def jira_get_sprint(self, ctx: discord.ApplicationContext, project_id=''):
        """
        Get information about the current sprint in a Jira project.

        Sends a list of issues in the sprint as well as a burndown chart of
        the sprint's progress. Command requires a project ID as an argument. If one isn't
        provided, present the user with a list of projects in the authenticated workspace.

        :return: None
        """

        userId = ctx.user.id
        msg = ctx.message.content

        tokenExists = (userId in jira_subscribers)
        if tokenExists == False:
            await ctx.respond(embed=discord.Embed(
                color=discord.Color.red(),
                title='Authentication Error',
                description=f'User {ctx.user.name} is not authenticated with Jira.')
            )
            return

        jiraInfo = jira_subscribers[userId]
        jira = JIRA(jiraInfo["url"], basic_auth=(jiraInfo["email"], jiraInfo["token"]))

        # No args
        if project_id == '':
            await ctx.respond(embed=discord.Embed(
                title='Usage',
                color=discord.Color.yellow(),
                description='/sprint <PROJECT_ID>')
            )
            embed = discord.Embed(color=discord.Color.yellow(), title="Available Projects")
            projects = jira.projects()
            for project in projects:
                embed.add_field(name=project.name, value=f'Project ID: {project.id}', inline=False)
            await ctx.respond(embed=embed)
        else:
            # Find issues from the project's current sprint using JQL query
            query = 'project={0} AND SPRINT not in closedSprints() AND sprint not in futureSprints()'.format(project_id)
            issues = jira.search_issues(query)

            # TODO: Move to utils
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
            await paginator.respond(ctx.interaction, ephemeral=True)

            # Create burndown chart
            burndown_chart = self.burndown(jira, issues)
            with open(burndown_chart, 'rb') as f:
                picture = discord.File(f)
                await ctx.respond('**Burndown Chart:**', file=picture)
            remove(burndown_chart)  # Delete chart after sending it

    @commands.slash_command(name='jira-assign', description='Assign a Jira issue to a user.')
    async def jira_assign_issue(self, ctx: discord.ApplicationContext, issue_id='', user_id=''):
        """
        Assign a Jira ticket to a user.

        If the ticket already has an assignee, ask the user if they want to reassign it.
        If they respond yes, reassign it; if they respond no, don't reassign it.
        :return: None
        """

        userId = ctx.user.id

        tokenExists = (userId in jira_subscribers)
        if tokenExists == False:
            await ctx.respond(embed=discord.Embed(
                color=discord.Color.red(),
                title='Authentication Error',
                description=f'User {ctx.user.name} is not authenticated with Jira.')
            )
            return

        jiraInfo = jira_subscribers[userId]
        jira = JIRA(jiraInfo["url"], basic_auth=(jiraInfo["email"], jiraInfo["token"]))

        # TODO: Move to utils
        def divide_chunks(l, n):
            for i in range(0, len(l), n):
                yield l[i:i + n]

        if issue_id == '' and user_id == '':
            # projects = jira.projects()
            # for project in projects:
            # embed.add_field(name=project.name, value=project.id, inline=False)
            await ctx.respond(embed=discord.Embed(
                color=discord.Color.yellow(),
                title='Usage',
                description='/jira-assign <TICKET_ID> <USER_ID>')
            )

        # TODO: Move to get-issues command
        # User but no ticket
        # elif len(parts) == 2 and parts[1].isdigit():
        #     project_name = parts[1]
        #     issues = []
        #     i = 0
        #     chunk_size = 500
        #     while True:
        #         chunk = jira.search_issues(f'project = {project_name}', startAt=i, maxResults=chunk_size)
        #         i += chunk_size
        #         issues += chunk.iterable
        #         if i >= chunk.total:
        #             break
        #
        #     embed = discord.Embed(color=discord.Color.yellow(), title="Available tickets: ")
        #     for issue in issues:
        #         if issue.fields.status.name != 'Done':
        #             embed.add_field(name=issue, value=issue.fields.status, inline=False)
        #
        #     await ctx.respond(embed=embed)

        # Ticket but not user
        elif user_id == '':
            project_name = issue_id.split('-')[0]

            users = jira.search_assignable_users_for_projects('', project_name, maxResults=500)
            user_chunks = list(divide_chunks(users, 12))

            embeds = []
            pages = []
            for i in range(0, len(user_chunks)):
                embeds.append(discord.Embed(color=discord.Color.yellow(), title='Assignable Users'))
                for user in user_chunks[i]:
                    embeds[i].add_field(name=user.displayName, value=user.accountId, inline=False)
                pages.append(Page(
                    content=f'Available assignees (Part {i + 1}):',
                    embeds=[embeds[i]])
                )
            paginator = Paginator(pages=pages)
            await paginator.respond(ctx.interaction, ephemeral=True)

        else:
            project_name = issue_id.split('-')[0]
            users_dict = {}
            # TODO: Deal with max results
            users = jira.search_assignable_users_for_projects('', project_name, maxResults=200)

            for user in users:
                users_dict[user.accountId] = user.displayName

            if user_id.isnumeric():  # account ID
                user_name = users_dict.get(user_id)
            else:  # Given name
                user_name = user_id

            issue = jira.issue(issue_id)
            if issue.fields.assignee is not None:
                await ctx.respond(f'{issue_id} is already assigned to {issue.fields.assignee}. Reassign to {user_name}?')
                response = await ctx.bot.wait_for('message', timeout=20.0)
                if response.content in ['yes', 'Yes', 'y', 'Y']:
                    try:
                        jira.assign_issue(issue_id, user_name)
                        await ctx.respond(embed=discord.Embed(
                            color=discord.Color.green(),
                            title='Success',
                            description=f'Successfully reassigned {issue_id} to {user_name}.')
                        )
                    except JIRAError:
                        await ctx.respond(embed=discord.Embed(
                            title='User Error',
                            color=discord.Color.red(),
                            description=f'User {user_name} not found.')
                        )
                else:
                    await ctx.send(f'{issue_id} will not be reassigned to {user_name}.')
            else:
                try:
                    jira.assign_issue(issue_id, user_name)
                    await ctx.respond(embed=discord.Embed(
                        color=discord.Color.green(),
                        title='Success',
                        description=f'Successfully reassigned {issue_id} to {user_name}.')
                    )
                except JIRAError:
                    await ctx.respond(embed=discord.Embed(
                        title='User Error',
                        color=discord.Color.red(),
                        description=f'User {user_name} not found.')
                    )

    @commands.slash_command(name='jira-unassign', description='Unassign a Jira issue.')
    async def jira_unassign_issue(self, ctx: discord.ApplicationContext, issue_id=''):
        """
        Unassign a user from a Jira issue that has already been assigned to someone.

        Requires an issue ID and username to work.
        :return:
        """
        userId = ctx.user.id

        if issue_id == '':
            await ctx.respond(embed=discord.Embed(
                color=discord.Color.yellow(),
                title='Usage',
                description='/jira-unassign <ISSUE_ID>')
            )
            return
        else:
            tokenExists = (userId in jira_subscribers)
            if tokenExists == False:
                await ctx.respond(embed=discord.Embed(
                    color=discord.Color.red(),
                    title='Authentication Error',
                    description=f'User {ctx.user.name} is not authenticated with Jira.')
                )
                return

            jiraInfo = jira_subscribers[userId]
            jira = JIRA(jiraInfo["url"], basic_auth=(jiraInfo["email"], jiraInfo["token"]))

            jira.assign_issue(issue_id, None)
            await ctx.respond(embed=discord.Embed(
                color=discord.Color.green(),
                title='Success',
                description=f'{issue_id} has been unassigned.')
            )

def setup(bot):
    bot.add_cog(JiraCog(bot))
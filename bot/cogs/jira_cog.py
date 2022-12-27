import asyncio
import json
import os

import discord
import requests
from discord import Guild, Member, guild_only
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.pages import Page, Paginator
from jira import JIRA, JIRAError
from os import remove, getenv
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from queue import Queue
from bot.embeds import JiraExpiredTokenError, JiraNotAuthenticatedError, JiraAuthSuccess, HelpEmbed, UsageMessage, \
    JiraUserError, IssueAssignSuccess, JiraInstanceNotFoundError

JIRA_RESOURCES_ENDPOINT = os.getenv('JIRA_RESOURCES_ENDPOINT')
JIRA_API_URL = os.getenv('JIRA_API_URL')

with open('bot/cogs/json_/jira_tokens.json') as f:
    jira_tokens = json.load(f)  # channel ids of channels subscribed to issues
    f.close()
with open('bot/cogs/json_/jira_sites.json') as f:
    jira_sites = json.load(f)  # channel ids of channels subscribed to issues
    f.close()

auth_queue = Queue(maxsize=1)
queue_lock = asyncio.Lock()


class JiraCog(commands.Cog):
    jira = discord.SlashCommandGroup('jira', 'Commands related to Jira.')
    instance_commands = jira.create_subgroup('instance', 'Add/remove a Jira instance from the server.')
    issue = jira.create_subgroup('issue', 'Commands related to Jira issues.')

    def __init__(self, bot):
        self.bot = bot
        self.auth_queue_users = Queue(maxsize=5)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        """
        Delete existing records of guild and its members when the guild is deleted or the
        bot is removed.

        Parameters
        ----------
        guild

        Returns
        -------
        None
        """

        user = str(guild.id)
        members = guild.members

        for user in members:
            if jira_tokens.get(str(user.id)) is not None:
                jira_tokens.pop(str(user.id))

        if jira_sites.get(user) is not None:
            jira_sites.pop(user)

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

        if jira_tokens.get(user) is not None:
            jira_tokens.pop(user)

        self.save_dicts()

    def save_dicts(self):
        with open('bot/cogs/json_/jira_tokens.json', 'w') as f:
            json.dump(jira_tokens, f)  # channel ids of channels subscribed to issues
            f.close()
        with open('bot/cogs/json_/jira_sites.json', 'w') as f:
            json.dump(jira_sites, f)  # channel ids of channels subscribed to issues
            f.close()

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

    @issue.command(name='get', description='Get summary, description, issue type, and assignee of a Jira issue.')
    @guild_only()
    async def jira_get_issue(self, ctx: discord.ApplicationContext, issue_id=''):
        """
        Respond with information about a Jira issue.

        Requires an issue ID to be passed as an argument. If no argument is present, responds with
        usage instruction. If the sending user doesn't have a token added to the list of
        Jira subscribers, instructs the user to add one.

        :return: None
        """

        user_id = str(ctx.user.id)
        server = str(ctx.guild_id)
        token = jira_tokens.get(user_id)
        site = jira_sites.get(server)
        if issue_id == '':
            await ctx.respond(embed=UsageMessage('/jira issue <ISSUE_ID>'))
        elif token is None:
            await ctx.respond(embed=JiraNotAuthenticatedError(ctx.user.name))
        elif site is None:
            await ctx.respond(embed=HelpEmbed('No Instance Set', f'No Jira instance has been associated with this '
                                                                 f'server yet. Use **/jira instance set** to set one up.'))
        # Expired token
        elif datetime.strptime(token[1], "%Y-%m-%d %H:%M:%S") < datetime.now():
            await ctx.respond(embed=JiraExpiredTokenError(ctx.user.name))
        else:
            options = {
                'server': f'{JIRA_API_URL}/{site[1]}',
                'headers': {
                    'Authorization': f'Bearer {token[0]}'
                }
            }
            jira = JIRA(options=options)
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

    @jira.command(name='sprint', description='Get summary of a project\'s active sprint.')
    @guild_only()
    async def jira_get_sprint(self, ctx: discord.ApplicationContext, project_id=''):
        """
        Get information about the current sprint in a Jira project.

        Sends a list of issues in the sprint as well as a burndown chart of
        the sprint's progress. Command requires a project ID as an argument. If one isn't
        provided, present the user with a list of projects in the authenticated workspace.

        :return: None
        """

        user_id = str(ctx.user.id)
        server = str(ctx.guild_id)
        token = jira_tokens.get(user_id)
        site = jira_sites.get(server)
        if token is None:
            await ctx.respond(embed=JiraNotAuthenticatedError(ctx.user.name))
        elif site is None:
            await ctx.respond(embed=HelpEmbed('No Instance Found', f'No Jira instance has been associated with this'
                                                                   f'server yet. Use **/jira instance set** to set one up.'))
        # Expired token
        elif datetime.strptime(token[1], "%Y-%m-%d %H:%M:%S") < datetime.now():
            await ctx.respond(embed=JiraExpiredTokenError(ctx.user.name))
        # No args
        elif project_id == '':
            await ctx.respond(embed=UsageMessage('/jira sprint <PROJECT_ID>'))
            options = {
                'server': f'{JIRA_API_URL}/{site[1]}',
                'headers': {
                    'Authorization': f'Bearer {token[0]}'
                }
            }
            jira = JIRA(options=options)
            embed = discord.Embed(color=discord.Color.yellow(), title="Available Projects")
            projects = jira.projects()
            for project in projects:
                embed.add_field(name=project.name, value=f'Project ID: {project.id}', inline=False)
            await ctx.respond(embed=embed)
        else:
            options = {
                'server': f'{JIRA_API_URL}/{site[1]}',
                'headers': {
                    'Authorization': f'Bearer {token[0]}'
                }
            }
            jira = JIRA(options=options)
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
            await paginator.respond(ctx.interaction, ephemeral=False)

            # Create burndown chart
            burndown_chart = self.burndown(jira, issues)
            with open(burndown_chart, 'rb') as f:
                picture = discord.File(f)
                await ctx.respond('**Burndown Chart:**', file=picture)
            remove(burndown_chart)  # Delete chart after sending it

    @issue.command(name='assign', description='Assign a Jira issue to a user.')
    @guild_only()
    async def jira_assign_issue(self, ctx: discord.ApplicationContext, issue_id='', user_id=''):
        """
        Assign a Jira ticket to a user.

        If the ticket already has an assignee, ask the user if they want to reassign it.
        If they respond yes, reassign it; if they respond no, don't reassign it.
        :return: None
        """

        user = str(ctx.user.id)
        server = str(ctx.guild_id)
        token = jira_tokens.get(user)
        site = jira_sites.get(server)

        if token is None:
            await ctx.respond(embed=JiraNotAuthenticatedError(ctx.user.name))
        elif site is None:
            await ctx.respond(embed=HelpEmbed('Instance Not Set', 'No Jira instance has been associated with this '
                                                                  'server yet. Use **/jira instance set** to set one up.'))
        elif datetime.strptime(token[1], "%Y-%m-%d %H:%M:%S") < datetime.now():
            await ctx.respond(embed=JiraExpiredTokenError(ctx.user.name))
        else:
            if issue_id == '' and user_id == '':
                await ctx.respond(embed=UsageMessage('/jira assign <TICKET_ID> <USER_ID>'))
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
                # TODO: Move to utils
                def divide_chunks(l, n):
                    for i in range(0, len(l), n):
                        yield l[i:i + n]

                project_name = issue_id.split('-')[0]
                options = {
                    'server': f'{JIRA_API_URL}/{site[1]}',
                    'headers': {
                        'Authorization': f'Bearer {token[0]}'
                    }
                }
                jira = JIRA(options=options)
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
                await paginator.respond(ctx.interaction, ephemeral=False)
            else:
                options = {
                    'server': f'{JIRA_API_URL}/{site[1]}',
                    'headers': {
                        'Authorization': f'Bearer {token[0]}'
                    }
                }
                jira = JIRA(options=options)
                project_name = issue_id.split('-')[0]
                users_dict = {}
                # TODO: Deal with max results
                users = jira.search_assignable_users_for_projects('', project_name, maxResults=200)

                for user in users:
                    users_dict[user.accountId] = user.displayName

                if user_id[0].isnumeric():  # account ID
                    user_name = users_dict.get(user_id)
                else:  # Given name
                    user_name = user_id

                issue = jira.issue(issue_id)
                if issue.fields.assignee is not None:
                    await ctx.respond(
                        f'{issue_id} is already assigned to {issue.fields.assignee}. Reassign to {user_name}?')
                    response = await ctx.bot.wait_for('message', timeout=20.0)
                    if response.content in ['yes', 'Yes', 'y', 'Y']:
                        # TODO: Switch to some other kind of error checking?
                        try:
                            jira.assign_issue(issue_id, user_name)
                            await ctx.respond(embed=IssueAssignSuccess(issue_id, user_name))
                        except JIRAError:
                            await ctx.respond(embed=JiraUserError(user_name))
                    else:
                        await ctx.send(f'{issue_id} will not be reassigned to {user_name}.')
                else:
                    try:
                        jira.assign_issue(issue_id, user_name)
                        await ctx.respond(embed=IssueAssignSuccess(issue_id, user_name))
                    except JIRAError:
                        await ctx.respond(embed=JiraUserError(user_name))

    @issue.command(name='unassign', description='Unassign a Jira issue.')
    @guild_only()
    async def jira_unassign_issue(self, ctx: discord.ApplicationContext, issue_id=''):
        """
        Unassign a user from a Jira issue that has already been assigned to someone.

        Requires an issue ID and username to work.
        :return:
        """
        user_id = str(ctx.user.id)
        server = str(ctx.guild_id)
        token = jira_tokens.get(user_id)
        site = jira_sites.get(server)

        if token is None:
            await ctx.respond(embed=JiraNotAuthenticatedError(ctx.user.name))
        elif site is None:
            await ctx.respond(embed=HelpEmbed('Instance Not Set',
                                              f'No Jira instance has been associated with this server yet. Use '
                                              f'**/jira instance set** to set one up.'))
        elif datetime.strptime(token[1], "%Y-%m-%d %H:%M:%S") < datetime.now():
            await ctx.respond(embed=JiraExpiredTokenError(ctx.user.name))
        else:
            if issue_id == '':
                await ctx.respond(embed=UsageMessage('/jira unassign <ISSUE_ID>'))
            else:
                options = {
                    'server': f'{JIRA_API_URL}/{site[1]}',
                    'headers': {
                        'Authorization': f'Bearer {token[0]}'
                    }
                }
                jira = JIRA(options=options)
                jira.assign_issue(issue_id, None)
                await ctx.respond(embed=discord.Embed(
                    color=discord.Color.green(),
                    title='Success',
                    description=f'{issue_id} has been unassigned.')
                )

    @jira.command(name='auth', description='Authenticate with the CollabyBot OAuth app to use Jira commands'
                                           ' that access the Jira API.')
    @guild_only()
    async def jira_auth(self, ctx: discord.ApplicationContext):
        user_id = str(ctx.author.id)
        token = jira_tokens.get(user_id)
        if token is not None and datetime.strptime(token[1], "%Y-%m-%d %H:%M:%S") > datetime.now():
            await ctx.respond(embed=HelpEmbed('User Already Authenticated',
                                              f'User {ctx.user.name} is already authenticated with Jira.'))
        else:
            await queue_lock.acquire()
            user = ctx.author
            self.auth_queue_users.put(user_id)

            await user.send('Click here to authorize CollabyBot to access the Jira API.',
                            view=AuthButton())
            await ctx.respond('Follow the link in your DMs to authorize CollabyBot on Jira.')

    async def jira_add_token(self, token: str, expires: datetime):
        user_id = self.auth_queue_users.get()
        queue_lock.release()
        jira_tokens[user_id] = (token, expires)
        user = await self.bot.fetch_user(int(user_id))
        await user.send('Authentication complete.')

    @instance_commands.command(name='set', description='Associate your Jira instance with this server '
                                                                  'to access your project using Jira commands.')
    @guild_only()
    async def jira_set_instance(self, ctx: discord.ApplicationContext, instance=''):
        user_id = str(ctx.user.id)
        server = str(ctx.guild_id)
        token = jira_tokens.get(user_id)

        if instance == '':
            await ctx.respond(embed=UsageMessage('/jira instance set <INSTANCE_NAME>'))
        elif token is None:
            await ctx.respond(embed=JiraNotAuthenticatedError(ctx.user.name))
        elif datetime.strptime(token[1], "%Y-%m-%d %H:%M:%S") < datetime.now():
            await ctx.respond(embed=JiraExpiredTokenError(ctx.user.name))
        else:
            # Instance already exists
            if jira_sites.get(server) is not None:
                await ctx.send(f'This server is already linked to the {jira_sites.get(server)[0]} instance. '
                               f'Replace it with {instance}? (Yes/no)')
                response = await ctx.bot.wait_for('message', timeout=20.0)
                if response.content in ['y', 'Y', 'yes', 'Yes']:
                    r = requests.get(JIRA_RESOURCES_ENDPOINT,
                                     headers={'Authorization': f'Bearer {token[0]}',
                                              'Accept': 'application/json'})
                    for site in r.json():
                        if site['name'] == instance:
                            jira_sites[server] = (site['name'], site['id'])
                            await ctx.respond(embed=JiraAuthSuccess(instance))
                            break
                    # Instance was not found in response
                    if jira_sites.get(server) is None:
                        await ctx.respond(embed=JiraInstanceNotFoundError(instance, ctx.user.name))
                else:
                    await ctx.send(f'The instance will not be changed to {instance}.')
            else:
                r = requests.get(JIRA_RESOURCES_ENDPOINT,
                                 headers={'Authorization': f'Bearer {token[0]}',
                                          'Accept': 'application/json'})
                for site in r.json():
                    if site['name'] == instance:
                        jira_sites[server] = (site['name'], site['id'])
                        await ctx.respond(embed=discord.Embed(
                            color=discord.Color.green(),
                            title='Success',
                            description=f'You can now use Jira commands to access projects in {instance}!')
                        )
                        break
                # Instance was not found in response
                if jira_sites.get(server) is None:
                    await ctx.respond(embed=JiraInstanceNotFoundError(instance, ctx.user.name))

    @instance_commands.command(name='get', description='Get the name of the Jira instance currently associated '
                                                       'with this server.')
    @guild_only()
    async def jira_get_instance(self, ctx: discord.ApplicationContext):
        server = str(ctx.guild_id)
        site = jira_sites.get(server)
        if site is None:
            await ctx.respond(embed=HelpEmbed('Instance Not Set',
                                              'No Jira instance has been associated with this server yet. Use **/jira instance set** to set one up.'))
        else:
            await ctx.respond(embed=discord.Embed(
                color=discord.Color.blurple(),
                title='Current Jira Instance',
                description=f'{site[0]}')
            )

    @instance_commands.command(name='remove', description='Remove the Jira instance currently associated '
                                                                     'with this server.')
    @guild_only()
    async def jira_remove_instance(self, ctx: discord.ApplicationContext):
        server = str(ctx.guild_id)
        site = jira_sites.get(server)
        if site is None:
            await ctx.respond(embed=HelpEmbed('Instance Not Set', 'No Jira instance has been associated with this '
                                                                  'server yet. Use **/jira instance set** to set one up.'))
        else:
            await ctx.respond(f'Are you sure you want to remove {site[0]} from this server? It can be added back at any'
                              f' time using **/jira instance set**. (Yes/no)')
            response = await ctx.bot.wait_for('message', timeout=20.0)
            if response.content in ['y', 'Y', 'yes', 'Yes']:
                site = jira_sites.pop(server)
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.green(),
                    title='Success',
                    description=f'{site[0]} is no longer associated with this server.')
                )
            else:
                await ctx.respond(
                    f'{site[0]} will not be removed from this server.')


def setup(bot):
    bot.add_cog(JiraCog(bot))


class AuthButton(discord.ui.View):
    def __init__(self):
        super().__init__()
        button = discord.ui.Button(label="Authorize",
                                   style=discord.ButtonStyle.link,
                                   url=f'https://9a28-104-254-90-195.ngrok.io/auth/jira')
        self.add_item(button)

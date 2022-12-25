from discord import Color, Embed


class RepoAddSuccess(Embed):
    def __init__(self, repo: str):
        self.color = Color.green()
        self.title = 'Success'
        self.description = f'{repo} has been added.'


class GitHubNotAuthenticatedError(Embed):
    def __init__(self, user: str):
        self.color = Color.red()
        self.title = 'Success'
        self.description = f'{user} has not been authenticated. Use /**github authenticate** to authenticate ' \
                           f'before using GitHub commands.'


class JiraNotAuthenticatedError(Embed):
    def __init__(self, user: str):
        self.color = Color.red()
        self.title = 'Authentication Error'
        self.description = f'{user} has not been authenticated. Use /**jira authenticate** to authenticate ' \
                           f'before using Jira commands.'


class UsageMessage(Embed):
    def __init__(self, message: str):
        self.color = Color.yellow(),
        self.title = 'Usage',
        self.description = message


class GitHub422Error(Embed):
    def __init__(self, repo: str, server: str):
        self.color = Color.yellow(),
        self.title = 'Webhook Already Exists',
        self.description = f'{repo} already has CollabyBot webhooks installed. It will still '
        f'be added to {server}\'s list of tracked repositories.'


class GitHub403Error(Embed):
    def __init__(self, message: str):
        self.color = Color.red()
        self.title = 'Access Denied Error'
        self.description = message


class GitHub404Error(Embed):
    def __init__(self, repo: str):
        self.color = Color.red()
        self.title = 'Not Found Error'
        self.description = f'Repository {repo} not found. Either the repo doesn\'t exist, uou don\'t have permission' \
                           f' to add webhooks to this repository, or the repo is private and you don\'t' \
                           f' have access to it.'


class HelpEmbed(Embed):
    def __init__(self, title: str, message: str):
        self.color = Color.yellow()
        self.title = title
        self.description = message


class CommitSubscriptionSuccess(Embed):
    def __init__(self, channel: str, repo: str, branch: str):
        self.color = Color.green()
        self.title = 'Success'
        self.description = f'#{channel} is now subscribed to commits for {repo} on {branch}!'


class IssueSubscriptionSuccess(Embed):
    def __init__(self, channel: str, repo: str):
        self.color = Color.green()
        self.title = 'Success'
        self.description = f'#{channel} is now subscribed to issues for {repo}!'


class PullRequestSubscriptionSuccess(Embed):
    def __init__(self, channel: str, repo: str):
        self.color = Color.green()
        self.title = 'Success'
        self.description = f'#{channel} is now subscribed to pull requests for {repo}!'


class JiraExpiredTokenError(Embed):
    def __init__(self, user: str):
        self.color = Color.red()
        self.title = 'Authenticated Error: Expired Token'
        self.description = f'It looks like {user}\'s OAuth token has expired. Use /jira-auth to get' \
                           f' a new token.'


class JiraAuthSuccess(Embed):
    def __init__(self, instance: str):
        self.color = Color.green()
        self.title = 'Success'
        self.description = f'You can now use Jira commands to access projects in {instance}!'


class IssueAssignSuccess(Embed):
    def __init__(self, issue: str, user: str):
        self.color = Color.green()
        self.title = 'Success'
        self.description = f'Successfully assigned {issue} to {user}!'


class JiraUserError(Embed):
    def __init__(self, user: str):
        self.color = Color.red()
        self.title = 'User Error'
        self.description = f'User {user} not found.'


class JiraInstanceNotFoundError(Embed):
    def __init__(self, instance: str, user: str):
        self.color = Color.red()
        self.title = 'Instance Not Found'
        self.description = f'Could not find Jira instance named {instance} within {user}\'s scope.'

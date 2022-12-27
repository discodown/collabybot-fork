from discord import Color, Embed


class RepoAddSuccess(Embed):
    def __init__(self, repo: str):
        super().__init__(color=Color.green(), title='Success', description=f'{repo} has been added.')


class GitHubNotAuthenticatedError(Embed):
    def __init__(self, user: str):
        super().__init__(color=Color.red(), title='Authentication Error',
                         description=f'{user} has not been authenticated. Use /**github auth** to authenticate ' \
                                     f'before using GitHub commands.'
                         )


class JiraNotAuthenticatedError(Embed):
    def __init__(self, user: str):
        super().__init__(color=Color.red(), title='Authentication Error',
                         description=f'{user} has not been authenticated. Use /**jira auth** to authenticate ' \
                                     f'before using Jira commands.'
                         )


class UsageMessage(Embed):
    def __init__(self, message: str):
        super().__init__()
        self.color = Color.yellow(),
        self.title = 'Usage',
        self.description = message


class GitHub422Error(Embed):
    def __init__(self, repo: str, server: str):
        super().__init__(color=Color.yellow(), title='Webhook Already Exists',
                         description=f'{repo} already has CollabyBot webhooks installed. It will still '
                                     f'be added to {server}\'s list of tracked repositories.'
                         )


class GitHub403Error(Embed):
    def __init__(self, message: str):
        super().__init__(color=Color.red(), title='Access Denied Error', description=message)


class GitHub404Error(Embed):
    def __init__(self, repo: str):
        super().__init__(color=Color.red(), title='Not Found Error',
                         description=f'Repository {repo} not found. Either the repo doesn\'t exist, uou don\'t have permission' \
                                     f' to add webhooks to this repository, or the repo is private and you don\'t' \
                                     f' have access to it.'
                         )


class HelpEmbed(Embed):
    def __init__(self, title: str, message: str):
        super().__init__(title=title, color=Color.yellow(), description=message)


class SuccessEmbed(Embed):
    def __int__(self, message: str):
        super().__init__(color=Color.green(), title='Success', description=message)


class CommitSubscriptionSuccess(Embed):
    def __init__(self, channel: str, repo: str, branch: str):
        super().__init__(color=Color.green(), title='Success',
                         description=f'#{channel} is now subscribed to commits for {repo} on {branch}!')


class IssueSubscriptionSuccess(Embed):
    def __init__(self, channel: str, repo: str):
        super().__init__(color=Color.green(), title='Success',
                         description=f'#{channel} is now subscribed to issues for {repo}!')


class PullRequestSubscriptionSuccess(Embed):
    def __init__(self, channel: str, repo: str):
        super().__init__(color=Color.green(), title='Success',
                         description=f'#{channel} is now subscribed to pull requests for {repo}!')


class JiraExpiredTokenError(Embed):
    def __init__(self, user: str):
        super().__init__(color=Color.red(), title='Authenticated Error: Expired Token',
                         description=f'It looks like {user}\'s OAuth token has expired. Use **/jira auth** to get' \
                                     f' a new token.')


class JiraAuthSuccess(Embed):
    def __init__(self, instance: str):
        super().__init__(color=Color.green(), title='Success',
                         description=f'You can now use Jira commands to access projects in {instance}!')


class IssueAssignSuccess(Embed):
    def __init__(self, issue: str, user: str):
        super().__init__(color=Color.green(), title='Success',
                         description=f'Successfully assigned {issue} to {user}!')


class JiraUserError(Embed):
    def __init__(self, user: str):
        super().__init__(color=Color.red(), title='User Error', description=f'User {user} not found.')


class JiraInstanceNotFoundError(Embed):
    def __init__(self, instance: str, user: str):
        super().__init__(color=Color.red(), title='Instance Not Found',
                         description=f'Could not find Jira instance named {instance} within {user}\'s scope.')

from bot.CollabyBot import DiscordCollabyBot
from fastapi import Request, APIRouter
import http
from pprint import pprint
from bot.github_objects import *

router = APIRouter()
discordBot = DiscordCollabyBot()

@router.post("/webhook/commits", tags=['webhook'], status_code=http.HTTPStatus.ACCEPTED)
async def payload_handler_commits(
        request: Request
):
    """
    Triggered when a commit event is received from GitHub.

    When a payload is received, the commit's message, repository, author, timestamp,
    action type, and URL are extracted to create a Commit object. A string representation
    of the object is sent to the bot using send_payload_message along with the branch
    the commit was pushed to.

    :param Request request: Request header of the payload.
    :raises AttributeError: Raised if no branch is specified in the response.
    :return: None
    """

    if request.headers['X-Github-Event'] == 'ping':
        pass
    else:
        payload_json = await request.json()
        # TODO: Add status check, add modifief param
        repo = payload_json.get('repository')['name']

        # Get branch
        try:
            branch = payload_json.get('ref').split('/')[-1]
        except AttributeError:  # if ref isn't in the response, it came from the main branch
            print('No branch information in payload. Defaulting to main.')
            branch = 'main'

        commit = Commit(str(payload_json.get('commits')[0].get('message')), 'commit',
                        str(payload_json.get('repository').get('full_name')),
                        str(payload_json.get('commits')[0].get('timestamp')),
                        str(payload_json.get('commits')[0].get('url')),
                        str(payload_json.get('commits')[0].get('author').get('name')))
        await discordBot.get_cog('GitHubCog').send_payload_message(commit.object_string(), event='push', repo=repo,
                                                                   branch=branch)


@router.post("/webhook/issues", tags=['webhook'], status_code=http.HTTPStatus.ACCEPTED)
async def payload_handler_issues(
        request: Request
):
    """
    Triggered when a issue event is received from GitHub.

    When a payload is received, the issue's body, action type, repository URL,
    associated user, and time of creation are extracted from the response
    object and used to create an Issue object. A string representation of the
    object is sent to the bot using send_payload_message.

    :param Request request: Request header of the payload.
    :raises AttributeError: Raised if no branch is specified in the response.
    :return: None
    """

    if request.headers['X-Github-Event'] == 'ping':
        pass
    else:
        payload_json = await request.json()
        # TODO: Add status check, add modified param
        repo = payload_json.get('repository')['name']

        try:
            branch = payload_json.get('ref').split('/')[-1]
        except AttributeError:  # if ref isn't in the response, it came from the main branch
            print('No branch information in payload. Defaulting to main.')
            branch = 'main'

        issue = Issue(str(payload_json.get('issue').get('body')), str(payload_json.get('action')),
                      str(payload_json.get('repository').get('full_name')),
                      str(payload_json.get('issue').get('created_at')), str(payload_json.get('issue').get('html_url')),
                      str(payload_json.get('issue').get('user').get('login')))
        await discordBot.get_cog('GitHubCog').send_payload_message(issue.object_string(), event='issue', repo=repo,
                                                                   branch=branch)


@router.post("/webhook/pull-request", tags=['webhook'], status_code=http.HTTPStatus.ACCEPTED)
async def payload_handler_pr(
        request: Request
):
    """
    Triggered when a pull-request event is received from GitHub.

    When a payload is received, the pull request's reviewer, status, review body,
    reviewer requested flag, action, repository, associated user, URL, and
    action type are extracted from the response object and used to create a
    PullRequest object. A string representation of the object is sent to the bot
    using send_payload_message.

    :param Request request: Request header of the payload.
    :raises AttributeError: Raised if no branch is specified in the response.
    :return: None
    """

    if request.headers['X-Github-Event'] == 'ping':
        pass
    else:
        payload_json = await request.json()
        repo = payload_json.get('repository')['name']

        try:
            branch = payload_json.get('ref').split('/')[-1]
        except AttributeError:  # if ref isn't in the response, it came from the main branch
            print('No branch information in payload. Defaulting to main.')
            branch = 'main'

        reviewer_requested = None
        reviewer = None
        pr_state = None
        review_body = None
        timestamp = payload_json["pull_request"]["updated_at"]

        # if review is in the response, get review information
        if payload_json.get('review') is not None:
            reviewer = payload_json["review"]["user"]["login"]
            pr_state = payload_json["review"]["state"]
            review_body = payload_json["review"]["body"]
            timestamp = payload_json["review"]["submitted_at"]
        # get requested reviewer if there is one
        elif payload_json.get('action') == 'review_requested':
            reviewer_requested = payload_json["requested_reviewer"]["login"]
        else:
            pass
        # TODO: Add status check
        PR = PullRequest(payload_json.get('action'), payload_json["pull_request"]["body"],
                         payload_json["repository"]["full_name"], timestamp,
                         payload_json["pull_request"]["html_url"],
                         payload_json["pull_request"]["user"]["login"], reviewer_requested, reviewer, review_body, pr_state)
        await discordBot.get_cog('GitHubCog').send_payload_message(PR.object_string(), event='pull_request', repo=repo,
                                                                   branch=branch)
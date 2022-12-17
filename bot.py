import pprint
from src.bot.CollabyBot import DiscordCollabyBot
from src.bot.github_objects import *
import os
from dotenv import load_dotenv
import discord
import asyncio
from fastapi import FastAPI, Request, Response
import http
import uvicorn
import nest_asyncio


nest_asyncio.apply()  # needed to prevent errors caused by nested async tasks
load_dotenv()  # load env file
intents = discord.Intents().all()  # default to all intents for bot
discordToken = os.getenv('DISCORD_BOT_TOKEN')  # get bot token
discordBot = DiscordCollabyBot(intents=intents, command_prefix='/')  # create the bot instance
DiscordCollabyBot.add_all_commands(discordBot)  # register all bot commands before running the bot

# Create FastAPI app
app = FastAPI(
    title="CollabyBot",
    version="0.0.1",
)

app.payload = " "


@app.get("/")
async def root():
    """
    Root endpoint, needed for FastAPI to work.

    :return: None
    """

    if app.payload == " ":
        return {"message": "NO INCOMING POSTS"}

    elif app.payload != " ":
        return {"message": app.payload.sender}


@app.post("/webhook/commits", status_code=http.HTTPStatus.ACCEPTED)
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

    payload_json = await request.json()
    print(payload_json)
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
    await discordBot.get_cog('GitHubCog').send_payload_message(commit.object_string(), event='push', repo=repo, branch=branch)


@app.post("/webhook/issues", status_code=http.HTTPStatus.ACCEPTED)
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

    payload_json = await request.json()
    # TODO: Add status check, add modified param
    repo = payload_json.get('repository')['name']

    try:
        branch = payload_json.get('ref').split('/')[-1]
    except AttributeError:  # if ref isn't in the response, it came from the main branch
        print('No branch information in payload. Defaulting to main.')
        branch = 'main'

    issue = Issue(str(payload_json.get('issue').get('body')), str(payload_json.get('action')),
                  str(payload_json.get('issue').get('repository_url')),
                  str(payload_json.get('issue').get('created_at')), str(payload_json.get('issue').get('html_url')),
                  str(payload_json.get('issue').get('user').get('login')))
    await discordBot.get_cog('GitHubCog').send_payload_message(issue.object_string(), event='issue', repo=repo, branch=branch)


@app.post("/webhook/pull-request", status_code=http.HTTPStatus.ACCEPTED)
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

    payload_json = await request.json()
    pprint.pprint(payload_json)

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
    await discordBot.get_cog('GitHubCog').send_payload_message(PR.object_string(), event='pull_request', repo=repo, branch=branch)


@app.on_event("startup")
async def startup_event():
    """
    Run the Discord bot as an asyncio task before starting the FastAPI server.

    This is needed to prevent the bot from blocking the server from executing
    any further code.

    :return: None
    """
    asyncio.create_task(discordBot.start(discordToken))

@app.on_event("shutdown")
async def shutdown_event():
    cog = discordBot.get_cog('GitHubCog')
    cog.save_dicts()


# Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

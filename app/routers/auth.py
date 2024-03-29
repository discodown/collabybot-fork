from datetime import datetime, timedelta
import hashlib
import json
from dotenv import load_dotenv
from fastapi import APIRouter
import http
from queue import Queue
from asyncio import Lock
import os
from fastapi.responses import RedirectResponse, Response
import requests
from bot.CollabyBot import DiscordCollabyBot
from uuid import UUID, uuid4

from hashlib import sha256

router = APIRouter()
lock = Lock()
load_dotenv()
GH_CLIENT_ID = os.getenv('GH_CLIENT_ID')
GH_CLIENT_SECRET = os.getenv('GH_CLIENT_SECRET')
JIRA_AUTH_URL = os.getenv('JIRA_AUTH_URL')
JIRA_CLIENT_ID = os.getenv('JIRA_CLIENT_ID')
JIRA_CLIENT_SECRET = os.getenv('JIRA_CLIENT_SECRET')
HOME_URL = os.getenv('HOME_URL')
JIRA_API_URL = os.getenv('JIRA_API_URL')
JIRA_RESOURCES_ENDPOINT = os.getenv('JIRA_RESOURCES_ENDPOINT')
bot = DiscordCollabyBot()


@router.get("/auth/github", tags=['auth'], status_code=http.HTTPStatus.ACCEPTED,
            response_class=RedirectResponse)
async def gh_auth():
    r = requests.get('https://github.com/login/oauth/authorize', params={'client_id': GH_CLIENT_ID,
                                                                         'scope': ['repo']})

    response = RedirectResponse(r.url)
    return response


@router.get('/auth/github/callback', tags=['auth'], status_code=http.HTTPStatus.ACCEPTED)
async def gh_callback(code: str):
    r = requests.post('https://github.com/login/oauth/access_token',
                      params={
                          'client_id': GH_CLIENT_ID,
                          'client_secret': GH_CLIENT_SECRET,
                          'code': code,
                      },
                      headers={'Accept': 'application/json'})
    token = r.json()['access_token']
    await bot.get_cog('GitHubCog').add_gh_token(token)


@router.get('/auth/jira', tags=['auth'], status_code=http.HTTPStatus.ACCEPTED,
            response_class=RedirectResponse)
async def jira_auth():
    session = uuid4()
    m = hashlib.sha256()
    m.update(session.bytes)
    state = m.hexdigest()
    url = JIRA_AUTH_URL.format(YOUR_USER_BOUND_VALUE=state)

    response = RedirectResponse(url)
    return response


@router.get('/auth/jira/callback', tags=['auth'], status_code=http.HTTPStatus.ACCEPTED)
async def jira_callback(state: str, code: str):
    r = requests.post('https://auth.atlassian.com/oauth/token',
                      json={
                          'grant_type': "authorization_code",
                          'client_id': JIRA_CLIENT_ID,
                          'client_secret': JIRA_CLIENT_SECRET,
                          'code': code,
                          'redirect_uri': f'{HOME_URL}/auth/jira/callback'
                      },
                      headers={'Content-Type': 'application/json'})
    print(r.content)
    token = r.json()['access_token']
    expires = datetime.now() + timedelta(seconds=r.json()['expires_in'])
    await bot.get_cog('JiraCog').jira_add_token(token, expires.strftime("%Y-%m-%d %H:%M:%S"))







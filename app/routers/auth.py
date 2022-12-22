from dotenv import load_dotenv
from fastapi import APIRouter
import http
from queue import Queue
from asyncio import Lock
import os
from fastapi.responses import RedirectResponse
import requests
from bot.CollabyBot import DiscordCollabyBot

router = APIRouter()
lock = Lock()
load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
bot = DiscordCollabyBot()


@router.get("/gh-auth", status_code=http.HTTPStatus.ACCEPTED, response_class=RedirectResponse)
async def gh_auth():
    r = requests.get('https://github.com/login/oauth/authorize', params={'client_id': CLIENT_ID,
                                                                         'scope': ['repo']})
    return RedirectResponse(r.url)


@router.get('/gh-auth/callback', status_code=http.HTTPStatus.ACCEPTED)
async def gh_callback(code: str):
    r = requests.post('https://github.com/login/oauth/access_token',
                      params={
                          'client_id': CLIENT_ID,
                          'client_secret': CLIENT_SECRET,
                          'code': code,
                      },
                      headers={'Accept': 'application/json'})
    token = r.json()['access_token']
    bot.get_cog('GitHubCog').add_gh_token(token)




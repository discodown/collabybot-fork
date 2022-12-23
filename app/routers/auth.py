import hashlib

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
import http
from queue import Queue
from asyncio import Lock
import os
from fastapi.responses import RedirectResponse, Response
import requests
from bot.CollabyBot import DiscordCollabyBot
from pydantic import BaseModel
from fastapi_sessions.frontends.implementations import SessionCookie, CookieParameters
from uuid import UUID, uuid4
from fastapi_sessions.backends.implementations import InMemoryBackend
from fastapi_sessions.session_verifier import SessionVerifier
from hashlib import sha256

router = APIRouter()
lock = Lock()
load_dotenv()
GH_CLIENT_ID = os.getenv('GH_CLIENT_ID')
GH_CLIENT_SECRET = os.getenv('GH_CLIENT_SECRET')
COOKIE_SECRET = os.getenv('COOKIE_SECRET')
JIRA_AUTH_URL = os.getenv('JIRA_AUTH_URL')
JIRA_CLIENT_ID = os.getenv('JIRA_CLIENT_ID')
JIRA_CLIENT_SECRET = os.getenv('JIRA_CLIENT_SECRET')
HOME_URL = os.getenv('HOME_URL')
bot = DiscordCollabyBot()


class SessionData(BaseModel):
    user_id: str


cookie_params = CookieParameters()

cookie = SessionCookie(
    cookie_name="cookie",
    identifier="general_verifier",
    auto_error=True,
    secret_key=COOKIE_SECRET,
    cookie_params=cookie_params,
)

backend = InMemoryBackend[UUID, SessionData]()


class BasicVerifier(SessionVerifier[UUID, SessionData]):
    def __init__(
        self,
        *,
        identifier: str,
        auto_error: bool,
        backend: InMemoryBackend[UUID, SessionData],
        auth_http_exception: HTTPException,
    ):
        self._identifier = identifier
        self._auto_error = auto_error
        self._backend = backend
        self._auth_http_exception = auth_http_exception

    @property
    def identifier(self):
        return self._identifier

    @property
    def backend(self):
        return self._backend

    @property
    def auto_error(self):
        return self._auto_error

    @property
    def auth_http_exception(self):
        return self._auth_http_exception

    def verify_session(self, model: SessionData) -> bool:
        """If the session exists, it is valid"""
        return True


verifier = BasicVerifier(
    identifier="general_verifier",
    auto_error=True,
    backend=backend,
    auth_http_exception=HTTPException(status_code=403, detail="invalid session"),
)


@router.get("/auth/github/{user_id}", tags=['auth'], status_code=http.HTTPStatus.ACCEPTED, response_class=RedirectResponse)
async def gh_auth(user_id: str):
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
    # bot.get_cog('GitHubCog').add_gh_token(token)


@router.get('/auth/jira/user_id={user_id}', tags=['auth'], status_code=http.HTTPStatus.ACCEPTED, response_class=RedirectResponse)
async def jira_auth(user_id: str):
    session = uuid4()
    data = SessionData(user_id=user_id)
    m = hashlib.sha256()
    m.update(session.bytes)
    state = m.hexdigest()
    url = JIRA_AUTH_URL.format(YOUR_USER_BOUND_VALUE=state)

    await backend.create(session, data)
    response = RedirectResponse(url)
    cookie.attach_to_response(response, session)
    return response


@router.get('/auth/jira/callback', tags=['auth'], status_code=http.HTTPStatus.ACCEPTED,
            dependencies=[Depends(cookie)])
def jira_callback(code: str, state: str):
    r = requests.post('https://auth.atlassian.com/oauth/token',
                      json={
                          'grant_type': "authorization_code",
                          'client_id': JIRA_CLIENT_ID,
                          'client_secret': JIRA_CLIENT_SECRET,
                          'code': code,
                          'redirect_uri': f'{HOME_URL}/auth/jira/callback'
                      },
                      headers={'Content-Type': 'application/json'})




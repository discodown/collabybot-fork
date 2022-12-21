from fastapi import APIRouter
import http

router = APIRouter()

@router.get("/gh-auth", status_code=http.HTTPStatus.ACCEPTED)
async def gh_auth(code: str):
    print(code)

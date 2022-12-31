import os
from dotenv import load_dotenv
import discord
import asyncio
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import http
import uvicorn
import nest_asyncio
from routers import webhook, auth
import bot
from bot.CollabyBot import DiscordCollabyBot
import logging

logging.basicConfig(level=logging.INFO)

nest_asyncio.apply()  # needed to prevent errors caused by nested async tasks
# load_dotenv()  # load env file
intents = discord.Intents().all()  # default to all intents for bot
discordToken = os.getenv('DISCORD_BOT_TOKEN')  # get bot token
discordBot = DiscordCollabyBot(intents=intents, command_prefix='/')  # create the bot instance
DiscordCollabyBot.add_all_commands(discordBot)  # register all bot commands before running the bot
PORT = os.getenv('PORT') or 8000


# Create FastAPI app
app = FastAPI(
    title="CollabyBot",
    version="0.0.1",
)

app.include_router(webhook.router)
app.include_router(auth.router)

app.payload = " "


@app.get("/", status_code=http.HTTPStatus.ACCEPTED, response_class=RedirectResponse)
async def root():
    """
    Root endpoint, needed for FastAPI to work.

    :return: None
    """

    if app.payload == " ":
        return {"message": "NO INCOMING POSTS"}

    elif app.payload != " ":
        return {"message": app.payload.sender}


@app.on_event("startup")
async def startup_event():
    """
    Run the Discord bot as an asyncio task before starting the FastAPI server.

    This is needed to prevent the bot from blocking the server from executing
    any further code.

    :return: None
    """
    asyncio.create_task(discordBot.start(discordToken))


# @app.on_event("shutdown")
# async def shutdown_event():
#     cog = discordBot.get_cog('GitHubCog')
#     cog.save_dicts()
#     cog = discordBot.get_cog('JiraCog')
#     cog.save_dicts()


# Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)

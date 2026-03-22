"""
Telegram Bot for automated reposting from VKontakte community pages
to Telegram channels.

v4.0
by @zaicol
original by @alcortazzo
"""
import asyncio
import os
import traceback

from aiogram import Bot
from aiogram.client.bot import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import BasicAuth
from loguru import logger

from config import SINGLE_START, TIME_TO_SLEEP, PROXY_URL, PROXY_LOGIN, PROXY_PASSWORD, TG_BOT_TOKEN
from custom_exceptions import ProxyException
from start_script import start_script
from tools import authors, remove_temp_folder

logger.add(
    "./logs/vktgbot.log",
    format="{time} {level} {message}",
    level="DEBUG",
    rotation="1 week",
    compression="zip",
)

logger.info("Script is started.")


async def run_loop(bot: Bot) -> None:
    while True:
        await start_script(bot)
        remove_temp_folder()

        if SINGLE_START:
            logger.info("Script has successfully completed its execution")
            break
        else:
            logger.info(f"Script went to sleep for {TIME_TO_SLEEP} seconds.")
            await asyncio.sleep(TIME_TO_SLEEP)


def create_bot() -> Bot:
    try:
        session = None
        if PROXY_URL:
            proxy_auth = BasicAuth(PROXY_LOGIN, PROXY_PASSWORD)
            session = AiohttpSession(proxy=(PROXY_URL, proxy_auth))

        # Инициализация бота
        return Bot(
            token=TG_BOT_TOKEN,
            session=session,
            default=DefaultBotProperties(parse_mode='HTML')
        )
    except TypeError as e:
        traceback.print_exc()
        raise ProxyException(e)


@logger.catch
async def main():
    with open("pid.txt", "w+") as pid_file:
        pid_file.write(str(os.getpid()))

    # Reading authors from the csv
    with open("authors.csv", "r+") as file:
        for line in file.readlines():
            authors[line.split(",")[0]] = "t.me/" + line.split(",")[1].replace("\n", "")

    bot: Bot = None
    try:
        bot = create_bot()
        await run_loop(bot)
    except KeyboardInterrupt:
        logger.info("Script is stopped by the user.")
        exit()
    except ProxyException as e:
        logger.error(f"Proxy error: {e}")
        exit()
    finally:
        if bot:
            await bot.session.close()


asyncio.run(main())

import asyncio

from aiogram import Bot, types
import aiohttp
from aiogram.types import InputMediaVideo
from aiogram.utils import exceptions
from loguru import logger

from tools import split_text


async def get_file_size(url: str) -> int:
    async with aiohttp.ClientSession() as session:
        async with session.head(url) as response:
            return int(response.headers.get("Content-Length", 0))


async def send_post(bot: Bot, tg_channel: str, text: str, photos: list, videos: list, docs: list, num_tries: int = 0) -> None:
    num_tries += 1
    logger.info("Videos: " + str(videos))
    if num_tries > 3:
        logger.error("Post was not sent to Telegram. Too many tries.")
        return
    try:
        # Если нет фото, видео и документов — просто текст
        if len(photos) == 0 and len(videos) == 0:
            await send_text_post(bot, tg_channel, text)

        # Если есть одно фото
        elif len(photos) == 1 and len(videos) == 0:
            await send_photo_post(bot, tg_channel, text, photos)

        # Если есть несколько фото
        elif len(photos) >= 2 and len(videos) == 0:
            await send_photos_post(bot, tg_channel, text, photos)

        # Если есть видео (обработка списка videos)
        if videos:
            for video in videos:
                logger.info(f"Video size: {await get_file_size(video)}")
            if len(videos) == 1:  # Одно видео
                await bot.send_video(chat_id=tg_channel, video=videos[0], caption=text)
            elif len(videos) > 1:  # Несколько видео
                media = [InputMediaVideo(media=video) for video in videos]
                # Если текст есть, добавляем его к первому видео
                if text:
                    media[0].caption = text
                await bot.send_media_group(chat_id=tg_channel, media=media)
        if docs:
            await send_docs_post(bot, tg_channel, docs)
    except exceptions.RetryAfter as ex:
        logger.warning(f"Flood limit is exceeded. Sleep {ex.timeout} seconds. Try: {num_tries}")
        await asyncio.sleep(ex.timeout)
        await send_post(bot, tg_channel, text, photos, videos, docs, num_tries)
    except exceptions.BadRequest as ex:
        logger.warning(f"Bad request. Wait 60 seconds. Try: {num_tries}. {ex}")
        await asyncio.sleep(60)
        await send_post(bot, tg_channel, text, photos, videos, docs, num_tries)


async def send_text_post(bot: Bot, tg_channel: str, text: str) -> None:
    if not text:
        return

    if len(text) < 4096:
        await bot.send_message(tg_channel, text, parse_mode=types.ParseMode.HTML)
    else:
        text_parts = split_text(text, 4084)
        prepared_text_parts = (
            [text_parts[0] + " (...)"]
            + ["(...) " + part + " (...)" for part in text_parts[1:-1]]
            + ["(...) " + text_parts[-1]]
        )

        for part in prepared_text_parts:
            await bot.send_message(tg_channel, part, parse_mode=types.ParseMode.HTML)
            await asyncio.sleep(0.5)
    logger.info("Text post sent to Telegram.")


async def send_photo_post(bot: Bot, tg_channel: str, text: str, photos: list) -> None:
    if len(text) <= 1024:
        await bot.send_photo(tg_channel, photos[0], text, parse_mode=types.ParseMode.HTML)
        logger.info("Text post (<=1024) with photo sent to Telegram.")
    else:
        prepared_text = f'<a href="{photos[0]}"> </a>{text}'
        if len(prepared_text) <= 4096:
            await bot.send_message(tg_channel, prepared_text, parse_mode=types.ParseMode.HTML)
        else:
            await send_text_post(bot, tg_channel, text)
            await bot.send_photo(tg_channel, photos[0])
        logger.info("Text post (>1024) with photo sent to Telegram.")


async def send_photos_post(bot: Bot, tg_channel: str, text: str, photos: list) -> None:
    media = types.MediaGroup()
    for photo in photos:
        media.attach_photo(types.InputMediaPhoto(photo))

    if (len(text) > 0) and (len(text) <= 1024):
        media.media[0].caption = text
        media.media[0].parse_mode = types.ParseMode.HTML
    elif len(text) > 1024:
        await send_text_post(bot, tg_channel, text)
    await bot.send_media_group(tg_channel, media)
    logger.info("Text post with photos sent to Telegram.")


async def send_photos_and_videos(bot: Bot, tg_channel: str, text: str, photos: list, videos: list) -> None:
    if not photos and not videos:
        await send_text_post(bot, tg_channel, text)
        return

    media = types.MediaGroup()

    for photo in photos:
        media.attach_photo(types.InputMediaPhoto(photo))

    for video in videos:
        media.attach_video(types.InputMediaVideo(video))

    if len(photos) + len(videos) == 1:
        if len(text) <= 1024:
            if photos:
                await bot.send_photo(tg_channel, photos[0], text, parse_mode=types.ParseMode.HTML)
            else:
                await bot.send_video(tg_channel, videos[0], text, parse_mode=types.ParseMode.HTML)
        else:
            prepared_text = f'<a href="{photos[0] if photos else videos[0]}"> </a>{text}'
            if len(prepared_text) <= 4096:
                await bot.send_message(tg_channel, prepared_text, parse_mode=types.ParseMode.HTML)
            else:
                await send_text_post(bot, tg_channel, text)
                if photos:
                    await bot.send_photo(tg_channel, photos[0])
                else:
                    await bot.send_video(tg_channel, videos[0])
    else:
        if (len(text) > 0) and (len(text) <= 1024):
            media.media[0].caption = text
            media.media[0].parse_mode = types.ParseMode.HTML
        elif len(text) > 1024:
            await send_text_post(bot, tg_channel, text)

        await bot.send_media_group(tg_channel, media)

    logger.info("Text post with media sent to Telegram.")


async def send_docs_post(bot: Bot, tg_channel: str, docs: list) -> None:
    media = types.MediaGroup()
    for doc in docs:
        media.attach_document(types.InputMediaDocument(open(f"./temp/{doc['title']}", "rb")))
    await bot.send_media_group(tg_channel, media)
    logger.info("Documents sent to Telegram.")

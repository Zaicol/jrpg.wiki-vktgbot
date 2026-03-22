import asyncio
import re

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from aiogram.types import (InputMediaPhoto, InputMediaVideo, InputMediaDocument,
                           FSInputFile, LinkPreviewOptions, ReplyParameters)
from aiogram.enums import ParseMode
import aiohttp
from loguru import logger


async def get_file_size(url: str) -> int:
    async with aiohttp.ClientSession() as session:
        async with session.head(url) as response:
            return int(response.headers.get("Content-Length", 0))


async def send_post(bot: Bot, tg_channel: str, text: str,
                    photos: list, videos: list, docs: list, num_tries: int = 0) -> None:
    """Главная функция по отправке поста в телеграм"""
    num_tries += 1
    logger.info("Videos: " + str(videos))
    if num_tries > 3:
        logger.error("Post was not sent to Telegram. Too many tries.")
        return
    try:
        # Особый режим для постов-впечатлений об играх.
        # Эти посты всегда длиннее стандартного лимита на количество символов,
        # Поэтому админ группы вызвалась их постить сама, с тг премиум
        if text.lower().startswith("впечатлени"):
            # await send_impressions_post(bot, tg_channel, text, photos)
            pass

        # Если нет фото, видео и документов — просто текст
        elif len(photos) == 0 and len(videos) == 0:
            await send_text_post(bot, tg_channel, text)
        else:
            await send_media_post(bot, tg_channel, text, photos, videos)
        if docs:
            await send_docs_post(bot, tg_channel, docs)

        return

    except TelegramRetryAfter as ex:
        logger.warning(f"Flood limit is exceeded. Sleep {ex.retry_after} seconds. Try: {num_tries}")
        await asyncio.sleep(ex.retry_after)
        await send_post(bot, tg_channel, text, photos, videos, docs, num_tries)
    except TelegramBadRequest as ex:
        logger.warning(f"Bad request. Wait 60 seconds. Try: {num_tries}. {ex}")
        await asyncio.sleep(60)
        await send_post(bot, tg_channel, text, photos, videos, docs, num_tries)


async def send_text_post(bot: Bot, tg_channel: str, text: str) -> int:
    if not text:
        return 0

    link_preview_settings = LinkPreviewOptions(is_disabled=True)
    last_msg = None

    if len(text) <= 4096:
        last_msg = await bot.send_message(tg_channel, text, parse_mode=ParseMode.HTML,
                                          link_preview_options=link_preview_settings)
        logger.info(f"Text post with length {len(text)} sent to Telegram.")
    else:
        text_parts = await split_text_by_chunks(text)
        prepared_text_parts = (
                [text_parts[0] + " (...)"]
                + ["(...) " + part + " (...)" for part in text_parts[1:-1]]
                + ["(...) " + text_parts[-1]]
        )

        for part in prepared_text_parts:
            last_msg = await bot.send_message(tg_channel, part, parse_mode=ParseMode.HTML,
                                              link_preview_options=link_preview_settings)
            await asyncio.sleep(0.5)
        logger.info(f"Text post with length {len(text)} spilt into {len(prepared_text_parts)} chunks sent to Telegram.")

    return last_msg.message_id if last_msg else 0


async def split_text_by_chunks(text: str) -> list:
    """Разделение текста на чанки по словам и абзацам, чтобы не превышать лимит в 4096 символов."""
    return_text = []
    cursor_index = 0
    max_text_length = 4096 - len('(...) ') * 2
    while cursor_index + max_text_length < len(text):
        chunk = text[cursor_index:cursor_index + max_text_length]
        # Сначала пробуем делить по абзацу
        paragraph_index = chunk.rfind("\n\n")
        if paragraph_index != -1:
            return_text.append(chunk[: paragraph_index + 2])
            cursor_index += paragraph_index + 2
            continue

        # Если не получилось, то пробуем делить по слову
        space_index = chunk.rfind(" ")
        if space_index != -1:
            return_text.append(chunk[: space_index + 1])
            cursor_index += space_index + 1
        else:
            return_text.append(chunk)
            cursor_index += max_text_length
    return_text.append(text[cursor_index:])
    return return_text


async def send_impressions_post(bot: Bot, tg_channel: str, text: str, photos: list) -> None:
    # Текст делится на три части: начало, понравилось, не понравилось.
    logger.info("Recognized impressions post.")
    text = re.split("ЧТО ПОНРАВИЛОСЬ|ЧТО НЕ ПОНРАВИЛОСЬ", text)
    await send_media_post(bot, tg_channel, text[0], photos, [])
    await send_text_post(bot, tg_channel, "ЧТО ПОНРАВИЛОСЬ" + text[1])
    await send_text_post(bot, tg_channel, "ЧТО НЕ ПОНРАВИЛОСЬ" + text[2])


async def send_media_post(bot: Bot, tg_channel: str, text: str, photos: list, videos: list) -> None:
    """Функция отправки сообщения с медиа"""

    # Добавляем фото и видео в группу медиа
    media = []
    for photo in photos:
        media.append(InputMediaPhoto(media=photo))
    for video in videos:
        media.append(InputMediaVideo(media=video))

    if not media:
        return

    reply_id = None

    # Прикрепляем текст к первому элементу медиагруппы
    if text:
        caption = text if len(text) <= 1024 else None
        media[0].caption = caption
        media[0].parse_mode = ParseMode.HTML

        # Если текст слишком длинный для подписи, шлем его отдельным сообщением
        if len(text) > 1024:
            reply_id = await send_text_post(bot, tg_channel, text)

    reply_params = ReplyParameters(message_id=reply_id) if reply_id else None

    await bot.send_media_group(tg_channel, media=media, reply_parameters=reply_params)
    logger.info("Text post with media sent to Telegram.")


async def send_docs_post(bot: Bot, tg_channel: str, docs: list) -> None:
    """Отправка документов без текста"""
    media = []
    for doc in docs:
        file_path = f"./temp/{doc['title']}"
        media.append(InputMediaDocument(media=FSInputFile(file_path)))

    if media:
        await bot.send_media_group(tg_channel, media=media)
        logger.info("Documents sent.")

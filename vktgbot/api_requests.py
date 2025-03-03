import asyncio
from typing import Union

import re

import aiohttp
import requests
from loguru import logger


def get_data_from_vk(
    vk_token: str, req_version: float, vk_domain: str, req_filter: str, req_count: int, offset: int = 0
) -> Union[dict, None]:
    logger.info("Trying to get posts from VK.")

    match = re.search("^(club|public)(\d+)$", vk_domain)
    if match:
        source_param = {"owner_id": "-" + match.groups()[1]}
    else:
        source_param = {"domain": vk_domain}

    response = requests.get(
        "https://api.vk.com/method/wall.get",
        params=dict(
            {
                "access_token": vk_token,
                "v": req_version,
                "filter": req_filter,
                "count": req_count,
                "offset": offset,
            },
            **source_param,
        ),
    )
    data = response.json()
    if "response" in data:
        return data["response"]["items"]
    elif "error" in data:
        logger.error("Error was detected when requesting data from VK: " f"{data['error']['error_msg']}")
    return None


def get_video_url(vk_token: str, req_version: float, owner_id: str, video_id: str, access_key: str, videos_urls: list) -> str:
    response = requests.get(
        "https://api.vk.com/method/video.get",
        params={
            "access_token": vk_token,
            "v": req_version,
            "videos": f"{owner_id}_{video_id}{'' if not access_key else f'_{access_key}'}",
        },
    )

    def get_file_size(url: str) -> int:
        response = requests.head(url)
        return int(response.headers.get("Content-Length", 0))

    def get_best_quality_url(files):
        # Сортируем ключи по качеству (числовая часть после "mp4_")
        mp4_keys = [key for key in files if key.startswith("mp4_")]
        if not mp4_keys:
            return None

        # Сортируем
        mp4_keys.sort(key=lambda key: int(key.split("_")[1]), reverse=True)
        index = 0
        while index < len(mp4_keys) - 1 and get_file_size(files[mp4_keys[index]]) > 20000000:
            index += 1

        if get_file_size(files[mp4_keys[index]]) > 20000000:
            logger.info(f"The video was skipped due to its size exceeding the 20MB limit: {files[mp4_keys[index]]}")
            return None
        best_quality_key = mp4_keys[index]
        logger.info(f"Best quality key: {best_quality_key}")
        return files[best_quality_key]

    logger.info(f"{owner_id}_{video_id}{'' if not access_key else f'_{access_key}'}")
    data = response.json()
    if "response" in data and data["response"]["items"]:
        ext = get_best_quality_url(data["response"]["items"][0]["files"])
        logger.info(f"Files:")
        logger.info(data['response']['items'][0]['files'])
        if not ext:
            videos_urls.append(f"https://vk.com/video{owner_id}_{video_id}")
        return ext
    elif "error" in data:
        logger.error(f"Error was detected when requesting data from VK: {data['error']['error_msg']}")
    return ""


def get_group_name(vk_token: str, req_version: float, owner_id) -> str:
    response = requests.get(
        "https://api.vk.com/method/groups.getById",
        params={
            "access_token": vk_token,
            "v": req_version,
            "group_id": owner_id,
        },
    )
    data = response.json()
    if "response" in data:
        return data["response"][0]["name"]
    elif "error" in data:
        logger.error(f"Error was detected when requesting data from VK: {data['error']['error_msg']}")
    return ""

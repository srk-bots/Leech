import contextlib
from asyncio import gather
from inspect import iscoroutinefunction
from pathlib import Path

from aioaria2 import Aria2WebsocketClient
from aiohttp import ClientError
from aioqbt.client import create_client
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tghbot import LOGGER, aria2_options


def wrap_with_retry(obj, max_retries=3):
    for attr_name in dir(obj):
        if attr_name.startswith("_"):
            continue

        attr = getattr(obj, attr_name)
        if iscoroutinefunction(attr):
            retry_policy = retry(
                stop=stop_after_attempt(max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=5),
                retry=retry_if_exception_type(
                    (ClientError, TimeoutError, RuntimeError),
                ),
            )
            wrapped = retry_policy(attr)
            setattr(obj, attr_name, wrapped)
    return obj


class TorrentManager:
    aria2 = None
    qbittorrent = None

    @classmethod
    async def initiate(cls):
        cls.aria2 = await Aria2WebsocketClient.new("http://localhost:6800/jsonrpc")
        try:
            cls.qbittorrent = await create_client("http://localhost:8090/api/v2/")
            cls.qbittorrent = wrap_with_retry(cls.qbittorrent)
        except Exception as e:
            LOGGER.warning(f"Failed to connect to qBittorrent: {e}")
            LOGGER.warning("qBittorrent functionality will be limited")
            cls.qbittorrent = None

    @classmethod
    async def close_all(cls):
        tasks = [cls.aria2.close()]
        if cls.qbittorrent is not None:
            tasks.append(cls.qbittorrent.close())
        await gather(*tasks)

    @classmethod
    async def aria2_remove(cls, download):
        if download.get("status", "") in ["active", "paused", "waiting"]:
            await cls.aria2.forceRemove(download.get("gid", ""))
        else:
            with contextlib.suppress(Exception):
                await cls.aria2.removeDownloadResult(download.get("gid", ""))

    @classmethod
    async def remove_all(cls):
        await cls.pause_all()
        tasks = [cls.aria2.purgeDownloadResult()]
        if cls.qbittorrent is not None:
            tasks.append(cls.qbittorrent.torrents.delete("all", True))
        await gather(*tasks)
        downloads = []
        results = await gather(
            cls.aria2.tellActive(),
            cls.aria2.tellWaiting(0, 1000),
        )
        for res in results:
            downloads.extend(res)
        tasks = []
        tasks.extend(
            cls.aria2.forceRemove(download.get("gid")) for download in downloads
        )
        with contextlib.suppress(Exception):
            await gather(*tasks)

    @classmethod
    async def overall_speed(cls):
        if cls.qbittorrent is not None:
            s1, s2 = await gather(
                cls.qbittorrent.transfer.info(),
                cls.aria2.getGlobalStat(),
            )
            download_speed = s1.dl_info_speed + int(s2.get("downloadSpeed", "0"))
            upload_speed = s1.up_info_speed + int(s2.get("uploadSpeed", "0"))
            return download_speed, upload_speed
        else:
            s2 = await cls.aria2.getGlobalStat()
            download_speed = int(s2.get("downloadSpeed", "0"))
            upload_speed = int(s2.get("uploadSpeed", "0"))
            return download_speed, upload_speed

    @classmethod
    async def pause_all(cls):
        tasks = [cls.aria2.forcePauseAll()]
        if cls.qbittorrent is not None:
            tasks.append(cls.qbittorrent.torrents.stop("all"))
        await gather(*tasks)

    @classmethod
    async def change_aria2_option(cls, key, value):
        downloads = []
        results = await gather(
            cls.aria2.tellActive(),
            cls.aria2.tellWaiting(0, 1000),
        )
        for res in results:
            downloads.extend(res)
            tasks = []
        for download in downloads:
            if download.get("status", "") != "complete":
                tasks.append(
                    cls.aria2.changeOption(download.get("gid"), {key: value}),
                )
        if tasks:
            try:
                await gather(*tasks)
            except Exception as e:
                LOGGER.error(e)
        if key not in ["checksum", "index-out", "out", "pause", "select-file"]:
            await cls.aria2.changeGlobalOption({key: value})
            aria2_options[key] = value


def aria2_name(download_info):
    if "bittorrent" in download_info and download_info["bittorrent"].get("info"):
        return download_info["bittorrent"]["info"]["name"]
    if download_info.get("files"):
        if download_info["files"][0]["path"].startswith("[METADATA]"):
            return download_info["files"][0]["path"]
        file_path = download_info["files"][0]["path"]
        dir_path = download_info["dir"]
        if file_path.startswith(dir_path):
            return Path(file_path[len(dir_path) + 1 :]).parts[0]
        return ""
    return ""


def is_metadata(download_info):
    return any(
        f["path"].startswith("[METADATA]") for f in download_info.get("files", [])
    )

from asyncio import create_task
from os import getcwd
from os import path as ospath
from re import search as re_search
from shlex import split as ssplit
from time import time
import json

import aiohttp
from aiofiles import open as aiopen
from aiofiles.os import mkdir
from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove

from bot import LOGGER
from bot.core.aeon_client import TgClient
from bot.helper.aeon_utils.access_check import token_check
from bot.helper.ext_utils.bot_utils import cmd_exec
from bot.helper.ext_utils.links_utils import is_url
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    delete_message,
    edit_message,
    send_message,
)

def parse_ffprobe_info(json_data, file_size, filename):
    tc = f"<h4>{filename}</h4><br><br>"
    tc += "<blockquote>General</blockquote><pre>"

    format_info = json_data.get("format", {})
    tc += f"{'File name':<28}: {filename}\n"
    tc += f"{'File size':<28}: {file_size / (1024 * 1024):.2f} MiB\n"

    for key in ["duration", "bit_rate", "format_name", "format_long_name"]:
        if key in format_info:
            tc += f"{key.replace('_', ' ').capitalize():<28}: {format_info[key]}\n"

    tags = format_info.get("tags", {})
    for k, v in tags.items():
        tc += f"{k.replace('_', ' ').capitalize():<28}: {v}\n"
    tc += "</pre><br>"

    for stream in json_data.get("streams", []):
        codec_type = stream.get("codec_type", "Unknown").capitalize()
        if codec_type in {"Video", "Audio", "Subtitle"}:
            tc += f"<blockquote>{codec_type}</blockquote><pre>"
            for k, v in stream.items():
                if isinstance(v, (str, int, float)):
                    tc += f"{k.replace('_', ' ').capitalize():<28}: {v}\n"
            for k, v in stream.get("tags", {}).items():
                tc += f"{k.replace('_', ' ').capitalize():<28}: {v}\n"
            tc += "</pre><br>"
    return tc

async def gen_mediainfo(message, link=None, media=None, reply=None):
    temp_send = await send_message(message, "Generating MediaInfo with ffprobe...")
    des_path = None
    tc = ""

    try:
        path = "Mediainfo/"
        if not await aiopath.isdir(path):
            await mkdir(path)

        file_size = 0
        if link:
            if not is_url(link):
                raise ValueError(f"Invalid URL: {link}")

            filename_match = re_search(".+/(.+)", link)
            filename = filename_match.group(1) if filename_match else f"mediainfo_{int(time())}"

            des_path = ospath.join(path, filename)
            headers = {
                "user-agent": "Mozilla/5.0 (Linux; Android 12; 2201116PI) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36",
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(link, headers=headers) as response:
                    file_size = int(response.headers.get("Content-Length", 0))
                    async with aiopen(des_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(10000000):
                            await f.write(chunk)
                            break
        elif media:
            des_path = ospath.join(path, media.file_name)
            file_size = media.file_size
            if file_size <= 30000000:
                await reply.download(ospath.join(getcwd(), des_path))
            else:
                async for chunk in TgClient.bot.stream_media(media, limit=3):
                    async with aiopen(des_path, "ab") as f:
                        await f.write(chunk)

        cmd = f'ffprobe -v quiet -print_format json -show_format -show_streams -show_chapters -show_programs -show_entries format_tags:stream_tags "{des_path}"'
        stdout, _, _ = await cmd_exec(ssplit(cmd))

        if stdout:
            data = json.loads(stdout)
            tc = parse_ffprobe_info(data, file_size, ospath.basename(des_path))

    except Exception as e:
        LOGGER.error(e)
        await edit_message(temp_send, f"MediaInfo failed: {e}")
    finally:
        if des_path:
            await aioremove(des_path)

    if tc:
        link_id = (await telegraph.create_page(title="MediaInfo", content=tc))["path"]
        tag = message.from_user.mention
        await temp_send.edit(
            f"<blockquote>{tag}, MediaInfo generated with ffprobe <a href='https://graph.org/{link_id}'>here</a>.</blockquote>",
            disable_web_page_preview=False,
        )
    else:
        await temp_send.edit("Failed to generate MediaInfo.")

async def mediainfo(_, message):
    user_id = message.from_user.id
    buttons = ButtonMaker()
    if message.chat.type != message.chat.type.PRIVATE:
        msg, buttons = await token_check(user_id, buttons)
        if msg is not None:
            reply_message = await send_message(message, msg, buttons.build_menu(1))
            await delete_links(message)
            create_task(auto_delete_message(reply_message, time=300))
            return

    reply = message.reply_to_message
    help_msg = (
        "<b>By replying to media:</b>"
        f"\n<code>/{BotCommands.MediaInfoCommand[0]} media </code> or <code>/{BotCommands.MediaInfoCommand[1]} media </code>"
        "\n\n<b>By reply/sending download link:</b>"
        f"\n<code>/{BotCommands.MediaInfoCommand[0]} link </code> or <code>/{BotCommands.MediaInfoCommand[1]} link </code>"
    )

    if len(message.command) > 1 or (reply and reply.text):
        await delete_links(message)
        link = reply.text if reply else message.command[1]
        await gen_mediainfo(message, link)
    elif reply:
        await delete_links(message)
        file = next(
            (
                i
                for i in [
                    reply.document,
                    reply.video,
                    reply.audio,
                    reply.animation,
                    reply.voice,
                    reply.video_note,
                ]
                if i
            ),
            None,
        )
        if file:
            await gen_mediainfo(message, None, file, reply)
        else:
            help_message = await send_message(message, help_msg)
            create_task(auto_delete_message(help_message, time=300))
    else:
        await delete_message(message)
        help_message = await send_message(message, help_msg)
        create_task(auto_delete_message(help_message, time=300))
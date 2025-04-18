from asyncio import (
    create_subprocess_exec,
    create_subprocess_shell,
    create_task,
    gather,
    sleep,
)
from functools import partial
from io import BytesIO
from os import getcwd
from time import time

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import remove, rename
from aioshutil import rmtree
from pyrogram.filters import create
from pyrogram.handlers import MessageHandler

from bot import (
    LOGGER,
    aria2_options,
    auth_chats,
    drives_ids,
    drives_names,
    excluded_extensions,
    index_urls,
    intervals,
    jd_listener_lock,
    nzb_options,
    qbit_options,
    sabnzbd_client,
    sudo_users,
    task_dict,
)
from bot.core.aeon_client import TgClient
from bot.core.config_manager import Config
from bot.core.jdownloader_booter import jdownloader
from bot.core.startup import (
    update_aria2_options,
    update_nzb_options,
    update_qb_options,
    update_variables,
)
from bot.core.torrent_manager import TorrentManager
from bot.helper.ext_utils.bot_utils import SetInterval, new_task
from bot.helper.ext_utils.db_handler import database
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.mirror_leech_utils.rclone_utils.serve import rclone_serve_booter
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_message,
    edit_message,
    send_file,
    send_message,
    update_status_message,
)

from .rss import add_job

start = 0
state = "view"
merge_page = 0  # Track current page for merge menu
handler_dict = {}
DEFAULT_VALUES = {
    "LEECH_SPLIT_SIZE": TgClient.MAX_SPLIT_SIZE,
    "RSS_DELAY": 600,
    "UPSTREAM_BRANCH": "main",
    "DEFAULT_UPLOAD": "rc",
    "FFMPEG_MEMORY_LIMIT": 2048,
    "FFMPEG_CPU_AFFINITY": "",
    "FFMPEG_DYNAMIC_THREADS": True,
    "AUTO_RESTART_ENABLED": False,
    "AUTO_RESTART_INTERVAL": 24,
}


async def get_buttons(key=None, edit_type=None, page=0, user_id=None):
    buttons = ButtonMaker()
    msg = ""  # Initialize msg with a default value
    if key is None:
        buttons.data_button("Config", "botset var")
        buttons.data_button("Pvt Files", "botset private")
        buttons.data_button("Media Tools", "botset mediatools")
        buttons.data_button("Qbit Settings", "botset qbit")
        buttons.data_button("Aria2c Settings", "botset aria")
        buttons.data_button("Sabnzbd", "botset nzb")
        buttons.data_button("JD Sync", "botset syncjd")
        buttons.data_button("Close", "botset close")
        msg = "Bot Settings:"
    elif edit_type is not None:
        if edit_type == "editvar" and (
            key.startswith(("WATERMARK_", "MERGE_", "METADATA_"))
            or key in ["CONCAT_DEMUXER_ENABLED", "FILTER_COMPLEX_ENABLED"]
        ):
            msg = ""
            if key.startswith("WATERMARK_"):
                buttons.data_button("Back", "botset mediatools_watermark")
            elif key.startswith("METADATA_"):
                buttons.data_button("Back", "botset mediatools_metadata")
            elif key.startswith("MERGE_") and "MERGE_OUTPUT_FORMAT" in key:
                # If it's a format setting, it's likely from the merge_config menu
                buttons.data_button("Back", "botset mediatools_merge_config")
            else:
                buttons.data_button("Back", "botset mediatools_merge")
            buttons.data_button("Close", "botset close")

            # Get help text for settings
            if key in {
                "WATERMARK_ENABLED",
                "MERGE_ENABLED",
                "CONCAT_DEMUXER_ENABLED",
                "FILTER_COMPLEX_ENABLED",
                "MERGE_THREADING",
                "MERGE_REMOVE_ORIGINAL",
                "MERGE_VIDEO_FASTSTART",
            }:
                help_text = (
                    "Send 'true' to enable or 'false' to disable this feature."
                )
            elif key == "WATERMARK_KEY":
                help_text = "Send your text which will be added as watermark in all mkv videos."
            elif key == "WATERMARK_POSITION":
                help_text = "Send watermark position. Valid options: top_left, top_right, bottom_left, bottom_right, center."
            elif key in {
                "WATERMARK_SIZE",
                "WATERMARK_THREAD_NUMBER",
                "MERGE_THREAD_NUMBER",
                "MERGE_PRIORITY",
                "MERGE_VIDEO_CRF",
                "MERGE_IMAGE_COLUMNS",
                "MERGE_IMAGE_QUALITY",
                "MERGE_IMAGE_DPI",
                "MERGE_SUBTITLE_FONT_SIZE",
                "MERGE_DOCUMENT_MARGIN",
                "MERGE_AUDIO_CHANNELS",
            }:
                help_text = "Send an integer value. Example: 4."
            elif key in {
                "WATERMARK_COLOR",
                "MERGE_VIDEO_PIXEL_FORMAT",
                "MERGE_VIDEO_TUNE",
                "MERGE_IMAGE_BACKGROUND",
                "MERGE_SUBTITLE_FONT_COLOR",
                "MERGE_SUBTITLE_BACKGROUND",
            }:
                help_text = "Send a color name. Example: white, black, red, green, blue, yellow."
            elif key in {"WATERMARK_FONT", "MERGE_SUBTITLE_FONT"}:
                help_text = "Send font file name. The font file should be available in the bot's directory. Example: Arial.ttf."
            elif key == "MERGE_OUTPUT_FORMAT_VIDEO":
                help_text = "Send video output format. Example: mp4, mkv, avi, etc."
            elif key == "MERGE_OUTPUT_FORMAT_AUDIO":
                help_text = "Send audio output format. Example: mp3, aac, flac, etc."
            elif key == "MERGE_OUTPUT_FORMAT_IMAGE":
                help_text = "Send image output format. Example: jpg, png, webp, etc."
            elif key == "MERGE_OUTPUT_FORMAT_DOCUMENT":
                help_text = "Send document output format. Example: pdf, docx, etc."
            elif key == "MERGE_OUTPUT_FORMAT_SUBTITLE":
                help_text = "Send subtitle output format. Example: srt, ass, etc."
            elif key == "MERGE_VIDEO_CODEC":
                help_text = "Send video codec. Example: h264, h265, copy, etc."
            elif key == "MERGE_VIDEO_QUALITY":
                help_text = "Send video quality. Example: high, medium, low, etc."
            elif key == "MERGE_VIDEO_PRESET":
                help_text = "Send video preset. Example: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow, etc."
            elif key == "MERGE_AUDIO_CODEC":
                help_text = "Send audio codec. Example: aac, mp3, copy, etc."
            elif key == "MERGE_AUDIO_BITRATE":
                help_text = "Send audio bitrate. Example: 128k, 192k, 320k, etc."
            elif key == "MERGE_AUDIO_SAMPLING":
                help_text = "Send audio sampling rate. Example: 44100, 48000, etc."
            elif key == "MERGE_AUDIO_VOLUME":
                help_text = (
                    "Send audio volume multiplier. Example: 1.0, 1.5, 0.5, etc."
                )
            elif key == "MERGE_IMAGE_MODE":
                help_text = "Send image mode. Example: auto, grid, horizontal, vertical, etc."
            elif key == "MERGE_IMAGE_RESIZE":
                help_text = (
                    "Send image resize option. Example: none, 1080p, 720p, etc."
                )
            elif key == "MERGE_SUBTITLE_ENCODING":
                help_text = "Send subtitle encoding. Example: utf-8, ascii, etc."
            elif key == "MERGE_DOCUMENT_PAPER_SIZE":
                help_text = "Send document paper size. Example: a4, letter, etc."
            elif key == "MERGE_DOCUMENT_ORIENTATION":
                help_text = (
                    "Send document orientation. Example: portrait, landscape, etc."
                )
            elif key in {
                "MERGE_METADATA_TITLE",
                "MERGE_METADATA_AUTHOR",
                "MERGE_METADATA_COMMENT",
                "METADATA_TITLE",
                "METADATA_AUTHOR",
                "METADATA_COMMENT",
            }:
                help_text = "Send metadata text. Example: My Video, John Doe, etc."
            elif key == "METADATA_KEY":
                help_text = "Send legacy metadata key for backward compatibility."
            elif key == "METADATA_ALL":
                help_text = "Send metadata text to apply to all metadata fields."
            else:
                help_text = f"Send a valid value for {key}."

            msg += f"{help_text}\n\nCurrent value is '{Config.get(key)}'. Timeout: 60 sec"
        elif edit_type == "botvar":
            msg = ""
            buttons.data_button("Back", "botset var")
            if key not in ["TELEGRAM_HASH", "TELEGRAM_API", "OWNER_ID", "BOT_TOKEN"]:
                buttons.data_button("Default", f"botset resetvar {key}")
            buttons.data_button("Close", "botset close")
            if key in [
                "CMD_SUFFIX",
                "OWNER_ID",
                "USER_SESSION_STRING",
                "TELEGRAM_HASH",
                "TELEGRAM_API",
                "BOT_TOKEN",
                "TG_PROXY",
            ]:
                msg += "Restart required for this edit to take effect! You will not see the changes in bot vars, the edit will be in database only!\n\n"

            # Add help text for resource management settings
            if key == "FFMPEG_MEMORY_LIMIT":
                msg += "Set the memory limit for FFmpeg and PIL operations in MB. Use 0 for no limit.\n\n"
                msg += "Example: 2048 (for 2GB limit)\n\n"
            elif key == "FFMPEG_CPU_AFFINITY":
                msg += "Set CPU cores to use for FFmpeg operations. Use comma-separated list of core numbers (0-based).\n\n"
                msg += "Example: 0,1,2,3 (to use first 4 cores)\n\n"
                msg += "Leave empty to use all cores.\n\n"
            elif key == "FFMPEG_DYNAMIC_THREADS":
                msg += "Enable or disable dynamic thread allocation based on system load.\n\n"
                msg += "Send 'true' to enable or 'false' to disable.\n\n"
            elif key == "AUTO_RESTART_ENABLED":
                msg += "Enable or disable automatic bot restart at specified intervals.\n\n"
                msg += "Send 'true' to enable or 'false' to disable.\n\n"
                msg += "Note: Changes will take effect after saving.\n\n"
            elif key == "AUTO_RESTART_INTERVAL":
                msg += (
                    "Set the interval in hours between automatic bot restarts.\n\n"
                )
                msg += "Example: 24 (for daily restart)\n\n"
                msg += "Minimum value is 1 hour.\n\n"

            msg += f"Send a valid value for {key}. Current value is '{Config.get(key)}'. Timeout: 60 sec"
        elif edit_type == "ariavar":
            buttons.data_button("Back", "botset aria")
            if key != "newkey":
                buttons.data_button("Empty String", f"botset emptyaria {key}")
            buttons.data_button("Close", "botset close")
            msg = (
                "Send a key with value. Example: https-proxy-user:value. Timeout: 60 sec"
                if key == "newkey"
                else f"Send a valid value for {key}. Current value is '{aria2_options[key]}'. Timeout: 60 sec"
            )
        elif edit_type == "qbitvar":
            buttons.data_button("Back", "botset qbit")
            buttons.data_button("Empty", f"botset emptyqbit {key}")
            buttons.data_button("Close", "botset close")
            msg = f"Send a valid value for {key}. Current value is '{qbit_options[key]}'. Timeout: 60 sec"
        elif edit_type == "nzbvar":
            buttons.data_button("Back", "botset nzb")
            buttons.data_button("Default", f"botset resetnzb {key}")
            buttons.data_button("Empty String", f"botset emptynzb {key}")
            buttons.data_button("Close", "botset close")
            msg = f"Send a valid value for {key}. Current value is '{nzb_options[key]}'.\nIf the value is list then seperate them by space or ,\nExample: .exe,info or .exe .info\nTimeout: 60 sec"
        elif edit_type.startswith("nzbsevar"):
            index = 0 if key == "newser" else int(edit_type.replace("nzbsevar", ""))
            buttons.data_button("Back", f"botset nzbser{index}")
            if key != "newser":
                buttons.data_button("Empty", f"botset emptyserkey {index} {key}")
            buttons.data_button("Close", "botset close")
            if key == "newser":
                msg = "Send one server as dictionary {}, like in config.py without []. Timeout: 60 sec"
            else:
                msg = f"Send a valid value for {key} in server {Config.USENET_SERVERS[index]['name']}. Current value is {Config.USENET_SERVERS[index][key]}. Timeout: 60 sec"
    elif key == "var":
        conf_dict = Config.get_all()
        # Filter out watermark, merge configs, and metadata settings
        filtered_keys = [
            k
            for k in list(conf_dict.keys())
            if not (
                k.startswith(("WATERMARK_", "MERGE_", "METADATA_"))
                or k in ["CONCAT_DEMUXER_ENABLED", "FILTER_COMPLEX_ENABLED"]
            )
        ]

        # Add resource management settings to the config menu
        resource_keys = [
            "FFMPEG_MEMORY_LIMIT",
            "FFMPEG_CPU_AFFINITY",
            "FFMPEG_DYNAMIC_THREADS",
            "AUTO_RESTART_ENABLED",
            "AUTO_RESTART_INTERVAL",
        ]

        # Ensure resource keys are in the filtered keys list
        for rk in resource_keys:
            if rk not in filtered_keys:
                filtered_keys.append(rk)

        # Sort the keys alphabetically
        filtered_keys.sort()

        for k in filtered_keys[start : 10 + start]:
            if k == "DATABASE_URL" and state != "view":
                continue
            # Highlight resource management settings
            if k in resource_keys:
                buttons.data_button(f"⚙️ {k}", f"botset botvar {k}")
            else:
                buttons.data_button(k, f"botset botvar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit var")
        else:
            buttons.data_button("View", "botset view var")
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close")
        for x in range(0, len(filtered_keys), 10):
            buttons.data_button(
                f"{int(x / 10)}",
                f"botset start var {x}",
                position="footer",
            )

        msg = f"Config Variables | Page: {int(start / 10)} | State: {state}"
    elif key == "private":
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close")
        msg = """Send private file: config.py, token.pickle, rclone.conf, accounts.zip, list_drives.txt, cookies.txt, .netrc or any other private file!
To delete private file send only the file name as text message.
Note: Changing .netrc will not take effect for aria2c until restart.
Timeout: 60 sec"""
    elif key == "aria":
        for k in list(aria2_options.keys())[start : 10 + start]:
            buttons.data_button(k, f"botset ariavar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit aria")
        else:
            buttons.data_button("View", "botset view aria")
        buttons.data_button("Add Option", "botset ariavar newkey")
        buttons.data_button("Sync Aria2c", "botset syncaria")
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close")
        for x in range(0, len(aria2_options), 10):
            buttons.data_button(
                f"{int(x / 10)}",
                f"botset start aria {x}",
                position="footer",
            )
        msg = f"Aria2c Options | Page: {int(start / 10)} | State: {state}"
    elif key == "qbit":
        for k in list(qbit_options.keys())[start : 10 + start]:
            buttons.data_button(k, f"botset qbitvar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit qbit")
        else:
            buttons.data_button("View", "botset view qbit")
        buttons.data_button("Sync Qbittorrent", "botset syncqbit")
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close")
        for x in range(0, len(qbit_options), 10):
            buttons.data_button(
                f"{int(x / 10)}",
                f"botset start qbit {x}",
                position="footer",
            )
        msg = f"Qbittorrent Options | Page: {int(start / 10)} | State: {state}"
    elif key == "nzb":
        for k in list(nzb_options.keys())[start : 10 + start]:
            buttons.data_button(k, f"botset nzbvar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit nzb")
        else:
            buttons.data_button("View", "botset view nzb")
        buttons.data_button("Servers", "botset nzbserver")
        buttons.data_button("Sync Sabnzbd", "botset syncnzb")
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close")
        for x in range(0, len(nzb_options), 10):
            buttons.data_button(
                f"{int(x / 10)}",
                f"botset start nzb {x}",
                position="footer",
            )
        msg = f"Sabnzbd Options | Page: {int(start / 10)} | State: {state}"

    elif key == "nzbserver":
        if len(Config.USENET_SERVERS) > 0:
            for index, k in enumerate(Config.USENET_SERVERS[start : 10 + start]):
                buttons.data_button(k["name"], f"botset nzbser{index}")
        buttons.data_button("Add New", "botset nzbsevar newser")
        buttons.data_button("Back", "botset nzb")
        buttons.data_button("Close", "botset close")
        if len(Config.USENET_SERVERS) > 10:
            for x in range(0, len(Config.USENET_SERVERS), 10):
                buttons.data_button(
                    f"{int(x / 10)}",
                    f"botset start nzbser {x}",
                    position="footer",
                )
        msg = f"Usenet Servers | Page: {int(start / 10)} | State: {state}"
    elif key.startswith("nzbser"):
        index = int(key.replace("nzbser", ""))
        for k in list(Config.USENET_SERVERS[index].keys())[start : 10 + start]:
            buttons.data_button(k, f"botset nzbsevar{index} {k}")
        if state == "view":
            buttons.data_button("Edit", f"botset edit {key}")
        else:
            buttons.data_button("View", f"botset view {key}")
        buttons.data_button("Remove Server", f"botset remser {index}")
        buttons.data_button("Back", "botset nzbserver")
        buttons.data_button("Close", "botset close")
        if len(Config.USENET_SERVERS[index].keys()) > 10:
            for x in range(0, len(Config.USENET_SERVERS[index]), 10):
                buttons.data_button(
                    f"{int(x / 10)}",
                    f"botset start {key} {x}",
                    position="footer",
                )
        msg = f"Server Keys | Page: {int(start / 10)} | State: {state}"
    elif key == "mediatools":
        buttons.data_button("Watermark Settings", "botset mediatools_watermark")
        buttons.data_button("Merge Settings", "botset mediatools_merge")
        buttons.data_button("Metadata Settings", "botset mediatools_metadata")
        buttons.data_button("Back", "botset back", "footer")
        buttons.data_button("Close", "botset close", "footer")
        msg = "<b>Media Tools Settings</b>\n\nConfigure global settings for media tools."
    elif key == "mediatools_watermark":
        # Add buttons for each watermark setting in a 2-column layout
        watermark_settings = [
            "WATERMARK_ENABLED",
            "WATERMARK_KEY",
            "WATERMARK_POSITION",
            "WATERMARK_SIZE",
            "WATERMARK_COLOR",
            "WATERMARK_FONT",
            "WATERMARK_PRIORITY",
            "WATERMARK_THREADING",
            "WATERMARK_THREAD_NUMBER",
        ]
        for setting in watermark_settings:
            display_name = (
                setting.replace("WATERMARK_", "").replace("_", " ").title()
            )
            buttons.data_button(display_name, f"botset editvar {setting}")

        if state == "view":
            buttons.data_button("Edit", "botset edit mediatools_watermark")
        else:
            buttons.data_button("View", "botset view mediatools_watermark")

        buttons.data_button("Default", "botset default_watermark")

        buttons.data_button("Back", "botset mediatools", "footer")
        buttons.data_button("Close", "botset close", "footer")

        # Get current watermark settings
        watermark_enabled = (
            "✅ Enabled" if Config.WATERMARK_ENABLED else "❌ Disabled"
        )
        watermark_text = Config.WATERMARK_KEY or "None"
        watermark_position = Config.WATERMARK_POSITION or "top_left (Default)"
        watermark_size = Config.WATERMARK_SIZE or "20 (Default)"
        watermark_color = Config.WATERMARK_COLOR or "white (Default)"
        watermark_font = Config.WATERMARK_FONT or "default.otf (Default)"
        watermark_priority = Config.WATERMARK_PRIORITY or "2 (Default)"
        watermark_threading = (
            "✅ Enabled" if Config.WATERMARK_THREADING else "❌ Disabled"
        )
        watermark_thread_number = Config.WATERMARK_THREAD_NUMBER or "4 (Default)"

        msg = f"""<b>Watermark Settings</b> | State: {state}

<b>Status:</b> {watermark_enabled}
<b>Text:</b> <code>{watermark_text}</code>
<b>Position:</b> <code>{watermark_position}</code>
<b>Size:</b> <code>{watermark_size}</code>
<b>Color:</b> <code>{watermark_color}</code>
<b>Font:</b> <code>{watermark_font}</code>
<b>Priority:</b> <code>{watermark_priority}</code>
<b>Threading:</b> {watermark_threading}
<b>Thread Number:</b> <code>{watermark_thread_number}</code>

Configure global watermark settings that will be used when user settings are not available."""

    elif key == "mediatools_merge":
        # Get all merge settings and organize them by category
        general_settings = [
            "MERGE_ENABLED",
            "CONCAT_DEMUXER_ENABLED",
            "FILTER_COMPLEX_ENABLED",
            "MERGE_PRIORITY",
            "MERGE_THREADING",
            "MERGE_THREAD_NUMBER",
            "MERGE_REMOVE_ORIGINAL",
        ]

        # Output formats
        formats = [
            "MERGE_OUTPUT_FORMAT_VIDEO",
            "MERGE_OUTPUT_FORMAT_AUDIO",
            "MERGE_OUTPUT_FORMAT_IMAGE",
            "MERGE_OUTPUT_FORMAT_DOCUMENT",
            "MERGE_OUTPUT_FORMAT_SUBTITLE",
        ]

        # Video settings
        video_settings = [
            "MERGE_VIDEO_CODEC",
            "MERGE_VIDEO_QUALITY",
            "MERGE_VIDEO_PRESET",
            "MERGE_VIDEO_CRF",
            "MERGE_VIDEO_PIXEL_FORMAT",
            "MERGE_VIDEO_TUNE",
            "MERGE_VIDEO_FASTSTART",
        ]

        # Audio settings
        audio_settings = [
            "MERGE_AUDIO_CODEC",
            "MERGE_AUDIO_BITRATE",
            "MERGE_AUDIO_CHANNELS",
            "MERGE_AUDIO_SAMPLING",
            "MERGE_AUDIO_VOLUME",
        ]

        # Image settings
        image_settings = [
            "MERGE_IMAGE_MODE",
            "MERGE_IMAGE_COLUMNS",
            "MERGE_IMAGE_QUALITY",
            "MERGE_IMAGE_DPI",
            "MERGE_IMAGE_RESIZE",
            "MERGE_IMAGE_BACKGROUND",
        ]

        # Subtitle settings
        subtitle_settings = [
            "MERGE_SUBTITLE_ENCODING",
            "MERGE_SUBTITLE_FONT",
            "MERGE_SUBTITLE_FONT_SIZE",
            "MERGE_SUBTITLE_FONT_COLOR",
            "MERGE_SUBTITLE_BACKGROUND",
        ]

        # Document settings
        document_settings = [
            "MERGE_DOCUMENT_PAPER_SIZE",
            "MERGE_DOCUMENT_ORIENTATION",
            "MERGE_DOCUMENT_MARGIN",
        ]

        # Metadata settings
        metadata_settings = [
            "MERGE_METADATA_TITLE",
            "MERGE_METADATA_AUTHOR",
            "MERGE_METADATA_COMMENT",
        ]

        # Combine all settings in a logical order
        merge_settings = (
            general_settings
            + formats
            + video_settings
            + audio_settings
            + image_settings
            + subtitle_settings
            + document_settings
            + metadata_settings
        )

        # 5 rows per page, 2 columns = 10 items per page
        items_per_page = 10  # 5 rows * 2 columns
        total_pages = (len(merge_settings) + items_per_page - 1) // items_per_page

        # Ensure page is valid
        # Use the global merge_page variable if page is not provided
        if page == 0 and globals()["merge_page"] != 0:
            current_page = globals()["merge_page"]
        else:
            current_page = page
            # Update the global merge_page variable
            globals()["merge_page"] = current_page

        # Validate page number
        if current_page >= total_pages:
            current_page = 0
            globals()["merge_page"] = 0
        elif current_page < 0:
            current_page = total_pages - 1
            globals()["merge_page"] = total_pages - 1

        LOGGER.debug(
            f"Using merge_page: {current_page} (global: {globals()['merge_page']})"
        )

        # Get settings for current page
        start_idx = current_page * items_per_page
        end_idx = min(start_idx + items_per_page, len(merge_settings))
        current_page_settings = merge_settings[start_idx:end_idx]

        # Add buttons for each setting on current page
        for setting in current_page_settings:
            display_name = setting.replace("MERGE_", "").replace("_", " ").title()
            if setting.startswith(("CONCAT", "FILTER")):
                display_name = setting.replace("_ENABLED", "").title()
            buttons.data_button(display_name, f"botset editvar {setting}")

        # Add action buttons in a separate row
        # Add Edit/View button
        if state == "view":
            buttons.data_button("Edit", "botset edit mediatools_merge", "footer")
        else:
            buttons.data_button("View", "botset view mediatools_merge", "footer")

        # Add Default button
        buttons.data_button("Default", "botset default_merge", "footer")

        # Add navigation buttons
        buttons.data_button("Back", "botset mediatools", "footer")
        buttons.data_button("Close", "botset close", "footer")

        # Add pagination buttons in a separate row below action buttons
        if total_pages > 1:
            for i in range(total_pages):
                # Make the current page button different
                if i == current_page:
                    buttons.data_button(
                        f"[{i + 1}]", f"botset start_merge {i}", "page"
                    )
                else:
                    buttons.data_button(
                        str(i + 1), f"botset start_merge {i}", "page"
                    )

            # Add a debug log message
            LOGGER.debug(
                f"Added pagination buttons for merge menu. Total pages: {total_pages}, Current page: {current_page}"
            )

        # Get current merge settings
        merge_enabled = "✅ Enabled" if Config.MERGE_ENABLED else "❌ Disabled"
        concat_demuxer = (
            "✅ Enabled" if Config.CONCAT_DEMUXER_ENABLED else "❌ Disabled"
        )
        filter_complex = (
            "✅ Enabled" if Config.FILTER_COMPLEX_ENABLED else "❌ Disabled"
        )
        video_format = Config.MERGE_OUTPUT_FORMAT_VIDEO or "mkv (Default)"
        audio_format = Config.MERGE_OUTPUT_FORMAT_AUDIO or "mp3 (Default)"
        merge_priority = Config.MERGE_PRIORITY or "1 (Default)"
        merge_threading = "✅ Enabled" if Config.MERGE_THREADING else "❌ Disabled"
        merge_thread_number = Config.MERGE_THREAD_NUMBER or "4 (Default)"
        merge_remove_original = (
            "✅ Enabled" if Config.MERGE_REMOVE_ORIGINAL else "❌ Disabled"
        )

        # Determine which category is shown on the current page
        start_idx = current_page * items_per_page
        end_idx = min(start_idx + items_per_page, len(merge_settings))

        # Get the categories shown on the current page
        categories = []
        if any(
            setting in general_settings
            for setting in merge_settings[start_idx:end_idx]
        ):
            categories.append("General")
        if any(setting in formats for setting in merge_settings[start_idx:end_idx]):
            categories.append("Formats")
        if any(
            setting in video_settings
            for setting in merge_settings[start_idx:end_idx]
        ):
            categories.append("Video")
        if any(
            setting in audio_settings
            for setting in merge_settings[start_idx:end_idx]
        ):
            categories.append("Audio")
        if any(
            setting in image_settings
            for setting in merge_settings[start_idx:end_idx]
        ):
            categories.append("Image")
        if any(
            setting in subtitle_settings
            for setting in merge_settings[start_idx:end_idx]
        ):
            categories.append("Subtitle")
        if any(
            setting in document_settings
            for setting in merge_settings[start_idx:end_idx]
        ):
            categories.append("Document")
        if any(
            setting in metadata_settings
            for setting in merge_settings[start_idx:end_idx]
        ):
            categories.append("Metadata")

        category_text = ", ".join(categories)

        msg = f"""<b>Merge Settings</b> | State: {state}

<b>Status:</b> {merge_enabled}
<b>Concat Demuxer:</b> {concat_demuxer}
<b>Filter Complex:</b> {filter_complex}
<b>Video Format:</b> <code>{video_format}</code>
<b>Audio Format:</b> <code>{audio_format}</code>
<b>Priority:</b> <code>{merge_priority}</code>
<b>Threading:</b> {merge_threading}
<b>Thread Number:</b> <code>{merge_thread_number}</code>
<b>Remove Original:</b> {merge_remove_original}

Configure global merge settings that will be used when user settings are not available.
Current page shows: {category_text} settings."""

        # Add page info to message
        if total_pages > 1:
            msg += f"\n\n<b>Page:</b> {current_page + 1}/{total_pages}"

        # Build the menu with 2 columns for settings, 4 columns for action buttons, and 8 columns for pagination
        btns = buttons.build_menu(2, 8, 4, 8)
        return msg, btns

    elif key == "mediatools_metadata":
        # Add buttons for each metadata setting in a 2-column layout
        metadata_settings = [
            "METADATA_KEY",
            "METADATA_ALL",
            "METADATA_TITLE",
            "METADATA_AUTHOR",
            "METADATA_COMMENT",
        ]
        for setting in metadata_settings:
            display_name = setting.replace("METADATA_", "").replace("_", " ").title()
            # Always use editvar in both view and edit states to ensure consistent behavior
            # This matches the behavior of the watermark settings
            callback_data = f"botset editvar {setting}"
            LOGGER.debug(
                f"Creating metadata button: {display_name} with callback: {callback_data} (state={state})"
            )
            buttons.data_button(display_name, callback_data)

        if state == "view":
            buttons.data_button("Edit", "botset edit mediatools_metadata")
        else:
            buttons.data_button("View", "botset view mediatools_metadata")

        buttons.data_button("Default", "botset default_metadata")

        buttons.data_button("Back", "botset mediatools", "footer")
        buttons.data_button("Close", "botset close", "footer")

        # Get current metadata settings
        metadata_key = Config.METADATA_KEY or "None"
        metadata_all = Config.METADATA_ALL or "None"
        metadata_title = Config.METADATA_TITLE or "None"
        metadata_author = Config.METADATA_AUTHOR or "None"
        metadata_comment = Config.METADATA_COMMENT or "None"

        msg = f"""<b>Metadata Settings</b> | State: {state}

<b>Legacy Key:</b> <code>{metadata_key}</code>
<b>All:</b> <code>{metadata_all}</code>
<b>Title:</b> <code>{metadata_title}</code>
<b>Author:</b> <code>{metadata_author}</code>
<b>Comment:</b> <code>{metadata_comment}</code>

<b>Note:</b> 'All' takes priority over individual settings when set.

Configure global metadata settings that will be used when user settings are not available."""

    elif key == "mediatools_merge_config":
        # Add buttons for each merge configuration setting in a 2-column layout
        # Group settings by category
        formats = [
            "MERGE_OUTPUT_FORMAT_VIDEO",
            "MERGE_OUTPUT_FORMAT_AUDIO",
            "MERGE_OUTPUT_FORMAT_IMAGE",
            "MERGE_OUTPUT_FORMAT_DOCUMENT",
            "MERGE_OUTPUT_FORMAT_SUBTITLE",
        ]

        video_settings = [
            "MERGE_VIDEO_CODEC",
            "MERGE_VIDEO_QUALITY",
            "MERGE_VIDEO_PRESET",
            "MERGE_VIDEO_CRF",
            "MERGE_VIDEO_PIXEL_FORMAT",
            "MERGE_VIDEO_TUNE",
            "MERGE_VIDEO_FASTSTART",
        ]

        audio_settings = [
            "MERGE_AUDIO_CODEC",
            "MERGE_AUDIO_BITRATE",
            "MERGE_AUDIO_CHANNELS",
            "MERGE_AUDIO_SAMPLING",
            "MERGE_AUDIO_VOLUME",
        ]

        image_settings = [
            "MERGE_IMAGE_MODE",
            "MERGE_IMAGE_COLUMNS",
            "MERGE_IMAGE_QUALITY",
            "MERGE_IMAGE_DPI",
            "MERGE_IMAGE_RESIZE",
            "MERGE_IMAGE_BACKGROUND",
        ]

        subtitle_settings = [
            "MERGE_SUBTITLE_ENCODING",
            "MERGE_SUBTITLE_FONT",
            "MERGE_SUBTITLE_FONT_SIZE",
            "MERGE_SUBTITLE_FONT_COLOR",
            "MERGE_SUBTITLE_BACKGROUND",
        ]

        document_settings = [
            "MERGE_DOCUMENT_PAPER_SIZE",
            "MERGE_DOCUMENT_ORIENTATION",
            "MERGE_DOCUMENT_MARGIN",
        ]

        metadata_settings = [
            "MERGE_METADATA_TITLE",
            "MERGE_METADATA_AUTHOR",
            "MERGE_METADATA_COMMENT",
        ]

        # Combine all settings
        merge_config_settings = (
            formats
            + video_settings
            + audio_settings
            + image_settings
            + subtitle_settings
            + document_settings
            + metadata_settings
        )

        # 5 rows per page, 2 columns = 10 items per page
        items_per_page = 10  # 5 rows * 2 columns
        total_pages = (
            len(merge_config_settings) + items_per_page - 1
        ) // items_per_page

        # Ensure page is valid
        current_page = page
        if current_page >= total_pages:
            current_page = 0
        elif current_page < 0:
            current_page = total_pages - 1

        # Get settings for current page
        start_idx = current_page * items_per_page
        end_idx = min(start_idx + items_per_page, len(merge_config_settings))
        current_page_settings = merge_config_settings[start_idx:end_idx]

        # Add buttons for each setting on current page
        for setting in current_page_settings:
            display_name = setting.replace("MERGE_", "").replace("_", " ").title()
            buttons.data_button(display_name, f"botset editvar {setting}")

        # Add action buttons in a separate row
        if state == "view":
            buttons.data_button(
                "Edit", "botset edit mediatools_merge_config", "footer"
            )
        else:
            buttons.data_button(
                "View", "botset view mediatools_merge_config", "footer"
            )

        # Add Default button
        buttons.data_button("Default", "botset default_merge_config", "footer")

        # Add navigation buttons
        buttons.data_button("Back", "botset mediatools_merge", "footer")
        buttons.data_button("Close", "botset close", "footer")

        # Add pagination buttons in a separate row below action buttons
        if total_pages > 1:
            for i in range(total_pages):
                # Make the current page button different
                if i == current_page:
                    buttons.data_button(
                        f"[{i + 1}]", f"botset start_merge_config {i}", "page"
                    )
                else:
                    buttons.data_button(
                        str(i + 1), f"botset start_merge_config {i}", "page"
                    )

            # Add a debug log message
            LOGGER.debug(
                f"Added pagination buttons for merge_config in bot_settings. Total pages: {total_pages}, Current page: {current_page}"
            )

        # Get current merge configuration settings - Output formats
        video_format = Config.MERGE_OUTPUT_FORMAT_VIDEO or "mkv (Default)"
        audio_format = Config.MERGE_OUTPUT_FORMAT_AUDIO or "mp3 (Default)"
        image_format = Config.MERGE_OUTPUT_FORMAT_IMAGE or "jpg (Default)"
        document_format = Config.MERGE_OUTPUT_FORMAT_DOCUMENT or "pdf (Default)"
        subtitle_format = Config.MERGE_OUTPUT_FORMAT_SUBTITLE or "srt (Default)"

        # Video settings
        video_codec = Config.MERGE_VIDEO_CODEC or "copy (Default)"
        video_quality = Config.MERGE_VIDEO_QUALITY or "medium (Default)"
        video_preset = Config.MERGE_VIDEO_PRESET or "medium (Default)"
        video_crf = Config.MERGE_VIDEO_CRF or "23 (Default)"
        video_pixel_format = Config.MERGE_VIDEO_PIXEL_FORMAT or "yuv420p (Default)"
        video_tune = Config.MERGE_VIDEO_TUNE or "film (Default)"
        video_faststart = "Enabled" if Config.MERGE_VIDEO_FASTSTART else "Disabled"

        # Audio settings
        audio_codec = Config.MERGE_AUDIO_CODEC or "copy (Default)"
        audio_bitrate = Config.MERGE_AUDIO_BITRATE or "192k (Default)"
        audio_channels = Config.MERGE_AUDIO_CHANNELS or "2 (Default)"
        audio_sampling = Config.MERGE_AUDIO_SAMPLING or "44100 (Default)"
        audio_volume = Config.MERGE_AUDIO_VOLUME or "1.0 (Default)"

        # Image settings
        image_mode = Config.MERGE_IMAGE_MODE or "auto (Default)"
        image_columns = Config.MERGE_IMAGE_COLUMNS or "2 (Default)"
        image_quality = Config.MERGE_IMAGE_QUALITY or "90 (Default)"
        image_dpi = Config.MERGE_IMAGE_DPI or "300 (Default)"
        image_resize = Config.MERGE_IMAGE_RESIZE or "none (Default)"
        image_background = Config.MERGE_IMAGE_BACKGROUND or "white (Default)"

        # Subtitle settings
        subtitle_encoding = Config.MERGE_SUBTITLE_ENCODING or "utf-8 (Default)"
        subtitle_font = Config.MERGE_SUBTITLE_FONT or "Arial (Default)"
        subtitle_font_size = Config.MERGE_SUBTITLE_FONT_SIZE or "24 (Default)"
        subtitle_font_color = Config.MERGE_SUBTITLE_FONT_COLOR or "white (Default)"
        subtitle_background = Config.MERGE_SUBTITLE_BACKGROUND or "black (Default)"

        # Document settings
        document_paper_size = Config.MERGE_DOCUMENT_PAPER_SIZE or "a4 (Default)"
        document_orientation = (
            Config.MERGE_DOCUMENT_ORIENTATION or "portrait (Default)"
        )
        document_margin = Config.MERGE_DOCUMENT_MARGIN or "50 (Default)"

        # Metadata settings
        metadata_title = Config.MERGE_METADATA_TITLE or "(Default: empty)"
        metadata_author = Config.MERGE_METADATA_AUTHOR or "(Default: empty)"
        metadata_comment = Config.MERGE_METADATA_COMMENT or "(Default: empty)"

        msg = f"""<b>Merge Configuration</b> | State: {state}

<b>Output Formats:</b>
• <b>Video:</b> <code>{video_format}</code>
• <b>Audio:</b> <code>{audio_format}</code>
• <b>Image:</b> <code>{image_format}</code>
• <b>Document:</b> <code>{document_format}</code>
• <b>Subtitle:</b> <code>{subtitle_format}</code>

<b>Video Settings:</b>
• <b>Codec:</b> <code>{video_codec}</code>
• <b>Quality:</b> <code>{video_quality}</code>
• <b>Preset:</b> <code>{video_preset}</code>
• <b>CRF:</b> <code>{video_crf}</code>
• <b>Pixel Format:</b> <code>{video_pixel_format}</code>
• <b>Tune:</b> <code>{video_tune}</code>
• <b>Faststart:</b> <code>{video_faststart}</code>

<b>Audio Settings:</b>
• <b>Codec:</b> <code>{audio_codec}</code>
• <b>Bitrate:</b> <code>{audio_bitrate}</code>
• <b>Channels:</b> <code>{audio_channels}</code>
• <b>Sampling:</b> <code>{audio_sampling}</code>
• <b>Volume:</b> <code>{audio_volume}</code>

<b>Image Settings:</b>
• <b>Mode:</b> <code>{image_mode}</code>
• <b>Columns:</b> <code>{image_columns}</code>
• <b>Quality:</b> <code>{image_quality}</code>
• <b>DPI:</b> <code>{image_dpi}</code>
• <b>Resize:</b> <code>{image_resize}</code>
• <b>Background:</b> <code>{image_background}</code>

<b>Subtitle Settings:</b>
• <b>Encoding:</b> <code>{subtitle_encoding}</code>
• <b>Font:</b> <code>{subtitle_font}</code>
• <b>Font Size:</b> <code>{subtitle_font_size}</code>
• <b>Font Color:</b> <code>{subtitle_font_color}</code>
• <b>Background:</b> <code>{subtitle_background}</code>

<b>Document Settings:</b>
• <b>Paper Size:</b> <code>{document_paper_size}</code>
• <b>Orientation:</b> <code>{document_orientation}</code>
• <b>Margin:</b> <code>{document_margin}</code>

<b>Metadata:</b>
• <b>Title:</b> <code>{metadata_title}</code>
• <b>Author:</b> <code>{metadata_author}</code>
• <b>Comment:</b> <code>{metadata_comment}</code>

Configure advanced merge settings that will be used when user settings are not available."""

        # Determine which category is shown on the current page
        start_idx = current_page * items_per_page
        end_idx = min(start_idx + items_per_page, len(merge_config_settings))

        # Get the categories shown on the current page
        categories = []
        if any(
            setting in formats
            for setting in merge_config_settings[start_idx:end_idx]
        ):
            categories.append("Formats")
        if any(
            setting in video_settings
            for setting in merge_config_settings[start_idx:end_idx]
        ):
            categories.append("Video")
        if any(
            setting in audio_settings
            for setting in merge_config_settings[start_idx:end_idx]
        ):
            categories.append("Audio")
        if any(
            setting in image_settings
            for setting in merge_config_settings[start_idx:end_idx]
        ):
            categories.append("Image")
        if any(
            setting in subtitle_settings
            for setting in merge_config_settings[start_idx:end_idx]
        ):
            categories.append("Subtitle")
        if any(
            setting in document_settings
            for setting in merge_config_settings[start_idx:end_idx]
        ):
            categories.append("Document")
        if any(
            setting in metadata_settings
            for setting in merge_config_settings[start_idx:end_idx]
        ):
            categories.append("Metadata")

        category_text = ", ".join(categories)

        # Add category and page info to message
        msg += f"\n\nCurrent page shows: {category_text} settings."
        if total_pages > 1:
            msg += f"\n<b>Page:</b> {current_page + 1}/{total_pages}"

    if key is None:
        button = buttons.build_menu(1)
    elif key in {"mediatools_merge", "mediatools_merge_config"}:
        # Build the menu with 2 columns for settings, 4 columns for action buttons, and 8 columns for pagination
        button = buttons.build_menu(2, 8, 4, 8)
    elif key == "mediatools_watermark":
        button = buttons.build_menu(2)
    else:
        button = buttons.build_menu(2)
    return msg, button


async def update_buttons(message, key=None, edit_type=None, page=0):
    user_id = message.chat.id
    LOGGER.debug(
        f"update_buttons called with key={key}, edit_type={edit_type}, page={page}"
    )
    msg, button = await get_buttons(key, edit_type, page, user_id)
    await edit_message(message, msg, button)


@new_task
async def edit_variable(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
        if key == "INCOMPLETE_TASK_NOTIFIER" and Config.DATABASE_URL:
            await database.trunc_table("tasks")
    elif key == "TORRENT_TIMEOUT":
        await TorrentManager.change_aria2_option("bt-stop-timeout", value)
        value = int(value)
    elif key == "LEECH_SPLIT_SIZE":
        value = min(int(value), TgClient.MAX_SPLIT_SIZE)
    elif key == "LEECH_FILENAME_CAPTION":
        # Check if caption exceeds Telegram's limit (1024 characters)
        if len(value) > 1024:
            error_msg = await send_message(
                message,
                "❌ Error: Caption exceeds Telegram's limit of 1024 characters. Please use a shorter caption.",
            )
            # Auto-delete error message after 5 minutes
            create_task(auto_delete_message(error_msg, time=300))
            return
    elif key == "LEECH_FILENAME":
        # No specific validation needed for LEECH_FILENAME
        pass
    elif key in {
        "WATERMARK_SIZE",
        "WATERMARK_THREAD_NUMBER",
        "MERGE_THREAD_NUMBER",
        "MERGE_PRIORITY",
        "MERGE_VIDEO_CRF",
        "MERGE_IMAGE_COLUMNS",
        "MERGE_IMAGE_QUALITY",
        "MERGE_IMAGE_DPI",
        "MERGE_SUBTITLE_FONT_SIZE",
        "MERGE_DOCUMENT_MARGIN",
        "MERGE_AUDIO_CHANNELS",
    }:
        try:
            value = int(value)
        except ValueError:
            # Use appropriate default values based on the key
            if key == "WATERMARK_SIZE":
                value = 20
            elif key in {"WATERMARK_THREAD_NUMBER", "MERGE_THREAD_NUMBER"}:
                value = 4
            elif key == "MERGE_PRIORITY":
                value = 1
            elif key == "MERGE_VIDEO_CRF":
                value = 23
            elif key == "MERGE_IMAGE_COLUMNS":
                value = 2
            elif key == "MERGE_IMAGE_QUALITY":
                value = 90
            elif key == "MERGE_IMAGE_DPI":
                value = 300
            elif key == "MERGE_SUBTITLE_FONT_SIZE":
                value = 24
            elif key == "MERGE_DOCUMENT_MARGIN":
                value = 50
            elif key == "MERGE_AUDIO_CHANNELS":
                value = 2
    elif key == "MERGE_AUDIO_VOLUME":
        try:
            value = float(value)
        except ValueError:
            value = 1.0  # Default volume if invalid input
    elif key == "WATERMARK_POSITION" and value not in [
        "top_left",
        "top_right",
        "bottom_left",
        "bottom_right",
        "center",
    ]:
        value = "top_left"  # Default position if invalid input
    elif key == "EXCLUDED_EXTENSIONS":
        fx = value.split()
        excluded_extensions.clear()
        excluded_extensions.extend(["aria2", "!qB"])
        for x in fx:
            x = x.lstrip(".")
            excluded_extensions.append(x.strip().lower())
    elif key == "GDRIVE_ID":
        if drives_names and drives_names[0] == "Main":
            drives_ids[0] = value
        else:
            drives_ids.insert(0, value)
    elif key == "INDEX_URL":
        if drives_names and drives_names[0] == "Main":
            index_urls[0] = value
        else:
            index_urls.insert(0, value)
    elif key == "AUTHORIZED_CHATS":
        aid = value.split()
        auth_chats.clear()
        for id_ in aid:
            chat_id, *thread_ids = id_.split("|")
            chat_id = int(chat_id.strip())
            if thread_ids:
                thread_ids = [int(x.strip()) for x in thread_ids]
                auth_chats[chat_id] = thread_ids
            else:
                auth_chats[chat_id] = []
    elif key == "SUDO_USERS":
        sudo_users.clear()
        aid = value.split()
        for id_ in aid:
            sudo_users.append(int(id_.strip()))
    elif key == "FFMPEG_MEMORY_LIMIT":
        try:
            value = int(value)
        except ValueError:
            value = 2048  # Default to 2GB if invalid input
    elif key == "FFMPEG_DYNAMIC_THREADS":
        value = value.lower() in ("true", "1", "yes")
    elif key == "AUTO_RESTART_ENABLED":
        value = value.lower() in ("true", "1", "yes")
        # Always schedule or cancel auto-restart when this setting is changed
        from bot.helper.ext_utils.auto_restart import schedule_auto_restart

        create_task(schedule_auto_restart())
    elif key == "AUTO_RESTART_INTERVAL":
        try:
            value = max(1, int(value))  # Minimum 1 hour
            # Schedule the next auto-restart with the new interval if enabled
            if Config.AUTO_RESTART_ENABLED:
                from bot.helper.ext_utils.auto_restart import schedule_auto_restart

                create_task(schedule_auto_restart())
        except ValueError:
            value = 24  # Default to 24 hours if invalid input
    elif value.isdigit():
        value = int(value)
    elif (value.startswith("[") and value.endswith("]")) or (
        value.startswith("{") and value.endswith("}")
    ):
        value = eval(value)
    Config.set(key, value)

    # Determine which menu to return to based on the key
    if key.startswith("WATERMARK_"):
        return_menu = "mediatools_watermark"
        LOGGER.debug(
            f"edit_variable: Setting return_menu for {key} to {return_menu}"
        )
    elif key.startswith("METADATA_"):
        return_menu = "mediatools_metadata"
        LOGGER.debug(
            f"edit_variable: Setting return_menu for {key} to {return_menu}"
        )
    elif key.startswith("MERGE_") or key in [
        "CONCAT_DEMUXER_ENABLED",
        "FILTER_COMPLEX_ENABLED",
    ]:
        # Check if we're in the merge_config menu
        if (pre_message.text and "Merge Configuration" in pre_message.text) or (
            key.startswith("MERGE_")
            and any(
                x in key
                for x in [
                    "OUTPUT_FORMAT",
                    "VIDEO_",
                    "AUDIO_",
                    "IMAGE_",
                    "SUBTITLE_",
                    "DOCUMENT_",
                    "METADATA_",
                ]
            )
        ):
            return_menu = "mediatools_merge_config"
        # Check if we need to return to a specific page in mediatools_merge or mediatools_merge_config
        elif pre_message.text and "Page:" in pre_message.text:
            try:
                page_info = pre_message.text.split("Page:")[1].strip().split("/")[0]
                page_no = int(page_info) - 1

                # Determine which menu to return to based on the message content
                if "Merge Configuration" in pre_message.text:
                    return_menu = "mediatools_merge_config"
                else:
                    return_menu = "mediatools_merge"

                # Return to the correct page
                await update_buttons(pre_message, return_menu, page=page_no)
                await delete_message(message)
                await database.update_config({key: value})
                return
            except (ValueError, IndexError):
                if "Merge Configuration" in pre_message.text:
                    return_menu = "mediatools_merge_config"
                else:
                    return_menu = "mediatools_merge"
        else:
            return_menu = "mediatools_merge"
    elif key == "MEDIA_TOOLS_PRIORITY":
        return_menu = "mediatools"
    else:
        return_menu = "var"

    await update_buttons(pre_message, return_menu)
    await delete_message(message)
    await database.update_config({key: value})

    if key in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
        await start_from_queued()
    elif key in [
        "RCLONE_SERVE_URL",
        "RCLONE_SERVE_PORT",
        "RCLONE_SERVE_USER",
        "RCLONE_SERVE_PASS",
    ]:
        await rclone_serve_booter()
    elif key in ["JD_EMAIL", "JD_PASS"]:
        await jdownloader.boot()
    elif key == "RSS_DELAY":
        add_job()
    elif key == "USET_SERVERS":
        for s in value:
            await sabnzbd_client.set_special_config("servers", s)


@new_task
async def edit_aria(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == "newkey":
        key, value = [x.strip() for x in value.split(":", 1)]
    elif value.lower() == "true":
        value = "true"
    elif value.lower() == "false":
        value = "false"
    await TorrentManager.change_aria2_option(key, value)
    await update_buttons(pre_message, "aria")
    await delete_message(message)
    await database.update_aria2(key, value)


@new_task
async def edit_qbit(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif key == "max_ratio":
        value = float(value)
    elif value.isdigit():
        value = int(value)
    await TorrentManager.qbittorrent.app.set_preferences({key: value})
    qbit_options[key] = value
    await update_buttons(pre_message, "qbit")
    await delete_message(message)
    await database.update_qbittorrent(key, value)


@new_task
async def edit_nzb(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.isdigit():
        value = int(value)
    elif value.startswith("[") and value.endswith("]"):
        try:
            value = ",".join(eval(value))
        except Exception as e:
            LOGGER.error(e)
            await update_buttons(pre_message, "nzb")
            return
    res = await sabnzbd_client.set_config("misc", key, value)
    nzb_options[key] = res["config"]["misc"][key]
    await update_buttons(pre_message, "nzb")
    await delete_message(message)
    await database.update_nzb_config()


@new_task
async def edit_nzb_server(_, message, pre_message, key, index=0):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == "newser":
        if value.startswith("{") and value.endswith("}"):
            try:
                value = eval(value)
            except Exception:
                await send_message(message, "Invalid dict format!")
                await update_buttons(pre_message, "nzbserver")
                return
            res = await sabnzbd_client.add_server(value)
            if not res["config"]["servers"][0]["host"]:
                await send_message(message, "Invalid server!")
                await update_buttons(pre_message, "nzbserver")
                return
            Config.USENET_SERVERS.append(value)
            await update_buttons(pre_message, "nzbserver")
        else:
            await send_message(message, "Invalid dict format!")
            await update_buttons(pre_message, "nzbserver")
            return
    else:
        if value.isdigit():
            value = int(value)
        res = await sabnzbd_client.add_server(
            {"name": Config.USENET_SERVERS[index]["name"], key: value},
        )
        if res["config"]["servers"][0][key] == "":
            await send_message(message, "Invalid value")
            return
        Config.USENET_SERVERS[index][key] = value
        await update_buttons(pre_message, f"nzbser{index}")
    await delete_message(message)
    await database.update_config({"USENET_SERVERS": Config.USENET_SERVERS})


async def sync_jdownloader():
    async with jd_listener_lock:
        if not Config.DATABASE_URL or not jdownloader.is_connected:
            return
        await jdownloader.device.system.exit_jd()
    if await aiopath.exists("cfg.zip"):
        await remove("cfg.zip")
    await (
        await create_subprocess_exec("7z", "a", "cfg.zip", "/JDownloader/cfg")
    ).wait()
    await database.update_private_file("cfg.zip")


@new_task
async def update_private_file(_, message, pre_message):
    handler_dict[message.chat.id] = False
    if not message.media and (file_name := message.text):
        if await aiopath.isfile(file_name) and file_name != "config.py":
            await remove(file_name)
        if file_name == "accounts.zip":
            if await aiopath.exists("accounts"):
                await rmtree("accounts", ignore_errors=True)
            if await aiopath.exists("rclone_sa"):
                await rmtree("rclone_sa", ignore_errors=True)
            Config.USE_SERVICE_ACCOUNTS = False
            await database.update_config({"USE_SERVICE_ACCOUNTS": False})
        elif file_name in [".netrc", "netrc"]:
            await (await create_subprocess_exec("touch", ".netrc")).wait()
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (
                await create_subprocess_exec("cp", ".netrc", "/root/.netrc")
            ).wait()
        await delete_message(message)
    elif doc := message.document:
        file_name = doc.file_name
        fpath = f"{getcwd()}/{file_name}"
        if await aiopath.exists(fpath):
            await remove(fpath)
        await message.download(file_name=fpath)
        if file_name == "accounts.zip":
            if await aiopath.exists("accounts"):
                await rmtree("accounts", ignore_errors=True)
            if await aiopath.exists("rclone_sa"):
                await rmtree("rclone_sa", ignore_errors=True)
            await (
                await create_subprocess_exec(
                    "7z",
                    "x",
                    "-o.",
                    "-aoa",
                    "accounts.zip",
                    "accounts/*.json",
                )
            ).wait()
            await (
                await create_subprocess_exec("chmod", "-R", "777", "accounts")
            ).wait()
        elif file_name == "list_drives.txt":
            drives_ids.clear()
            drives_names.clear()
            index_urls.clear()
            if Config.GDRIVE_ID:
                drives_names.append("Main")
                drives_ids.append(Config.GDRIVE_ID)
                index_urls.append(Config.INDEX_URL)
            async with aiopen("list_drives.txt", "r+") as f:
                lines = await f.readlines()
                for line in lines:
                    temp = line.strip().split()
                    drives_ids.append(temp[1])
                    drives_names.append(temp[0].replace("_", " "))
                    if len(temp) > 2:
                        index_urls.append(temp[2])
                    else:
                        index_urls.append("")
        elif file_name in [".netrc", "netrc"]:
            if file_name == "netrc":
                await rename("netrc", ".netrc")
                file_name = ".netrc"
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (
                await create_subprocess_exec("cp", ".netrc", "/root/.netrc")
            ).wait()
        elif file_name == "config.py":
            await load_config()
        await delete_message(message)
    if file_name == "rclone.conf":
        await rclone_serve_booter()
    await update_buttons(pre_message)
    await database.update_private_file(file_name)


async def event_handler(client, query, pfunc, rfunc, document=False):
    chat_id = query.message.chat.id
    handler_dict[chat_id] = True
    start_time = time()
    LOGGER.debug(
        f"Starting event_handler for chat_id={chat_id}, pfunc={pfunc}, rfunc={rfunc}"
    )

    # pylint: disable=unused-argument
    async def event_filter(_, *args):
        event = args[1]  # The event is the second argument
        user = event.from_user or event.sender_chat
        query_user = query.from_user

        # Check if both user and query_user are not None before comparing IDs
        if user is None or query_user is None:
            return False

        return bool(
            user.id == query_user.id
            and event.chat.id == chat_id
            and (event.text or (event.document and document)),
        )

    handler = client.add_handler(
        MessageHandler(pfunc, filters=create(event_filter)),
        group=-1,
    )
    while handler_dict[chat_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[chat_id] = False
            LOGGER.debug(
                f"Timeout in event_handler for chat_id={chat_id}, calling rfunc={rfunc}"
            )
            await rfunc()
    LOGGER.debug(f"Exiting event_handler for chat_id={chat_id}")
    client.remove_handler(*handler)


@new_task
async def edit_bot_settings(client, query):
    data = query.data.split()
    message = query.message
    user_id = message.chat.id
    handler_dict[user_id] = False
    if data[1] == "close":
        await query.answer()
        await delete_message(message.reply_to_message)
        await delete_message(message)
    elif data[1] == "back":
        await query.answer()
        globals()["start"] = 0
        await update_buttons(message, None)
    elif data[1] == "syncjd":
        if not Config.JD_EMAIL or not Config.JD_PASS:
            await query.answer(
                "No Email or Password provided!",
                show_alert=True,
            )
            return
        await query.answer(
            "Syncronization Started. JDownloader will get restarted. It takes up to 10 sec!",
            show_alert=True,
        )
        await sync_jdownloader()
    elif data[1] == "mediatools":
        await query.answer()
        await update_buttons(message, "mediatools")
    elif data[1] == "mediatools_watermark":
        await query.answer()
        await update_buttons(message, "mediatools_watermark")
    elif data[1] == "mediatools_merge":
        await query.answer()
        # Always start at page 0 when first entering merge settings
        await update_buttons(message, "mediatools_merge", page=0)
    elif data[1] == "mediatools_merge_config":
        await query.answer()
        # Always start at page 0 when first entering merge config settings
        await update_buttons(message, "mediatools_merge_config", page=0)
    elif data[1] == "mediatools_metadata":
        await query.answer()
        LOGGER.debug("mediatools_metadata button clicked")
        await update_buttons(message, "mediatools_metadata")
    elif data[1] == "default_watermark":
        await query.answer("Resetting all watermark settings to default...")
        # Reset all watermark settings to default
        Config.WATERMARK_ENABLED = False
        Config.WATERMARK_KEY = ""
        Config.WATERMARK_POSITION = "top_left"
        Config.WATERMARK_SIZE = 20
        Config.WATERMARK_COLOR = "white"
        Config.WATERMARK_FONT = "default.otf"
        Config.WATERMARK_PRIORITY = 2
        Config.WATERMARK_THREADING = True
        Config.WATERMARK_THREAD_NUMBER = 4
        # Update the database
        await database.update_config(
            {
                "WATERMARK_ENABLED": False,
                "WATERMARK_KEY": "",
                "WATERMARK_POSITION": "top_left",
                "WATERMARK_SIZE": 20,
                "WATERMARK_COLOR": "white",
                "WATERMARK_FONT": "default.otf",
                "WATERMARK_PRIORITY": 2,
                "WATERMARK_THREADING": True,
                "WATERMARK_THREAD_NUMBER": 4,
            }
        )
        await update_buttons(message, "mediatools_watermark")
    elif data[1] == "default_metadata":
        await query.answer("Resetting all metadata settings to default...")
        # Reset all metadata settings to default
        Config.METADATA_KEY = ""
        Config.METADATA_ALL = ""
        Config.METADATA_TITLE = ""
        Config.METADATA_AUTHOR = ""
        Config.METADATA_COMMENT = ""
        # Update the database
        await database.update_config(
            {
                "METADATA_KEY": "",
                "METADATA_ALL": "",
                "METADATA_TITLE": "",
                "METADATA_AUTHOR": "",
                "METADATA_COMMENT": "",
            }
        )
        # Update the UI - pass the current state to maintain edit/view mode
        await update_buttons(message, "mediatools_metadata")
    elif data[1] == "default_merge":
        await query.answer("Resetting all merge settings to default...")
        # Reset all merge settings to default
        Config.MERGE_ENABLED = False
        Config.CONCAT_DEMUXER_ENABLED = True
        Config.FILTER_COMPLEX_ENABLED = False
        # Reset output formats
        Config.MERGE_OUTPUT_FORMAT_VIDEO = "mkv"
        Config.MERGE_OUTPUT_FORMAT_AUDIO = "mp3"
        Config.MERGE_OUTPUT_FORMAT_IMAGE = "jpg"
        Config.MERGE_OUTPUT_FORMAT_DOCUMENT = "pdf"
        Config.MERGE_OUTPUT_FORMAT_SUBTITLE = "srt"

        # Reset video settings
        Config.MERGE_VIDEO_CODEC = "none"
        Config.MERGE_VIDEO_QUALITY = "none"
        Config.MERGE_VIDEO_PRESET = "none"
        Config.MERGE_VIDEO_CRF = 0
        Config.MERGE_VIDEO_PIXEL_FORMAT = "none"
        Config.MERGE_VIDEO_TUNE = "none"
        Config.MERGE_VIDEO_FASTSTART = False

        # Reset audio settings
        Config.MERGE_AUDIO_CODEC = "none"
        Config.MERGE_AUDIO_BITRATE = "none"
        Config.MERGE_AUDIO_CHANNELS = 0
        Config.MERGE_AUDIO_SAMPLING = "none"
        Config.MERGE_AUDIO_VOLUME = 0.0

        # Reset image settings
        Config.MERGE_IMAGE_MODE = "none"
        Config.MERGE_IMAGE_COLUMNS = 0
        Config.MERGE_IMAGE_QUALITY = 0
        Config.MERGE_IMAGE_DPI = 0
        Config.MERGE_IMAGE_RESIZE = "none"
        Config.MERGE_IMAGE_BACKGROUND = "none"

        # Reset subtitle settings
        Config.MERGE_SUBTITLE_ENCODING = "none"
        Config.MERGE_SUBTITLE_FONT = "none"
        Config.MERGE_SUBTITLE_FONT_SIZE = 0
        Config.MERGE_SUBTITLE_FONT_COLOR = "none"
        Config.MERGE_SUBTITLE_BACKGROUND = "none"

        # Reset document settings
        Config.MERGE_DOCUMENT_PAPER_SIZE = "none"
        Config.MERGE_DOCUMENT_ORIENTATION = "none"
        Config.MERGE_DOCUMENT_MARGIN = 0

        # Reset general settings
        Config.MERGE_METADATA_TITLE = "none"
        Config.MERGE_METADATA_AUTHOR = "none"
        Config.MERGE_METADATA_COMMENT = "none"
        Config.MERGE_PRIORITY = 1
        Config.MERGE_THREADING = True
        Config.MERGE_THREAD_NUMBER = 4
        Config.MERGE_REMOVE_ORIGINAL = True
        # Update the database
        await database.update_config(
            {
                "MERGE_ENABLED": False,
                "CONCAT_DEMUXER_ENABLED": True,
                "FILTER_COMPLEX_ENABLED": False,
                # Output formats
                "MERGE_OUTPUT_FORMAT_VIDEO": "mkv",
                "MERGE_OUTPUT_FORMAT_AUDIO": "mp3",
                "MERGE_OUTPUT_FORMAT_IMAGE": "jpg",
                "MERGE_OUTPUT_FORMAT_DOCUMENT": "pdf",
                "MERGE_OUTPUT_FORMAT_SUBTITLE": "srt",
                # Video settings
                "MERGE_VIDEO_CODEC": "none",
                "MERGE_VIDEO_QUALITY": "none",
                "MERGE_VIDEO_PRESET": "none",
                "MERGE_VIDEO_CRF": 0,
                "MERGE_VIDEO_PIXEL_FORMAT": "none",
                "MERGE_VIDEO_TUNE": "none",
                "MERGE_VIDEO_FASTSTART": False,
                # Audio settings
                "MERGE_AUDIO_CODEC": "none",
                "MERGE_AUDIO_BITRATE": "none",
                "MERGE_AUDIO_CHANNELS": 0,
                "MERGE_AUDIO_SAMPLING": "none",
                "MERGE_AUDIO_VOLUME": 0.0,
                # Image settings
                "MERGE_IMAGE_MODE": "none",
                "MERGE_IMAGE_COLUMNS": 0,
                "MERGE_IMAGE_QUALITY": 0,
                "MERGE_IMAGE_DPI": 0,
                "MERGE_IMAGE_RESIZE": "none",
                "MERGE_IMAGE_BACKGROUND": "none",
                # Subtitle settings
                "MERGE_SUBTITLE_ENCODING": "none",
                "MERGE_SUBTITLE_FONT": "none",
                "MERGE_SUBTITLE_FONT_SIZE": 0,
                "MERGE_SUBTITLE_FONT_COLOR": "none",
                "MERGE_SUBTITLE_BACKGROUND": "none",
                # Document settings
                "MERGE_DOCUMENT_PAPER_SIZE": "none",
                "MERGE_DOCUMENT_ORIENTATION": "none",
                "MERGE_DOCUMENT_MARGIN": 0,
                # General settings
                "MERGE_METADATA_TITLE": "none",
                "MERGE_METADATA_AUTHOR": "none",
                "MERGE_METADATA_COMMENT": "none",
                "MERGE_PRIORITY": 1,
                "MERGE_THREADING": True,
                "MERGE_THREAD_NUMBER": 4,
                "MERGE_REMOVE_ORIGINAL": True,
            }
        )
        # Keep the current page
        await update_buttons(message, "mediatools_merge")
    elif data[1] == "edit" and data[2] in [
        "mediatools_watermark",
        "mediatools_merge",
        "mediatools_merge_config",
        "mediatools_metadata",
    ]:
        await query.answer()
        globals()["state"] = "edit"
        # For merge settings, maintain the current page
        if data[2] == "mediatools_merge":
            # Just update the state, the page is maintained by the global merge_page variable
            LOGGER.debug(
                f"Edit button clicked, using merge_page: {globals()['merge_page']}"
            )
            await update_buttons(
                message, "mediatools_merge", page=globals()["merge_page"]
            )
        elif data[2] == "mediatools_metadata":
            LOGGER.debug("Edit button clicked for metadata settings")
            await update_buttons(message, "mediatools_metadata")
        else:
            await update_buttons(message, data[2])
    elif data[1] == "view" and data[2] in [
        "mediatools_watermark",
        "mediatools_merge",
        "mediatools_merge_config",
        "mediatools_metadata",
    ]:
        await query.answer()
        globals()["state"] = "view"
        # For merge settings, maintain the current page
        if data[2] == "mediatools_merge":
            LOGGER.debug(
                f"View button clicked, using merge_page: {globals()['merge_page']}"
            )
            await update_buttons(
                message, "mediatools_merge", page=globals()["merge_page"]
            )
        elif data[2] == "mediatools_metadata":
            LOGGER.debug("View button clicked for metadata settings")
            await update_buttons(message, "mediatools_metadata")
        else:
            await update_buttons(message, data[2])
        # This section is now handled above
    elif data[1] == "editvar" and data[2] in [
        "WATERMARK_ENABLED",
        "WATERMARK_KEY",
        "WATERMARK_POSITION",
        "WATERMARK_SIZE",
        "WATERMARK_COLOR",
        "WATERMARK_FONT",
        "WATERMARK_PRIORITY",
        "WATERMARK_THREADING",
        "WATERMARK_THREAD_NUMBER",
        "METADATA_KEY",
        "METADATA_ALL",
        "METADATA_TITLE",
        "METADATA_AUTHOR",
        "METADATA_COMMENT",
        "MERGE_ENABLED",
        "CONCAT_DEMUXER_ENABLED",
        "FILTER_COMPLEX_ENABLED",
        "MERGE_OUTPUT_FORMAT_VIDEO",
        "MERGE_OUTPUT_FORMAT_AUDIO",
        "MERGE_OUTPUT_FORMAT_IMAGE",
        "MERGE_OUTPUT_FORMAT_DOCUMENT",
        "MERGE_OUTPUT_FORMAT_SUBTITLE",
        "MERGE_IMAGE_MODE",
        "MERGE_IMAGE_COLUMNS",
        "MERGE_IMAGE_QUALITY",
        "MERGE_IMAGE_DPI",
        "MERGE_IMAGE_RESIZE",
        "MERGE_IMAGE_BACKGROUND",
        "MERGE_VIDEO_CODEC",
        "MERGE_VIDEO_QUALITY",
        "MERGE_VIDEO_PRESET",
        "MERGE_VIDEO_CRF",
        "MERGE_VIDEO_PIXEL_FORMAT",
        "MERGE_VIDEO_TUNE",
        "MERGE_VIDEO_FASTSTART",
        "MERGE_AUDIO_CODEC",
        "MERGE_AUDIO_BITRATE",
        "MERGE_AUDIO_CHANNELS",
        "MERGE_AUDIO_SAMPLING",
        "MERGE_AUDIO_VOLUME",
        "MERGE_SUBTITLE_ENCODING",
        "MERGE_SUBTITLE_FONT",
        "MERGE_SUBTITLE_FONT_SIZE",
        "MERGE_SUBTITLE_FONT_COLOR",
        "MERGE_SUBTITLE_BACKGROUND",
        "MERGE_DOCUMENT_PAPER_SIZE",
        "MERGE_DOCUMENT_ORIENTATION",
        "MERGE_DOCUMENT_MARGIN",
        "MERGE_METADATA_TITLE",
        "MERGE_METADATA_AUTHOR",
        "MERGE_METADATA_COMMENT",
        "MERGE_PRIORITY",
        "MERGE_THREADING",
        "MERGE_THREAD_NUMBER",
        "MERGE_REMOVE_ORIGINAL",
        "MEDIA_TOOLS_PRIORITY",
    ]:
        if state == "view":
            # Handle view mode - show the current value in a popup
            value = f"{Config.get(data[2])}"
            if len(value) > 200:
                await query.answer()
                with BytesIO(str.encode(value)) as out_file:
                    out_file.name = f"{data[2]}.txt"
                    await send_file(message, out_file)
                return
            if value == "":
                value = None
            await query.answer(f"{value}", show_alert=True)
        else:
            # Handle edit mode
            await query.answer()
            LOGGER.debug(f"Handling editvar for {data[2]} in edit mode")
            await update_buttons(message, data[2], data[1])
            pfunc = partial(edit_variable, pre_message=message, key=data[2])

            # Determine which menu to return to based on the key
            if data[2].startswith("WATERMARK_"):
                LOGGER.debug(
                    f"Setting return function for {data[2]} to mediatools_watermark"
                )
                rfunc = partial(update_buttons, message, "mediatools_watermark")
            elif data[2].startswith("METADATA_"):
                LOGGER.debug(
                    f"Setting return function for {data[2]} to mediatools_metadata"
                )
                rfunc = partial(update_buttons, message, "mediatools_metadata")
            elif data[2].startswith("MERGE_") or data[2] in [
                "CONCAT_DEMUXER_ENABLED",
                "FILTER_COMPLEX_ENABLED",
            ]:
                # Check if we're in the merge_config menu
                if (message.text and "Merge Configuration" in message.text) or (
                    data[2].startswith("MERGE_")
                    and any(
                        x in data[2]
                        for x in [
                            "OUTPUT_FORMAT",
                            "VIDEO_",
                            "AUDIO_",
                            "IMAGE_",
                            "SUBTITLE_",
                            "DOCUMENT_",
                            "METADATA_",
                        ]
                    )
                ):
                    rfunc = partial(
                        update_buttons, message, "mediatools_merge_config"
                    )
                # Check if we need to return to a specific page in mediatools_merge
                elif message.text and "Page:" in message.text:
                    try:
                        page_info = (
                            message.text.split("Page:")[1].strip().split("/")[0]
                        )
                        page_no = int(page_info) - 1
                        # Set the global merge_page variable to ensure we return to the correct page
                        globals()["merge_page"] = page_no
                        rfunc = partial(update_buttons, message, "mediatools_merge")
                    except (ValueError, IndexError):
                        rfunc = partial(update_buttons, message, "mediatools_merge")
                else:
                    # Use the global merge_page variable
                    rfunc = partial(update_buttons, message, "mediatools_merge")
            else:
                rfunc = partial(update_buttons, message, "mediatools_watermark")
            await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "default_merge_config":
        await query.answer("Resetting all merge config settings to default...")
        # Reset all merge config settings to default
        # Reset output formats
        Config.MERGE_OUTPUT_FORMAT_VIDEO = "mkv"
        Config.MERGE_OUTPUT_FORMAT_AUDIO = "mp3"
        Config.MERGE_OUTPUT_FORMAT_IMAGE = "jpg"
        Config.MERGE_OUTPUT_FORMAT_DOCUMENT = "pdf"
        Config.MERGE_OUTPUT_FORMAT_SUBTITLE = "srt"

        # Reset video settings
        Config.MERGE_VIDEO_CODEC = "none"
        Config.MERGE_VIDEO_QUALITY = "none"
        Config.MERGE_VIDEO_PRESET = "none"
        Config.MERGE_VIDEO_CRF = 0
        Config.MERGE_VIDEO_PIXEL_FORMAT = "none"
        Config.MERGE_VIDEO_TUNE = "none"
        Config.MERGE_VIDEO_FASTSTART = False

        # Reset audio settings
        Config.MERGE_AUDIO_CODEC = "none"
        Config.MERGE_AUDIO_BITRATE = "none"
        Config.MERGE_AUDIO_CHANNELS = 0
        Config.MERGE_AUDIO_SAMPLING = "none"
        Config.MERGE_AUDIO_VOLUME = 0.0

        # Reset image settings
        Config.MERGE_IMAGE_MODE = "none"
        Config.MERGE_IMAGE_COLUMNS = 0
        Config.MERGE_IMAGE_QUALITY = 0
        Config.MERGE_IMAGE_DPI = 0
        Config.MERGE_IMAGE_RESIZE = "none"
        Config.MERGE_IMAGE_BACKGROUND = "none"

        # Reset subtitle settings
        Config.MERGE_SUBTITLE_ENCODING = "none"
        Config.MERGE_SUBTITLE_FONT = "none"
        Config.MERGE_SUBTITLE_FONT_SIZE = 0
        Config.MERGE_SUBTITLE_FONT_COLOR = "none"
        Config.MERGE_SUBTITLE_BACKGROUND = "none"

        # Reset document settings
        Config.MERGE_DOCUMENT_PAPER_SIZE = "none"
        Config.MERGE_DOCUMENT_ORIENTATION = "none"
        Config.MERGE_DOCUMENT_MARGIN = 0

        # Reset metadata settings
        Config.MERGE_METADATA_TITLE = "none"
        Config.MERGE_METADATA_AUTHOR = "none"
        Config.MERGE_METADATA_COMMENT = "none"

        # Update the database
        await database.update_config(
            {
                # Output formats
                "MERGE_OUTPUT_FORMAT_VIDEO": "mkv",
                "MERGE_OUTPUT_FORMAT_AUDIO": "mp3",
                "MERGE_OUTPUT_FORMAT_IMAGE": "jpg",
                "MERGE_OUTPUT_FORMAT_DOCUMENT": "pdf",
                "MERGE_OUTPUT_FORMAT_SUBTITLE": "srt",
                # Video settings
                "MERGE_VIDEO_CODEC": "none",
                "MERGE_VIDEO_QUALITY": "none",
                "MERGE_VIDEO_PRESET": "none",
                "MERGE_VIDEO_CRF": 0,
                "MERGE_VIDEO_PIXEL_FORMAT": "none",
                "MERGE_VIDEO_TUNE": "none",
                "MERGE_VIDEO_FASTSTART": False,
                # Audio settings
                "MERGE_AUDIO_CODEC": "none",
                "MERGE_AUDIO_BITRATE": "none",
                "MERGE_AUDIO_CHANNELS": 0,
                "MERGE_AUDIO_SAMPLING": "none",
                "MERGE_AUDIO_VOLUME": 0.0,
                # Image settings
                "MERGE_IMAGE_MODE": "none",
                "MERGE_IMAGE_COLUMNS": 0,
                "MERGE_IMAGE_QUALITY": 0,
                "MERGE_IMAGE_DPI": 0,
                "MERGE_IMAGE_RESIZE": "none",
                "MERGE_IMAGE_BACKGROUND": "none",
                # Subtitle settings
                "MERGE_SUBTITLE_ENCODING": "none",
                "MERGE_SUBTITLE_FONT": "none",
                "MERGE_SUBTITLE_FONT_SIZE": 0,
                "MERGE_SUBTITLE_FONT_COLOR": "none",
                "MERGE_SUBTITLE_BACKGROUND": "none",
                # Document settings
                "MERGE_DOCUMENT_PAPER_SIZE": "none",
                "MERGE_DOCUMENT_ORIENTATION": "none",
                "MERGE_DOCUMENT_MARGIN": 0,
                # Metadata settings
                "MERGE_METADATA_TITLE": "none",
                "MERGE_METADATA_AUTHOR": "none",
                "MERGE_METADATA_COMMENT": "none",
            }
        )
        # Keep the current page
        await update_buttons(message, "mediatools_merge_config")
    elif data[1] in [
        "var",
        "aria",
        "qbit",
        "nzb",
        "nzbserver",
        "mediatools",
        "mediatools_watermark",
        "mediatools_merge",
        "mediatools_merge_config",
        "mediatools_metadata",
    ] or data[1].startswith(
        "nzbser",
    ):
        if data[1] == "nzbserver":
            globals()["start"] = 0
        await query.answer()
        await update_buttons(message, data[1])
    elif data[1] == "resetvar":
        await query.answer()
        value = ""
        if data[2] in DEFAULT_VALUES:
            value = DEFAULT_VALUES[data[2]]
        elif data[2] == "EXCLUDED_EXTENSIONS":
            excluded_extensions.clear()
            excluded_extensions.extend(["aria2", "!qB"])
        elif data[2] == "TORRENT_TIMEOUT":
            await TorrentManager.change_aria2_option("bt-stop-timeout", "0")
            await database.update_aria2("bt-stop-timeout", "0")
        elif data[2] == "FFMPEG_MEMORY_LIMIT":
            value = 2048  # Default to 2GB
        elif data[2] == "FFMPEG_CPU_AFFINITY":
            value = ""  # Default to all cores
        elif data[2] == "FFMPEG_DYNAMIC_THREADS":
            value = True  # Default to enabled
        elif data[2] == "BASE_URL":
            await (
                await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")
            ).wait()
        elif data[2] == "BASE_URL_PORT":
            value = 80
            if Config.BASE_URL:
                await (
                    await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")
                ).wait()
                await create_subprocess_shell(
                    f"gunicorn -k uvicorn.workers.UvicornWorker -w 1 web.wserver:app --bind 0.0.0.0:{value}",
                )
        elif data[2] == "GDRIVE_ID":
            if drives_names and drives_names[0] == "Main":
                drives_names.pop(0)
                drives_ids.pop(0)
                index_urls.pop(0)
        elif data[2] == "INDEX_URL":
            if drives_names and drives_names[0] == "Main":
                index_urls[0] = ""
        elif data[2] == "INCOMPLETE_TASK_NOTIFIER":
            await database.trunc_table("tasks")
        elif data[2] in ["JD_EMAIL", "JD_PASS"]:
            await create_subprocess_exec("pkill", "-9", "-f", "java")
        elif data[2] == "USENET_SERVERS":
            for s in Config.USENET_SERVERS:
                await sabnzbd_client.delete_config("servers", s["name"])
        elif data[2] == "AUTHORIZED_CHATS":
            auth_chats.clear()
        elif data[2] == "SUDO_USERS":
            sudo_users.clear()
        Config.set(data[2], value)
        await update_buttons(message, "var")
        if data[2] == "DATABASE_URL":
            await database.disconnect()
        await database.update_config({data[2]: value})
        if data[2] in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
            await start_from_queued()
        elif data[2] in [
            "RCLONE_SERVE_URL",
            "RCLONE_SERVE_PORT",
            "RCLONE_SERVE_USER",
            "RCLONE_SERVE_PASS",
        ]:
            await rclone_serve_booter()
    elif data[1] == "syncaria":
        await query.answer()
        aria2_options.clear()
        await update_aria2_options()
        await update_buttons(message, "aria")
    elif data[1] == "syncqbit":
        await query.answer()
        qbit_options.clear()
        await update_qb_options()
        await database.save_qbit_settings()
    elif data[1] == "resetnzb":
        await query.answer()
        res = await sabnzbd_client.set_config_default(data[2])
        nzb_options[data[2]] = res["config"]["misc"][data[2]]
        await update_buttons(message, "nzb")
        await database.update_nzb_config()
    elif data[1] == "syncnzb":
        await query.answer(
            "Syncronization Started. It takes up to 2 sec!",
            show_alert=True,
        )
        nzb_options.clear()
        await update_nzb_options()
        await database.update_nzb_config()
    elif data[1] == "emptyaria":
        await query.answer()
        aria2_options[data[2]] = ""
        await update_buttons(message, "aria")
        await TorrentManager.change_aria2_option(data[2], "")
        await database.update_aria2(data[2], "")
    elif data[1] == "emptyqbit":
        await query.answer()
        value = ""
        if isinstance(qbit_options[data[2]], bool):
            value = False
        elif isinstance(qbit_options[data[2]], int):
            value = 0
        elif isinstance(qbit_options[data[2]], float):
            value = 0.0
        await TorrentManager.qbittorrent.app.set_preferences({data[2]: value})
        qbit_options[data[2]] = value
        await update_buttons(message, "qbit")
        await database.update_qbittorrent(data[2], value)
    elif data[1] == "emptynzb":
        await query.answer()
        res = await sabnzbd_client.set_config("misc", data[2], "")
        nzb_options[data[2]] = res["config"]["misc"][data[2]]
        await update_buttons(message, "nzb")
        await database.update_nzb_config()
    elif data[1] == "remser":
        index = int(data[2])
        await sabnzbd_client.delete_config(
            "servers",
            Config.USENET_SERVERS[index]["name"],
        )
        del Config.USENET_SERVERS[index]
        await update_buttons(message, "nzbserver")
        await database.update_config({"USENET_SERVERS": Config.USENET_SERVERS})
    elif data[1] == "private":
        await query.answer()
        await update_buttons(message, data[1])
        pfunc = partial(update_private_file, pre_message=message)
        rfunc = partial(update_buttons, message)
        await event_handler(client, query, pfunc, rfunc, True)
    elif data[1] == "botvar" and state == "edit":
        await query.answer()
        LOGGER.debug(f"Handling botvar for {data[2]} in edit mode")
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_variable, pre_message=message, key=data[2])

        # Determine which menu to return to based on the key
        if data[2].startswith("METADATA_"):
            LOGGER.debug(
                f"Setting return function for botvar {data[2]} to mediatools_metadata"
            )
            rfunc = partial(update_buttons, message, "mediatools_metadata")
        else:
            rfunc = partial(update_buttons, message, "var")

        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "botvar" and state == "view":
        value = f"{Config.get(data[2])}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        if value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "ariavar" and (state == "edit" or data[2] == "newkey"):
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_aria, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "aria")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "ariavar" and state == "view":
        value = f"{aria2_options[data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        if value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "qbitvar" and state == "edit":
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_qbit, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "qbit")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "qbitvar" and state == "view":
        value = f"{qbit_options[data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        if value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "nzbvar" and state == "edit":
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_nzb, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "nzb")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "nzbvar" and state == "view":
        value = f"{nzb_options[data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        if value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "emptyserkey":
        await query.answer()
        await update_buttons(message, f"nzbser{data[2]}")
        index = int(data[2])
        res = await sabnzbd_client.add_server(
            {"name": Config.USENET_SERVERS[index]["name"], data[3]: ""},
        )
        Config.USENET_SERVERS[index][data[3]] = res["config"]["servers"][0][data[3]]
        await database.update_config({"USENET_SERVERS": Config.USENET_SERVERS})
    elif data[1].startswith("nzbsevar") and (state == "edit" or data[2] == "newser"):
        index = 0 if data[2] == "newser" else int(data[1].replace("nzbsevar", ""))
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(
            edit_nzb_server,
            pre_message=message,
            key=data[2],
            index=index,
        )
        rfunc = partial(update_buttons, message, data[1])
        await event_handler(client, query, pfunc, rfunc)
    elif data[1].startswith("nzbsevar") and state == "view":
        index = int(data[1].replace("nzbsevar", ""))
        value = f"{Config.USENET_SERVERS[index][data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        if value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "edit":
        await query.answer()
        globals()["state"] = "edit"
        await update_buttons(message, data[2])
    elif data[1] == "view":
        await query.answer()
        globals()["state"] = "view"
        await update_buttons(message, data[2])
    elif data[1] == "start":
        await query.answer()
        if start != int(data[3]):
            globals()["start"] = int(data[3])
            await update_buttons(message, data[2])
    elif data[1] == "start_merge":
        await query.answer()
        try:
            if len(data) > 2:
                # Update the global merge_page variable
                globals()["merge_page"] = int(data[2])
                LOGGER.debug(f"Updated merge_page to {globals()['merge_page']}")
                await update_buttons(
                    message, "mediatools_merge", page=globals()["merge_page"]
                )
            else:
                # If no page number is provided, stay on the current page
                await update_buttons(
                    message, "mediatools_merge", page=globals()["merge_page"]
                )
        except (ValueError, IndexError) as e:
            # In case of any error, stay on the current page
            LOGGER.error(f"Error in start_merge handler: {e}")
            await update_buttons(
                message, "mediatools_merge", page=globals()["merge_page"]
            )
    elif data[1] == "start_merge_config":
        await query.answer()
        try:
            if len(data) > 2:
                page = int(data[2])
                await update_buttons(message, "mediatools_merge_config", page=page)
            else:
                # If no page number is provided, stay on the current page
                await update_buttons(message, "mediatools_merge_config")
        except (ValueError, IndexError):
            # In case of any error, stay on the current page
            await update_buttons(message, "mediatools_merge_config")
    # Handle redirects for mediatools callbacks
    elif data[0] == "mediatools" and len(data) >= 3 and data[2] == "merge_config":
        # This is a callback from the pagination buttons in mediatools_merge_config
        # Redirect it to the media_tools module
        from bot.modules.media_tools import media_tools_callback

        await media_tools_callback(client, query)


@new_task
async def send_bot_settings(_, message):
    user_id = message.chat.id
    handler_dict[user_id] = False
    msg, button = await get_buttons(user_id=user_id)
    globals()["start"] = 0
    await send_message(message, msg, button)


async def load_config():
    Config.load()
    drives_ids.clear()
    drives_names.clear()
    index_urls.clear()
    await update_variables()

    if not await aiopath.exists("accounts"):
        Config.USE_SERVICE_ACCOUNTS = False

    if len(task_dict) != 0 and (st := intervals["status"]):
        for key, intvl in list(st.items()):
            intvl.cancel()
            intervals["status"][key] = SetInterval(
                1,
                update_status_message,
                key,
            )

    if Config.TORRENT_TIMEOUT:
        await TorrentManager.change_aria2_option(
            "bt-stop-timeout",
            f"{Config.TORRENT_TIMEOUT}",
        )
        await database.update_aria2("bt-stop-timeout", f"{Config.TORRENT_TIMEOUT}")

    if not Config.INCOMPLETE_TASK_NOTIFIER:
        await database.trunc_table("tasks")

    await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
    if Config.BASE_URL:
        await create_subprocess_shell(
            f"gunicorn -k uvicorn.workers.UvicornWorker -w 1 web.wserver:app --bind 0.0.0.0:{Config.BASE_URL_PORT}",
        )

    if Config.DATABASE_URL:
        await database.connect()
        config_dict = Config.get_all()
        await database.update_config(config_dict)
    else:
        await database.disconnect()
    await gather(start_from_queued(), rclone_serve_booter())
    add_job()

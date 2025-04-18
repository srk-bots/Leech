import contextlib
import os
from asyncio import gather, sleep
from os import path as ospath
from os import walk
from re import IGNORECASE, sub
from secrets import token_hex
from shlex import split
from time import time

from aiofiles.os import listdir, makedirs, remove
from aiofiles.os import path as aiopath
from aioshutil import move, rmtree
from pyrogram.enums import ChatAction

from bot import (
    DOWNLOAD_DIR,
    LOGGER,
    cpu_eater_lock,
    cpu_no,
    excluded_extensions,
    intervals,
    multi_tags,
    task_dict,
    task_dict_lock,
    user_data,
)
from bot.core.aeon_client import TgClient
from bot.core.config_manager import Config
from bot.helper.aeon_utils.command_gen import (
    get_embed_thumb_cmd,
    get_metadata_cmd,
    get_watermark_cmd,
    analyze_media_for_merge,
    get_merge_concat_demuxer_cmd,
    get_merge_filter_complex_cmd,
    get_merge_mixed_cmd,
)

from .ext_utils.bot_utils import get_size_bytes, new_task, sync_to_async
from .ext_utils.bulk_links import extract_bulk_links
from .ext_utils.files_utils import (
    SevenZ,
    get_base_name,
    get_path_size,
    is_archive,
    is_archive_split,
    is_first_archive_split,
    split_file,
)
from .ext_utils.links_utils import (
    is_gdrive_id,
    is_gdrive_link,
    is_rclone_path,
    is_telegram_link,
)
from .ext_utils.media_utils import (
    FFMpeg,
    create_thumb,
    get_document_type,
    is_mkv,
    take_ss,
)
from .mirror_leech_utils.gdrive_utils.list import GoogleDriveList
from .mirror_leech_utils.rclone_utils.list import RcloneList
from .mirror_leech_utils.status_utils.ffmpeg_status import FFmpegStatus
from .mirror_leech_utils.status_utils.sevenz_status import SevenZStatus
from .telegram_helper.message_utils import (
    get_tg_link_message,
    send_message,
    send_status_message,
)


class TaskConfig:
    def __init__(self):
        self.mid = self.message.id
        self.user = self.message.from_user or self.message.sender_chat
        self.user_id = self.user.id
        self.user_dict = user_data.get(self.user_id, {})
        self.dir = f"{DOWNLOAD_DIR}{self.mid}"
        self.up_dir = ""
        self.link = ""
        self.up_dest = ""
        self.rc_flags = ""
        self.tag = ""
        self.name = ""
        self.subname = ""
        self.name_sub = ""
        self.metadata = ""
        self.metadata_title = ""
        self.metadata_author = ""
        self.metadata_comment = ""
        self.metadata_all = ""
        self.watermark = ""
        self.watermark_enabled = False
        self.watermark_position = ""
        self.watermark_size = 0
        self.watermark_color = ""
        self.watermark_font = ""
        self.watermark_priority = 0
        self.watermark_threading = False
        self.merge_enabled = False
        self.merge_priority = 0
        self.merge_threading = False
        self.concat_demuxer_enabled = False
        self.filter_complex_enabled = False
        self.merge_output_format_video = ""
        self.merge_output_format_audio = ""
        self.merge_video = False
        self.merge_audio = False
        self.merge_subtitle = False
        self.merge_all = False
        self.merge_image = False
        self.merge_pdf = False
        self.thumbnail_layout = ""
        self.folder_name = ""
        self.split_size = 0
        self.max_split_size = 0
        self.multi = 0
        self.size = 0
        self.subsize = 0
        self.proceed_count = 0
        self.is_leech = False
        self.is_jd = False
        self.is_qbit = False
        self.is_nzb = False
        self.is_clone = False
        self.is_ytdlp = False
        self.user_transmission = False
        self.hybrid_leech = False
        self.extract = False
        self.compress = False
        self.select = False
        self.seed = False
        self.compress = False
        self.extract = False
        self.join = False
        self.private_link = False
        self.stop_duplicate = False
        self.sample_video = False
        self.convert_audio = False
        self.convert_video = False
        self.screen_shots = False
        self.is_cancelled = False
        self.force_run = False
        self.force_download = False
        self.force_upload = False
        self.is_torrent = False
        self.as_med = False
        self.as_doc = False
        self.is_file = False
        self.bot_trans = False
        self.user_trans = False
        self.progress = True
        self.ffmpeg_cmds = None
        self.chat_thread_id = None
        self.subproc = None
        self.thumb = None
        self.excluded_extensions = []
        self.files_to_proceed = []
        self.is_super_chat = self.message.chat.type.name in ["SUPERGROUP", "CHANNEL"]

    def get_token_path(self, dest):
        if dest.startswith("mtp:"):
            return f"tokens/{self.user_id}.pickle"
        if dest.startswith("sa:") or (
            Config.USE_SERVICE_ACCOUNTS and not dest.startswith("tp:")
        ):
            return "accounts"
        return "token.pickle"

    def get_config_path(self, dest):
        return (
            f"rclone/{self.user_id}.conf" if dest.startswith("mrcc:") else "rclone.conf"
        )

    async def is_token_exists(self, path, status):
        if is_rclone_path(path):
            config_path = self.get_config_path(path)
            if config_path != "rclone.conf" and status == "up":
                self.private_link = True
            if not await aiopath.exists(config_path):
                raise ValueError(f"Rclone Config: {config_path} not Exists!")
        elif (status == "dl" and is_gdrive_link(path)) or (
            status == "up" and is_gdrive_id(path)
        ):
            token_path = self.get_token_path(path)
            if token_path.startswith("tokens/") and status == "up":
                self.private_link = True
            if not await aiopath.exists(token_path):
                raise ValueError(f"NO TOKEN! {token_path} not Exists!")

    async def before_start(self):
        self.name_sub = (
            self.name_sub
            or self.user_dict.get("NAME_SUBSTITUTE", False)
            or (
                Config.NAME_SUBSTITUTE
                if "NAME_SUBSTITUTE" not in self.user_dict
                else ""
            )
        )
        # Get metadata settings with priority
        # Command line arguments take highest priority
        self.metadata = (
            self.metadata
            or self.user_dict.get("METADATA_KEY", False)
            or (Config.METADATA_KEY if "METADATA_KEY" not in self.user_dict else "")
        )

        # Get enhanced metadata settings with priority: command line > user settings > owner settings
        # Command line arguments take highest priority
        self.metadata_all = (
            self.metadata_all
            or self.user_dict.get("METADATA_ALL", False)
            or (Config.METADATA_ALL if "METADATA_ALL" not in self.user_dict else "")
        )

        self.metadata_title = (
            self.metadata_title
            or self.user_dict.get("METADATA_TITLE", False)
            or (Config.METADATA_TITLE if "METADATA_TITLE" not in self.user_dict else "")
        )

        self.metadata_author = (
            self.metadata_author
            or self.user_dict.get("METADATA_AUTHOR", False)
            or (
                Config.METADATA_AUTHOR
                if "METADATA_AUTHOR" not in self.user_dict
                else ""
            )
        )

        self.metadata_comment = (
            self.metadata_comment
            or self.user_dict.get("METADATA_COMMENT", False)
            or (
                Config.METADATA_COMMENT
                if "METADATA_COMMENT" not in self.user_dict
                else ""
            )
        )
        # Initialize media tools settings with the correct priority
        # First check if user has enabled watermark
        user_watermark_enabled = self.user_dict.get("WATERMARK_ENABLED", False)

        # Check if owner has enabled watermark
        owner_watermark_enabled = Config.WATERMARK_ENABLED

        # Set watermark_enabled based on the following priority:
        # Global (enabled) & User (disabled) -> Apply global
        # User (enabled) & Global (disabled) -> Apply user
        # Global (enabled) & User (enabled) -> Apply user
        # Global (disabled) & User (disabled) -> Don't apply

        if "WATERMARK_ENABLED" in self.user_dict:
            # User has explicitly set watermark enabled/disabled
            if user_watermark_enabled:
                # User has enabled watermark - apply user settings
                self.watermark_enabled = True
                LOGGER.debug("Watermark enabled by user settings")
            else:
                # User has disabled watermark - check owner settings
                self.watermark_enabled = owner_watermark_enabled
                if self.watermark_enabled:
                    LOGGER.debug("Watermark enabled by owner settings (user disabled)")
                else:
                    LOGGER.debug("Watermark disabled (both user and owner disabled)")
        else:
            # User hasn't set watermark enabled/disabled - use owner settings
            self.watermark_enabled = owner_watermark_enabled
            if self.watermark_enabled:
                LOGGER.debug("Watermark enabled by owner settings (user not set)")
            else:
                LOGGER.debug("Watermark disabled (owner disabled, user not set)")

        # Initialize merge settings with the same priority logic
        user_merge_enabled = self.user_dict.get("MERGE_ENABLED", False)
        owner_merge_enabled = Config.MERGE_ENABLED

        if "MERGE_ENABLED" in self.user_dict:
            if user_merge_enabled:
                self.merge_enabled = True
                LOGGER.debug("Merge enabled by user settings")
            else:
                self.merge_enabled = owner_merge_enabled
                if self.merge_enabled:
                    LOGGER.debug("Merge enabled by owner settings (user disabled)")
                else:
                    LOGGER.debug("Merge disabled (both user and owner disabled)")
        else:
            self.merge_enabled = owner_merge_enabled
            if self.merge_enabled:
                LOGGER.debug("Merge enabled by owner settings (user not set)")
            else:
                LOGGER.debug("Merge disabled (owner disabled, user not set)")

        # Watermark enabled status has been logged in the priority logic above

        # Initialize watermark text based on the following priority:
        # 1. If watermark_text is provided via command line (-watermark flag), use that
        # 2. If user has explicitly enabled watermark and set text, use that
        # 3. If user has enabled watermark but not set text, or owner has enabled watermark, use owner's text
        # 4. Otherwise, use empty string

        # Check if watermark_text is provided via command line
        if hasattr(self, "watermark_text") and self.watermark_text:
            # Command line watermark text takes highest priority
            self.watermark = self.watermark_text
            # Force enable watermark when text is provided via command
            self.watermark_enabled = True
            LOGGER.debug(f"Using command line watermark text: {self.watermark}")
        elif (
            user_watermark_enabled
            and "WATERMARK_KEY" in self.user_dict
            and self.user_dict["WATERMARK_KEY"]
        ):
            # User has enabled watermark and set text - use user's text
            self.watermark = self.user_dict["WATERMARK_KEY"]
            LOGGER.debug(f"Using user's watermark text: {self.watermark}")
        elif self.watermark_enabled and Config.WATERMARK_KEY:
            # Either user has enabled watermark but not set text, or owner has enabled watermark
            # Use owner's text
            self.watermark = Config.WATERMARK_KEY
            LOGGER.debug(f"Using owner's watermark text: {self.watermark}")
        else:
            # Default case: no watermark text
            self.watermark = ""
            if self.watermark_enabled:
                LOGGER.debug(
                    "No watermark text available, watermark will not be applied"
                )

        # Initialize other watermark settings with the same priority logic
        # Position
        if (
            user_watermark_enabled
            and "WATERMARK_POSITION" in self.user_dict
            and self.user_dict["WATERMARK_POSITION"]
        ):
            # User has enabled watermark and set position - use user's position
            self.watermark_position = self.user_dict["WATERMARK_POSITION"]
        elif self.watermark_enabled and Config.WATERMARK_POSITION:
            # Either user has enabled watermark but not set position, or owner has enabled watermark
            # Use owner's position if available
            self.watermark_position = Config.WATERMARK_POSITION
        else:
            # Default position
            self.watermark_position = "top_left"

        # Size
        if (
            user_watermark_enabled
            and "WATERMARK_SIZE" in self.user_dict
            and self.user_dict["WATERMARK_SIZE"]
        ):
            # User has enabled watermark and set size - use user's size
            self.watermark_size = self.user_dict["WATERMARK_SIZE"]
        elif self.watermark_enabled and Config.WATERMARK_SIZE:
            # Either user has enabled watermark but not set size, or owner has enabled watermark
            # Use owner's size if available
            self.watermark_size = Config.WATERMARK_SIZE
        else:
            # Default size
            self.watermark_size = 20

        # Color
        if (
            user_watermark_enabled
            and "WATERMARK_COLOR" in self.user_dict
            and self.user_dict["WATERMARK_COLOR"]
        ):
            # User has enabled watermark and set color - use user's color
            self.watermark_color = self.user_dict["WATERMARK_COLOR"]
        elif self.watermark_enabled and Config.WATERMARK_COLOR:
            # Either user has enabled watermark but not set color, or owner has enabled watermark
            # Use owner's color if available
            self.watermark_color = Config.WATERMARK_COLOR
        else:
            # Default color
            self.watermark_color = "white"

        # Font
        if (
            user_watermark_enabled
            and "WATERMARK_FONT" in self.user_dict
            and self.user_dict["WATERMARK_FONT"]
        ):
            # User has enabled watermark and set font - use user's font
            self.watermark_font = self.user_dict["WATERMARK_FONT"]
        elif self.watermark_enabled and Config.WATERMARK_FONT:
            # Either user has enabled watermark but not set font, or owner has enabled watermark
            # Use owner's font if available
            self.watermark_font = Config.WATERMARK_FONT
        else:
            # Default font
            self.watermark_font = "default.otf"

        # Watermark Priority
        if (
            user_watermark_enabled
            and "WATERMARK_PRIORITY" in self.user_dict
            and self.user_dict["WATERMARK_PRIORITY"]
        ):
            self.watermark_priority = self.user_dict["WATERMARK_PRIORITY"]
        elif self.watermark_enabled and Config.WATERMARK_PRIORITY:
            self.watermark_priority = Config.WATERMARK_PRIORITY
        else:
            self.watermark_priority = 2

        # Watermark Threading
        if user_watermark_enabled and "WATERMARK_THREADING" in self.user_dict:
            self.watermark_threading = self.user_dict["WATERMARK_THREADING"]
        elif self.watermark_enabled and Config.WATERMARK_THREADING:
            self.watermark_threading = Config.WATERMARK_THREADING
        else:
            self.watermark_threading = True

        # Initialize merge settings with the same priority logic
        # Concat Demuxer
        if user_merge_enabled and "CONCAT_DEMUXER_ENABLED" in self.user_dict:
            self.concat_demuxer_enabled = self.user_dict["CONCAT_DEMUXER_ENABLED"]
        elif self.merge_enabled and Config.CONCAT_DEMUXER_ENABLED:
            self.concat_demuxer_enabled = Config.CONCAT_DEMUXER_ENABLED
        else:
            self.concat_demuxer_enabled = True

        # Filter Complex
        if user_merge_enabled and "FILTER_COMPLEX_ENABLED" in self.user_dict:
            self.filter_complex_enabled = self.user_dict["FILTER_COMPLEX_ENABLED"]
        elif self.merge_enabled and Config.FILTER_COMPLEX_ENABLED:
            self.filter_complex_enabled = Config.FILTER_COMPLEX_ENABLED
        else:
            self.filter_complex_enabled = False

        # Merge Output Format Video
        if (
            user_merge_enabled
            and "MERGE_OUTPUT_FORMAT_VIDEO" in self.user_dict
            and self.user_dict["MERGE_OUTPUT_FORMAT_VIDEO"]
        ):
            self.merge_output_format_video = self.user_dict["MERGE_OUTPUT_FORMAT_VIDEO"]
        elif self.merge_enabled and Config.MERGE_OUTPUT_FORMAT_VIDEO:
            self.merge_output_format_video = Config.MERGE_OUTPUT_FORMAT_VIDEO
        else:
            self.merge_output_format_video = "mkv"

        # Merge Output Format Audio
        if (
            user_merge_enabled
            and "MERGE_OUTPUT_FORMAT_AUDIO" in self.user_dict
            and self.user_dict["MERGE_OUTPUT_FORMAT_AUDIO"]
        ):
            self.merge_output_format_audio = self.user_dict["MERGE_OUTPUT_FORMAT_AUDIO"]
        elif self.merge_enabled and Config.MERGE_OUTPUT_FORMAT_AUDIO:
            self.merge_output_format_audio = Config.MERGE_OUTPUT_FORMAT_AUDIO
        else:
            self.merge_output_format_audio = "mp3"

        # Merge Priority
        if (
            user_merge_enabled
            and "MERGE_PRIORITY" in self.user_dict
            and self.user_dict["MERGE_PRIORITY"]
        ):
            self.merge_priority = self.user_dict["MERGE_PRIORITY"]
        elif self.merge_enabled and Config.MERGE_PRIORITY:
            self.merge_priority = Config.MERGE_PRIORITY
        else:
            self.merge_priority = 1

        # Merge Threading
        if user_merge_enabled and "MERGE_THREADING" in self.user_dict:
            self.merge_threading = self.user_dict["MERGE_THREADING"]
        elif self.merge_enabled and Config.MERGE_THREADING:
            self.merge_threading = Config.MERGE_THREADING
        else:
            self.merge_threading = True
        if self.name_sub:
            self.name_sub = [x.split("/") for x in self.name_sub.split(" | ")]
        self.excluded_extensions = self.user_dict.get("EXCLUDED_EXTENSIONS") or (
            excluded_extensions
            if "EXCLUDED_EXTENSIONS" not in self.user_dict
            else ["aria2", "!qB"]
        )
        if not self.rc_flags:
            if self.user_dict.get("RCLONE_FLAGS"):
                self.rc_flags = self.user_dict["RCLONE_FLAGS"]
            elif "RCLONE_FLAGS" not in self.user_dict and Config.RCLONE_FLAGS:
                self.rc_flags = Config.RCLONE_FLAGS
        if self.link not in ["rcl", "gdl"]:
            if not self.is_jd:
                if is_rclone_path(self.link):
                    if not self.link.startswith("mrcc:") and self.user_dict.get(
                        "USER_TOKENS",
                        False,
                    ):
                        self.link = f"mrcc:{self.link}"
                    await self.is_token_exists(self.link, "dl")
            elif is_gdrive_link(self.link):
                if not self.link.startswith(
                    ("mtp:", "tp:", "sa:"),
                ) and self.user_dict.get("USER_TOKENS", False):
                    self.link = f"mtp:{self.link}"
                await self.is_token_exists(self.link, "dl")
        elif self.link == "rcl":
            if not self.is_ytdlp and not self.is_jd:
                self.link = await RcloneList(self).get_rclone_path("rcd")
                if not is_rclone_path(self.link):
                    raise ValueError(self.link)
        elif self.link == "gdl" and not self.is_ytdlp and not self.is_jd:
            self.link = await GoogleDriveList(self).get_target_id("gdd")
            if not is_gdrive_id(self.link):
                raise ValueError(self.link)

        self.user_transmission = TgClient.IS_PREMIUM_USER and (
            self.user_dict.get("USER_TRANSMISSION")
            or (Config.USER_TRANSMISSION and "USER_TRANSMISSION" not in self.user_dict)
        )

        if self.user_dict.get("UPLOAD_PATHS", False):
            if self.up_dest in self.user_dict["UPLOAD_PATHS"]:
                self.up_dest = self.user_dict["UPLOAD_PATHS"][self.up_dest]
        elif (
            "UPLOAD_PATHS" not in self.user_dict
            and Config.UPLOAD_PATHS
            and self.up_dest in Config.UPLOAD_PATHS
        ):
            self.up_dest = Config.UPLOAD_PATHS[self.up_dest]

        if self.ffmpeg_cmds and not isinstance(self.ffmpeg_cmds, list):
            if self.user_dict.get("FFMPEG_CMDS", None):
                ffmpeg_dict = self.user_dict["FFMPEG_CMDS"]
                self.ffmpeg_cmds = [
                    value
                    for key in list(self.ffmpeg_cmds)
                    if key in ffmpeg_dict
                    for value in ffmpeg_dict[key]
                ]
            elif "FFMPEG_CMDS" not in self.user_dict and Config.FFMPEG_CMDS:
                ffmpeg_dict = Config.FFMPEG_CMDS
                self.ffmpeg_cmds = [
                    value
                    for key in list(self.ffmpeg_cmds)
                    if key in ffmpeg_dict
                    for value in ffmpeg_dict[key]
                ]
            else:
                self.ffmpeg_cmds = None
        if not self.is_leech:
            self.stop_duplicate = self.user_dict.get("STOP_DUPLICATE") or (
                "STOP_DUPLICATE" not in self.user_dict and Config.STOP_DUPLICATE
            )
            default_upload = (
                self.user_dict.get("DEFAULT_UPLOAD", "") or Config.DEFAULT_UPLOAD
            )
            if (not self.up_dest and default_upload == "rc") or self.up_dest == "rc":
                self.up_dest = self.user_dict.get("RCLONE_PATH") or Config.RCLONE_PATH
            elif (not self.up_dest and default_upload == "gd") or self.up_dest == "gd":
                self.up_dest = self.user_dict.get("GDRIVE_ID") or Config.GDRIVE_ID
            if not self.up_dest:
                raise ValueError("No Upload Destination!")
            if is_gdrive_id(self.up_dest):
                if not self.up_dest.startswith(
                    ("mtp:", "tp:", "sa:"),
                ) and self.user_dict.get("USER_TOKENS", False):
                    self.up_dest = f"mtp:{self.up_dest}"
            elif is_rclone_path(self.up_dest):
                if not self.up_dest.startswith("mrcc:") and self.user_dict.get(
                    "USER_TOKENS",
                    False,
                ):
                    self.up_dest = f"mrcc:{self.up_dest}"
                self.up_dest = self.up_dest.strip("/")
            else:
                raise ValueError("Wrong Upload Destination!")

            if self.up_dest not in ["rcl", "gdl"]:
                await self.is_token_exists(self.up_dest, "up")

            if self.up_dest == "rcl":
                if self.is_clone:
                    if not is_rclone_path(self.link):
                        raise ValueError(
                            "You can't clone from different types of tools",
                        )
                    config_path = self.get_config_path(self.link)
                else:
                    config_path = None
                self.up_dest = await RcloneList(self).get_rclone_path(
                    "rcu",
                    config_path,
                )
                if not is_rclone_path(self.up_dest):
                    raise ValueError(self.up_dest)
            elif self.up_dest == "gdl":
                if self.is_clone:
                    if not is_gdrive_link(self.link):
                        raise ValueError(
                            "You can't clone from different types of tools",
                        )
                    token_path = self.get_token_path(self.link)
                else:
                    token_path = None
                self.up_dest = await GoogleDriveList(self).get_target_id(
                    "gdu",
                    token_path,
                )
                if not is_gdrive_id(self.up_dest):
                    raise ValueError(self.up_dest)
            elif self.is_clone:
                if is_gdrive_link(self.link) and self.get_token_path(
                    self.link,
                ) != self.get_token_path(self.up_dest):
                    raise ValueError("You must use the same token to clone!")
                if is_rclone_path(self.link) and self.get_config_path(
                    self.link,
                ) != self.get_config_path(self.up_dest):
                    raise ValueError("You must use the same config to clone!")
        else:
            self.up_dest = (
                self.up_dest
                or self.user_dict.get("LEECH_DUMP_CHAT")
                or Config.LEECH_DUMP_CHAT
            )
            self.hybrid_leech = TgClient.IS_PREMIUM_USER and (
                self.user_dict.get("HYBRID_LEECH")
                or (Config.HYBRID_LEECH and "HYBRID_LEECH" not in self.user_dict)
            )
            if self.bot_trans:
                self.user_transmission = False
                self.hybrid_leech = False
            if self.user_trans:
                self.user_transmission = TgClient.IS_PREMIUM_USER
            if self.up_dest:
                if not isinstance(self.up_dest, int):
                    if self.up_dest.startswith("b:"):
                        self.up_dest = self.up_dest.replace("b:", "", 1)
                        self.user_transmission = False
                        self.hybrid_leech = False
                    elif self.up_dest.startswith("u:"):
                        self.up_dest = self.up_dest.replace("u:", "", 1)
                        self.user_transmission = TgClient.IS_PREMIUM_USER
                    elif self.up_dest.startswith("h:"):
                        self.up_dest = self.up_dest.replace("h:", "", 1)
                        self.user_transmission = TgClient.IS_PREMIUM_USER
                        self.hybrid_leech = self.user_transmission
                    if "|" in self.up_dest:
                        self.up_dest, self.chat_thread_id = [
                            int(x) if x.lstrip("-").isdigit() else x
                            for x in self.up_dest.split("|", 1)
                        ]
                    elif self.up_dest.lstrip("-").isdigit():
                        self.up_dest = int(self.up_dest)
                    elif self.up_dest.lower() == "pm":
                        self.up_dest = self.user_id

                if self.user_transmission:
                    try:
                        chat = await TgClient.user.get_chat(self.up_dest)
                    except Exception:
                        chat = None
                    if chat is None:
                        self.user_transmission = False
                        self.hybrid_leech = False
                    else:
                        uploader_id = TgClient.user.me.id
                        if chat.type.name not in ["SUPERGROUP", "CHANNEL", "GROUP"]:
                            self.user_transmission = False
                            self.hybrid_leech = False
                        else:
                            member = await chat.get_member(uploader_id)
                            if (
                                not member.privileges.can_manage_chat
                                or not member.privileges.can_delete_messages
                            ):
                                self.user_transmission = False
                                self.hybrid_leech = False

                if not self.user_transmission or self.hybrid_leech:
                    try:
                        chat = await self.client.get_chat(self.up_dest)
                    except Exception:
                        chat = None
                    if chat is None:
                        if self.user_transmission:
                            self.hybrid_leech = False
                        else:
                            raise ValueError("Chat not found!")
                    else:
                        uploader_id = self.client.me.id
                        if chat.type.name in ["SUPERGROUP", "CHANNEL", "GROUP"]:
                            member = await chat.get_member(uploader_id)
                            if (
                                not member.privileges.can_manage_chat
                                or not member.privileges.can_delete_messages
                            ):
                                if not self.user_transmission:
                                    raise ValueError(
                                        "You don't have enough privileges in this chat!",
                                    )
                                self.hybrid_leech = False
                        else:
                            try:
                                await self.client.send_chat_action(
                                    self.up_dest,
                                    ChatAction.TYPING,
                                )
                            except Exception:
                                raise ValueError(
                                    "Start the bot and try again!",
                                ) from None
            elif (
                self.user_transmission or self.hybrid_leech
            ) and not self.is_super_chat:
                self.user_transmission = False
                self.hybrid_leech = False
            if self.split_size:
                if self.split_size.isdigit():
                    self.split_size = int(self.split_size)
                else:
                    self.split_size = get_size_bytes(self.split_size)
            self.split_size = (
                self.split_size
                or self.user_dict.get("LEECH_SPLIT_SIZE")
                or Config.LEECH_SPLIT_SIZE
            )
            self.max_split_size = (
                TgClient.MAX_SPLIT_SIZE if self.user_transmission else 2097152000
            )
            self.split_size = min(self.split_size, self.max_split_size)

            if not self.as_doc:
                self.as_doc = (
                    not self.as_med
                    if self.as_med
                    else (
                        self.user_dict.get("AS_DOCUMENT", False)
                        or (Config.AS_DOCUMENT and "AS_DOCUMENT" not in self.user_dict)
                    )
                )

            self.thumbnail_layout = (
                self.thumbnail_layout
                or self.user_dict.get("THUMBNAIL_LAYOUT", False)
                or (
                    Config.THUMBNAIL_LAYOUT
                    if "THUMBNAIL_LAYOUT" not in self.user_dict
                    else ""
                )
            )

            if self.thumb != "none" and is_telegram_link(self.thumb):
                msg, _ = (await get_tg_link_message(self.thumb))[0]
                self.thumb = (
                    await create_thumb(msg) if msg.photo or msg.document else ""
                )

    async def get_tag(self, text: list):
        if len(text) > 1 and text[1].startswith("Tag: "):
            user_info = text[1].split("Tag: ")
            if len(user_info) >= 3:
                id_ = user_info[-1]
                self.tag = " ".join(user_info[:-1])
            else:
                self.tag, id_ = text[1].split("Tag: ")[1].split()
            self.user = self.message.from_user = await self.client.get_users(id_)
            self.user_id = self.user.id
            self.user_dict = user_data.get(self.user_id, {})
            with contextlib.suppress(Exception):
                await self.message.unpin()
        if self.user:
            if username := self.user.username:
                self.tag = f"@{username}"
            elif hasattr(self.user, "mention"):
                self.tag = self.user.mention
            else:
                self.tag = self.user.title

    @new_task
    async def run_multi(self, input_list, obj):
        await sleep(7)
        if not self.multi_tag and self.multi > 1:
            self.multi_tag = token_hex(2)
            multi_tags.add(self.multi_tag)
        elif self.multi <= 1:
            if self.multi_tag in multi_tags:
                multi_tags.discard(self.multi_tag)
            return
        if self.multi_tag and self.multi_tag not in multi_tags:
            await send_message(
                self.message,
                f"{self.tag} Multi Task has been cancelled!",
            )
            await send_status_message(self.message)
            async with task_dict_lock:
                for fd_name in self.same_dir:
                    self.same_dir[fd_name]["total"] -= self.multi
            return
        if len(self.bulk) != 0:
            msg = input_list[:1]
            msg.append(f"{self.bulk[0]} -i {self.multi - 1} {self.options}")
            msgts = " ".join(msg)
            if self.multi > 2:
                msgts += f"\nCancel Multi: <code>/stop {self.multi_tag}</code>"
            nextmsg = await send_message(self.message, msgts)
        else:
            msg = [s.strip() for s in input_list]
            index = msg.index("-i")
            msg[index + 1] = f"{self.multi - 1}"
            nextmsg = await self.client.get_messages(
                chat_id=self.message.chat.id,
                message_ids=self.message.reply_to_message_id + 1,
            )
            msgts = " ".join(msg)
            if self.multi > 2:
                msgts += f"\nCancel Multi: <code>/stop {self.multi_tag}</code>"
            nextmsg = await send_message(nextmsg, msgts)
        # Check if nextmsg is a Message object or a string
        if isinstance(nextmsg, str):
            LOGGER.warning(f"nextmsg is a string, not a Message object: {nextmsg}")
            # Try to find the message by content instead
            # Electrogram doesn't support 'limit' parameter for get_messages
            # Instead, use get_chat_history which supports limit
            try:
                messages = await self.client.get_chat_history(
                    chat_id=self.message.chat.id,
                    limit=5,  # Look at the last few messages
                )
            except Exception as e:
                LOGGER.error(f"Error getting chat history: {e}")
                messages = []
            for msg in messages:
                if msg and msg.text and msg.text == nextmsg:
                    nextmsg = msg
                    break
            # If we still couldn't find it, create a new message
            if isinstance(nextmsg, str):
                nextmsg = await send_message(self.message.chat.id, nextmsg)
        else:
            # Normal case - nextmsg is a Message object
            try:
                # Get the message by its ID
                try:
                    nextmsg = await self.client.get_messages(
                        chat_id=self.message.chat.id,
                        message_ids=nextmsg.id,
                    )
                except TypeError as e:
                    # Handle case where get_messages has different parameters in Electrogram
                    if "unexpected keyword argument" in str(e):
                        LOGGER.debug(f"Adapting to Electrogram API: {e}")
                        # Try alternative approach for Electrogram
                        nextmsg = await self.client.get_messages(
                            self.message.chat.id,  # chat_id as positional argument
                            nextmsg.id,  # message_ids as positional argument
                        )
                    else:
                        raise
            except Exception as e:
                LOGGER.error(f"Error getting message: {e}")
                # Create a new message if we can't get the original
                if hasattr(nextmsg, "text") and nextmsg.text:
                    nextmsg = await send_message(self.message.chat.id, nextmsg.text)
                else:
                    # If all else fails, create a generic message
                    nextmsg = await send_message(
                        self.message.chat.id,
                        "Processing your request...",
                    )
        if self.message.from_user:
            nextmsg.from_user = self.user
        else:
            nextmsg.sender_chat = self.user
        if intervals["stopAll"]:
            return
        await obj(
            self.client,
            nextmsg,
            self.is_qbit,
            self.is_leech,
            self.is_jd,
            self.is_nzb,
            self.same_dir,
            self.bulk,
            self.multi_tag,
            self.options,
        ).new_event()

    async def init_bulk(self, input_list, bulk_start, bulk_end, obj):
        try:
            self.bulk = await extract_bulk_links(self.message, bulk_start, bulk_end)
            if len(self.bulk) == 0:
                raise ValueError("Bulk Empty!")
            b_msg = input_list[:1]
            self.options = input_list[1:]
            index = self.options.index("-b")
            del self.options[index]
            if bulk_start or bulk_end:
                del self.options[index + 1]
            self.options = " ".join(self.options)
            b_msg.append(f"{self.bulk[0]} -i {len(self.bulk)} {self.options}")
            msg = " ".join(b_msg)
            if len(self.bulk) > 2:
                self.multi_tag = token_hex(2)
                multi_tags.add(self.multi_tag)
                msg += f"\nCancel Multi: <code>/stop {self.multi_tag}</code>"
            nextmsg = await send_message(self.message, msg)
            # Get the message by its ID with Electrogram compatibility
            try:
                nextmsg = await self.client.get_messages(
                    chat_id=self.message.chat.id,
                    message_ids=nextmsg.id,
                )
            except TypeError as e:
                # Handle case where get_messages has different parameters in Electrogram
                if "unexpected keyword argument" in str(e):
                    LOGGER.debug(f"Adapting to Electrogram API: {e}")
                    # Try alternative approach for Electrogram
                    nextmsg = await self.client.get_messages(
                        self.message.chat.id,  # chat_id as positional argument
                        nextmsg.id,  # message_ids as positional argument
                    )
                else:
                    raise
            if self.message.from_user:
                nextmsg.from_user = self.user
            else:
                nextmsg.sender_chat = self.user
            await obj(
                self.client,
                nextmsg,
                self.is_qbit,
                self.is_leech,
                self.is_jd,
                self.is_nzb,
                self.same_dir,
                self.bulk,
                self.multi_tag,
                self.options,
            ).new_event()
        except Exception:
            await send_message(
                self.message,
                "Reply to text file or to telegram message that have links seperated by new line!",
            )

    async def proceed_extract(self, dl_path, gid):
        pswd = self.extract if isinstance(self.extract, str) else ""
        self.files_to_proceed = []
        if self.is_file and is_archive(dl_path):
            self.files_to_proceed.append(dl_path)
        else:
            for dirpath, _, files in await sync_to_async(
                walk,
                dl_path,
                topdown=False,
            ):
                for file_ in files:
                    if is_first_archive_split(file_) or (
                        is_archive(file_) and not file_.strip().lower().endswith(".rar")
                    ):
                        f_path = ospath.join(dirpath, file_)
                        self.files_to_proceed.append(f_path)

        if not self.files_to_proceed:
            return dl_path
        sevenz = SevenZ(self)
        LOGGER.info(f"Extracting: {self.name}")
        async with task_dict_lock:
            task_dict[self.mid] = SevenZStatus(self, sevenz, gid, "Extract")
        for dirpath, _, files in await sync_to_async(
            walk,
            self.up_dir or self.dir,
            topdown=False,
        ):
            for file_ in files:
                if self.is_cancelled:
                    return False
                if is_first_archive_split(file_) or (
                    is_archive(file_) and not file_.strip().lower().endswith(".rar")
                ):
                    self.proceed_count += 1
                    f_path = ospath.join(dirpath, file_)
                    t_path = get_base_name(f_path) if self.is_file else dirpath
                    if not self.is_file:
                        self.subname = file_
                    code = await sevenz.extract(f_path, t_path, pswd)
                else:
                    code = 0
            if self.is_cancelled:
                return code
            if code == 0:
                for file_ in files:
                    if is_archive_split(file_) or is_archive(file_):
                        del_path = ospath.join(dirpath, file_)
                        try:
                            await remove(del_path)
                        except Exception:
                            self.is_cancelled = True
        return t_path if self.is_file and code == 0 else dl_path

    async def proceed_ffmpeg(self, dl_path, gid):
        checked = False
        cmds = []

        # Process each FFmpeg command with error handling for unclosed quotations
        for item in self.ffmpeg_cmds:
            try:
                # Try to split the command using shlex.split
                parts = [part.strip() for part in split(item) if part.strip()]
                cmds.append(parts)
            except ValueError as e:
                # Handle the "No closing quotation" error
                if "No closing quotation" in str(e):
                    # Fix the command by adding the missing quotation mark
                    fixed_item = item
                    if item.count('"') % 2 != 0:  # Odd number of double quotes
                        fixed_item = item + '"'
                    elif item.count("'") % 2 != 0:  # Odd number of single quotes
                        fixed_item = item + "'"

                    try:
                        # Try again with the fixed command
                        parts = [
                            part.strip() for part in split(fixed_item) if part.strip()
                        ]
                        cmds.append(parts)
                        LOGGER.debug(
                            f"Fixed unclosed quotation in FFmpeg command: {item} -> {fixed_item}"
                        )
                    except ValueError:
                        # If still failing, use a simple space-based split as fallback
                        LOGGER.debug(
                            f"Using fallback split for FFmpeg command with quotation error: {item}"
                        )
                        parts = [part for part in item.split() if part]
                        cmds.append(parts)
                else:
                    # For other ValueError exceptions, use simple split
                    LOGGER.debug(
                        f"Error parsing FFmpeg command: {e}. Using fallback split."
                    )
                    parts = [part for part in item.split() if part]
                    cmds.append(parts)
        try:
            ffmpeg = FFMpeg(self)
            for ffmpeg_cmd in cmds:
                self.proceed_count = 0
                from bot.helper.ext_utils.resource_manager import apply_resource_limits

                # Create the base command
                cmd = [
                    "xtra",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-progress",
                    "pipe:1",
                    "-threads",
                    f"{max(1, cpu_no // 2)}",  # Default thread count, will be replaced by resource manager if needed
                    *ffmpeg_cmd,
                ]

                # Generate a unique process ID for tracking
                process_id = f"ffmpeg_custom_{self.mid}_{time()}"

                # Apply resource limits to the command
                cmd = await apply_resource_limits(cmd, process_id, "Custom FFmpeg")
                if "-del" in cmd:
                    cmd.remove("-del")
                    delete_files = True
                else:
                    delete_files = False
                index = cmd.index("-i")
                input_file = cmd[index + 1]
                if input_file.lower().endswith(".video"):
                    ext = "video"
                elif input_file.lower().endswith(".audio"):
                    ext = "audio"
                elif "." not in input_file:
                    ext = "all"
                else:
                    ext = ospath.splitext(input_file)[-1].lower()
                if await aiopath.isfile(dl_path):
                    is_video, is_audio, _ = await get_document_type(dl_path)
                    if (not is_video and not is_audio) or (is_video and ext == "audio"):
                        break
                    if (is_audio and not is_video and ext == "video") or (
                        ext
                        not in [
                            "all",
                            "audio",
                            "video",
                        ]
                        and not dl_path.strip().lower().endswith(ext)
                    ):
                        break
                    new_folder = ospath.splitext(dl_path)[0]
                    name = ospath.basename(dl_path)
                    try:
                        await makedirs(new_folder, exist_ok=True)
                        file_path = f"{new_folder}/{name}"
                        await move(dl_path, file_path)
                    except FileExistsError:
                        LOGGER.warning(f"Folder already exists: {new_folder}")
                        # Try with a different folder name using timestamp
                        new_folder = f"{ospath.splitext(dl_path)[0]}_{int(time())}"
                        await makedirs(new_folder, exist_ok=True)
                        file_path = f"{new_folder}/{name}"
                        await move(dl_path, file_path)
                    if not checked:
                        checked = True
                        async with task_dict_lock:
                            task_dict[self.mid] = FFmpegStatus(
                                self,
                                ffmpeg,
                                gid,
                                "FFmpeg",
                            )
                        self.progress = False
                        await cpu_eater_lock.acquire()
                        self.progress = True
                    LOGGER.info(f"Running ffmpeg cmd for: {file_path}")
                    cmd[index + 1] = file_path
                    self.subsize = self.size
                    # Execute the command
                    res = await ffmpeg.ffmpeg_cmds(cmd, file_path)

                    # Clean up process tracking
                    from bot.helper.ext_utils.resource_manager import cleanup_process

                    cleanup_process(process_id)

                    if res:
                        if delete_files:
                            await remove(file_path)
                            if len(await listdir(new_folder)) == 1:
                                folder = new_folder.rsplit("/", 1)[0]
                                self.name = ospath.basename(res[0])
                                if self.name.startswith("ffmpeg"):
                                    self.name = self.name.split(".", 1)[-1]
                                dl_path = ospath.join(folder, self.name)
                                await move(res[0], dl_path)
                                await rmtree(new_folder)
                            else:
                                dl_path = new_folder
                                self.name = new_folder.rsplit("/", 1)[-1]
                        else:
                            dl_path = new_folder
                            self.name = new_folder.rsplit("/", 1)[-1]
                    else:
                        await move(file_path, dl_path)
                        await rmtree(new_folder)
                else:
                    for dirpath, _, files in await sync_to_async(
                        walk,
                        dl_path,
                        topdown=False,
                    ):
                        for file_ in files:
                            var_cmd = cmd.copy()
                            if self.is_cancelled:
                                return False
                            f_path = ospath.join(dirpath, file_)
                            is_video, is_audio, _ = await get_document_type(f_path)
                            if (not is_video and not is_audio) or (
                                is_video and ext == "audio"
                            ):
                                continue
                            if (is_audio and not is_video and ext == "video") or (
                                ext
                                not in [
                                    "all",
                                    "audio",
                                    "video",
                                ]
                                and not f_path.strip().lower().endswith(ext)
                            ):
                                continue
                            self.proceed_count += 1
                            var_cmd[index + 1] = f_path
                            if not checked:
                                checked = True
                                async with task_dict_lock:
                                    task_dict[self.mid] = FFmpegStatus(
                                        self,
                                        ffmpeg,
                                        gid,
                                        "FFmpeg",
                                    )
                                self.progress = False
                                await cpu_eater_lock.acquire()
                                self.progress = True

                            # Generate a unique process ID for each file
                            file_process_id = (
                                f"ffmpeg_custom_{self.mid}_{file_}_{time()}"
                            )

                            # Apply resource limits with the new process ID
                            from bot.helper.ext_utils.resource_manager import (
                                apply_resource_limits,
                                cleanup_process,
                            )

                            var_cmd = await apply_resource_limits(
                                var_cmd, file_process_id, "Custom FFmpeg"
                            )

                            LOGGER.info(f"Running ffmpeg cmd for: {f_path}")
                            self.subsize = await get_path_size(f_path)
                            self.subname = file_
                            # Execute the command
                            res = await ffmpeg.ffmpeg_cmds(var_cmd, f_path)

                            # Clean up process tracking for this file
                            cleanup_process(file_process_id)

                            if res and delete_files:
                                await remove(f_path)
                                if len(res) == 1:
                                    file_name = ospath.basename(res[0])
                                    if file_name.startswith("ffmpeg"):
                                        newname = file_name.split(".", 1)[-1]
                                        newres = ospath.join(dirpath, newname)
                                        await move(res[0], newres)
        finally:
            if checked:
                cpu_eater_lock.release()
        return dl_path

    async def substitute(self, dl_path):
        def perform_substitution(name, substitutions):
            for substitution in substitutions:
                sen = False
                pattern = substitution[0]
                if len(substitution) > 1:
                    if len(substitution) > 2:
                        sen = substitution[2] == "s"
                        res = substitution[1]
                    elif len(substitution[1]) == 0:
                        res = " "
                    else:
                        res = substitution[1]
                else:
                    res = ""
                try:
                    # Properly escape the pattern to avoid regex errors
                    escaped_pattern = pattern.replace("\\", "\\\\")
                    name = sub(
                        escaped_pattern,
                        res,
                        name,
                        flags=IGNORECASE if sen else 0,
                    )
                except Exception:
                    # Silently continue with other substitutions instead of failing completely
                    # No error logging to avoid cluttering logs
                    continue
                if len(name.encode()) > 255:
                    LOGGER.error(f"Substitute: {name} is too long")
                    return False
            return name

        if self.is_file:
            up_dir, name = dl_path.rsplit("/", 1)
            new_name = perform_substitution(name, self.name_sub)
            if not new_name:
                return dl_path
            new_path = ospath.join(up_dir, new_name)
            with contextlib.suppress(Exception):
                await move(dl_path, new_path)
            return new_path
        for dirpath, _, files in await sync_to_async(walk, dl_path, topdown=False):
            for file_ in files:
                f_path = ospath.join(dirpath, file_)
                new_name = perform_substitution(file_, self.name_sub)
                if not new_name:
                    continue
                with contextlib.suppress(Exception):
                    await move(f_path, ospath.join(dirpath, new_name))
        return dl_path

    async def remove_www_prefix(self, dl_path):
        def clean_filename(name):
            return sub(
                r"^www\.[^ ]+\s*-\s*|\s*^www\.[^ ]+\s*",
                "",
                name,
                flags=IGNORECASE,
            ).lstrip()

        if self.is_file:
            up_dir, name = dl_path.rsplit("/", 1)
            new_name = clean_filename(name)
            if new_name == name:
                return dl_path
            new_path = ospath.join(up_dir, new_name)
            with contextlib.suppress(Exception):
                await move(dl_path, new_path)
            return new_path

        for dirpath, _, files in await sync_to_async(walk, dl_path, topdown=False):
            for file_ in files:
                f_path = ospath.join(dirpath, file_)
                new_name = clean_filename(file_)
                if new_name == file_:
                    continue
                with contextlib.suppress(Exception):
                    await move(f_path, ospath.join(dirpath, new_name))

        return dl_path

    async def generate_screenshots(self, dl_path):
        ss_nb = int(self.screen_shots) if isinstance(self.screen_shots, str) else 10
        if self.is_file:
            if (await get_document_type(dl_path))[0]:
                LOGGER.info(f"Creating Screenshot for: {dl_path}")
                res = await take_ss(dl_path, ss_nb)
                if res:
                    new_folder = ospath.splitext(dl_path)[0]
                    name = ospath.basename(dl_path)
                    try:
                        await makedirs(new_folder, exist_ok=True)
                        await gather(
                            move(dl_path, f"{new_folder}/{name}"),
                            move(res, new_folder),
                        )
                    except FileExistsError:
                        LOGGER.warning(f"Folder already exists: {new_folder}")
                        # Try with a different folder name using timestamp
                        new_folder = f"{ospath.splitext(dl_path)[0]}_{int(time())}"
                        await makedirs(new_folder, exist_ok=True)
                        await gather(
                            move(dl_path, f"{new_folder}/{name}"),
                            move(res, new_folder),
                        )
                    return new_folder
        else:
            LOGGER.info(f"Creating Screenshot for: {dl_path}")
            for dirpath, _, files in await sync_to_async(
                walk,
                dl_path,
                topdown=False,
            ):
                for file_ in files:
                    f_path = ospath.join(dirpath, file_)
                    if (await get_document_type(f_path))[0]:
                        await take_ss(f_path, ss_nb)
        return dl_path

    async def convert_media(self, dl_path, gid):
        fvext = []
        if self.convert_video:
            vdata = self.convert_video.split()
            vext = vdata[0].lower()
            if len(vdata) > 2:
                if "+" in vdata[1].split():
                    vstatus = "+"
                elif "-" in vdata[1].split():
                    vstatus = "-"
                else:
                    vstatus = ""
                fvext.extend(f".{ext.lower()}" for ext in vdata[2:])
            else:
                vstatus = ""
        else:
            vext = ""
            vstatus = ""

        faext = []
        if self.convert_audio:
            adata = self.convert_audio.split()
            aext = adata[0].lower()
            if len(adata) > 2:
                if "+" in adata[1].split():
                    astatus = "+"
                elif "-" in adata[1].split():
                    astatus = "-"
                else:
                    astatus = ""
                faext.extend(f".{ext.lower()}" for ext in adata[2:])
            else:
                astatus = ""
        else:
            aext = ""
            astatus = ""

        self.files_to_proceed = {}
        all_files = []
        if self.is_file:
            all_files.append(dl_path)
        else:
            for dirpath, _, files in await sync_to_async(
                walk,
                dl_path,
                topdown=False,
            ):
                for file_ in files:
                    f_path = ospath.join(dirpath, file_)
                    all_files.append(f_path)

        for f_path in all_files:
            is_video, is_audio, _ = await get_document_type(f_path)
            if (
                is_video
                and vext
                and not f_path.strip().lower().endswith(f".{vext}")
                and (
                    (vstatus == "+" and f_path.strip().lower().endswith(tuple(fvext)))
                    or (
                        vstatus == "-"
                        and not f_path.strip().lower().endswith(tuple(fvext))
                    )
                    or not vstatus
                )
            ):
                self.files_to_proceed[f_path] = "video"
            elif (
                is_audio
                and aext
                and not is_video
                and not f_path.strip().lower().endswith(f".{aext}")
                and (
                    (astatus == "+" and f_path.strip().lower().endswith(tuple(faext)))
                    or (
                        astatus == "-"
                        and not f_path.strip().lower().endswith(tuple(faext))
                    )
                    or not astatus
                )
            ):
                self.files_to_proceed[f_path] = "audio"
        del all_files

        if self.files_to_proceed:
            ffmpeg = FFMpeg(self)
            async with task_dict_lock:
                task_dict[self.mid] = FFmpegStatus(self, ffmpeg, gid, "Convert")
            self.progress = False
            async with cpu_eater_lock:
                self.progress = True
                for f_path, f_type in self.files_to_proceed.items():
                    self.proceed_count += 1
                    LOGGER.info(f"Converting: {f_path}")
                    if self.is_file:
                        self.subsize = self.size
                    else:
                        self.subsize = await get_path_size(f_path)
                        self.subname = ospath.basename(f_path)
                    if f_type == "video":
                        res = await ffmpeg.convert_video(f_path, vext)
                    else:
                        res = await ffmpeg.convert_audio(f_path, aext)
                    if res:
                        try:
                            await remove(f_path)
                        except Exception:
                            self.is_cancelled = True
                            return False
                        if self.is_file:
                            return res
        return dl_path

    async def generate_sample_video(self, dl_path, gid):
        data = (
            self.sample_video.split(":") if isinstance(self.sample_video, str) else ""
        )
        if data:
            sample_duration = int(data[0]) if data[0] else 60
            part_duration = int(data[1]) if len(data) > 1 else 4
        else:
            sample_duration = 60
            part_duration = 4

        self.files_to_proceed = {}
        if self.is_file and (await get_document_type(dl_path))[0]:
            file_ = ospath.basename(dl_path)
            self.files_to_proceed[dl_path] = file_
        else:
            for dirpath, _, files in await sync_to_async(
                walk,
                dl_path,
                topdown=False,
            ):
                for file_ in files:
                    f_path = ospath.join(dirpath, file_)
                    if (await get_document_type(f_path))[0]:
                        self.files_to_proceed[f_path] = file_
        if self.files_to_proceed:
            ffmpeg = FFMpeg(self)
            async with task_dict_lock:
                task_dict[self.mid] = FFmpegStatus(self, ffmpeg, gid, "Sample Video")
            self.progress = False
            async with cpu_eater_lock:
                self.progress = True
                LOGGER.info(f"Creating Sample video: {self.name}")
                for f_path, file_ in self.files_to_proceed.items():
                    self.proceed_count += 1
                    if self.is_file:
                        self.subsize = self.size
                    else:
                        self.subsize = await get_path_size(f_path)
                        self.subname = file_
                    res = await ffmpeg.sample_video(
                        f_path,
                        sample_duration,
                        part_duration,
                    )
                    if res and self.is_file:
                        new_folder = ospath.splitext(f_path)[0]
                        try:
                            await makedirs(new_folder, exist_ok=True)
                            await gather(
                                move(f_path, f"{new_folder}/{file_}"),
                                move(res, f"{new_folder}/SAMPLE.{file_}"),
                            )
                            return new_folder
                        except FileExistsError:
                            LOGGER.warning(f"Folder already exists: {new_folder}")
                            # Try with a different folder name
                            new_folder = f"{ospath.splitext(f_path)[0]}_{int(time())}"
                            await makedirs(new_folder, exist_ok=True)
                            await gather(
                                move(f_path, f"{new_folder}/{file_}"),
                                move(res, f"{new_folder}/SAMPLE.{file_}"),
                            )
                            return new_folder
        return dl_path

    async def proceed_compress(self, dl_path, gid):
        pswd = self.compress if isinstance(self.compress, str) else ""
        if self.is_leech and self.is_file:
            new_folder = ospath.splitext(dl_path)[0]
            name = ospath.basename(dl_path)
            try:
                await makedirs(new_folder, exist_ok=True)
                new_dl_path = f"{new_folder}/{name}"
                await move(dl_path, new_dl_path)
            except FileExistsError:
                LOGGER.warning(f"Folder already exists: {new_folder}")
                # Try with a different folder name using timestamp
                new_folder = f"{ospath.splitext(dl_path)[0]}_{int(time())}"
                await makedirs(new_folder, exist_ok=True)
                new_dl_path = f"{new_folder}/{name}"
                await move(dl_path, new_dl_path)
            dl_path = new_dl_path
            up_path = f"{new_dl_path}.zip"
            self.is_file = False
        else:
            up_path = f"{dl_path}.zip"
        sevenz = SevenZ(self)
        async with task_dict_lock:
            task_dict[self.mid] = SevenZStatus(self, sevenz, gid, "Zip")
        return await sevenz.zip(dl_path, up_path, pswd)

    async def proceed_split(self, dl_path, gid):
        self.files_to_proceed = {}
        if self.is_file:
            f_size = await get_path_size(dl_path)
            if f_size > self.split_size:
                self.files_to_proceed[dl_path] = [f_size, ospath.basename(dl_path)]
        else:
            for dirpath, _, files in await sync_to_async(
                walk,
                dl_path,
                topdown=False,
            ):
                for file_ in files:
                    f_path = ospath.join(dirpath, file_)
                    f_size = await get_path_size(f_path)
                    if f_size > self.split_size:
                        self.files_to_proceed[f_path] = [f_size, file_]
        if self.files_to_proceed:
            ffmpeg = FFMpeg(self)
            async with task_dict_lock:
                task_dict[self.mid] = FFmpegStatus(self, ffmpeg, gid, "Split")
            LOGGER.info(f"Splitting: {self.name}")
            for f_path, (f_size, file_) in self.files_to_proceed.items():
                self.proceed_count += 1
                if self.is_file:
                    self.subsize = self.size
                else:
                    self.subsize = f_size
                    self.subname = file_
                parts = -(-f_size // self.split_size)
                split_size = self.split_size
                if not self.as_doc and (await get_document_type(f_path))[0]:
                    self.progress = True
                    res = await ffmpeg.split(f_path, file_, parts, split_size)
                else:
                    self.progress = False
                    res = await split_file(f_path, split_size, self)
                if self.is_cancelled:
                    return False
                if res or f_size >= self.max_split_size:
                    try:
                        await remove(f_path)
                    except Exception:
                        self.is_cancelled = True
            return None
        return None

    async def proceed_metadata(self, dl_path, gid):
        # Get metadata values with priority
        # metadata_all takes priority over individual settings
        metadata_all = self.metadata_all
        metadata_title = self.metadata_title
        metadata_author = self.metadata_author
        metadata_comment = self.metadata_comment

        # Legacy key for backward compatibility
        key = self.metadata

        # Log metadata settings with source information
        LOGGER.info(
            f"Metadata settings - All: {metadata_all}, Title: {metadata_title}, Author: {metadata_author}, Comment: {metadata_comment}, Legacy Key: {key}"
        )

        # Log if command line arguments were used
        if self.metadata_all:
            LOGGER.info(f"Using metadata-all from command line: {self.metadata_all}")
        if self.metadata_title:
            LOGGER.info(
                f"Using metadata-title from command line: {self.metadata_title}"
            )
        if self.metadata_author:
            LOGGER.info(
                f"Using metadata-author from command line: {self.metadata_author}"
            )
        if self.metadata_comment:
            LOGGER.info(
                f"Using metadata-comment from command line: {self.metadata_comment}"
            )

        ffmpeg = FFMpeg(self)
        checked = False
        if self.is_file:
            if is_mkv(dl_path):
                cmd, temp_file = await get_metadata_cmd(
                    dl_path,
                    key,
                    title=metadata_title,
                    author=metadata_author,
                    comment=metadata_comment,
                    metadata_all=metadata_all,
                )
                if cmd:
                    if not checked:
                        checked = True
                        async with task_dict_lock:
                            task_dict[self.mid] = FFmpegStatus(
                                self,
                                ffmpeg,
                                gid,
                                "Metadata",
                            )
                        self.progress = False
                        await cpu_eater_lock.acquire()
                        self.progress = True
                    self.subsize = self.size
                    res = await ffmpeg.metadata_watermark_cmds(cmd, dl_path)
                    if res:
                        os.replace(temp_file, dl_path)
                    elif await aiopath.exists(temp_file):
                        os.remove(temp_file)
        else:
            for dirpath, _, files in await sync_to_async(
                walk,
                dl_path,
                topdown=False,
            ):
                for file_ in files:
                    file_path = ospath.join(dirpath, file_)
                    if self.is_cancelled:
                        cpu_eater_lock.release()
                        return ""
                    self.proceed_count += 1
                    if is_mkv(file_path):
                        cmd, temp_file = await get_metadata_cmd(
                            file_path,
                            key,
                            title=metadata_title,
                            author=metadata_author,
                            comment=metadata_comment,
                            metadata_all=metadata_all,
                        )
                        if cmd:
                            if not checked:
                                checked = True
                                async with task_dict_lock:
                                    task_dict[self.mid] = FFmpegStatus(
                                        self,
                                        ffmpeg,
                                        gid,
                                        "Metadata",
                                    )
                                self.progress = False
                                await cpu_eater_lock.acquire()
                                self.progress = True
                            LOGGER.info(f"Running metadata cmd for: {file_path}")
                            self.subsize = await aiopath.getsize(file_path)
                            self.subname = file_
                            res = await ffmpeg.metadata_watermark_cmds(
                                cmd,
                                file_path,
                            )
                            if res:
                                os.replace(temp_file, file_path)
                            elif await aiopath.exists(temp_file):
                                os.remove(temp_file)
        if checked:
            cpu_eater_lock.release()
        return dl_path

    async def proceed_merge(self, dl_path, gid):
        # Skip if merge is not enabled
        if not self.merge_enabled:
            LOGGER.info("Merge not applied: merge is not enabled")
            return dl_path

        LOGGER.info(f"Analyzing directory for merge: {dl_path}")

        # Get all files in the directory
        all_files = []
        if self.is_file:
            # If it's a single file, we can't merge it
            LOGGER.info("Merge not applied: single file cannot be merged")
            return dl_path
        else:
            for dirpath, _, files in await sync_to_async(walk, dl_path, topdown=False):
                for file_ in files:
                    f_path = ospath.join(dirpath, file_)
                    all_files.append(f_path)

        if not all_files:
            LOGGER.info("Merge not applied: no files found")
            return dl_path

        # Analyze media files for merging with enhanced analysis
        analysis = await analyze_media_for_merge(all_files)

        if not analysis["recommended_approach"]:
            LOGGER.info("Merge not applied: no suitable files for merging")
            return dl_path

        LOGGER.info(
            f"Merge analysis recommended approach: {analysis['recommended_approach']}"
        )
        LOGGER.info(
            f"Found {len(analysis['video_files'])} video files, {len(analysis['audio_files'])} audio files, "
            f"{len(analysis['subtitle_files'])} subtitle files, {len(analysis['image_files'])} image files, "
            f"{len(analysis['document_files'])} document files"
        )

        # Check for merge flags
        merge_video_only = self.merge_video
        merge_audio_only = self.merge_audio
        merge_subtitle_only = self.merge_subtitle
        merge_image_only = self.merge_image
        merge_pdf_only = self.merge_pdf
        merge_all_types = self.merge_all

        # Filter files based on merge flags
        if merge_video_only:
            LOGGER.info("Merge flag: -merge-video detected, only merging video files")
            if not analysis["video_files"]:
                LOGGER.info("Merge not applied: no video files found")
                return dl_path
            # Only use video files
            analysis["audio_files"] = []
            analysis["subtitle_files"] = []
            analysis["image_files"] = []
            analysis["document_files"] = []
            # Use the recommended approach based on codec compatibility
            if (
                "video_codec_groups" in analysis
                and len(analysis["video_codec_groups"]) > 1
            ):
                # Multiple codec groups - need to use filter_complex
                analysis["recommended_approach"] = "filter_complex"
                LOGGER.info(
                    f"Multiple video codec groups detected: {len(analysis['video_codec_groups'])}. Using filter_complex approach."
                )
            else:
                # Single codec group - can use concat_demuxer
                analysis["recommended_approach"] = "concat_demuxer"
                LOGGER.info(
                    "Single video codec group detected. Using concat_demuxer approach."
                )
        elif merge_audio_only:
            LOGGER.info("Merge flag: -merge-audio detected, only merging audio files")
            if not analysis["audio_files"]:
                LOGGER.info("Merge not applied: no audio files found")
                return dl_path
            # Only use audio files
            analysis["video_files"] = []
            analysis["subtitle_files"] = []
            analysis["image_files"] = []
            analysis["document_files"] = []
            # Use the recommended approach based on codec compatibility
            if (
                "audio_codec_groups" in analysis
                and len(analysis["audio_codec_groups"]) > 1
            ):
                # Multiple codec groups - need to use filter_complex
                analysis["recommended_approach"] = "filter_complex"
                LOGGER.info(
                    f"Multiple audio codec groups detected: {len(analysis['audio_codec_groups'])}. Using filter_complex approach."
                )
            else:
                # Single codec group - can use concat_demuxer
                analysis["recommended_approach"] = "concat_demuxer"
                LOGGER.info(
                    "Single audio codec group detected. Using concat_demuxer approach."
                )
        elif merge_subtitle_only:
            LOGGER.info(
                "Merge flag: -merge-subtitle detected, only merging subtitle files"
            )
            if not analysis["subtitle_files"]:
                LOGGER.info("Merge not applied: no subtitle files found")
                return dl_path
            # Only use subtitle files
            analysis["video_files"] = []
            analysis["audio_files"] = []
            analysis["image_files"] = []
            analysis["document_files"] = []
            # Use the recommended approach based on format compatibility
            if (
                "subtitle_format_groups" in analysis
                and len(analysis["subtitle_format_groups"]) > 1
            ):
                # Multiple format groups - need to use special handling
                analysis["recommended_approach"] = "subtitle_special"
                LOGGER.info(
                    f"Multiple subtitle format groups detected: {len(analysis['subtitle_format_groups'])}. Using special subtitle handling."
                )
            else:
                # Single format group - can use concat_demuxer
                analysis["recommended_approach"] = "concat_demuxer"
                LOGGER.info(
                    "Single subtitle format group detected. Using concat_demuxer approach."
                )
        elif merge_image_only:
            LOGGER.info("Merge flag: -merge-image detected, only merging image files")
            if not analysis["image_files"]:
                LOGGER.info("Merge not applied: no image files found")
                return dl_path
            # Only use image files
            analysis["video_files"] = []
            analysis["audio_files"] = []
            analysis["subtitle_files"] = []
            analysis["document_files"] = []
            # Set the recommended approach to image_merge
            analysis["recommended_approach"] = "image_merge"
            LOGGER.info("Using image_merge approach for image files")

        elif merge_pdf_only:
            LOGGER.info("Merge flag: -merge-pdf detected, only merging PDF files")
            # Filter document files to only include PDFs
            pdf_files = [
                f for f in analysis["document_files"] if f.lower().endswith(".pdf")
            ]
            if not pdf_files:
                LOGGER.info("Merge not applied: no PDF files found")
                return dl_path
            # Only use PDF files
            analysis["video_files"] = []
            analysis["audio_files"] = []
            analysis["subtitle_files"] = []
            analysis["image_files"] = []
            analysis["document_files"] = pdf_files
            # Set the recommended approach to document_merge
            analysis["recommended_approach"] = "document_merge"
            LOGGER.info("Using document_merge approach for PDF files")

        elif merge_all_types:
            LOGGER.info(
                "Merge flag: -merge-all detected, merging all file types separately"
            )
            # Keep all files but change approach to mixed
            if (
                len(analysis["video_files"])
                + len(analysis["audio_files"])
                + len(analysis["subtitle_files"])
                + len(analysis["image_files"])
                + len(analysis["document_files"])
                == 0
            ):
                LOGGER.info("Merge not applied: no media files found")
                return dl_path
            # Set approach to mixed to preserve all video and audio tracks
            analysis["recommended_approach"] = "mixed"
            LOGGER.info("Using mixed approach to preserve all video and audio tracks")

        # Determine which approach to use based on settings and analysis
        approach = analysis["recommended_approach"]
        ffmpeg = FFMpeg(self)

        # Create status for merge operation
        async with task_dict_lock:
            task_dict[self.mid] = FFmpegStatus(self, ffmpeg, gid, "Merge")

        self.progress = False
        await cpu_eater_lock.acquire()
        self.progress = True

        # Log the workflow being used
        if (
            self.merge_video
            or self.merge_audio
            or self.merge_subtitle
            or self.merge_image
            or self.merge_pdf
            or self.merge_all
        ):
            LOGGER.info("Using Special Flag Merge Workflow")
        else:
            LOGGER.info("Using Standard Merge Workflow")

        # Log the settings being used
        LOGGER.info(
            f"Merge settings - Concat Demuxer: {self.concat_demuxer_enabled}, Filter Complex: {self.filter_complex_enabled}"
        )

        try:
            # Special Flag Merge Workflow for -merge-video
            if self.merge_video:
                LOGGER.info("Special Flag Workflow: -merge-video")

                # Check if we have video files
                if not analysis["video_files"]:
                    LOGGER.info("Merge not applied: no video files found")
                    return dl_path

                # Try concat demuxer first if enabled
                if self.concat_demuxer_enabled:
                    LOGGER.info("Trying concat demuxer approach for -merge-video")
                    cmd, output_file = await get_merge_concat_demuxer_cmd(
                        analysis["video_files"],
                        self.merge_output_format_video,
                        "video",
                    )

                    if cmd:
                        # Calculate total size
                        total_size = 0
                        for f in all_files:
                            total_size += await get_path_size(f)
                        self.subsize = total_size
                        res = await ffmpeg.metadata_watermark_cmds(cmd, dl_path)
                        if res and await aiopath.exists(output_file):
                            LOGGER.info(
                                f"Video merge successful with concat demuxer: {output_file}"
                            )
                            # Remove original files after successful merge if enabled
                            if self.merge_remove_original:
                                for f in all_files:
                                    try:
                                        if await aiopath.exists(f) and f != output_file:
                                            LOGGER.debug(
                                                f"Removing original file after merge: {f}"
                                            )
                                            await remove(f)
                                    except Exception as e:
                                        LOGGER.error(
                                            f"Error removing original file {f}: {str(e)}"
                                        )
                            return output_file
                        else:
                            LOGGER.warning(
                                "Concat demuxer approach failed, trying filter complex"
                            )

                # If concat demuxer failed or is not enabled, try filter complex
                if self.filter_complex_enabled:
                    LOGGER.info("Trying filter complex approach for -merge-video")
                    cmd, output_file = await get_merge_filter_complex_cmd(
                        analysis["video_files"],
                        "video",
                        self.merge_output_format_video,
                    )

                    if cmd:
                        # Calculate total size
                        total_size = 0
                        for f in all_files:
                            total_size += await get_path_size(f)
                        self.subsize = total_size
                        res = await ffmpeg.metadata_watermark_cmds(cmd, dl_path)
                        if res and await aiopath.exists(output_file):
                            LOGGER.info(
                                f"Video merge successful with filter complex: {output_file}"
                            )
                            # Remove original files after successful merge if enabled
                            if self.merge_remove_original:
                                for f in all_files:
                                    try:
                                        if await aiopath.exists(f) and f != output_file:
                                            LOGGER.debug(
                                                f"Removing original file after merge: {f}"
                                            )
                                            await remove(f)
                                    except Exception as e:
                                        LOGGER.error(
                                            f"Error removing original file {f}: {str(e)}"
                                        )
                            return output_file
                        else:
                            LOGGER.warning("Filter complex approach failed")

                # If both approaches failed, return original path
                LOGGER.info("Video merge failed: all approaches failed")
                return dl_path

            # Special Flag Merge Workflow for -merge-image
            elif self.merge_image:
                LOGGER.info("Special Flag Workflow: -merge-image")

                # For image files, use PIL to merge images
                from bot.helper.aeon_utils.media_merge import merge_images

                if analysis["image_files"]:
                    # Determine merge mode based on number of images
                    if len(analysis["image_files"]) <= 2:
                        mode = "horizontal"
                    elif len(analysis["image_files"]) <= 4:
                        mode = "collage"
                        columns = 2
                    else:
                        mode = "collage"
                        columns = 3

                    # Get output format from first image or default to jpg
                    first_ext = os.path.splitext(analysis["image_files"][0])[1].lower()[
                        1:
                    ]
                    output_format = (
                        first_ext if first_ext in ["jpg", "jpeg", "png"] else "jpg"
                    )

                    LOGGER.info(
                        f"Merging {len(analysis['image_files'])} images in {mode} mode"
                    )
                    output_file = await merge_images(
                        analysis["image_files"],
                        output_format=output_format,
                        mode=mode,
                        columns=columns,
                    )

                    if output_file and await aiopath.exists(output_file):
                        LOGGER.info(f"Image merge successful: {output_file}")
                        # Remove original files after successful merge
                        for f in all_files:
                            try:
                                if await aiopath.exists(f) and f != output_file:
                                    LOGGER.debug(
                                        f"Removing original file after merge: {f}"
                                    )
                                    await remove(f)
                            except Exception as e:
                                LOGGER.error(
                                    f"Error removing original file {f}: {str(e)}"
                                )
                        return output_file
                    else:
                        LOGGER.warning("Image merge failed")
                        return dl_path
                else:
                    LOGGER.info("No image files found for merging")
                    return dl_path

            # Special Flag Merge Workflow for -merge-pdf
            elif self.merge_pdf:
                LOGGER.info("Special Flag Workflow: -merge-pdf")

                # For PDF files, use PyPDF2 to merge PDFs
                from bot.helper.aeon_utils.media_merge import merge_documents

                # Check if we have PDF files
                pdf_files = [
                    f for f in analysis["document_files"] if f.lower().endswith(".pdf")
                ]

                if pdf_files:
                    LOGGER.info(f"Merging {len(pdf_files)} PDF documents")
                    output_file = await merge_documents(pdf_files)

                    if output_file and await aiopath.exists(output_file):
                        LOGGER.info(f"Document merge successful: {output_file}")
                        # Remove original files after successful merge
                        for f in all_files:
                            try:
                                if await aiopath.exists(f) and f != output_file:
                                    LOGGER.debug(
                                        f"Removing original file after merge: {f}"
                                    )
                                    await remove(f)
                            except Exception as e:
                                LOGGER.error(
                                    f"Error removing original file {f}: {str(e)}"
                                )
                        return output_file
                    else:
                        LOGGER.warning("Document merge failed")
                        return dl_path
                else:
                    LOGGER.info("No PDF files found for merging")
                    return dl_path

            # Special Flag Merge Workflow for -merge-audio, -merge-subtitle, or -merge-all
            elif self.merge_audio or self.merge_subtitle or self.merge_all:
                LOGGER.info(
                    f"Special Flag Workflow: {'-merge-audio' if self.merge_audio else '-merge-subtitle' if self.merge_subtitle else '-merge-all'}"
                )

                # For these flags, always try filter_complex first
                if self.filter_complex_enabled:
                    LOGGER.info(
                        "Trying filter complex approach first (user/owner setting)"
                    )

                    if approach in ["mixed", "subtitle_special", "slideshow"]:
                        # Mixed media types, use filter complex or mixed approach
                        LOGGER.info(
                            f"Using {approach} approach for different media types"
                        )
                        # For -merge-all flag, ensure we preserve all tracks
                        if self.merge_all:
                            LOGGER.info(
                                "Preserving all video, audio, and subtitle tracks during merge"
                            )
                        cmd, output_file = await get_merge_mixed_cmd(
                            analysis["video_files"],
                            analysis["audio_files"],
                            analysis["subtitle_files"],
                            self.merge_output_format_video,
                        )
                    elif self.merge_audio and analysis["audio_files"]:
                        LOGGER.info("Using filter complex for audio files")
                        cmd, output_file = await get_merge_filter_complex_cmd(
                            analysis["audio_files"],
                            "audio",
                            self.merge_output_format_audio,
                        )
                    elif self.merge_subtitle and analysis["subtitle_files"]:
                        LOGGER.info("Using filter complex for subtitle files")
                        cmd, output_file = await get_merge_filter_complex_cmd(
                            analysis["subtitle_files"], "subtitle", "srt"
                        )
                    else:
                        cmd, output_file = None, None

                    if cmd:
                        # Calculate total size
                        total_size = 0
                        for f in all_files:
                            total_size += await get_path_size(f)
                        self.subsize = total_size
                        res = await ffmpeg.metadata_watermark_cmds(cmd, dl_path)
                        if res and await aiopath.exists(output_file):
                            LOGGER.info(
                                f"Merge successful with filter complex: {output_file}"
                            )
                            # Remove original files after successful merge
                            for f in all_files:
                                try:
                                    if await aiopath.exists(f) and f != output_file:
                                        LOGGER.debug(
                                            f"Removing original file after merge: {f}"
                                        )
                                        await remove(f)
                                except Exception as e:
                                    LOGGER.error(
                                        f"Error removing original file {f}: {str(e)}"
                                    )
                            return output_file
                        else:
                            LOGGER.warning(
                                "Filter complex approach failed, trying concat demuxer"
                            )

                # If filter complex failed or is not enabled, try concat demuxer
                if self.concat_demuxer_enabled:
                    LOGGER.info("Trying concat demuxer approach (user/owner setting)")

                    if self.merge_audio and analysis["audio_files"]:
                        LOGGER.info("Using concat demuxer for audio files")
                        cmd, output_file = await get_merge_concat_demuxer_cmd(
                            analysis["audio_files"],
                            self.merge_output_format_audio,
                            "audio",
                        )
                    elif self.merge_subtitle and analysis["subtitle_files"]:
                        LOGGER.info("Using concat demuxer for subtitle files")
                        cmd, output_file = await get_merge_concat_demuxer_cmd(
                            analysis["subtitle_files"], "srt", "subtitle"
                        )
                    else:
                        cmd, output_file = None, None

                    if cmd:
                        # Calculate total size
                        total_size = 0
                        for f in all_files:
                            total_size += await get_path_size(f)
                        self.subsize = total_size
                        res = await ffmpeg.metadata_watermark_cmds(cmd, dl_path)
                        if res and await aiopath.exists(output_file):
                            LOGGER.info(
                                f"Merge successful with concat demuxer: {output_file}"
                            )
                            # Remove original files after successful merge
                            for f in all_files:
                                try:
                                    if await aiopath.exists(f) and f != output_file:
                                        LOGGER.debug(
                                            f"Removing original file after merge: {f}"
                                        )
                                        await remove(f)
                                except Exception as e:
                                    LOGGER.error(
                                        f"Error removing original file {f}: {str(e)}"
                                    )
                            return output_file
                        else:
                            LOGGER.warning(
                                "Concat demuxer approach failed, trying fallback approach"
                            )

            # Standard Merge Workflow (no special flags)
            else:
                LOGGER.info("Standard Merge Workflow")

                # For same file types, try concat demuxer first if enabled
                if approach == "concat_demuxer" and self.concat_demuxer_enabled:
                    # All files are of the same type, use concat demuxer
                    LOGGER.info("Trying concat demuxer approach (user/owner setting)")
                    if analysis["video_files"]:
                        LOGGER.info("Using concat demuxer for video files")
                        cmd, output_file = await get_merge_concat_demuxer_cmd(
                            analysis["video_files"],
                            self.merge_output_format_video,
                            "video",
                        )
                    elif analysis["audio_files"]:
                        LOGGER.info("Using concat demuxer for audio files")
                        cmd, output_file = await get_merge_concat_demuxer_cmd(
                            analysis["audio_files"],
                            self.merge_output_format_audio,
                            "audio",
                        )
                    elif analysis["subtitle_files"]:
                        LOGGER.info("Using concat demuxer for subtitle files")
                        cmd, output_file = await get_merge_concat_demuxer_cmd(
                            analysis["subtitle_files"], "srt", "subtitle"
                        )
                    else:
                        cmd, output_file = None, None

                    if cmd:
                        # Calculate total size by summing individual file sizes
                        total_size = 0
                        for f in all_files:
                            total_size += await get_path_size(f)
                        self.subsize = total_size
                        res = await ffmpeg.metadata_watermark_cmds(cmd, dl_path)
                        if res and await aiopath.exists(output_file):
                            LOGGER.info(
                                f"Merge successful with concat demuxer: {output_file}"
                            )
                            # Remove original files after successful merge
                            for f in all_files:
                                try:
                                    if await aiopath.exists(f) and f != output_file:
                                        LOGGER.debug(
                                            f"Removing original file after merge: {f}"
                                        )
                                        await remove(f)
                                except Exception as e:
                                    LOGGER.error(
                                        f"Error removing original file {f}: {str(e)}"
                                    )
                            return output_file
                        else:
                            LOGGER.warning(
                                "Concat demuxer approach failed, trying filter complex approach"
                            )

                # If concat demuxer failed or is disabled, try filter complex
                if self.filter_complex_enabled:
                    if approach in ["mixed", "subtitle_special", "slideshow"]:
                        # Mixed media types, use filter complex or mixed approach
                        LOGGER.info(
                            f"Using {approach} approach for different media types"
                        )
                        # For -merge-all flag, ensure we preserve all tracks
                        if self.merge_all:
                            LOGGER.info(
                                "Preserving all video, audio, and subtitle tracks during merge"
                            )
                        cmd, output_file = await get_merge_mixed_cmd(
                            analysis["video_files"],
                            analysis["audio_files"],
                            analysis["subtitle_files"],
                            self.merge_output_format_video,
                        )
                    elif approach == "image_merge" and analysis["image_files"]:
                        # For image files, use PIL to merge images
                        from bot.helper.aeon_utils.media_merge import merge_images

                        # Determine merge mode based on number of images
                        if len(analysis["image_files"]) <= 2:
                            mode = "horizontal"
                        elif len(analysis["image_files"]) <= 4:
                            mode = "collage"
                            columns = 2
                        else:
                            mode = "collage"
                            columns = 3

                        # Get output format from first image or default to jpg
                        first_ext = os.path.splitext(analysis["image_files"][0])[
                            1
                        ].lower()[1:]
                        output_format = (
                            first_ext if first_ext in ["jpg", "jpeg", "png"] else "jpg"
                        )

                        LOGGER.info(
                            f"Merging {len(analysis['image_files'])} images in {mode} mode"
                        )
                        output_file = await merge_images(
                            analysis["image_files"],
                            output_format=output_format,
                            mode=mode,
                            columns=columns,
                        )

                        if output_file and await aiopath.exists(output_file):
                            LOGGER.info(f"Image merge successful: {output_file}")
                            return output_file
                        else:
                            LOGGER.warning("Image merge failed")
                            return dl_path

                    elif approach == "document_merge" and analysis["document_files"]:
                        # For document files, use PyPDF2 to merge PDFs
                        from bot.helper.aeon_utils.media_merge import merge_documents

                        # Check if we have PDF files
                        pdf_files = [
                            f
                            for f in analysis["document_files"]
                            if f.lower().endswith(".pdf")
                        ]

                        if pdf_files:
                            LOGGER.info(f"Merging {len(pdf_files)} PDF documents")
                            output_file = await merge_documents(pdf_files)

                            if output_file and await aiopath.exists(output_file):
                                LOGGER.info(f"Document merge successful: {output_file}")
                                return output_file
                            else:
                                LOGGER.warning("Document merge failed")
                                return dl_path
                        else:
                            LOGGER.info("No PDF files found for merging")
                            return dl_path
                    else:
                        # Try filter complex for same media types
                        if analysis["video_files"]:
                            LOGGER.info("Using filter complex for video files")
                            cmd, output_file = await get_merge_filter_complex_cmd(
                                analysis["video_files"],
                                "video",
                                self.merge_output_format_video,
                            )
                        elif analysis["audio_files"]:
                            LOGGER.info("Using filter complex for audio files")
                            cmd, output_file = await get_merge_filter_complex_cmd(
                                analysis["audio_files"],
                                "audio",
                                self.merge_output_format_audio,
                            )
                        elif analysis["subtitle_files"]:
                            LOGGER.info("Using filter complex for subtitle files")
                            cmd, output_file = await get_merge_filter_complex_cmd(
                                analysis["subtitle_files"], "subtitle", "srt"
                            )
                        else:
                            cmd, output_file = None, None

                    if cmd:
                        # Calculate total size by summing individual file sizes
                        total_size = 0
                        for f in all_files:
                            total_size += await get_path_size(f)
                        self.subsize = total_size
                        res = await ffmpeg.metadata_watermark_cmds(cmd, dl_path)
                        if res and await aiopath.exists(output_file):
                            LOGGER.info(
                                f"Merge successful with filter complex: {output_file}"
                            )
                            # Remove original files after successful merge
                            for f in all_files:
                                try:
                                    if await aiopath.exists(f) and f != output_file:
                                        LOGGER.debug(
                                            f"Removing original file after merge: {f}"
                                        )
                                        await remove(f)
                                except Exception as e:
                                    LOGGER.error(
                                        f"Error removing original file {f}: {str(e)}"
                                    )
                            return output_file
                        else:
                            LOGGER.warning(
                                "Filter complex approach failed, trying fallback approach"
                            )

            # If all approaches failed, try a fallback approach for video files
            if analysis["video_files"] and len(analysis["video_files"]) > 1:
                LOGGER.info("Trying fallback approach for video files")
                # Create a temporary file list for concat demuxer
                concat_list_path = "concat_list.txt"
                with open(concat_list_path, "w") as f:
                    for file_path in sorted(analysis["video_files"]):
                        # Escape single quotes in file paths
                        escaped_path = file_path.replace("'", "'\\''")
                        f.write(f"file '{escaped_path}'\n")

                # Determine output path
                base_dir = os.path.dirname(analysis["video_files"][0])
                output_file = os.path.join(
                    base_dir, f"merged.{self.merge_output_format_video}"
                )

                # Use a simpler concat command with minimal options
                # Always preserve all tracks in the fallback approach
                LOGGER.info(
                    "Using fallback approach with -map 0 to preserve all tracks"
                )
                cmd = [
                    "xtra",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-progress",
                    "pipe:1",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    concat_list_path,
                    "-c",
                    "copy",
                    "-map",
                    "0",  # Map all streams to preserve all video, audio, and subtitle tracks
                    "-threads",
                    f"{max(1, cpu_no // 2)}",
                    output_file,
                ]

                # Calculate total size by summing individual file sizes
                total_size = 0
                for f in analysis["video_files"]:
                    total_size += await get_path_size(f)
                self.subsize = total_size
                res = await ffmpeg.metadata_watermark_cmds(cmd, dl_path)
                if res and await aiopath.exists(output_file):
                    LOGGER.info(
                        f"Merge successful with fallback approach: {output_file}"
                    )
                    # Remove original files after successful merge
                    for f in analysis["video_files"]:
                        try:
                            if await aiopath.exists(f) and f != output_file:
                                LOGGER.debug(f"Removing original file after merge: {f}")
                                await remove(f)
                        except Exception as e:
                            LOGGER.error(f"Error removing original file {f}: {str(e)}")
                    return output_file

            # If all approaches failed, return original path
            LOGGER.info("Merge failed: all approaches failed")
            return dl_path
        finally:
            cpu_eater_lock.release()

    async def proceed_watermark(self, dl_path, gid):
        # Skip if watermark is not enabled or no watermark text is provided
        # This follows the priority logic set in before_start method
        if not self.watermark_enabled or not self.watermark:
            # Log why watermark is not being applied
            if not self.watermark_enabled:
                LOGGER.info("Watermark not applied: watermark is not enabled")
            elif not self.watermark:
                LOGGER.info("Watermark not applied: no watermark text provided")
            return dl_path

        # Use the settings that were determined in before_start method
        # These already follow the correct priority logic
        key = self.watermark
        position = self.watermark_position
        size = self.watermark_size
        color = self.watermark_color
        font = self.watermark_font

        # Determine the source of the watermark settings
        user_enabled = "WATERMARK_ENABLED" in self.user_dict and self.user_dict.get(
            "WATERMARK_ENABLED", False
        )
        owner_enabled = Config.WATERMARK_ENABLED

        # Determine the source of the settings for detailed logging
        settings_source = {
            "text": "user"
            if "WATERMARK_KEY" in self.user_dict and self.user_dict["WATERMARK_KEY"]
            else ("owner" if Config.WATERMARK_KEY else "default"),
            "position": "user"
            if "WATERMARK_POSITION" in self.user_dict
            and self.user_dict["WATERMARK_POSITION"]
            else ("owner" if Config.WATERMARK_POSITION else "default"),
            "size": "user"
            if "WATERMARK_SIZE" in self.user_dict and self.user_dict["WATERMARK_SIZE"]
            else ("owner" if Config.WATERMARK_SIZE else "default"),
            "color": "user"
            if "WATERMARK_COLOR" in self.user_dict and self.user_dict["WATERMARK_COLOR"]
            else ("owner" if Config.WATERMARK_COLOR else "default"),
            "font": "user"
            if "WATERMARK_FONT" in self.user_dict and self.user_dict["WATERMARK_FONT"]
            else ("owner" if Config.WATERMARK_FONT else "default"),
        }

        # Log detailed information about the sources of each setting
        LOGGER.debug(f"Watermark settings sources: {settings_source}")

        # Determine the overall source
        if user_enabled:
            source = "user"
        elif owner_enabled:
            source = "owner"
        else:
            source = "default"

        LOGGER.info(
            f"Applying watermark with {source} settings: Text='{key}', Position={position}, Size={size}, Color={color}, Font={font}"
        )

        ffmpeg = FFMpeg(self)
        checked = False
        if self.is_file:
            # Check if the file is a supported media type for watermarking
            if is_mkv(dl_path):  # is_mkv now checks for all supported media types
                cmd, temp_file = await get_watermark_cmd(
                    dl_path, key, position, size, color, font
                )
                if cmd:
                    if not checked:
                        checked = True
                        async with task_dict_lock:
                            task_dict[self.mid] = FFmpegStatus(
                                self,
                                ffmpeg,
                                gid,
                                "Watermark",
                            )
                        self.progress = False
                        await cpu_eater_lock.acquire()
                        self.progress = True
                    self.subsize = self.size
                    LOGGER.info(f"Applying watermark to: {dl_path}")
                    res = await ffmpeg.metadata_watermark_cmds(cmd, dl_path)
                    if res:
                        os.replace(temp_file, dl_path)
                        LOGGER.info(f"Successfully applied watermark to: {dl_path}")
                    elif await aiopath.exists(temp_file):
                        os.remove(temp_file)
                        LOGGER.warning(f"Failed to apply watermark to: {dl_path}")
                else:
                    LOGGER.warning(
                        f"Could not generate watermark command for: {dl_path}"
                    )
        else:
            # Process all files in the directory
            for dirpath, _, files in await sync_to_async(
                walk,
                dl_path,
                topdown=False,
            ):
                for file_ in files:
                    file_path = ospath.join(dirpath, file_)
                    if self.is_cancelled:
                        if checked:
                            cpu_eater_lock.release()
                        return ""

                    # Check if the file is a supported media type for watermarking
                    if is_mkv(
                        file_path
                    ):  # is_mkv now checks for all supported media types
                        cmd, temp_file = await get_watermark_cmd(
                            file_path, key, position, size, color, font
                        )
                        if cmd:
                            if not checked:
                                checked = True
                                async with task_dict_lock:
                                    task_dict[self.mid] = FFmpegStatus(
                                        self,
                                        ffmpeg,
                                        gid,
                                        "Watermark",
                                    )
                                self.progress = False
                                await cpu_eater_lock.acquire()
                                self.progress = True
                            LOGGER.info(f"Applying watermark to: {file_path}")
                            self.subsize = await aiopath.getsize(file_path)
                            self.subname = file_
                            res = await ffmpeg.metadata_watermark_cmds(
                                cmd,
                                file_path,
                            )
                            if res:
                                os.replace(temp_file, file_path)
                                LOGGER.info(
                                    f"Successfully applied watermark to: {file_path}"
                                )
                            elif await aiopath.exists(temp_file):
                                os.remove(temp_file)
                                LOGGER.warning(
                                    f"Failed to apply watermark to: {file_path}"
                                )
                        else:
                            LOGGER.warning(
                                f"Could not generate watermark command for: {file_path}"
                            )
        if checked:
            cpu_eater_lock.release()
        return dl_path

    async def proceed_embed_thumb(self, dl_path, gid):
        thumb = self.e_thumb
        ffmpeg = FFMpeg(self)
        checked = False
        if self.is_file:
            if is_mkv(dl_path):
                cmd, temp_file = await get_embed_thumb_cmd(dl_path, thumb)
                if cmd:
                    if not checked:
                        checked = True
                        async with task_dict_lock:
                            task_dict[self.mid] = FFmpegStatus(
                                self,
                                ffmpeg,
                                gid,
                                "E_thumb",
                            )
                        self.progress = False
                        await cpu_eater_lock.acquire()
                        self.progress = True
                    self.subsize = self.size
                    res = await ffmpeg.metadata_watermark_cmds(cmd, dl_path)
                    if res:
                        os.replace(temp_file, dl_path)
                    elif await aiopath.exists(temp_file):
                        os.remove(temp_file)
        else:
            for dirpath, _, files in await sync_to_async(
                walk,
                dl_path,
                topdown=False,
            ):
                for file_ in files:
                    file_path = ospath.join(dirpath, file_)
                    if self.is_cancelled:
                        cpu_eater_lock.release()
                        return ""
                    if is_mkv(file_path):
                        cmd, temp_file = await get_embed_thumb_cmd(file_path, thumb)
                        if cmd:
                            if not checked:
                                checked = True
                                async with task_dict_lock:
                                    task_dict[self.mid] = FFmpegStatus(
                                        self,
                                        ffmpeg,
                                        gid,
                                        "E_thumb",
                                    )
                                self.progress = False
                                await cpu_eater_lock.acquire()
                                self.progress = True
                            LOGGER.info(f"Running cmd for: {file_path}")
                            self.subsize = await aiopath.getsize(file_path)
                            self.subname = file_
                            res = await ffmpeg.metadata_watermark_cmds(
                                cmd,
                                file_path,
                            )
                            if res:
                                os.replace(temp_file, file_path)
                            elif await aiopath.exists(temp_file):
                                os.remove(temp_file)
        if checked:
            cpu_eater_lock.release()
        return dl_path

import ast
import os
from importlib import import_module
from typing import Any, ClassVar


class Config:
    AS_DOCUMENT: bool = False
    AUTHORIZED_CHATS: str = ""
    BASE_URL: str = ""
    BASE_URL_PORT: int = 80
    BOT_TOKEN: str = ""
    CMD_SUFFIX: str = ""
    DATABASE_URL: str = ""
    DEFAULT_UPLOAD: str = "rc"
    EXCLUDED_EXTENSIONS: str = ""
    FFMPEG_CMDS: ClassVar[dict[str, list[str]]] = {}
    FILELION_API: str = ""
    GDRIVE_ID: str = ""
    INCOMPLETE_TASK_NOTIFIER: bool = False
    INDEX_URL: str = ""
    IMDB_TEMPLATE: str = ""
    JD_EMAIL: str = ""
    JD_PASS: str = ""
    IS_TEAM_DRIVE: bool = False
    LEECH_DUMP_CHAT: str = ""
    LEECH_FILENAME_PREFIX: str = ""
    LEECH_SUFFIX: str = ""
    LEECH_FONT: str = ""
    LEECH_FILENAME: str = ""
    LEECH_SPLIT_SIZE: int = 2097152000
    LOGIN_PASS: str = ""
    MEDIA_GROUP: bool = False
    HYBRID_LEECH: bool = False
    MUSIC_SEARCH_CHATS: ClassVar[list] = []
    NAME_SUBSTITUTE: str = r""
    OWNER_ID: int = 0
    QUEUE_ALL: int = 0
    QUEUE_DOWNLOAD: int = 0
    QUEUE_UPLOAD: int = 0
    RCLONE_FLAGS: str = ""
    RCLONE_PATH: str = ""
    RCLONE_SERVE_URL: str = ""
    RCLONE_SERVE_USER: str = ""
    RCLONE_SERVE_PASS: str = ""
    RCLONE_SERVE_PORT: int = 8080
    RSS_CHAT: str = ""
    RSS_DELAY: int = 600
    RSS_SIZE_LIMIT: int = 0
    STOP_DUPLICATE: bool = False
    STREAMWISH_API: str = ""
    SUDO_USERS: str = ""
    TELEGRAM_API: int = 0
    TELEGRAM_HASH: str = ""
    TG_PROXY: dict | None = None
    THUMBNAIL_LAYOUT: str = ""
    TORRENT_TIMEOUT: int = 0
    UPLOAD_PATHS: ClassVar[dict] = {}
    UPSTREAM_REPO: str = ""
    USENET_SERVERS: ClassVar[list] = []
    UPSTREAM_BRANCH: str = "main"
    USER_SESSION_STRING: str = ""
    USER_TRANSMISSION: bool = False
    USE_SERVICE_ACCOUNTS: bool = False
    WEB_PINCODE: bool = False
    YT_DLP_OPTIONS: ClassVar[dict] = {}

    # INKYPINKY
    METADATA_KEY: str = ""
    METADATA_ALL: str = ""
    METADATA_TITLE: str = ""
    METADATA_AUTHOR: str = ""
    METADATA_COMMENT: str = ""
    SET_COMMANDS: bool = True
    TOKEN_TIMEOUT: int = 0
    PAID_CHANNEL_ID: int = 0
    PAID_CHANNEL_LINK: str = ""
    DELETE_LINKS: bool = False
    FSUB_IDS: str = ""
    LOG_CHAT_ID: int = 0
    LEECH_FILENAME_CAPTION: str = ""
    HYDRA_IP: str = ""
    HYDRA_API_KEY: str = ""
    INSTADL_API: str = ""
    MEDIA_STORE: bool = False

    # Media Tools Settings
    MEDIA_TOOLS_ENABLED: bool = True

    # Watermark Settings
    WATERMARK_ENABLED: bool = False
    WATERMARK_KEY: str = ""
    WATERMARK_POSITION: str = "top_left"
    WATERMARK_SIZE: int = 20
    WATERMARK_COLOR: str = "white"
    WATERMARK_FONT: str = "default.otf"
    WATERMARK_PRIORITY: int = 2
    WATERMARK_THREADING: bool = True
    WATERMARK_THREAD_NUMBER: int = 4

    # Merge Settings
    MERGE_ENABLED: bool = False
    MERGE_PRIORITY: int = 1
    MERGE_THREADING: bool = True
    MERGE_THREAD_NUMBER: int = 4
    CONCAT_DEMUXER_ENABLED: bool = True
    FILTER_COMPLEX_ENABLED: bool = False

    # Output formats
    MERGE_OUTPUT_FORMAT_VIDEO: str = "mkv"
    MERGE_OUTPUT_FORMAT_AUDIO: str = "mp3"
    MERGE_OUTPUT_FORMAT_IMAGE: str = "jpg"
    MERGE_OUTPUT_FORMAT_DOCUMENT: str = "pdf"
    MERGE_OUTPUT_FORMAT_SUBTITLE: str = "srt"

    # Video settings
    MERGE_VIDEO_CODEC: str = "none"
    MERGE_VIDEO_QUALITY: str = "none"
    MERGE_VIDEO_PRESET: str = "none"
    MERGE_VIDEO_CRF: int = 0
    MERGE_VIDEO_PIXEL_FORMAT: str = "none"
    MERGE_VIDEO_TUNE: str = "none"
    MERGE_VIDEO_FASTSTART: bool = False

    # Audio settings
    MERGE_AUDIO_CODEC: str = "none"
    MERGE_AUDIO_BITRATE: str = "none"
    MERGE_AUDIO_CHANNELS: int = 0
    MERGE_AUDIO_SAMPLING: str = "none"
    MERGE_AUDIO_VOLUME: float = 0.0

    # Image settings
    MERGE_IMAGE_MODE: str = "none"
    MERGE_IMAGE_COLUMNS: int = 0
    MERGE_IMAGE_QUALITY: int = 0
    MERGE_IMAGE_DPI: int = 0
    MERGE_IMAGE_RESIZE: str = "none"
    MERGE_IMAGE_BACKGROUND: str = "none"

    # Subtitle settings
    MERGE_SUBTITLE_ENCODING: str = "none"
    MERGE_SUBTITLE_FONT: str = "none"
    MERGE_SUBTITLE_FONT_SIZE: int = 0
    MERGE_SUBTITLE_FONT_COLOR: str = "none"
    MERGE_SUBTITLE_BACKGROUND: str = "none"

    # Document settings
    MERGE_DOCUMENT_PAPER_SIZE: str = "none"
    MERGE_DOCUMENT_ORIENTATION: str = "none"
    MERGE_DOCUMENT_MARGIN: int = 0

    # General settings
    MERGE_REMOVE_ORIGINAL: bool = True
    MERGE_METADATA_TITLE: str = "none"
    MERGE_METADATA_AUTHOR: str = "none"
    MERGE_METADATA_COMMENT: str = "none"

    # Resource Management Settings
    FFMPEG_MEMORY_LIMIT: int = 2048
    FFMPEG_CPU_AFFINITY: str = ""
    FFMPEG_DYNAMIC_THREADS: bool = True

    # Auto Restart Settings
    AUTO_RESTART_ENABLED: bool = False
    AUTO_RESTART_INTERVAL: int = 24  # in hours

    @classmethod
    def get(cls, key):
        return getattr(cls, key) if hasattr(cls, key) else None

    @classmethod
    def set(cls, key, value):
        if hasattr(cls, key):
            setattr(cls, key, value)
        else:
            raise KeyError(f"{key} is not a valid configuration key.")

    @classmethod
    def get_all(cls):
        return {
            key: getattr(cls, key)
            for key in sorted(cls.__dict__)
            if not key.startswith("__") and not callable(getattr(cls, key))
        }

    @classmethod
    def load(cls):
        try:
            settings = import_module("config")
        except ModuleNotFoundError:
            return
        else:
            for attr in dir(settings):
                if hasattr(cls, attr):
                    value = getattr(settings, attr)
                    if not value:
                        continue
                    if isinstance(value, str):
                        value = value.strip()
                    if attr == "DEFAULT_UPLOAD" and value != "gd":
                        value = "rc"
                    elif (
                        attr
                        in [
                            "BASE_URL",
                            "RCLONE_SERVE_URL",
                            "INDEX_URL",
                        ]
                        and value
                    ):
                        value = value.strip("/")
                    elif attr == "USENET_SERVERS":
                        try:
                            if not value[0].get("host"):
                                continue
                        except Exception:
                            continue
                    setattr(cls, attr, value)

    @classmethod
    def load_dict(cls, config_dict):
        for key, value in config_dict.items():
            if hasattr(cls, key):
                if key == "DEFAULT_UPLOAD" and value != "gd":
                    value = "rc"
                elif (
                    key
                    in [
                        "BASE_URL",
                        "RCLONE_SERVE_URL",
                        "INDEX_URL",
                    ]
                    and value
                ):
                    value = value.strip("/")
                elif key == "USENET_SERVERS":
                    try:
                        if not value[0].get("host"):
                            value = []
                    except Exception:
                        value = []
                setattr(cls, key, value)


class SystemEnv:
    @classmethod
    def load(cls):
        config_vars = Config.get_all()
        for key in config_vars:
            env_value = os.getenv(key)
            if env_value is not None:
                converted_value = cls._convert_type(key, env_value)
                Config.set(key, converted_value)

    @classmethod
    def _convert_type(cls, key: str, value: str) -> Any:
        original_value = getattr(Config, key, None)

        if original_value is None:
            return value

        if isinstance(original_value, bool):
            return value.lower() in ("true", "1", "yes")

        if isinstance(original_value, int):
            try:
                return int(value)
            except ValueError:
                return original_value

        if isinstance(original_value, float):
            try:
                return float(value)
            except ValueError:
                return original_value

        if isinstance(original_value, list):
            return value.split(",")

        if isinstance(original_value, dict):
            try:
                return ast.literal_eval(value)
            except (SyntaxError, ValueError):
                return original_value

        return value

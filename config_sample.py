# REQUIRED CONFIG
BOT_TOKEN = ""
OWNER_ID = 0
TELEGRAM_API = 0
TELEGRAM_HASH = ""

# SEMI-REQUIRED, WE SUGGEST TO FILL IT FROM MONGODB
DATABASE_URL = ""

# OPTIONAL CONFIG
TG_PROXY = {}
USER_SESSION_STRING = ""
DOWNLOAD_DIR = "/usr/src/app/downloads/"
CMD_SUFFIX = ""
AUTHORIZED_CHATS = ""
SUDO_USERS = ""
DEFAULT_UPLOAD = "rc"
FILELION_API = ""
STREAMWISH_API = ""
EXCLUDED_EXTENSIONS = ""
INCOMPLETE_TASK_NOTIFIER = False
YT_DLP_OPTIONS = ""
USE_SERVICE_ACCOUNTS = False
NAME_SUBSTITUTE = ""
FFMPEG_CMDS = {}
UPLOAD_PATHS = {}

# INKYPINKY
DELETE_LINKS = False
FSUB_IDS = ""
TOKEN_TIMEOUT = 0
LOGIN_PASS = ""  # Set a password to enable login feature
PAID_CHANNEL_ID = 0
PAID_CHANNEL_LINK = ""
SET_COMMANDS = True
METADATA_KEY = ""
LOG_CHAT_ID = 0
LEECH_FILENAME_CAPTION = ""
HYDRA_IP = ""
HYDRA_API_KEY = ""
INSTADL_API = ""
MEDIA_STORE = False

# Media Tools Settings
MEDIA_TOOLS_ENABLED = True  # Enable/disable Media Tools feature

# Watermark Settings
WATERMARK_ENABLED = False  # Enable/disable watermark feature
WATERMARK_KEY = ""  # Text to use as watermark
WATERMARK_POSITION = "top_left"  # Position of watermark (top_left, top_right, bottom_left, bottom_right, center)
WATERMARK_SIZE = 20  # Font size of watermark
WATERMARK_COLOR = "white"  # Color of watermark text
WATERMARK_FONT = "default.otf"  # Font file for watermark
WATERMARK_PRIORITY = (
    2  # Priority for watermark processing (lower number = higher priority)
)
WATERMARK_THREADING = True  # Enable/disable threading for watermark processing
WATERMARK_THREAD_NUMBER = 4  # Number of threads to use for watermark processing

# Merge Settings
MERGE_ENABLED = False  # Enable/disable merge feature
CONCAT_DEMUXER_ENABLED = True  # Enable/disable concat demuxer method for merging
FILTER_COMPLEX_ENABLED = False  # Enable/disable filter complex method for merging
MERGE_OUTPUT_FORMAT_VIDEO = "mkv"  # Default output format for merged videos
MERGE_OUTPUT_FORMAT_AUDIO = "mp3"  # Default output format for merged audio
MERGE_PRIORITY = 1  # Priority for merge processing (lower number = higher priority)
MERGE_THREADING = True  # Enable/disable threading for merge processing
MERGE_THREAD_NUMBER = 4  # Number of threads to use for merge processing

# Music Search
MUSIC_SEARCH_CHATS = []  # List of chat IDs to search for music

# GDrive Tools
GDRIVE_ID = ""
IS_TEAM_DRIVE = False
STOP_DUPLICATE = False
INDEX_URL = ""

# Rclone
RCLONE_PATH = ""
RCLONE_FLAGS = ""
RCLONE_SERVE_URL = ""
RCLONE_SERVE_PORT = 0
RCLONE_SERVE_USER = ""
RCLONE_SERVE_PASS = ""

# Mega credentials
MEGA_EMAIL = ""
MEGA_PASSWORD = ""

# Sabnzbd
USENET_SERVERS = [
    {
        "name": "main",
        "host": "",
        "port": 563,
        "timeout": 60,
        "username": "",
        "password": "",
        "connections": 8,
        "ssl": 1,
        "ssl_verify": 2,
        "ssl_ciphers": "",
        "enable": 1,
        "required": 0,
        "optional": 0,
        "retention": 0,
        "send_group": 0,
        "priority": 0,
    },
]

# Update
UPSTREAM_REPO = "https://github.com/AeonOrg/Aeon-MLTB"
UPSTREAM_BRANCH = "main"

# Leech
LEECH_SPLIT_SIZE = 0
AS_DOCUMENT = False
MEDIA_GROUP = False
USER_TRANSMISSION = False
HYBRID_LEECH = False
LEECH_FILENAME_PREFIX = ""
LEECH_SUFFIX = ""
LEECH_FONT = ""
LEECH_FILENAME = ""
LEECH_DUMP_CHAT = ""
THUMBNAIL_LAYOUT = ""

# qBittorrent/Aria2c
TORRENT_TIMEOUT = 0
BASE_URL = ""
BASE_URL_PORT = 80
WEB_PINCODE = False

# Queueing system
QUEUE_ALL = 0
QUEUE_DOWNLOAD = 0
QUEUE_UPLOAD = 0

# Resource Management
FFMPEG_MEMORY_LIMIT = 2048  # Memory limit in MB (0 = no limit)
FFMPEG_CPU_AFFINITY = (
    ""  # CPU cores to use (e.g., "0-3" or "0,2,4,6"), empty = all cores
)
FFMPEG_DYNAMIC_THREADS = True  # Dynamically adjust thread count based on system load

# Auto Restart Settings
AUTO_RESTART_ENABLED = False  # Enable/disable automatic bot restart
AUTO_RESTART_INTERVAL = 24  # Restart interval in hours

# RSS
RSS_DELAY = 600
RSS_CHAT = ""
RSS_SIZE_LIMIT = 0

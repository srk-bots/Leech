# REQUIRED CONFIG
BOT_TOKEN = ""
OWNER_ID = "1416841137"
TELEGRAM_API = "27975779"
TELEGRAM_HASH = "378062eb0a32d8d6b1bbbe97cb63a75a"

# SEMI-REQUIRED, WE SUGGEST TO FILL IT FROM MONGODB
DATABASE_URL = "mongodb+srv://Anime:tamilan@cluster0.swaztvx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# OPTIONAL CONFIG
TG_PROXY = {}
USER_SESSION_STRING = ""
DOWNLOAD_DIR = "/usr/src/app/downloads/"
CMD_SUFFIX = ""
AUTHORIZED_CHATS = ""-1002248132609
SUDO_USERS = "1416841137"
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
PAID_CHANNEL_ID = 0
PAID_CHANNEL_LINK = ""
SET_COMMANDS = True
METADATA_KEY = ""
WATERMARK_KEY = ""
LOG_CHAT_ID = 0
LEECH_FILENAME_CAPTION = ""
HYDRA_IP = ""
HYDRA_API_KEY = ""
INSTADL_API = ""

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
LEECH_DUMP_CHAT = [-1002558820684]
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

# RSS
RSS_DELAY = 600
RSS_CHAT = ""
RSS_SIZE_LIMIT = 0

# Heroku config for get BASE_URL automatically
HEROKU_APP_NAME = ""
HEROKU_API_KEY = ""

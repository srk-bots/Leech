from bot import LOGGER
from bot.core.config_manager import Config
from bot.helper.ext_utils.bot_utils import (
    check_storage_threshold,
    getdailytasks,
    sync_to_async,
    timeval_check,
)
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.telegram_helper.filters import CustomFilters


async def limit_checker(
    size,
    listener,
    isTorrent=False,
    isMega=False,
    isDriveLink=False,
    isYtdlp=False,
    isPlayList=None,
    is_jd=False,
    is_nzb=False,
):
    """Check size limits with improved memory management.

    Args:
        size: Size to check
        listener: Listener object
        isTorrent: Whether it's a torrent
        isMega: Whether it's a Mega link
        isDriveLink: Whether it's a Drive link
        isYtdlp: Whether it's a YouTube link
        isPlayList: Number of items in playlist
        is_jd: Whether it's a JDownloader download
        is_nzb: Whether it's an NZB download

    Returns:
        str: Limit exceeded message, or None if no limit exceeded
    """
    LOGGER.info("Checking Size Limit of link/file/folder/tasks...")
    user_id = (
        listener.message.from_user.id
        if hasattr(listener.message, "from_user")
        else listener.message.chat.id
    )

    # Skip limit check for sudo users
    if await CustomFilters.sudo("", listener.message):
        return None

    # Check time interval between tasks
    if wait_time := await timeval_check(user_id):
        return f"⚠️ Please wait {wait_time:.1f} seconds before starting another task."

    limit_exceeded = ""

    # Check specific limits based on link type
    is_clone = getattr(listener, "isClone", False)
    # Use parameters if provided, otherwise check listener attributes
    is_jd = is_jd or getattr(listener, "is_jd", False)
    is_nzb = is_nzb or getattr(listener, "is_nzb", False)

    if is_clone:
        if CLONE_LIMIT := Config.CLONE_LIMIT:
            limit = CLONE_LIMIT * 1024**3
            if size > 0 and size > limit:
                limit_exceeded = f"Clone limit is {get_readable_file_size(limit)}."
    elif is_jd:
        if JD_LIMIT := Config.JD_LIMIT:
            limit = JD_LIMIT * 1024**3
            if size > 0 and size > limit:
                limit_exceeded = (
                    f"JDownloader limit is {get_readable_file_size(limit)}"
                )
    elif is_nzb:
        if NZB_LIMIT := Config.NZB_LIMIT:
            limit = NZB_LIMIT * 1024**3
            if size > 0 and size > limit:
                limit_exceeded = f"NZB limit is {get_readable_file_size(limit)}"
    elif isMega:
        if MEGA_LIMIT := Config.MEGA_LIMIT:
            limit = MEGA_LIMIT * 1024**3
            if size > 0 and size > limit:
                limit_exceeded = f"Mega limit is {get_readable_file_size(limit)}"
    elif isDriveLink:
        if GDRIVE_LIMIT := Config.GDRIVE_LIMIT:
            limit = GDRIVE_LIMIT * 1024**3
            if size > 0 and size > limit:
                limit_exceeded = (
                    f"Google Drive limit is {get_readable_file_size(limit)}"
                )
    elif isYtdlp:
        if YTDLP_LIMIT := Config.YTDLP_LIMIT:
            limit = YTDLP_LIMIT * 1024**3
            if size > 0 and size > limit:
                limit_exceeded = f"YouTube limit is {get_readable_file_size(limit)}"
        if (
            not limit_exceeded
            and isPlayList
            and (PLAYLIST_LIMIT := Config.PLAYLIST_LIMIT)
            and isPlayList > PLAYLIST_LIMIT
        ):
            limit_exceeded = f"Playlist limit is {PLAYLIST_LIMIT}"
    elif isTorrent:
        if TORRENT_LIMIT := Config.TORRENT_LIMIT:
            limit = TORRENT_LIMIT * 1024**3
            if size > 0 and size > limit:
                limit_exceeded = f"Torrent limit is {get_readable_file_size(limit)}"
    elif DIRECT_LIMIT := Config.DIRECT_LIMIT:
        limit = DIRECT_LIMIT * 1024**3
        if size > 0 and size > limit:
            limit_exceeded = f"Direct link limit is {get_readable_file_size(limit)}"

    # If no specific limit exceeded, check general limits
    if not limit_exceeded:
        # Check leech limit
        is_leech = getattr(listener, "is_leech", getattr(listener, "isLeech", False))
        if (LEECH_LIMIT := Config.LEECH_LIMIT) and is_leech:
            limit = LEECH_LIMIT * 1024**3
            if size > 0 and size > limit:
                limit_exceeded = f"Leech limit is {get_readable_file_size(limit)}"

        # Check storage threshold
        is_clone = getattr(listener, "isClone", False)
        if (STORAGE_THRESHOLD := Config.STORAGE_THRESHOLD) and not is_clone:
            compress = getattr(listener, "compress", False)
            extract = getattr(listener, "extract", False)
            arch = any([compress, extract])
            limit = STORAGE_THRESHOLD * 1024**3
            acpt = await sync_to_async(check_storage_threshold, size, limit, arch)
            if not acpt:
                limit_exceeded = (
                    f"You must leave {get_readable_file_size(limit)} free storage."
                )

        # Check daily task limit first
        if (
            DAILY_TASK_LIMIT := Config.DAILY_TASK_LIMIT
        ) and await check_daily_task_limit(DAILY_TASK_LIMIT, listener):
            limit_exceeded = f"Daily task limit is {DAILY_TASK_LIMIT} tasks"

        # Check daily mirror limit
        if (
            not limit_exceeded
            and (DAILY_MIRROR_LIMIT := Config.DAILY_MIRROR_LIMIT)
            and not is_leech
        ):
            limit = DAILY_MIRROR_LIMIT * 1024**3
            if await check_daily_mirror_limit(limit, listener, size):
                limit_exceeded = (
                    f"Daily mirror limit is {get_readable_file_size(limit)}"
                )

        # Check daily leech limit
        if (
            not limit_exceeded
            and (DAILY_LEECH_LIMIT := Config.DAILY_LEECH_LIMIT)
            and is_leech
        ):
            limit = DAILY_LEECH_LIMIT * 1024**3
            if await check_daily_leech_limit(limit, listener, size):
                limit_exceeded = (
                    f"Daily leech limit is {get_readable_file_size(limit)}"
                )

    if limit_exceeded:
        # Log the limit exceeded message for debugging
        LOGGER.warning(f"Limit exceeded for user {user_id}: {limit_exceeded}")
        return f"⚠️ {limit_exceeded}. Your task has been cancelled."
    return None


async def check_daily_mirror_limit(limit, listener, size):
    """Check if user has exceeded daily mirror limit.

    Args:
        limit: Daily mirror limit in bytes
        listener: Listener object with user info
        size: Size of current task in bytes

    Returns:
        bool: True if limit exceeded, False otherwise
    """
    user_id = (
        listener.message.from_user.id
        if hasattr(listener.message, "from_user")
        else listener.message.chat.id
    )

    # Get current mirror usage
    current_usage = await getdailytasks(user_id, check_mirror=True)

    # Check if adding this task would exceed the limit
    if size > 0 and (size >= (limit - current_usage) or limit <= current_usage):
        return True

    # Update mirror usage if not checking
    is_clone = getattr(listener, "isClone", False)
    if not is_clone:
        await getdailytasks(user_id, upmirror=size)
        LOGGER.info(
            f"User: {user_id} | Daily Mirror Size: {get_readable_file_size(current_usage + size)}"
        )

    return False


async def check_daily_leech_limit(limit, listener, size):
    """Check if user has exceeded daily leech limit.

    Args:
        limit: Daily leech limit in bytes
        listener: Listener object with user info
        size: Size of current task in bytes

    Returns:
        bool: True if limit exceeded, False otherwise
    """
    user_id = (
        listener.message.from_user.id
        if hasattr(listener.message, "from_user")
        else listener.message.chat.id
    )

    # Get current leech usage
    current_usage = await getdailytasks(user_id, check_leech=True)

    # Check if adding this task would exceed the limit
    if size > 0 and (size >= (limit - current_usage) or limit <= current_usage):
        return True

    # Update leech usage if not checking
    await getdailytasks(user_id, upleech=size)
    LOGGER.info(
        f"User: {user_id} | Daily Leech Size: {get_readable_file_size(current_usage + size)}"
    )

    return False


async def check_daily_task_limit(limit, listener):
    """Check if user has exceeded daily task count limit.

    Args:
        limit: Maximum number of tasks per day
        listener: Listener object with user info

    Returns:
        bool: True if limit exceeded, False otherwise
    """
    user_id = (
        listener.message.from_user.id
        if hasattr(listener.message, "from_user")
        else listener.message.chat.id
    )

    # Get current task count before incrementing
    current_tasks = await getdailytasks(user_id)

    # Check if limit is reached
    if current_tasks >= limit:
        return True

    # Increment task count
    new_count = await getdailytasks(user_id, increase_task=True)
    LOGGER.info(f"User: {user_id} | Daily Tasks: {new_count}")

    return False

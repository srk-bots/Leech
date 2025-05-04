import gc
import os
import sys
import tracemalloc
from asyncio import create_task, sleep
from functools import wraps

from bot import LOGGER
from bot.core.config_manager import Config
from bot.helper.ext_utils.bot_utils import (
    check_storage_threshold,
    getdailytasks,
    sync_to_async,
    timeval_check,
)
from bot.helper.ext_utils.gc_utils import smart_garbage_collection
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import auto_delete_message, send_message

try:
    import psutil
except ImportError:
    psutil = None

# Enable memory tracking for debugging if not already started
if not tracemalloc.is_tracing():
    tracemalloc.start(10)  # Track 10 frames


def optimize_memory(aggressive=False):
    """Optimize memory usage by forcing garbage collection.

    This function performs aggressive memory optimization to prevent
    memory leaks and reduce memory usage.

    Args:
        aggressive (bool): Whether to use aggressive garbage collection
    """
    # First, use smart_garbage_collection which is already imported
    if smart_garbage_collection is not None:
        if aggressive:
            smart_garbage_collection(aggressive=True)
        else:
            smart_garbage_collection(aggressive=False)

    # Force Python's garbage collector
    gc.collect(2)  # Full collection

    if aggressive:
        # Run a second collection for better results
        gc.collect(2)

        # Clear memory cache if psutil is available
        if psutil is not None:
            try:
                # Try to drop system caches on Linux
                if sys.platform.startswith('linux'):
                    os.system('sync')  # Sync disk with memory

                # Find and clear large objects
                for obj in gc.get_objects():
                    try:
                        if hasattr(obj, '__sizeof__'):
                            size = obj.__sizeof__()
                            # Clear objects larger than 10MB if they have a clear method
                            if size > 10 * 1024 * 1024 and hasattr(obj, 'clear') and callable(obj.clear):
                                obj.clear()
                    except Exception:
                        pass
            except Exception as e:
                LOGGER.error(f"Error in aggressive memory optimization: {e}")

    # Log memory snapshots if tracing is enabled
    if tracemalloc.is_tracing():
        try:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            LOGGER.debug("[ Top 5 memory consumers ]")
            for stat in top_stats[:5]:
                LOGGER.debug(f"{stat}")
        except Exception as e:
            LOGGER.error(f"Error taking memory snapshot: {e}")


def log_memory_usage():
    """Log current memory usage information with detailed breakdown."""
    if psutil is None:
        return None

    try:
        process = psutil.Process()
        memory_info = process.memory_info()

        # Calculate memory usage in MB
        rss_mb = memory_info.rss / (1024 * 1024)
        vms_mb = memory_info.vms / (1024 * 1024)

        # Get memory maps for detailed breakdown
        try:
            memory_maps = process.memory_maps()
            private_mb = sum(m.private for m in memory_maps) / (1024 * 1024) if memory_maps else 0
            shared_mb = sum(m.shared for m in memory_maps) / (1024 * 1024) if memory_maps else 0
        except Exception:
            private_mb = 0
            shared_mb = 0

        # Get system memory info
        system_memory = psutil.virtual_memory()
        system_memory_percent = system_memory.percent
        available_mb = system_memory.available / (1024 * 1024)
        total_mb = system_memory.total / (1024 * 1024)

        # Get Python's memory allocator info
        gc_counts = gc.get_count()
        gc_objects = len(gc.get_objects())

        # Log detailed memory usage
        LOGGER.info(
            f"Memory usage: {rss_mb:.1f} MB (RSS), {vms_mb:.1f} MB (VMS), "
            f"{system_memory_percent:.1f}% of system memory"
        )
        LOGGER.info(
            f"System memory: {available_mb:.1f} MB available of {total_mb:.1f} MB total"
        )
        LOGGER.info(
            f"GC objects: {gc_objects}, GC counts: {gc_counts}"
        )

        # Log warning if memory usage is high
        if system_memory_percent > 80:
            LOGGER.warning(f"HIGH MEMORY USAGE: {system_memory_percent:.1f}% - Consider restarting the bot")
            # Try emergency memory cleanup
            optimize_memory(aggressive=True)

        return {
            "rss_mb": rss_mb,
            "vms_mb": vms_mb,
            "private_mb": private_mb,
            "shared_mb": shared_mb,
            "system_percent": system_memory_percent,
            "available_mb": available_mb,
            "total_mb": total_mb,
            "gc_objects": gc_objects,
        }
    except Exception as e:
        LOGGER.error(f"Error logging memory usage: {e}")
        return None


def memory_safe(func):
    """Decorator to make functions memory-safe.

    This decorator wraps a function with memory optimization before and after
    execution, and handles memory cleanup in case of exceptions.

    Args:
        func: The function to wrap

    Returns:
        The wrapped function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Optimize memory before execution
        optimize_memory(aggressive=False)

        try:
            # Execute the function
            result = await func(*args, **kwargs)

            # Optimize memory after execution
            optimize_memory(aggressive=True)

            # Log memory usage
            if psutil is not None:
                log_memory_usage()

            return result
        except Exception as e:
            # Log the error
            LOGGER.error(f"Error in {func.__name__}: {e}")

            # Try to recover memory in case of exception
            optimize_memory(aggressive=True)

            # Re-raise the exception
            raise

    return wrapper


def get_limit_message(limit_result):
    """Extract the error message from limit_checker result.

    This helper function handles both old-style string returns and
    new-style tuple returns from limit_checker.

    Args:
        limit_result: Result from limit_checker (str, tuple, or None)

    Returns:
        str: The error message, or None if no limit was exceeded
    """
    if limit_result is None:
        return None

    # If it's a tuple (message_object, error_message)
    if isinstance(limit_result, tuple) and len(limit_result) == 2:
        return limit_result[1]

    # If it's just a string message
    return limit_result


@memory_safe
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

    This function checks various limits based on the type of download and user configuration.
    It now includes auto-delete functionality for warning messages and memory optimization.

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
        None: If no limit exceeded
        tuple: (message_object, error_message) if limit exceeded
              The message_object is the Telegram message that was sent
              The error_message is the text of the warning message

    Note:
        Use the get_limit_message() helper function to extract just the error message
        from the return value if needed.
    """
    LOGGER.info("Checking Size Limit of link/file/folder/tasks...")

    # Force garbage collection before starting
    optimize_memory(aggressive=True)

    # Skip processing if size is 0 or negative
    if size <= 0:
        return None

    # Get user ID efficiently
    user_id = getattr(
        listener.message,
        "from_user",
        None
    )
    user_id = getattr(user_id, "id", None) if user_id else listener.message.chat.id

    # Skip limit check for sudo users
    if await CustomFilters.sudo("", listener.message):
        return None

    # Check time interval between tasks
    if wait_time := await timeval_check(user_id):
        error_msg = f"⚠️ Please wait {wait_time:.1f} seconds before starting another task."
        msg = await send_message(listener.message, error_msg)
        create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
        return msg, error_msg

    # Get common attributes once to avoid repeated getattr calls
    is_clone = getattr(listener, "isClone", False)
    is_jd = is_jd or getattr(listener, "is_jd", False)
    is_nzb = is_nzb or getattr(listener, "is_nzb", False)
    is_leech = getattr(listener, "is_leech", getattr(listener, "isLeech", False))

    # Check specific limits based on link type
    if is_clone and (CLONE_LIMIT := Config.CLONE_LIMIT):
        limit = CLONE_LIMIT * 1024**3
        if size > limit:
            error_msg = f"⚠️ Clone limit is {get_readable_file_size(limit)}. Your task has been cancelled."
            msg = await send_message(listener.message, error_msg)
            create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
            return msg, error_msg

    elif is_jd and (JD_LIMIT := Config.JD_LIMIT):
        limit = JD_LIMIT * 1024**3
        if size > limit:
            error_msg = f"⚠️ JDownloader limit is {get_readable_file_size(limit)}. Your task has been cancelled."
            msg = await send_message(listener.message, error_msg)
            create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
            return msg, error_msg

    elif is_nzb and (NZB_LIMIT := Config.NZB_LIMIT):
        limit = NZB_LIMIT * 1024**3
        if size > limit:
            error_msg = f"⚠️ NZB limit is {get_readable_file_size(limit)}. Your task has been cancelled."
            msg = await send_message(listener.message, error_msg)
            create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
            return msg, error_msg

    elif isMega and (MEGA_LIMIT := Config.MEGA_LIMIT):
        limit = MEGA_LIMIT * 1024**3
        if size > limit:
            error_msg = f"⚠️ Mega limit is {get_readable_file_size(limit)}. Your task has been cancelled."
            msg = await send_message(listener.message, error_msg)
            create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
            return msg, error_msg

    elif isDriveLink and (GDRIVE_LIMIT := Config.GDRIVE_LIMIT):
        limit = GDRIVE_LIMIT * 1024**3
        if size > limit:
            error_msg = f"⚠️ Google Drive limit is {get_readable_file_size(limit)}. Your task has been cancelled."
            msg = await send_message(listener.message, error_msg)
            create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
            return msg, error_msg

    elif isYtdlp:
        if (YTDLP_LIMIT := Config.YTDLP_LIMIT):
            limit = YTDLP_LIMIT * 1024**3
            if size > limit:
                error_msg = f"⚠️ YouTube limit is {get_readable_file_size(limit)}. Your task has been cancelled."
                msg = await send_message(listener.message, error_msg)
                create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
                return msg, error_msg

        if isPlayList and (PLAYLIST_LIMIT := Config.PLAYLIST_LIMIT) and isPlayList > PLAYLIST_LIMIT:
            error_msg = f"⚠️ Playlist limit is {PLAYLIST_LIMIT}. Your task has been cancelled."
            msg = await send_message(listener.message, error_msg)
            create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
            return msg, error_msg

    elif isTorrent and (TORRENT_LIMIT := Config.TORRENT_LIMIT):
        limit = TORRENT_LIMIT * 1024**3
        if size > limit:
            error_msg = f"⚠️ Torrent limit is {get_readable_file_size(limit)}. Your task has been cancelled."
            msg = await send_message(listener.message, error_msg)
            create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
            return msg, error_msg

    elif (DIRECT_LIMIT := Config.DIRECT_LIMIT):
        limit = DIRECT_LIMIT * 1024**3
        if size > limit:
            error_msg = f"⚠️ Direct link limit is {get_readable_file_size(limit)}. Your task has been cancelled."
            msg = await send_message(listener.message, error_msg)
            create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
            return msg, error_msg

    # Check leech limit
    if (LEECH_LIMIT := Config.LEECH_LIMIT) and is_leech:
        limit = LEECH_LIMIT * 1024**3
        if size > limit:
            error_msg = f"⚠️ Leech limit is {get_readable_file_size(limit)}. Your task has been cancelled."
            msg = await send_message(listener.message, error_msg)
            create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
            return msg, error_msg

    # Check storage threshold
    if (STORAGE_THRESHOLD := Config.STORAGE_THRESHOLD) and not is_clone:
        compress = getattr(listener, "compress", False)
        extract = getattr(listener, "extract", False)
        arch = compress or extract  # Simplified from any([compress, extract])
        limit = STORAGE_THRESHOLD * 1024**3
        acpt = await sync_to_async(check_storage_threshold, size, limit, arch)
        if not acpt:
            error_msg = f"⚠️ You must leave {get_readable_file_size(limit)} free storage. Your task has been cancelled."
            msg = await send_message(listener.message, error_msg)
            create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
            return msg, error_msg

    # Check daily task limit first
    if (DAILY_TASK_LIMIT := Config.DAILY_TASK_LIMIT) and await check_daily_task_limit(DAILY_TASK_LIMIT, listener):
        error_msg = f"⚠️ Daily task limit is {DAILY_TASK_LIMIT} tasks. Your task has been cancelled."
        msg = await send_message(listener.message, error_msg)
        create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
        return msg, error_msg

    # Check daily mirror limit
    if (DAILY_MIRROR_LIMIT := Config.DAILY_MIRROR_LIMIT) and not is_leech:
        limit = DAILY_MIRROR_LIMIT * 1024**3
        if await check_daily_mirror_limit(limit, listener, size):
            error_msg = f"⚠️ Daily mirror limit is {get_readable_file_size(limit)}. Your task has been cancelled."
            msg = await send_message(listener.message, error_msg)
            create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
            return msg, error_msg

    # Check daily leech limit
    if (DAILY_LEECH_LIMIT := Config.DAILY_LEECH_LIMIT) and is_leech:
        limit = DAILY_LEECH_LIMIT * 1024**3
        if await check_daily_leech_limit(limit, listener, size):
            error_msg = f"⚠️ Daily leech limit is {get_readable_file_size(limit)}. Your task has been cancelled."
            msg = await send_message(listener.message, error_msg)
            create_task(auto_delete_message(msg, time=300))  # Auto-delete after 5 minutes
            return msg, error_msg

    # Run memory optimization to free memory
    optimize_memory(aggressive=False)

    # Log memory usage after optimization
    if psutil is not None:
        log_memory_usage()

    return None


@memory_safe
async def check_daily_mirror_limit(limit, listener, size):
    """Check if user has exceeded daily mirror limit.

    Args:
        limit: Daily mirror limit in bytes
        listener: Listener object with user info
        size: Size of current task in bytes

    Returns:
        bool: True if limit exceeded, False otherwise
    """
    # Skip if size is 0 or negative
    if size <= 0:
        return False

    # Get user ID efficiently
    user_id = getattr(listener.message, "from_user", None)
    user_id = getattr(user_id, "id", None) if user_id else listener.message.chat.id

    # Get current mirror usage
    current_usage = await getdailytasks(user_id, check_mirror=True)

    # Check if adding this task would exceed the limit
    if size >= (limit - current_usage) or limit <= current_usage:
        return True

    # Update mirror usage if not a clone task
    is_clone = getattr(listener, "isClone", False)
    if not is_clone:
        await getdailytasks(user_id, upmirror=size)
        LOGGER.info(
            f"User: {user_id} | Daily Mirror Size: {get_readable_file_size(current_usage + size)}"
        )

    return False


@memory_safe
async def check_daily_leech_limit(limit, listener, size):
    """Check if user has exceeded daily leech limit.

    Args:
        limit: Daily leech limit in bytes
        listener: Listener object with user info
        size: Size of current task in bytes

    Returns:
        bool: True if limit exceeded, False otherwise
    """
    # Skip if size is 0 or negative
    if size <= 0:
        return False

    # Get user ID efficiently
    user_id = getattr(listener.message, "from_user", None)
    user_id = getattr(user_id, "id", None) if user_id else listener.message.chat.id

    # Get current leech usage
    current_usage = await getdailytasks(user_id, check_leech=True)

    # Check if adding this task would exceed the limit
    if size >= (limit - current_usage) or limit <= current_usage:
        return True

    # Update leech usage
    await getdailytasks(user_id, upleech=size)
    LOGGER.info(
        f"User: {user_id} | Daily Leech Size: {get_readable_file_size(current_usage + size)}"
    )

    return False


@memory_safe
async def check_daily_task_limit(limit, listener):
    """Check if user has exceeded daily task count limit.

    Args:
        limit: Maximum number of tasks per day
        listener: Listener object with user info

    Returns:
        bool: True if limit exceeded, False otherwise
    """
    # Get user ID efficiently
    user_id = getattr(listener.message, "from_user", None)
    user_id = getattr(user_id, "id", None) if user_id else listener.message.chat.id

    # Get current task count before incrementing
    current_tasks = await getdailytasks(user_id)

    # Check if limit is reached
    if current_tasks >= limit:
        return True

    # Increment task count
    new_count = await getdailytasks(user_id, increase_task=True)
    LOGGER.info(f"User: {user_id} | Daily Tasks: {new_count}")

    return False

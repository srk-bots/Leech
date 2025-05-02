from asyncio import Event

from bot import (
    LOGGER,
    non_queued_dl,
    non_queued_up,
    queue_dict_lock,
    queued_dl,
    queued_up,
)
from bot.core.config_manager import Config
from bot.helper.mirror_leech_utils.gdrive_utils.search import GoogleDriveSearch

from .bot_utils import get_telegraph_list, sync_to_async
from .files_utils import get_base_name
from .links_utils import is_gdrive_id


async def stop_duplicate_check(listener):
    # Skip duplicate check in certain conditions
    if (
        isinstance(listener.up_dest, int)
        or listener.select
        or (listener.up_dest and listener.up_dest.startswith("mtp:"))
        or not Config.STOP_DUPLICATE  # Only use global setting
        or listener.same_dir
    ):
        return False, None

    name = listener.name
    LOGGER.info(f"Checking if file/folder already exists: {name}")

    # Process name based on compression/extraction settings
    if listener.compress:
        # Check if it's the new compression feature or the old 7z compression
        if hasattr(listener, "compression_enabled") and listener.compression_enabled:
            # For the new compression feature, we keep the original name
            # as the compressed file will maintain its extension
            pass
        else:
            # For the old 7z compression
            name = f"{name}.7z"
    elif listener.extract:
        try:
            name = get_base_name(name)
        except Exception:
            name = None

    if not name:
        return False, None

    # Import here to avoid circular imports
    from bot.helper.ext_utils.file_tracker import check_duplicate, format_duplicate_message

    # Prepare parameters for duplicate check
    file_size = getattr(listener, "size", 0)
    file_path = getattr(listener, "path", "")
    telegram_id = ""
    torrent_hash = ""
    metadata = {}

    # Get torrent hash if available
    if hasattr(listener, "is_torrent") and listener.is_torrent:
        torrent_hash = getattr(listener, "hash", "")

    # Get telegram file ID if available
    if hasattr(listener, "message") and hasattr(listener.message, "document"):
        telegram_id = getattr(listener.message.document, "file_id", "")

    # Check for duplicates using our enhanced system
    is_duplicate, match_type, matches = await check_duplicate(
        file_name=name,
        file_size=file_size,
        file_path=file_path,
        telegram_id=telegram_id,
        torrent_hash=torrent_hash,
        metadata=metadata,
        user_id=listener.user_id
    )

    # If duplicate found, format message and return
    if is_duplicate and matches:
        msg, button = await format_duplicate_message(match_type, matches, name)
        return msg, button

    # If not a leech operation and uploading to Google Drive, also check Drive
    if not listener.is_leech and is_gdrive_id(listener.up_dest):
        LOGGER.info(f"Checking File/Folder if already in Drive: {name}")
        telegraph_content, contents_no = await sync_to_async(
            GoogleDriveSearch(stop_dup=True, no_multi=listener.is_clone).drive_list,
            name,
            listener.up_dest,
            listener.user_id,
        )
        if telegraph_content:
            msg = f"File/Folder is already available in Drive.\nHere are {contents_no} list results:"
            button = await get_telegraph_list(telegraph_content)
            return msg, button

    return False, None


async def check_running_tasks(listener, state="dl"):
    all_limit = Config.QUEUE_ALL
    state_limit = Config.QUEUE_DOWNLOAD if state == "dl" else Config.QUEUE_UPLOAD
    event = None
    is_over_limit = False
    async with queue_dict_lock:
        if state == "up" and listener.mid in non_queued_dl:
            non_queued_dl.remove(listener.mid)
        if (
            (all_limit or state_limit)
            and not listener.force_run
            and not (listener.force_upload and state == "up")
            and not (listener.force_download and state == "dl")
        ):
            dl_count = len(non_queued_dl)
            up_count = len(non_queued_up)
            t_count = dl_count if state == "dl" else up_count
            is_over_limit = (
                all_limit
                and dl_count + up_count >= all_limit
                and (not state_limit or t_count >= state_limit)
            ) or (state_limit and t_count >= state_limit)
            if is_over_limit:
                event = Event()
                if state == "dl":
                    queued_dl[listener.mid] = event
                else:
                    queued_up[listener.mid] = event
        if not is_over_limit:
            if state == "up":
                non_queued_up.add(listener.mid)
            else:
                non_queued_dl.add(listener.mid)

    return is_over_limit, event


async def start_dl_from_queued(mid: int):
    queued_dl[mid].set()
    del queued_dl[mid]
    non_queued_dl.add(mid)


async def start_up_from_queued(mid: int):
    queued_up[mid].set()
    del queued_up[mid]
    non_queued_up.add(mid)


async def start_from_queued():
    if all_limit := Config.QUEUE_ALL:
        dl_limit = Config.QUEUE_DOWNLOAD
        up_limit = Config.QUEUE_UPLOAD
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            all_ = dl + up
            if all_ < all_limit:
                f_tasks = all_limit - all_
                if queued_up and (not up_limit or up < up_limit):
                    for index, mid in enumerate(list(queued_up.keys()), start=1):
                        await start_up_from_queued(mid)
                        f_tasks -= 1
                        if f_tasks == 0 or (up_limit and index >= up_limit - up):
                            break
                if queued_dl and (not dl_limit or dl < dl_limit) and f_tasks != 0:
                    for index, mid in enumerate(list(queued_dl.keys()), start=1):
                        await start_dl_from_queued(mid)
                        if (dl_limit and index >= dl_limit - dl) or index == f_tasks:
                            break
        return

    if up_limit := Config.QUEUE_UPLOAD:
        async with queue_dict_lock:
            up = len(non_queued_up)
            if queued_up and up < up_limit:
                f_tasks = up_limit - up
                for index, mid in enumerate(list(queued_up.keys()), start=1):
                    await start_up_from_queued(mid)
                    if index == f_tasks:
                        break
    else:
        async with queue_dict_lock:
            if queued_up:
                for mid in list(queued_up.keys()):
                    await start_up_from_queued(mid)

    if dl_limit := Config.QUEUE_DOWNLOAD:
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            if queued_dl and dl < dl_limit:
                f_tasks = dl_limit - dl
                for index, mid in enumerate(list(queued_dl.keys()), start=1):
                    await start_dl_from_queued(mid)
                    if index == f_tasks:
                        break
    else:
        async with queue_dict_lock:
            if queued_dl:
                for mid in list(queued_dl.keys()):
                    await start_dl_from_queued(mid)

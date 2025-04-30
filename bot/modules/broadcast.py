import asyncio
import traceback
from logging import getLogger
from time import time

from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked

from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.db_handler import database
from bot.helper.ext_utils.status_utils import get_readable_time
from bot.helper.telegram_helper.message_utils import edit_message, send_message

LOGGER = getLogger(__name__)

# Track broadcast state - use a dictionary to track by user ID
# This allows multiple admins to use broadcast without interfering with each other
broadcast_awaiting_message = {}


@new_task
async def broadcast(_, message):
    """
    Original broadcast function that broadcasts a replied-to message

    This function is kept for backward compatibility
    """
    # Check if user is owner
    if not await is_owner(message):
        LOGGER.warning(
            f"Non-owner user {message.from_user.id} attempted to use broadcast command"
        )
        return

    if not message.reply_to_message:
        await send_message(
            message,
            "Reply to any message to broadcast messages to users in Bot PM.",
        )
        return

    total, successful, blocked, unsuccessful = 0, 0, 0, 0
    start_time = time()
    updater = time()
    broadcast_message = await send_message(message, "Broadcast in progress...")

    # Get the message to broadcast
    msg_to_broadcast = message.reply_to_message

    try:
        pm_users = await database.get_pm_uids()
        if not pm_users:
            LOGGER.warning("No users found in database for broadcast")
            await edit_message(broadcast_message, "No users found in database.")
            return

        LOGGER.info(f"Starting broadcast to {len(pm_users)} users")

        for uid in pm_users:
            try:
                # Use copy method which handles all media types automatically
                await msg_to_broadcast.copy(uid)
                successful += 1
                LOGGER.debug(f"Successfully sent broadcast to user {uid}")
            except FloodWait as e:
                LOGGER.warning(
                    f"FloodWait detected during broadcast: {e.value} seconds"
                )
                await asyncio.sleep(e.value)
                try:
                    await msg_to_broadcast.copy(uid)
                    successful += 1
                    LOGGER.debug(
                        f"Successfully sent broadcast to user {uid} after FloodWait"
                    )
                except Exception as retry_err:
                    LOGGER.error(
                        f"Failed to send broadcast to {uid} after FloodWait: {retry_err!s}"
                    )
                    unsuccessful += 1
            except (UserIsBlocked, InputUserDeactivated) as user_err:
                LOGGER.info(f"Removing user {uid} from database: {user_err!s}")
                await database.rm_pm_user(uid)
                blocked += 1
            except Exception as e:
                LOGGER.error(f"Error sending broadcast to {uid}: {e!s}")
                unsuccessful += 1

            total += 1

            if (time() - updater) > 10:
                status = generate_status(total, successful, blocked, unsuccessful)
                await edit_message(broadcast_message, status)
                updater = time()
                LOGGER.info(
                    f"Broadcast progress: {successful}/{total} successful, {blocked} blocked, {unsuccessful} failed"
                )

        elapsed_time = get_readable_time(time() - start_time, True)
        status = generate_status(
            total, successful, blocked, unsuccessful, elapsed_time
        )
        await edit_message(broadcast_message, status)
        LOGGER.info(
            f"Broadcast completed: {successful}/{total} successful, {blocked} blocked, {unsuccessful} failed, time: {elapsed_time}"
        )

    except Exception as e:
        error_traceback = traceback.format_exc()
        LOGGER.error(f"Broadcast failed with error: {e!s}\n{error_traceback}")
        await edit_message(
            broadcast_message,
            f"<b>❌ Broadcast failed with error:</b>\n<code>{e!s}</code>",
        )
        return


# Enhanced broadcast function that supports a two-step process and multiple media types
@new_task
async def broadcast_media(client, message, options=None):
    """
    Enhanced broadcast function with support for various media types

    Args:
        client: The bot client
        message: The message object
        options: If None, this is the first step. If True, this is the second step.
    """
    global broadcast_awaiting_message

    # Only allow owner to use this command
    if not await is_owner(message):
        LOGGER.warning(
            f"Non-owner user {message.from_user.id} attempted to use broadcast command"
        )
        return

    # First step: Ask for the message to broadcast
    if options is None:
        user_id = message.from_user.id
        LOGGER.info(f"Broadcast command initiated by owner {user_id}")
        # Set this user as waiting for broadcast message
        broadcast_awaiting_message[user_id] = True
        await send_message(
            message,
            "<b>🎙️ Send Any Message to Broadcast in HTML\n\nTo Cancel: /cancelbc</b>",
            markdown=False,  # Use HTML mode (not markdown)
        )
        # Set up handler for the next message
        # This is handled by the core handlers system
        return

    # Check for cancellation
    if message.text and message.text == "/cancelbc":
        user_id = message.from_user.id
        LOGGER.info(f"Broadcast cancelled by owner {user_id}")
        # Remove this user from the waiting list
        if user_id in broadcast_awaiting_message:
            del broadcast_awaiting_message[user_id]
        await send_message(
            message,
            "<b>❌ Broadcast Cancelled</b>",
            markdown=False,  # Use HTML mode (not markdown)
        )
        return

    # Check if we're actually waiting for a message
    user_id = message.from_user.id
    if options is True and user_id not in broadcast_awaiting_message:
        LOGGER.debug(
            f"Ignoring message from owner {user_id} as no broadcast is in progress for this user"
        )
        return

    # Initialize counters
    total, successful, blocked, unsuccessful = 0, 0, 0, 0
    start_time = time()
    updater = time()
    broadcast_message = await send_message(message, "Broadcast in progress...")

    # Get all PM users
    try:
        # Reset the broadcast state for this user
        user_id = message.from_user.id
        if user_id in broadcast_awaiting_message:
            del broadcast_awaiting_message[user_id]

        pm_users = await database.get_pm_uids()
        if not pm_users:
            LOGGER.warning("No users found in database for broadcast")
            await edit_message(broadcast_message, "No users found in database.")
            return

        LOGGER.info(f"Starting broadcast to {len(pm_users)} users")

        # Determine message type and prepare for broadcast
        # Log message details for debugging
        msg_type = "unknown"
        if message.text:
            msg_type = "text"
        elif message.photo:
            msg_type = "photo"
        elif message.video:
            msg_type = "video"
        elif message.document:
            msg_type = "document"
        elif message.audio:
            msg_type = "audio"
        elif message.voice:
            msg_type = "voice"
        elif message.sticker:
            msg_type = "sticker"
        elif message.animation:
            msg_type = "animation"

        LOGGER.info(f"Broadcasting message of type: {msg_type}")

        for uid in pm_users:
            try:
                # Copy the message with all its media and formatting
                await message.copy(uid)
                successful += 1
                LOGGER.debug(f"Successfully sent broadcast to user {uid}")
            except FloodWait as e:
                LOGGER.warning(
                    f"FloodWait detected during broadcast: {e.value} seconds"
                )
                await asyncio.sleep(e.value)
                try:
                    await message.copy(uid)
                    successful += 1
                    LOGGER.debug(
                        f"Successfully sent broadcast to user {uid} after FloodWait"
                    )
                except Exception as retry_err:
                    LOGGER.error(
                        f"Failed to send broadcast to {uid} after FloodWait: {retry_err!s}"
                    )
                    unsuccessful += 1
            except (UserIsBlocked, InputUserDeactivated) as user_err:
                LOGGER.info(f"Removing user {uid} from database: {user_err!s}")
                await database.rm_pm_user(uid)
                blocked += 1
            except Exception as e:
                LOGGER.error(f"Error sending broadcast to {uid}: {e!s}")
                unsuccessful += 1

            total += 1

            if (time() - updater) > 10:
                status = generate_status(total, successful, blocked, unsuccessful)
                await edit_message(broadcast_message, status)
                updater = time()
                LOGGER.info(
                    f"Broadcast progress: {successful}/{total} successful, {blocked} blocked, {unsuccessful} failed"
                )

        elapsed_time = get_readable_time(time() - start_time, True)
        status = generate_status(
            total, successful, blocked, unsuccessful, elapsed_time
        )
        await edit_message(broadcast_message, status)
        LOGGER.info(
            f"Broadcast completed: {successful}/{total} successful, {blocked} blocked, {unsuccessful} failed, time: {elapsed_time}"
        )

    except Exception as e:
        error_traceback = traceback.format_exc()
        LOGGER.error(f"Broadcast failed with error: {e!s}\n{error_traceback}")
        await edit_message(
            broadcast_message,
            f"<b>❌ Broadcast failed with error:</b>\n<code>{e!s}</code>",
        )
        return


def generate_status(total, successful, blocked, unsuccessful, elapsed_time=""):
    status = "<b>Broadcast Stats :</b>\n\n"
    status += f"<b>• Total users:</b> {total}\n"
    status += f"<b>• Success:</b> {successful}\n"
    status += f"<b>• Blocked or deleted:</b> {blocked}\n"
    status += f"<b>• Unsuccessful attempts:</b> {unsuccessful}"
    if elapsed_time:
        status += f"\n\n<b>Elapsed Time:</b> {elapsed_time}"
    return status


async def is_owner(message):
    """Check if the user is the owner of the bot"""
    from bot.helper.telegram_helper.filters import CustomFilters

    return await CustomFilters.owner("", message)

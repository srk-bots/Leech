import asyncio
import traceback
from time import time
from logging import getLogger

from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked
from pyrogram import enums

from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.db_handler import database
from bot.helper.ext_utils.status_utils import get_readable_time
from bot.helper.telegram_helper.message_utils import edit_message, send_message
from bot.core.aeon_client import TgClient
from bot.core.config_manager import Config

LOGGER = getLogger(__name__)

# Track broadcast state
broadcast_awaiting_message = False


@new_task
async def broadcast(_, message):
    """
    Original broadcast function that broadcasts a replied-to message

    This function is kept for backward compatibility
    """
    # Check if user is owner
    if not await is_owner(message):
        LOGGER.warning(f"Non-owner user {message.from_user.id} attempted to use broadcast command")
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
                LOGGER.warning(f"FloodWait detected during broadcast: {e.value} seconds")
                await asyncio.sleep(e.value)
                try:
                    await msg_to_broadcast.copy(uid)
                    successful += 1
                    LOGGER.debug(f"Successfully sent broadcast to user {uid} after FloodWait")
                except Exception as retry_err:
                    LOGGER.error(f"Failed to send broadcast to {uid} after FloodWait: {str(retry_err)}")
                    unsuccessful += 1
            except (UserIsBlocked, InputUserDeactivated) as user_err:
                LOGGER.info(f"Removing user {uid} from database: {str(user_err)}")
                await database.rm_pm_user(uid)
                blocked += 1
            except Exception as e:
                LOGGER.error(f"Error sending broadcast to {uid}: {str(e)}")
                unsuccessful += 1

            total += 1

            if (time() - updater) > 10:
                status = generate_status(total, successful, blocked, unsuccessful)
                await edit_message(broadcast_message, status)
                updater = time()
                LOGGER.info(f"Broadcast progress: {successful}/{total} successful, {blocked} blocked, {unsuccessful} failed")

        elapsed_time = get_readable_time(time() - start_time, True)
        status = generate_status(total, successful, blocked, unsuccessful, elapsed_time)
        await edit_message(broadcast_message, status)
        LOGGER.info(f"Broadcast completed: {successful}/{total} successful, {blocked} blocked, {unsuccessful} failed, time: {elapsed_time}")

    except Exception as e:
        error_traceback = traceback.format_exc()
        LOGGER.error(f"Broadcast failed with error: {str(e)}\n{error_traceback}")
        await edit_message(broadcast_message, f"<b>❌ Broadcast failed with error:</b>\n<code>{str(e)}</code>")
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
    # Only allow owner to use this command
    if not await is_owner(message):
        LOGGER.warning(f"Non-owner user {message.from_user.id} attempted to use broadcast command")
        return

    # First step: Ask for the message to broadcast
    if options is None:
        global broadcast_awaiting_message
        LOGGER.info(f"Broadcast command initiated by owner {message.from_user.id}")
        broadcast_awaiting_message = True
        await send_message(
            message,
            "<b>🎙️ Send Any Message to Broadcast in HTML\n\nTo Cancel: /cancelbc</b>",
            parse_mode="html",
        )
        # Set up handler for the next message
        # This is handled by the core handlers system
        return

    # Check for cancellation
    if message.text and message.text == "/cancelbc":
        global broadcast_awaiting_message
        LOGGER.info(f"Broadcast cancelled by owner {message.from_user.id}")
        broadcast_awaiting_message = False
        await send_message(
            message,
            "<b>❌ Broadcast Cancelled</b>",
            parse_mode="html",
        )
        return

    # Check if we're actually waiting for a message
    if options is True and not broadcast_awaiting_message:
        LOGGER.debug(f"Ignoring message from owner {message.from_user.id} as no broadcast is in progress")
        return

    # Initialize counters
    total, successful, blocked, unsuccessful = 0, 0, 0, 0
    start_time = time()
    updater = time()
    broadcast_message = await send_message(message, "Broadcast in progress...")

    # Get all PM users
    try:
        # Reset the broadcast state
        global broadcast_awaiting_message
        broadcast_awaiting_message = False

        pm_users = await database.get_pm_uids()
        if not pm_users:
            LOGGER.warning("No users found in database for broadcast")
            await edit_message(broadcast_message, "No users found in database.")
            return

        LOGGER.info(f"Starting broadcast to {len(pm_users)} users")

        # Determine message type and prepare for broadcast
        for uid in pm_users:
            try:
                # Copy the message with all its media and formatting
                await message.copy(uid)
                successful += 1
                LOGGER.debug(f"Successfully sent broadcast to user {uid}")
            except FloodWait as e:
                LOGGER.warning(f"FloodWait detected during broadcast: {e.value} seconds")
                await asyncio.sleep(e.value)
                try:
                    await message.copy(uid)
                    successful += 1
                    LOGGER.debug(f"Successfully sent broadcast to user {uid} after FloodWait")
                except Exception as retry_err:
                    LOGGER.error(f"Failed to send broadcast to {uid} after FloodWait: {str(retry_err)}")
                    unsuccessful += 1
            except (UserIsBlocked, InputUserDeactivated) as user_err:
                LOGGER.info(f"Removing user {uid} from database: {str(user_err)}")
                await database.rm_pm_user(uid)
                blocked += 1
            except Exception as e:
                LOGGER.error(f"Error sending broadcast to {uid}: {str(e)}")
                unsuccessful += 1

            total += 1

            if (time() - updater) > 10:
                status = generate_status(total, successful, blocked, unsuccessful)
                await edit_message(broadcast_message, status)
                updater = time()
                LOGGER.info(f"Broadcast progress: {successful}/{total} successful, {blocked} blocked, {unsuccessful} failed")

        elapsed_time = get_readable_time(time() - start_time, True)
        status = generate_status(total, successful, blocked, unsuccessful, elapsed_time)
        await edit_message(broadcast_message, status)
        LOGGER.info(f"Broadcast completed: {successful}/{total} successful, {blocked} blocked, {unsuccessful} failed, time: {elapsed_time}")

    except Exception as e:
        error_traceback = traceback.format_exc()
        LOGGER.error(f"Broadcast failed with error: {str(e)}\n{error_traceback}")
        await edit_message(broadcast_message, f"<b>❌ Broadcast failed with error:</b>\n<code>{str(e)}</code>")
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

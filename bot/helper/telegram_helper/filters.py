from pyrogram.filters import create

from bot import LOGGER, auth_chats, sudo_users, user_data
from bot.core.config_manager import Config


class CustomFilters:
    async def owner_filter(self, _, update):
        # Check if update is None
        if not update:
            LOGGER.warning("Update is None in owner_filter")
            return False

        # Safely get user and handle None case
        user = update.from_user or update.sender_chat
        if not user:
            LOGGER.warning("Both from_user and sender_chat are None in owner_filter")
            return False

        return user.id == Config.OWNER_ID

    owner = create(owner_filter)

    async def authorized_user(self, _, update):
        # Check if update is None or doesn't have required attributes
        if not update or not hasattr(update, "chat") or not update.chat:
            LOGGER.warning(
                "Update missing required attributes in authorized_user filter",
            )
            return False

        # Safely get user and handle None case
        user = update.from_user or update.sender_chat
        if not user:
            LOGGER.warning(
                "Both from_user and sender_chat are None in authorized_user filter",
            )
            return False

        # Now we can safely access user.id
        uid = user.id
        chat_id = update.chat.id
        thread_id = (
            update.message_thread_id
            if hasattr(update, "is_topic_message") and update.is_topic_message
            else None
        )

        return bool(
            uid == Config.OWNER_ID
            or (
                uid in user_data
                and (
                    user_data[uid].get("AUTH", False)
                    or user_data[uid].get("SUDO", False)
                )
            )
            or (
                chat_id in user_data
                and user_data[chat_id].get("AUTH", False)
                and (
                    thread_id is None
                    or thread_id in user_data[chat_id].get("thread_ids", [])
                )
            )
            or uid in sudo_users
            or uid in auth_chats
            or (
                chat_id in auth_chats
                and (
                    (
                        auth_chats[chat_id]
                        and thread_id
                        and thread_id in auth_chats[chat_id]
                    )
                    or not auth_chats[chat_id]
                )
            ),
        )

    authorized = create(authorized_user)

    async def sudo_user(self, _, update):
        # Check if update is None or doesn't have required attributes
        if not update:
            LOGGER.warning("Update is None in sudo_user filter")
            return False

        # Safely get user and handle None case
        user = update.from_user or update.sender_chat
        if not user:
            LOGGER.warning(
                "Both from_user and sender_chat are None in sudo_user filter",
            )
            return False

        uid = user.id
        return bool(
            uid == Config.OWNER_ID
            or (uid in user_data and user_data[uid].get("SUDO"))
            or uid in sudo_users,
        )

    sudo = create(sudo_user)

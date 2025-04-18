import logging
from asyncio import sleep
from functools import partial

from pyrogram.filters import create
from pyrogram.handlers import MessageHandler

from bot import user_data
from bot.core.config_manager import Config
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.db_handler import database
from bot.helper.ext_utils.help_messages import media_tools_text
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_message,
    edit_message,
    send_message,
)

LOGGER = logging.getLogger(__name__)

handler_dict = {}
merge_config_page = 0  # Global variable to track merge_config page


async def get_media_tools_settings(from_user, stype="main", page_no=0):
    """Get media tools settings for a user."""
    user_id = from_user.id
    user_name = from_user.mention(style="html")
    buttons = ButtonMaker()
    user_dict = user_data.get(user_id, {})

    if stype == "main":
        # Main Media Tools menu
        buttons.data_button("Watermark", f"mediatools {user_id} watermark")
        buttons.data_button("Merge", f"mediatools {user_id} merge")
        buttons.data_button("Remove All", f"mediatools {user_id} remove_all")
        buttons.data_button("Reset All", f"mediatools {user_id} reset_all")
        buttons.data_button("Close", f"mediatools {user_id} close", "footer")
        btns = buttons.build_menu(2)

        # Check if watermark is enabled for the user
        user_watermark_enabled = user_dict.get("WATERMARK_ENABLED", False)
        owner_watermark_enabled = Config.WATERMARK_ENABLED

        if user_watermark_enabled:
            watermark_status = "✅ Enabled (User)"
        elif owner_watermark_enabled:
            watermark_status = "✅ Enabled (Global)"
        else:
            watermark_status = "❌ Disabled"

        # Get watermark text based on priority
        user_has_text = "WATERMARK_KEY" in user_dict and user_dict["WATERMARK_KEY"]
        owner_has_text = Config.WATERMARK_KEY

        if user_has_text:
            watermark_text = f"{user_dict['WATERMARK_KEY']} (User)"
        elif user_watermark_enabled and owner_has_text:
            watermark_text = f"{Config.WATERMARK_KEY} (Global)"
        elif owner_watermark_enabled and owner_has_text:
            watermark_text = f"{Config.WATERMARK_KEY} (Global)"
        else:
            watermark_text = "None"

        # Check if merge is enabled for the user
        user_merge_enabled = user_dict.get("MERGE_ENABLED", False)
        owner_merge_enabled = Config.MERGE_ENABLED

        if user_merge_enabled:
            merge_status = "✅ Enabled (User)"
        elif owner_merge_enabled:
            merge_status = "✅ Enabled (Global)"
        else:
            merge_status = "❌ Disabled"

        text = f"""⌬ <b>Media Tools Settings :</b>
┟ <b>Name</b> → {user_name}
┃
┠ <b>Watermark</b> → {watermark_status}
┠ <b>Watermark Text</b> → <code>{watermark_text}</code>
┃
┠ <b>Merge</b> → {merge_status}
┖ <b>Priority</b> → {user_dict.get("MEDIA_TOOLS_PRIORITY", "Default Order")}"""

    elif stype == "watermark":
        # Watermark settings menu
        watermark_enabled = user_dict.get("WATERMARK_ENABLED", False)
        buttons.data_button(
            "✅ Enabled" if watermark_enabled else "❌ Disabled",
            f"mediatools {user_id} tog WATERMARK_ENABLED {'f' if watermark_enabled else 't'}",
        )
        buttons.data_button("Configure", f"mediatools {user_id} watermark_config")
        buttons.data_button(
            "Set Priority", f"mediatools {user_id} menu WATERMARK_PRIORITY"
        )
        buttons.data_button("Reset", f"mediatools {user_id} reset_watermark")
        buttons.data_button("Remove", f"mediatools {user_id} remove_watermark")
        buttons.data_button("Back", f"mediatools {user_id} back", "footer")
        buttons.data_button("Close", f"mediatools {user_id} close", "footer")
        btns = buttons.build_menu(2)

        # Get watermark text based on priority
        user_has_text = "WATERMARK_KEY" in user_dict and user_dict["WATERMARK_KEY"]
        owner_has_text = Config.WATERMARK_KEY

        if user_has_text:
            watermark_text = f"{user_dict['WATERMARK_KEY']} (User)"
        elif watermark_enabled and owner_has_text:
            watermark_text = f"{Config.WATERMARK_KEY} (Global)"
        elif Config.WATERMARK_ENABLED and owner_has_text:
            watermark_text = f"{Config.WATERMARK_KEY} (Global)"
        else:
            watermark_text = "None"

        # Get watermark position based on priority
        user_has_position = (
            "WATERMARK_POSITION" in user_dict and user_dict["WATERMARK_POSITION"]
        )
        owner_has_position = Config.WATERMARK_POSITION

        if user_has_position:
            watermark_position = f"{user_dict['WATERMARK_POSITION']} (User)"
        elif watermark_enabled and owner_has_position:
            watermark_position = f"{Config.WATERMARK_POSITION} (Global)"
        elif Config.WATERMARK_ENABLED and owner_has_position:
            watermark_position = f"{Config.WATERMARK_POSITION} (Global)"
        else:
            watermark_position = "top_left (Default)"

        # Get watermark size based on priority
        user_has_size = "WATERMARK_SIZE" in user_dict and user_dict["WATERMARK_SIZE"]
        owner_has_size = Config.WATERMARK_SIZE

        if user_has_size:
            watermark_size = f"{user_dict['WATERMARK_SIZE']} (User)"
        elif watermark_enabled and owner_has_size:
            watermark_size = f"{Config.WATERMARK_SIZE} (Global)"
        elif Config.WATERMARK_ENABLED and owner_has_size:
            watermark_size = f"{Config.WATERMARK_SIZE} (Global)"
        else:
            watermark_size = "20 (Default)"

        # Get watermark color based on priority
        user_has_color = "WATERMARK_COLOR" in user_dict and user_dict["WATERMARK_COLOR"]
        owner_has_color = Config.WATERMARK_COLOR

        if user_has_color:
            watermark_color = f"{user_dict['WATERMARK_COLOR']} (User)"
        elif watermark_enabled and owner_has_color:
            watermark_color = f"{Config.WATERMARK_COLOR} (Global)"
        elif Config.WATERMARK_ENABLED and owner_has_color:
            watermark_color = f"{Config.WATERMARK_COLOR} (Global)"
        else:
            watermark_color = "white (Default)"

        # Get watermark font based on priority
        user_has_font = "WATERMARK_FONT" in user_dict and user_dict["WATERMARK_FONT"]
        owner_has_font = Config.WATERMARK_FONT

        if user_has_font:
            watermark_font = f"{user_dict['WATERMARK_FONT']} (User)"
        elif watermark_enabled and owner_has_font:
            watermark_font = f"{Config.WATERMARK_FONT} (Global)"
        elif Config.WATERMARK_ENABLED and owner_has_font:
            watermark_font = f"{Config.WATERMARK_FONT} (Global)"
        else:
            watermark_font = "default.otf (Default)"

        # Get watermark threading status
        user_has_threading = "WATERMARK_THREADING" in user_dict
        if user_has_threading:
            threading_status = (
                "✅ Enabled (User)"
                if user_dict["WATERMARK_THREADING"]
                else "❌ Disabled (User)"
            )
        elif Config.WATERMARK_THREADING:
            threading_status = "✅ Enabled (Global)"
        else:
            threading_status = "❌ Disabled"

        # Get thread number
        user_has_thread_number = (
            "WATERMARK_THREAD_NUMBER" in user_dict
            and user_dict["WATERMARK_THREAD_NUMBER"]
        )
        if user_has_thread_number:
            thread_number = f"{user_dict['WATERMARK_THREAD_NUMBER']} (User)"
        elif Config.WATERMARK_THREAD_NUMBER:
            thread_number = f"{Config.WATERMARK_THREAD_NUMBER} (Global)"
        else:
            thread_number = "4 (Default)"

        text = f"""⌬ <b>Watermark Settings :</b>
┟ <b>Name</b> → {user_name}
┃
┠ <b>Status</b> → {"✅ Enabled" if watermark_enabled else "❌ Disabled"}
┠ <b>Text</b> → <code>{watermark_text}</code>
┠ <b>Position</b> → <code>{watermark_position}</code>
┠ <b>Size</b> → <code>{watermark_size}</code>
┠ <b>Color</b> → <code>{watermark_color}</code>
┠ <b>Font</b> → <code>{watermark_font}</code>
┠ <b>Threading</b> → {threading_status}
┖ <b>Thread Number</b> → <code>{thread_number}</code>"""

    elif stype == "watermark_config":
        # Watermark configuration menu
        buttons.data_button("Set Text", f"mediatools {user_id} menu WATERMARK_KEY")
        buttons.data_button(
            "Set Position", f"mediatools {user_id} menu WATERMARK_POSITION"
        )
        buttons.data_button("Set Size", f"mediatools {user_id} menu WATERMARK_SIZE")
        buttons.data_button("Set Color", f"mediatools {user_id} menu WATERMARK_COLOR")
        buttons.data_button("Set Font", f"mediatools {user_id} menu WATERMARK_FONT")
        buttons.data_button("Back", f"mediatools {user_id} watermark", "footer")
        buttons.data_button("Close", f"mediatools {user_id} close", "footer")
        btns = buttons.build_menu(2)

        # Get watermark text based on priority
        watermark_enabled = user_dict.get("WATERMARK_ENABLED", False)
        user_has_text = "WATERMARK_KEY" in user_dict and user_dict["WATERMARK_KEY"]
        owner_has_text = Config.WATERMARK_KEY

        if user_has_text:
            watermark_text = f"{user_dict['WATERMARK_KEY']} (User)"
        elif watermark_enabled and owner_has_text:
            watermark_text = f"{Config.WATERMARK_KEY} (Global)"
        elif Config.WATERMARK_ENABLED and owner_has_text:
            watermark_text = f"{Config.WATERMARK_KEY} (Global)"
        else:
            watermark_text = "None"

        # Get watermark position based on priority
        user_has_position = (
            "WATERMARK_POSITION" in user_dict and user_dict["WATERMARK_POSITION"]
        )
        owner_has_position = Config.WATERMARK_POSITION

        if user_has_position:
            watermark_position = f"{user_dict['WATERMARK_POSITION']} (User)"
        elif watermark_enabled and owner_has_position:
            watermark_position = f"{Config.WATERMARK_POSITION} (Global)"
        elif Config.WATERMARK_ENABLED and owner_has_position:
            watermark_position = f"{Config.WATERMARK_POSITION} (Global)"
        else:
            watermark_position = "top_left (Default)"

        # Get watermark size based on priority
        user_has_size = "WATERMARK_SIZE" in user_dict and user_dict["WATERMARK_SIZE"]
        owner_has_size = Config.WATERMARK_SIZE

        if user_has_size:
            watermark_size = f"{user_dict['WATERMARK_SIZE']} (User)"
        elif watermark_enabled and owner_has_size:
            watermark_size = f"{Config.WATERMARK_SIZE} (Global)"
        elif Config.WATERMARK_ENABLED and owner_has_size:
            watermark_size = f"{Config.WATERMARK_SIZE} (Global)"
        else:
            watermark_size = "20 (Default)"

        # Get watermark color based on priority
        user_has_color = "WATERMARK_COLOR" in user_dict and user_dict["WATERMARK_COLOR"]
        owner_has_color = Config.WATERMARK_COLOR

        if user_has_color:
            watermark_color = f"{user_dict['WATERMARK_COLOR']} (User)"
        elif watermark_enabled and owner_has_color:
            watermark_color = f"{Config.WATERMARK_COLOR} (Global)"
        elif Config.WATERMARK_ENABLED and owner_has_color:
            watermark_color = f"{Config.WATERMARK_COLOR} (Global)"
        else:
            watermark_color = "white (Default)"

        # Get watermark font based on priority
        user_has_font = "WATERMARK_FONT" in user_dict and user_dict["WATERMARK_FONT"]
        owner_has_font = Config.WATERMARK_FONT

        if user_has_font:
            watermark_font = f"{user_dict['WATERMARK_FONT']} (User)"
        elif watermark_enabled and owner_has_font:
            watermark_font = f"{Config.WATERMARK_FONT} (Global)"
        elif Config.WATERMARK_ENABLED and owner_has_font:
            watermark_font = f"{Config.WATERMARK_FONT} (Global)"
        else:
            watermark_font = "default.otf (Default)"

        # Get watermark threading status
        user_has_threading = "WATERMARK_THREADING" in user_dict
        if user_has_threading:
            threading_status = (
                "✅ Enabled (User)"
                if user_dict["WATERMARK_THREADING"]
                else "❌ Disabled (User)"
            )
        elif Config.WATERMARK_THREADING:
            threading_status = "✅ Enabled (Global)"
        else:
            threading_status = "❌ Disabled"

        # Get thread number
        user_has_thread_number = (
            "WATERMARK_THREAD_NUMBER" in user_dict
            and user_dict["WATERMARK_THREAD_NUMBER"]
        )
        if user_has_thread_number:
            thread_number = f"{user_dict['WATERMARK_THREAD_NUMBER']} (User)"
        elif Config.WATERMARK_THREAD_NUMBER:
            thread_number = f"{Config.WATERMARK_THREAD_NUMBER} (Global)"
        else:
            thread_number = "4 (Default)"

        text = f"""⌬ <b>Configure Watermark :</b>
┟ <b>Name</b> → {user_name}
┃
┠ <b>Text</b> → <code>{watermark_text}</code>
┠ <b>Position</b> → <code>{watermark_position}</code>
┠ <b>Size</b> → <code>{watermark_size}</code>
┠ <b>Color</b> → <code>{watermark_color}</code>
┠ <b>Font</b> → <code>{watermark_font}</code>
┠ <b>Threading</b> → {threading_status}
┖ <b>Thread Number</b> → <code>{thread_number}</code>"""

    elif stype == "merge":
        # Merge settings menu
        merge_enabled = user_dict.get("MERGE_ENABLED", False)
        buttons.data_button(
            "✅ Enabled" if merge_enabled else "❌ Disabled",
            f"mediatools {user_id} tog MERGE_ENABLED {'f' if merge_enabled else 't'}",
        )

        # Add Concat Demuxer/Filter Complex toggle
        concat_enabled = user_dict.get("CONCAT_DEMUXER_ENABLED", True)
        filter_enabled = user_dict.get("FILTER_COMPLEX_ENABLED", True)

        # Show a single toggle button that cycles through the states
        if concat_enabled and filter_enabled:
            # Both enabled - next state is concat only
            buttons.data_button(
                "Concat & Filter: Both ON",
                f"mediatools {user_id} toggle_concat_filter concat",
            )
        elif concat_enabled and not filter_enabled:
            # Only concat enabled - next state is filter only
            buttons.data_button(
                "Concat: ON | Filter: OFF",
                f"mediatools {user_id} toggle_concat_filter filter",
            )
        elif not concat_enabled and filter_enabled:
            # Only filter enabled - next state is both enabled
            buttons.data_button(
                "Concat: OFF | Filter: ON",
                f"mediatools {user_id} toggle_concat_filter both",
            )
        else:
            # Both disabled - next state is both enabled
            buttons.data_button(
                "Concat & Filter: Both OFF",
                f"mediatools {user_id} toggle_concat_filter both",
            )

        buttons.data_button("Configure", f"mediatools {user_id} merge_config")
        buttons.data_button("Set Priority", f"mediatools {user_id} menu MERGE_PRIORITY")
        buttons.data_button(
            "Remove Original", f"mediatools {user_id} menu MERGE_REMOVE_ORIGINAL"
        )
        buttons.data_button("Reset", f"mediatools {user_id} reset_merge")
        buttons.data_button("Remove", f"mediatools {user_id} remove_merge")
        buttons.data_button("Back", f"mediatools {user_id} back", "footer")
        buttons.data_button("Close", f"mediatools {user_id} close", "footer")
        btns = buttons.build_menu(2)

        # Get concat demuxer status
        user_has_concat = "CONCAT_DEMUXER_ENABLED" in user_dict
        if user_has_concat:
            concat_status = (
                "✅ Enabled (User)"
                if user_dict["CONCAT_DEMUXER_ENABLED"]
                else "❌ Disabled (User)"
            )
        elif Config.CONCAT_DEMUXER_ENABLED:
            concat_status = "✅ Enabled (Global)"
        else:
            concat_status = "❌ Disabled"

        # Get filter complex status
        user_has_filter = "FILTER_COMPLEX_ENABLED" in user_dict
        if user_has_filter:
            filter_status = (
                "✅ Enabled (User)"
                if user_dict["FILTER_COMPLEX_ENABLED"]
                else "❌ Disabled (User)"
            )
        elif Config.FILTER_COMPLEX_ENABLED:
            filter_status = "✅ Enabled (Global)"
        else:
            filter_status = "❌ Disabled"

        # Get output formats
        user_has_video_format = (
            "MERGE_OUTPUT_FORMAT_VIDEO" in user_dict
            and user_dict["MERGE_OUTPUT_FORMAT_VIDEO"]
        )
        user_has_audio_format = (
            "MERGE_OUTPUT_FORMAT_AUDIO" in user_dict
            and user_dict["MERGE_OUTPUT_FORMAT_AUDIO"]
        )

        if user_has_video_format:
            video_format = f"{user_dict['MERGE_OUTPUT_FORMAT_VIDEO']} (User)"
        elif Config.MERGE_OUTPUT_FORMAT_VIDEO:
            video_format = f"{Config.MERGE_OUTPUT_FORMAT_VIDEO} (Global)"
        else:
            video_format = "mkv (Default)"

        if user_has_audio_format:
            audio_format = f"{user_dict['MERGE_OUTPUT_FORMAT_AUDIO']} (User)"
        elif Config.MERGE_OUTPUT_FORMAT_AUDIO:
            audio_format = f"{Config.MERGE_OUTPUT_FORMAT_AUDIO} (Global)"
        else:
            audio_format = "mp3 (Default)"

        # Get threading status
        user_has_threading = "MERGE_THREADING" in user_dict
        if user_has_threading:
            threading_status = (
                "✅ Enabled (User)"
                if user_dict["MERGE_THREADING"]
                else "❌ Disabled (User)"
            )
        elif Config.MERGE_THREADING:
            threading_status = "✅ Enabled (Global)"
        else:
            threading_status = "❌ Disabled"

        # Get thread number
        user_has_thread_number = (
            "MERGE_THREAD_NUMBER" in user_dict and user_dict["MERGE_THREAD_NUMBER"]
        )
        if user_has_thread_number:
            thread_number = f"{user_dict['MERGE_THREAD_NUMBER']} (User)"
        elif Config.MERGE_THREAD_NUMBER:
            thread_number = f"{Config.MERGE_THREAD_NUMBER} (Global)"
        else:
            thread_number = "4 (Default)"

        # Get remove original status
        user_has_remove_original = "MERGE_REMOVE_ORIGINAL" in user_dict
        if user_has_remove_original:
            remove_original = (
                "✅ Enabled (User)"
                if user_dict["MERGE_REMOVE_ORIGINAL"]
                else "❌ Disabled (User)"
            )
        elif Config.MERGE_REMOVE_ORIGINAL:
            remove_original = "✅ Enabled (Global)"
        else:
            remove_original = "❌ Disabled"

        text = f"""⌬ <b>Merge Settings :</b>
┟ <b>Name</b> → {user_name}
┃
┠ <b>Status</b> → {"✅ Enabled" if merge_enabled else "❌ Disabled"}
┠ <b>Concat Demuxer</b> → {concat_status}
┠ <b>Filter Complex</b> → {filter_status}
┠ <b>Threading</b> → {threading_status}
┠ <b>Thread Number</b> → <code>{thread_number}</code>
┠ <b>Remove Original</b> → {remove_original}
┠ <b>Video Format</b> → <code>{video_format}</code>
┖ <b>Audio Format</b> → <code>{audio_format}</code>"""

    elif stype.startswith("merge_config"):
        # Get all merge settings and sort them alphabetically
        merge_settings = [
            # Output formats
            "MERGE_OUTPUT_FORMAT_VIDEO",
            "MERGE_OUTPUT_FORMAT_AUDIO",
            "MERGE_OUTPUT_FORMAT_IMAGE",
            "MERGE_OUTPUT_FORMAT_DOCUMENT",
            "MERGE_OUTPUT_FORMAT_SUBTITLE",
            # Video settings
            "MERGE_VIDEO_CODEC",
            "MERGE_VIDEO_QUALITY",
            "MERGE_VIDEO_PRESET",
            "MERGE_VIDEO_CRF",
            "MERGE_VIDEO_PIXEL_FORMAT",
            "MERGE_VIDEO_TUNE",
            "MERGE_VIDEO_FASTSTART",
            # Audio settings
            "MERGE_AUDIO_CODEC",
            "MERGE_AUDIO_BITRATE",
            "MERGE_AUDIO_CHANNELS",
            "MERGE_AUDIO_SAMPLING",
            "MERGE_AUDIO_VOLUME",
            # Image settings
            "MERGE_IMAGE_MODE",
            "MERGE_IMAGE_COLUMNS",
            "MERGE_IMAGE_QUALITY",
            "MERGE_IMAGE_DPI",
            "MERGE_IMAGE_RESIZE",
            "MERGE_IMAGE_BACKGROUND",
            # Subtitle settings
            "MERGE_SUBTITLE_ENCODING",
            "MERGE_SUBTITLE_FONT",
            "MERGE_SUBTITLE_FONT_SIZE",
            "MERGE_SUBTITLE_FONT_COLOR",
            "MERGE_SUBTITLE_BACKGROUND",
            # Document settings
            "MERGE_DOCUMENT_PAPER_SIZE",
            "MERGE_DOCUMENT_ORIENTATION",
            "MERGE_DOCUMENT_MARGIN",
            # Metadata settings
            "MERGE_METADATA_TITLE",
            "MERGE_METADATA_AUTHOR",
            "MERGE_METADATA_COMMENT",
        ]

        # Sort settings alphabetically
        merge_settings.sort()

        # Pagination setup
        global merge_config_page

        # If a specific page is requested in the stype parameter, use that
        if len(stype.split()) > 1:
            try:
                page_no = int(stype.split()[1])
                # Update the global variable
                merge_config_page = page_no
                LOGGER.debug(
                    f"Setting merge_config_page to {page_no} from stype parameter"
                )
            except (ValueError, IndexError):
                # Use the global variable
                page_no = merge_config_page
                LOGGER.debug(
                    f"Invalid page in stype, using global merge_config_page: {page_no}"
                )
        else:
            # Use the global variable if no page is specified
            page_no = merge_config_page
            LOGGER.debug(
                f"No page specified, using global merge_config_page: {page_no}"
            )

        # 5 rows per page, 2 columns = 10 items per page
        items_per_page = 10  # 5 rows * 2 columns
        total_pages = (len(merge_settings) + items_per_page - 1) // items_per_page

        # Ensure page_no is valid
        if page_no >= total_pages:
            page_no = 0
            merge_config_page = 0  # Update global variable
            LOGGER.debug(f"Page number {page_no} is too large, resetting to 0")
        elif page_no < 0:
            page_no = total_pages - 1
            merge_config_page = total_pages - 1  # Update global variable
            LOGGER.debug(
                f"Page number {page_no} is negative, setting to last page {total_pages - 1}"
            )

        # Get settings for current page
        start_idx = page_no * items_per_page
        end_idx = min(start_idx + items_per_page, len(merge_settings))
        current_page_settings = merge_settings[start_idx:end_idx]

        # Add buttons for each setting on current page
        for setting in current_page_settings:
            display_name = setting.replace("MERGE_", "").replace("_", " ").title()
            buttons.data_button(display_name, f"mediatools {user_id} menu {setting}")

        # Add action buttons in a separate row
        buttons.data_button("Back", f"mediatools {user_id} merge", "footer")
        buttons.data_button("Close", f"mediatools {user_id} close", "footer")

        # Add pagination buttons in a separate row below action buttons
        if total_pages > 1:
            LOGGER.debug(
                f"Creating pagination buttons. Total pages: {total_pages}, Current page: {page_no}, Global merge_config_page: {merge_config_page}"
            )

            # Log the current state of the buttons
            LOGGER.debug(
                f"Button state before adding pagination: Regular: {len(buttons._button)}, Header: {len(buttons._header_button)}, Footer: {len(buttons._footer_button)}, Page: {len(buttons._page_button)}"
            )

            for i in range(total_pages):
                # Make the current page button different
                if i == page_no:
                    LOGGER.debug(
                        f"Adding current page button [{i + 1}] with callback: mediatools {user_id} merge_config {i}"
                    )
                    # Make sure the page number is passed as a separate parameter
                    buttons.data_button(
                        f"[{i + 1}]", f"mediatools {user_id} merge_config {i}", "page"
                    )
                else:
                    LOGGER.debug(
                        f"Adding page button {i + 1} with callback: mediatools {user_id} merge_config {i}"
                    )
                    # Make sure the page number is passed as a separate parameter
                    buttons.data_button(
                        str(i + 1), f"mediatools {user_id} merge_config {i}", "page"
                    )

            # Log the state after adding pagination buttons
            LOGGER.debug(
                f"Button state after adding pagination: Regular: {len(buttons._button)}, Header: {len(buttons._header_button)}, Footer: {len(buttons._footer_button)}, Page: {len(buttons._page_button)}"
            )

            # Add a debug log message
            LOGGER.debug(
                f"Added pagination buttons for merge_config. Total pages: {total_pages}, Current page: {page_no}"
            )

        # Build the menu with 2 columns for settings, 4 columns for action buttons, and 8 columns for pagination
        LOGGER.debug(
            "Building menu with parameters: b_cols=2, h_cols=8, f_cols=4, p_cols=8"
        )
        btns = buttons.build_menu(2, 8, 4, 8)
        LOGGER.debug(f"Menu built with {len(btns.inline_keyboard)} rows of buttons")

        # Determine which category is shown on the current page
        start_idx = page_no * items_per_page
        end_idx = min(start_idx + items_per_page, len(merge_settings))

        # Define category groups
        formats = [
            "MERGE_OUTPUT_FORMAT_VIDEO",
            "MERGE_OUTPUT_FORMAT_AUDIO",
            "MERGE_OUTPUT_FORMAT_IMAGE",
            "MERGE_OUTPUT_FORMAT_DOCUMENT",
            "MERGE_OUTPUT_FORMAT_SUBTITLE",
        ]

        video_settings = [
            "MERGE_VIDEO_CODEC",
            "MERGE_VIDEO_QUALITY",
            "MERGE_VIDEO_PRESET",
            "MERGE_VIDEO_CRF",
            "MERGE_VIDEO_PIXEL_FORMAT",
            "MERGE_VIDEO_TUNE",
            "MERGE_VIDEO_FASTSTART",
        ]

        audio_settings = [
            "MERGE_AUDIO_CODEC",
            "MERGE_AUDIO_BITRATE",
            "MERGE_AUDIO_CHANNELS",
            "MERGE_AUDIO_SAMPLING",
            "MERGE_AUDIO_VOLUME",
        ]

        image_settings = [
            "MERGE_IMAGE_MODE",
            "MERGE_IMAGE_COLUMNS",
            "MERGE_IMAGE_QUALITY",
            "MERGE_IMAGE_DPI",
            "MERGE_IMAGE_RESIZE",
            "MERGE_IMAGE_BACKGROUND",
        ]

        subtitle_settings = [
            "MERGE_SUBTITLE_ENCODING",
            "MERGE_SUBTITLE_FONT",
            "MERGE_SUBTITLE_FONT_SIZE",
            "MERGE_SUBTITLE_FONT_COLOR",
            "MERGE_SUBTITLE_BACKGROUND",
        ]

        document_settings = [
            "MERGE_DOCUMENT_PAPER_SIZE",
            "MERGE_DOCUMENT_ORIENTATION",
            "MERGE_DOCUMENT_MARGIN",
        ]

        metadata_settings = [
            "MERGE_METADATA_TITLE",
            "MERGE_METADATA_AUTHOR",
            "MERGE_METADATA_COMMENT",
        ]

        # Get the categories shown on the current page
        categories = []
        if any(setting in formats for setting in merge_settings[start_idx:end_idx]):
            categories.append("Formats")
        if any(
            setting in video_settings for setting in merge_settings[start_idx:end_idx]
        ):
            categories.append("Video")
        if any(
            setting in audio_settings for setting in merge_settings[start_idx:end_idx]
        ):
            categories.append("Audio")
        if any(
            setting in image_settings for setting in merge_settings[start_idx:end_idx]
        ):
            categories.append("Image")
        if any(
            setting in subtitle_settings
            for setting in merge_settings[start_idx:end_idx]
        ):
            categories.append("Subtitle")
        if any(
            setting in document_settings
            for setting in merge_settings[start_idx:end_idx]
        ):
            categories.append("Document")
        if any(
            setting in metadata_settings
            for setting in merge_settings[start_idx:end_idx]
        ):
            categories.append("Metadata")

        category_text = ", ".join(categories)

        # Get page info for message
        page_info = f"\n\nCurrent page shows: {category_text} settings."
        if total_pages > 1:
            page_info += f"\n<b>Page:</b> {page_no + 1}/{total_pages}"

        # Get concat demuxer status
        user_has_concat = "CONCAT_DEMUXER_ENABLED" in user_dict
        if user_has_concat:
            concat_status = (
                "✅ Enabled (User)"
                if user_dict["CONCAT_DEMUXER_ENABLED"]
                else "❌ Disabled (User)"
            )
        elif Config.CONCAT_DEMUXER_ENABLED:
            concat_status = "✅ Enabled (Global)"
        else:
            concat_status = "❌ Disabled"

        # Get filter complex status
        user_has_filter = "FILTER_COMPLEX_ENABLED" in user_dict
        if user_has_filter:
            filter_status = (
                "✅ Enabled (User)"
                if user_dict["FILTER_COMPLEX_ENABLED"]
                else "❌ Disabled (User)"
            )
        elif Config.FILTER_COMPLEX_ENABLED:
            filter_status = "✅ Enabled (Global)"
        else:
            filter_status = "❌ Disabled"

        # Get output formats
        user_has_video_format = (
            "MERGE_OUTPUT_FORMAT_VIDEO" in user_dict
            and user_dict["MERGE_OUTPUT_FORMAT_VIDEO"]
        )
        user_has_audio_format = (
            "MERGE_OUTPUT_FORMAT_AUDIO" in user_dict
            and user_dict["MERGE_OUTPUT_FORMAT_AUDIO"]
        )

        if user_has_video_format:
            video_format = f"{user_dict['MERGE_OUTPUT_FORMAT_VIDEO']} (User)"
        elif Config.MERGE_OUTPUT_FORMAT_VIDEO:
            video_format = f"{Config.MERGE_OUTPUT_FORMAT_VIDEO} (Global)"
        else:
            video_format = "mkv (Default)"

        if user_has_audio_format:
            audio_format = f"{user_dict['MERGE_OUTPUT_FORMAT_AUDIO']} (User)"
        elif Config.MERGE_OUTPUT_FORMAT_AUDIO:
            audio_format = f"{Config.MERGE_OUTPUT_FORMAT_AUDIO} (Global)"
        else:
            audio_format = "mp3 (Default)"

        # Get priority
        user_has_priority = (
            "MERGE_PRIORITY" in user_dict and user_dict["MERGE_PRIORITY"]
        )
        if user_has_priority:
            priority = f"{user_dict['MERGE_PRIORITY']} (User)"
        elif Config.MERGE_PRIORITY:
            priority = f"{Config.MERGE_PRIORITY} (Global)"
        else:
            priority = "1 (Default)"

        # Get threading
        user_has_threading = "MERGE_THREADING" in user_dict
        if user_has_threading:
            threading = (
                "✅ Enabled (User)"
                if user_dict["MERGE_THREADING"]
                else "❌ Disabled (User)"
            )
        elif Config.MERGE_THREADING:
            threading = "✅ Enabled (Global)"
        else:
            threading = "❌ Disabled"

        # Get thread number
        user_has_thread_number = (
            "MERGE_THREAD_NUMBER" in user_dict and user_dict["MERGE_THREAD_NUMBER"]
        )
        if user_has_thread_number:
            thread_number = f"{user_dict['MERGE_THREAD_NUMBER']} (User)"
        elif Config.MERGE_THREAD_NUMBER:
            thread_number = f"{Config.MERGE_THREAD_NUMBER} (Global)"
        else:
            thread_number = "4 (Default)"

        # Get format options
        # Video settings
        user_has_video_format = (
            "MERGE_OUTPUT_FORMAT_VIDEO" in user_dict
            and user_dict["MERGE_OUTPUT_FORMAT_VIDEO"]
        )

        # Audio settings
        user_has_audio_format = (
            "MERGE_OUTPUT_FORMAT_AUDIO" in user_dict
            and user_dict["MERGE_OUTPUT_FORMAT_AUDIO"]
        )

        # We only need a few variables for the text display
        user_has_remove_original = "MERGE_REMOVE_ORIGINAL" in user_dict

        # Get values for video options
        if user_has_video_format:
            video_format = f"{user_dict['MERGE_OUTPUT_FORMAT_VIDEO']} (User)"
        elif Config.MERGE_OUTPUT_FORMAT_VIDEO:
            video_format = f"{Config.MERGE_OUTPUT_FORMAT_VIDEO} (Global)"
        else:
            video_format = "mkv (Default)"

        # Get values for audio options
        if user_has_audio_format:
            audio_format = f"{user_dict['MERGE_OUTPUT_FORMAT_AUDIO']} (User)"
        elif Config.MERGE_OUTPUT_FORMAT_AUDIO:
            audio_format = f"{Config.MERGE_OUTPUT_FORMAT_AUDIO} (Global)"
        else:
            audio_format = "mp3 (Default)"

        # We don't need to get all values since we're only showing a few in the text

        if user_has_remove_original:
            remove_original = (
                "✅ Enabled (User)"
                if user_dict["MERGE_REMOVE_ORIGINAL"]
                else "❌ Disabled (User)"
            )
        elif Config.MERGE_REMOVE_ORIGINAL:
            remove_original = "✅ Enabled (Global)"
        else:
            remove_original = "❌ Disabled"

        text = f"""⌬ <b>Configure Merge :</b>
┟ <b>Name</b> → {user_name}
┃
┠ <b>Select a setting to configure</b>
┃
┠ <b>Current Settings:</b>
┃ • <b>Concat Demuxer:</b> {concat_status}
┃ • <b>Filter Complex:</b> {filter_status}
┃ • <b>Priority:</b> <code>{priority}</code>
┃ • <b>Threading:</b> {threading}
┃ • <b>Thread Number:</b> <code>{thread_number}</code>
┃ • <b>Remove Original:</b> {remove_original}
┃ • <b>Video Format:</b> <code>{video_format}</code>
┃ • <b>Audio Format:</b> <code>{audio_format}</code>
┖ <b>Note:</b> Most settings default to 'none' unless specified{page_info}"""

    elif stype == "help":
        # Media Tools Help menu
        buttons.data_button("Merge Help", f"mediatools {user_id} help_merge")
        buttons.data_button("Watermark Help", f"mediatools {user_id} help_watermark")
        buttons.data_button("Priority Guide", f"mediatools {user_id} help_priority")
        buttons.data_button("Usage Examples", f"mediatools {user_id} help_examples")
        buttons.data_button("Back", f"mediatools {user_id} back", "footer")
        buttons.data_button("Close", f"mediatools {user_id} close", "footer")
        btns = buttons.build_menu(2)

        text = f"""⌬ <b>Media Tools Help :</b>
┟ <b>Name</b> → {user_name}
┃
┠ <b>Select a help topic from the buttons below.</b>
┃
┠ <b>Merge Help</b> - Information about merging media files
┠ <b>Watermark Help</b> - Information about watermarking media
┠ <b>Priority Guide</b> - How tool priority affects processing
┖ <b>Usage Examples</b> - Examples of how to use media tools"""

    elif stype == "help_watermark":
        # Watermark Help
        buttons.data_button("Back to Help", f"mediatools {user_id} help", "footer")
        buttons.data_button("Close", f"mediatools {user_id} close", "footer")
        btns = buttons.build_menu(2)

        text = f"""⌬ <b>Watermark Help :</b>
┟ <b>Name</b> → {user_name}
┃
┠ <b>Overview:</b>
┃ The watermark feature allows you to add text overlays to your videos and images.
┃
┠ <b>Supported Media Types:</b>
┃ • <b>Videos</b> - MP4, MKV, AVI, WebM, etc.
┃ • <b>Images</b> - JPG, PNG, WebP, etc.
┃
┠ <b>Settings:</b>
┃ • <b>Enabled/Disabled</b> - Toggle watermark feature
┃ • <b>Text</b> - The text to display as watermark
┃ • <b>Position</b> - Where to place the watermark on the media
┃ • <b>Size</b> - Font size of the watermark text
┃ • <b>Color</b> - Color of the watermark text
┃ • <b>Font</b> - Font to use for the watermark text
┃ • <b>Priority</b> - Processing order when multiple tools are enabled
┃ • <b>Threading</b> - Enable/disable parallel processing
┃
┠ <b>Usage:</b>
┃ Add <code>-watermark "Your Text"</code> to any download command
┃ Example: <code>/leech https://example.com/media.zip -watermark "© My Channel"</code>
┃
┖ <b>Note:</b> For best results, use short text and contrasting colors."""

    elif stype == "help_merge":
        # Merge Help
        buttons.data_button("Back to Help", f"mediatools {user_id} help", "footer")
        buttons.data_button("Close", f"mediatools {user_id} close", "footer")
        btns = buttons.build_menu(2)

        text = f"""⌬ <b>Merge Help :</b>
┟ <b>Name</b> → {user_name}
┃
┠ <b>Overview:</b>
┃ The merge feature allows you to combine multiple media files.
┃
┠ <b>Supported Merge Types:</b>
┃ • Video + Video + Video + ... (creates a single video file)
┃ • Audio + Audio + Audio + ... (creates a single audio file)
┃ • Subtitle + Subtitle + ... (creates a single subtitle file)
┃ • Video + Audio + Subtitle (adds audio and subtitle tracks to video)
┃ • Images (creates a collage or horizontal/vertical image)
┃ • Documents (combines PDFs into a single document)
┃
┠ <b>Merge Flags:</b>
┃ • <code>-merge-video</code> - Merge only video files
┃ • <code>-merge-audio</code> - Merge only audio files
┃ • <code>-merge-subtitle</code> - Merge only subtitle files
┃ • <code>-merge-image</code> - Merge only image files
┃ • <code>-merge-pdf</code> - Merge only PDF documents
┃ • <code>-merge-all</code> - Merge all files by type
┃
┠ <b>Settings:</b>
┃ • <b>Enabled/Disabled</b> - Toggle merge feature
┃ • <b>Concat Demuxer</b> - Use FFmpeg concat demuxer (faster, same format files)
┃ • <b>Filter Complex</b> - Use FFmpeg filter complex (slower, mixed format files)
┃ • <b>Output Formats:</b>
┃   - <b>Video Format</b> - Output format for merged videos (mkv, mp4, etc.)
┃   - <b>Audio Format</b> - Output format for merged audios (mp3, flac, etc.)
┃   - <b>Image Format</b> - Output format for merged images (jpg, png, etc.)
┃   - <b>Document Format</b> - Output format for merged documents (pdf)
┃   - <b>Subtitle Format</b> - Output format for merged subtitles (srt, vtt, etc.)
┃ • <b>Video Settings:</b>
┃   - <b>Codec</b> - Video codec to use (copy, h264, h265, etc.)
┃   - <b>Quality</b> - Video quality preset (low, medium, high, etc.)
┃   - <b>Preset</b> - Encoding speed vs compression (medium, slow, etc.)
┃   - <b>CRF</b> - Quality control (0-51, lower is better quality)
┃   - <b>Pixel Format</b> - Color encoding format (yuv420p, etc.)
┃   - <b>Tune</b> - Content-specific optimizations (film, animation, etc.)
┃   - <b>Faststart</b> - Allow playback before download completes
┃ • <b>Audio Settings:</b>
┃   - <b>Codec</b> - Audio codec to use (copy, aac, mp3, etc.)
┃   - <b>Bitrate</b> - Audio quality (128k, 192k, 320k, etc.)
┃   - <b>Channels</b> - Number of audio channels (1=mono, 2=stereo)
┃   - <b>Sampling</b> - Audio sampling rate (44100, 48000, etc.)
┃   - <b>Volume</b> - Volume adjustment (1.0=normal, 2.0=double)
┃ • <b>Image Settings:</b>
┃   - <b>Mode</b> - How to arrange images (auto, horizontal, vertical, collage)
┃   - <b>Columns</b> - Number of columns in image collage mode
┃   - <b>Quality</b> - Image quality (1-100)
┃   - <b>DPI</b> - Resolution for printing (300=print, 72=screen)
┃   - <b>Resize</b> - Image dimensions (none, 1920x1080, etc.)
┃   - <b>Background</b> - Background color (white, black, #FF0000, etc.)
┃ • <b>Subtitle Settings:</b>
┃   - <b>Encoding</b> - Character encoding (utf-8, latin1, etc.)
┃   - <b>Font</b> - Font for rendering (Arial, DejaVu Sans, etc.)
┃   - <b>Font Size</b> - Text size (24, 32, etc.)
┃   - <b>Font Color</b> - Text color (white, yellow, #FFFFFF, etc.)
┃   - <b>Background</b> - Text background (black, transparent, etc.)
┃ • <b>Document Settings:</b>
┃   - <b>Paper Size</b> - Page dimensions (a4, letter, etc.)
┃   - <b>Orientation</b> - Page orientation (portrait, landscape)
┃   - <b>Margin</b> - Page margins in points (50, 0, etc.)
┃ • <b>Metadata:</b>
┃   - <b>Title</b> - File title metadata
┃   - <b>Author</b> - File author metadata
┃   - <b>Comment</b> - File comment metadata
┃ • <b>General Settings:</b>
┃   - <b>Remove Original</b> - Delete original files after successful merge
┃   - <b>Priority</b> - Processing order when multiple tools are enabled
┃   - <b>Threading</b> - Enable/disable parallel processing
┃   - <b>Thread Number</b> - Number of parallel processing threads
┃
┠ <b>Video Merging:</b>
┃ • <b>Concat Demuxer</b> - Fast merging for files with identical codecs
┃ • <b>Filter Complex</b> - Advanced merging for files with different codecs
┃ • Supported formats: MP4, MKV, AVI, WebM, etc.
┃ • Files are merged in alphabetical order
┃
┠ <b>Image Merging:</b>
┃ • <b>Collage Mode</b> - Creates a grid of images (default for 3+ images)
┃ • <b>Horizontal Mode</b> - Places images side by side (default for 2 images)
┃ • <b>Vertical Mode</b> - Stacks images on top of each other
┃ • Supported formats: JPG, PNG, GIF, BMP, WebP, TIFF
┃
┠ <b>Document Merging:</b>
┃ • Currently supports merging PDF files
┃ • Files are merged in alphabetical order
┃ • All PDF pages are preserved in the merged document
┃
┠ <b>Usage Examples:</b>
┃ • <code>/leech https://example.com/videos.zip -merge-video</code>
┃ • <code>/mirror https://example.com/images.zip -merge-image</code>
┃ • <code>/leech https://example.com/documents.zip -merge-pdf</code>
┃ • <code>/mirror https://example.com/media.zip -merge-all</code>
┃
┠ <b>Multi-Link Usage:</b>
┃ • <code>/cmd -i 3 -m folder_name -merge-video</code> (reply to first link)
┃ • <code>/cmd -b -m folder_name -merge-audio</code> (reply to text with links)
┃
┖ <b>Note:</b> Original files are removed after successful merge."""

    elif stype == "help_priority":
        # Priority Guide
        buttons.data_button("Back to Help", f"mediatools {user_id} help", "footer")
        buttons.data_button("Close", f"mediatools {user_id} close", "footer")
        btns = buttons.build_menu(2)

        text = f"""⌬ <b>Media Tools Priority Guide :</b>
┟ <b>Name</b> → {user_name}
┃
┠ <b>Overview:</b>
┃ The priority system controls the order in which media tools are applied.
┃
┠ <b>How Priority Works:</b>
┃ • Lower number means higher priority (1 is highest priority)
┃ • When multiple media tools are enabled, they run in priority order
┃ • Default priorities: Merge (1), Watermark (2)
┃
┠ <b>Why Priority Matters:</b>
┃ The order of processing affects the final result:
┃ • <b>Merge → Watermark</b>: Watermark appears once on the merged file
┃ • <b>Watermark → Merge</b>: Each file is watermarked before merging
┃
┠ <b>Setting Priority:</b>
┃ 1. Go to Media Tools settings
┃ 2. Select the tool (Watermark or Merge)
┃ 3. Click "Set Priority"
┃ 4. Enter a number (lower = higher priority)
┃
┖ <b>Note:</b> Priorities follow the user/owner/default configuration hierarchy."""

    elif stype == "help_examples":
        # Usage Examples
        buttons.data_button("Back to Help", f"mediatools {user_id} help", "footer")
        buttons.data_button("Close", f"mediatools {user_id} close", "footer")
        btns = buttons.build_menu(2)

        text = f"""⌬ <b>Media Tools Usage Examples :</b>
┟ <b>Name</b> → {user_name}
┃
┠ <b>Watermark Examples:</b>
┃ • <b>Basic Usage:</b>
┃   <code>/mirror https://example.com/media.zip -watermark "© My Channel"</code>
┃   This will add the watermark to all media files
┃
┃ • <b>With Images:</b>
┃   <code>/leech https://example.com/photos.zip -watermark "My Brand"</code>
┃   This will add the watermark to all image files
┃
┠ <b>Merge Examples:</b>
┃ • <b>Video Merge:</b>
┃   <code>/leech https://example.com/videos.zip -merge-video</code>
┃   This will merge only video files into a single video
┃
┃ • <b>Audio Merge:</b>
┃   <code>/mirror https://example.com/music.zip -merge-audio</code>
┃   This will merge only audio files into a single audio file
┃
┃ • <b>Image Merge:</b>
┃   <code>/mirror https://example.com/images.zip -merge-image</code>
┃   This will merge image files into a collage or grid
┃
┃ • <b>PDF Merge:</b>
┃   <code>/leech https://example.com/documents.zip -merge-pdf</code>
┃   This will merge PDF documents into a single PDF file
┃
┃ • <b>All Types Merge:</b>
┃   <code>/mirror https://example.com/media.zip -merge-all</code>
┃   This will merge all files by type (videos with videos, etc.)
┃
┠ <b>Combined Examples:</b>
┃ • <b>Watermark + Merge:</b>
┃   <code>/leech https://example.com/videos.zip -watermark "© 2025" -merge-video</code>
┃   This will apply both watermark and merge operations
┃
┃ • <b>Multi-Link with Merge:</b>
┃   <code>/mirror -i 3 -m merge-folder -merge-video</code> (reply to first link)
┃   This will download multiple links and merge the videos
┃
┃ • <b>Bulk Download with Merge:</b>
┃   <code>/leech -b -m merge-folder -merge-audio</code> (reply to text with links)
┃   This will download all links and merge the audio files
┃
┠ <b>Priority Example:</b>
┃ If both watermark and merge are enabled with default priorities:
┃ • Merge (priority 1) runs first
┃ • Watermark (priority 2) runs second
┃ • Result: One watermark on the final merged file
┃
┖ <b>Note:</b> Use the Media Tools settings to configure all options."""

    return text, btns


async def update_media_tools_settings(query, stype="main"):
    """Update media tools settings UI."""
    handler_dict[query.from_user.id] = False

    # Extract page number if present in stype
    page_no = 0
    global merge_config_page

    LOGGER.debug(
        f"update_media_tools_settings called with stype: {stype}, current global merge_config_page: {merge_config_page}"
    )

    if stype.startswith("merge_config "):
        try:
            # Format: merge_config X
            page_no = int(stype.split(" ")[1])
            # Update the global variable
            old_page = merge_config_page
            merge_config_page = page_no
            stype = "merge_config"
            LOGGER.debug(
                f"Extracted page number {page_no} from stype, updated global merge_config_page from {old_page} to {merge_config_page}"
            )
        except (ValueError, IndexError) as e:
            # Use the global variable
            page_no = merge_config_page
            LOGGER.error(
                f"Failed to extract page number from stype: {stype}, using global merge_config_page: {page_no}. Error: {e}"
            )
    elif stype == "merge_config":
        # Use the global variable for merge_config
        page_no = merge_config_page
        LOGGER.debug(f"Using global merge_config_page: {page_no} for merge_config menu")

    LOGGER.debug(
        f"Calling get_media_tools_settings with stype: {stype}, page_no: {page_no}"
    )
    msg, button = await get_media_tools_settings(
        query.from_user, stype, page_no=page_no
    )
    LOGGER.debug(
        f"Editing message with button menu containing {len(button.inline_keyboard)} rows"
    )
    await edit_message(query.message, msg, button)


def update_user_ldata(user_id, key, value):
    """Update user data with the provided key and value."""
    if user_id in user_data:
        user_data[user_id][key] = value
    else:
        user_data[user_id] = {key: value}


async def get_menu(option, message, user_id):
    """Get menu for a specific option."""
    handler_dict[user_id] = False
    user_dict = user_data.get(user_id, {})
    buttons = ButtonMaker()

    key = "set"
    buttons.data_button(
        "Change" if user_dict.get(option, False) else "Set",
        f"mediatools {user_id} {key} {option}",
    )

    if option in user_dict:
        buttons.data_button("Reset", f"mediatools {user_id} reset {option}")

    # Determine the back button target based on the option
    if option == "WATERMARK_PRIORITY":
        back_target = "watermark"
    elif option == "MERGE_PRIORITY":
        back_target = "merge"
    elif option.startswith("WATERMARK_"):
        back_target = "watermark_config"
    elif option.startswith("MERGE_") or option in [
        "CONCAT_DEMUXER_ENABLED",
        "FILTER_COMPLEX_ENABLED",
    ]:
        # Check if we need to return to a specific page in merge_config
        global merge_config_page

        if message.text and "Page:" in message.text:
            try:
                page_info = message.text.split("Page:")[1].strip().split("/")[0]
                page_no = int(page_info) - 1
                # Update the global variable
                merge_config_page = page_no
                LOGGER.debug(
                    f"Setting back button to merge_config page {page_no}, updated global merge_config_page"
                )
                back_target = f"merge_config {page_no}"
            except (ValueError, IndexError) as e:
                LOGGER.error(
                    f"Failed to extract page number from message text: {e}, using global merge_config_page: {merge_config_page}"
                )
                back_target = f"merge_config {merge_config_page}"
        else:
            # Use the global variable
            LOGGER.debug(
                f"No page info in message text, using global merge_config_page: {merge_config_page}"
            )
            back_target = f"merge_config {merge_config_page}"
    else:
        back_target = "back"

    buttons.data_button("Back", f"mediatools {user_id} {back_target}", "footer")
    buttons.data_button("Close", f"mediatools {user_id} close", "footer")

    # Get current value
    if option in user_dict:
        current_value = user_dict[option]
    elif hasattr(Config, option) and getattr(Config, option):
        current_value = f"{getattr(Config, option)} (Global)"
    else:
        if option == "WATERMARK_POSITION":
            current_value = "top_left (Default)"
        elif option == "WATERMARK_SIZE":
            current_value = "20 (Default)"
        elif option == "WATERMARK_COLOR":
            current_value = "white (Default)"
        elif option == "WATERMARK_FONT":
            current_value = "default.otf (Default)"
        elif option == "WATERMARK_PRIORITY":
            current_value = "2 (Default)"
        elif option == "WATERMARK_THREADING":
            current_value = "True (Default)"
        elif option == "MERGE_PRIORITY":
            current_value = "1 (Default)"
        elif option == "MERGE_THREADING":
            current_value = "True (Default)"
        elif option == "CONCAT_DEMUXER_ENABLED":
            current_value = "True (Default)"
        elif option == "FILTER_COMPLEX_ENABLED":
            current_value = "True (Default)"
        elif option == "MERGE_OUTPUT_FORMAT_VIDEO":
            current_value = "mkv (Default)"
        elif option == "MERGE_OUTPUT_FORMAT_AUDIO":
            current_value = "mp3 (Default)"
        elif option == "MERGE_OUTPUT_FORMAT_IMAGE":
            current_value = "jpg (Default)"
        elif option == "MERGE_OUTPUT_FORMAT_DOCUMENT":
            current_value = "pdf (Default)"
        elif option == "MERGE_OUTPUT_FORMAT_SUBTITLE":
            current_value = "srt (Default)"
        elif option == "MERGE_IMAGE_MODE":
            current_value = "auto (Default)"
        elif option == "MERGE_IMAGE_COLUMNS":
            current_value = "2 (Default)"
        elif option == "MERGE_IMAGE_QUALITY":
            current_value = "90 (Default)"
        elif option == "MERGE_IMAGE_DPI":
            current_value = "300 (Default)"
        elif option == "MERGE_IMAGE_RESIZE":
            current_value = "none (Default)"
        elif option == "MERGE_IMAGE_BACKGROUND":
            current_value = "white (Default)"
        elif option == "MERGE_VIDEO_CODEC":
            current_value = "copy (Default)"
        elif option == "MERGE_VIDEO_QUALITY":
            current_value = "medium (Default)"
        elif option == "MERGE_VIDEO_PRESET":
            current_value = "medium (Default)"
        elif option == "MERGE_VIDEO_CRF":
            current_value = "23 (Default)"
        elif option == "MERGE_VIDEO_PIXEL_FORMAT":
            current_value = "yuv420p (Default)"
        elif option == "MERGE_VIDEO_TUNE":
            current_value = "film (Default)"
        elif option == "MERGE_VIDEO_FASTSTART":
            current_value = "True (Default)"
        elif option == "MERGE_AUDIO_CODEC":
            current_value = "copy (Default)"
        elif option == "MERGE_AUDIO_BITRATE":
            current_value = "192k (Default)"
        elif option == "MERGE_AUDIO_CHANNELS":
            current_value = "2 (Default)"
        elif option == "MERGE_AUDIO_SAMPLING":
            current_value = "44100 (Default)"
        elif option == "MERGE_AUDIO_VOLUME":
            current_value = "1.0 (Default)"
        elif option == "MERGE_SUBTITLE_ENCODING":
            current_value = "utf-8 (Default)"
        elif option == "MERGE_SUBTITLE_FONT":
            current_value = "Arial (Default)"
        elif option == "MERGE_SUBTITLE_FONT_SIZE":
            current_value = "24 (Default)"
        elif option == "MERGE_SUBTITLE_FONT_COLOR":
            current_value = "white (Default)"
        elif option == "MERGE_SUBTITLE_BACKGROUND":
            current_value = "black (Default)"
        elif option == "MERGE_DOCUMENT_PAPER_SIZE":
            current_value = "a4 (Default)"
        elif option == "MERGE_DOCUMENT_ORIENTATION":
            current_value = "portrait (Default)"
        elif option == "MERGE_DOCUMENT_MARGIN":
            current_value = "50 (Default)"
        elif option == "MERGE_METADATA_TITLE":
            current_value = "(Default: empty)"
        elif option == "MERGE_METADATA_AUTHOR":
            current_value = "(Default: empty)"
        elif option == "MERGE_METADATA_COMMENT":
            current_value = "(Default: empty)"
        elif option == "MERGE_REMOVE_ORIGINAL":
            current_value = "True (Default)"
        elif option == "MEDIA_TOOLS_PRIORITY":
            current_value = "Default Order"
        else:
            current_value = "None"

    text = f"<b>Option:</b> {option}\n<b>Current Value:</b> <code>{current_value}</code>\n\n{media_tools_text.get(option, 'Set a value for this option.')}"

    await edit_message(message, text, buttons.build_menu(1))


async def set_option(_, message, option, rfunc):
    """Set an option value from user input."""
    user_id = message.from_user.id
    value = message.text
    # Set handler_dict to False to signal that we've received input

    if (
        option == "WATERMARK_SIZE"
        or option == "MERGE_IMAGE_COLUMNS"
        or option == "MERGE_THREAD_NUMBER"
    ):
        try:
            value = int(value)
            if value <= 0:
                error_msg = await send_message(
                    message, "Value must be a positive integer!"
                )
                await auto_delete_message(error_msg, time=300)
                return
        except ValueError:
            error_msg = await send_message(message, "Value must be a valid integer!")
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "WATERMARK_POSITION":
        valid_positions = [
            "top_left",
            "top_right",
            "bottom_left",
            "bottom_right",
            "center",
            "top_center",
            "bottom_center",
            "left_center",
            "right_center",
        ]
        if value not in valid_positions:
            error_msg = await send_message(
                message,
                f"Invalid position! Valid options are: {', '.join(valid_positions)}",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_IMAGE_MODE":
        valid_modes = ["auto", "horizontal", "vertical", "collage"]
        if value not in valid_modes:
            error_msg = await send_message(
                message,
                f"Invalid image mode! Valid options are: {', '.join(valid_modes)}",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_VIDEO_CODEC":
        valid_codecs = ["copy", "h264", "h265", "vp9", "av1"]
        if value not in valid_codecs:
            error_msg = await send_message(
                message,
                f"Invalid video codec! Valid options are: {', '.join(valid_codecs)}\nExample: copy - preserves original codec when possible\nExample: h264 - widely compatible codec",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_VIDEO_QUALITY":
        valid_qualities = ["low", "medium", "high", "veryhigh"]
        if value not in valid_qualities:
            error_msg = await send_message(
                message,
                f"Invalid video quality! Valid options are: {', '.join(valid_qualities)}\nExample: medium - balanced quality and file size\nExample: high - better quality but larger file size",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_VIDEO_PRESET":
        valid_presets = [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ]
        if value not in valid_presets:
            error_msg = await send_message(
                message,
                f"Invalid video preset! Valid options are: {', '.join(valid_presets)}\nExample: medium - balanced encoding speed and compression\nExample: slow - better compression but slower encoding",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_VIDEO_CRF":
        try:
            crf = int(value)
            if crf < 0 or crf > 51:
                error_msg = await send_message(
                    message,
                    "CRF value must be between 0 and 51! Lower values mean better quality but larger file size.\nExample: 23 - default value, good balance\nExample: 18 - visually lossless",
                )
                await auto_delete_message(error_msg, time=300)
                return
        except ValueError:
            error_msg = await send_message(
                message,
                "CRF value must be an integer between 0 and 51!\nExample: 23 - default value, good balance\nExample: 18 - visually lossless",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_VIDEO_PIXEL_FORMAT":
        valid_formats = [
            "yuv420p",
            "yuv422p",
            "yuv444p",
            "yuv420p10le",
            "yuv422p10le",
            "yuv444p10le",
        ]
        if value not in valid_formats:
            error_msg = await send_message(
                message,
                f"Invalid pixel format! Valid options are: {', '.join(valid_formats)}\nExample: yuv420p - most compatible format\nExample: yuv444p - highest quality but larger file size",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_VIDEO_TUNE":
        valid_tunes = [
            "film",
            "animation",
            "grain",
            "stillimage",
            "fastdecode",
            "zerolatency",
        ]
        if value not in valid_tunes:
            error_msg = await send_message(
                message,
                f"Invalid video tune! Valid options are: {', '.join(valid_tunes)}\nExample: film - for live-action content\nExample: animation - for animated content",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_VIDEO_FASTSTART":
        if value.lower() not in ["true", "false"]:
            error_msg = await send_message(
                message,
                "Faststart value must be 'true' or 'false'!\nEnabling faststart allows videos to start playing before they are fully downloaded.",
            )
            await auto_delete_message(error_msg, time=300)
            return
        value = value.lower() == "true"
    elif option == "MERGE_AUDIO_CODEC":
        valid_codecs = ["copy", "aac", "mp3", "opus", "flac"]
        if value not in valid_codecs:
            error_msg = await send_message(
                message,
                f"Invalid audio codec! Valid options are: {', '.join(valid_codecs)}\nExample: copy - preserves original codec when possible\nExample: aac - good quality and compatibility",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_AUDIO_BITRATE":
        valid_bitrates = ["64k", "96k", "128k", "192k", "256k", "320k"]
        if value not in valid_bitrates and not (
            value.endswith("k") and value[:-1].isdigit()
        ):
            error_msg = await send_message(
                message,
                f"Invalid audio bitrate! Common options are: {', '.join(valid_bitrates)}\nExample: 192k - good quality for most content\nExample: 320k - high quality audio",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_AUDIO_CHANNELS":
        try:
            channels = int(value)
            if channels < 1 or channels > 8:
                error_msg = await send_message(
                    message,
                    "Audio channels must be between 1 and 8!\nExample: 2 - stereo audio\nExample: 1 - mono audio",
                )
                await auto_delete_message(error_msg, time=300)
                return
        except ValueError:
            error_msg = await send_message(
                message,
                "Audio channels must be an integer between 1 and 8!\nExample: 2 - stereo audio\nExample: 1 - mono audio",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_AUDIO_SAMPLING":
        valid_rates = ["8000", "11025", "22050", "44100", "48000", "96000"]
        if value not in valid_rates and not value.isdigit():
            error_msg = await send_message(
                message,
                f"Invalid sampling rate! Common options are: {', '.join(valid_rates)}\nExample: 44100 - CD quality\nExample: 48000 - DVD/professional audio quality",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_AUDIO_VOLUME":
        try:
            volume = float(value)
            if volume < 0 or volume > 10:
                error_msg = await send_message(
                    message,
                    "Volume must be between 0 and 10!\nExample: 1.0 - original volume\nExample: 2.0 - double volume",
                )
                await auto_delete_message(error_msg, time=300)
                return
        except ValueError:
            error_msg = await send_message(
                message,
                "Volume must be a number between 0 and 10!\nExample: 1.0 - original volume\nExample: 2.0 - double volume",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_IMAGE_MODE":
        valid_modes = ["auto", "horizontal", "vertical", "collage"]
        if value not in valid_modes:
            error_msg = await send_message(
                message,
                f"Invalid image mode! Valid options are: {', '.join(valid_modes)}\nExample: auto - choose based on number of images\nExample: collage - grid layout",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_IMAGE_QUALITY":
        try:
            quality = int(value)
            if quality < 1 or quality > 100:
                error_msg = await send_message(
                    message,
                    "Image quality must be between 1 and 100!\nExample: 90 - high quality\nExample: 75 - good balance of quality and size",
                )
                await auto_delete_message(error_msg, time=300)
                return
        except ValueError:
            error_msg = await send_message(
                message,
                "Image quality must be an integer between 1 and 100!\nExample: 90 - high quality\nExample: 75 - good balance of quality and size",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_IMAGE_DPI":
        try:
            dpi = int(value)
            if dpi < 72 or dpi > 1200:
                error_msg = await send_message(
                    message,
                    "DPI must be between 72 and 1200!\nExample: 300 - good for printing\nExample: 72 - standard screen resolution",
                )
                await auto_delete_message(error_msg, time=300)
                return
        except ValueError:
            error_msg = await send_message(
                message,
                "DPI must be an integer between 72 and 1200!\nExample: 300 - good for printing\nExample: 72 - standard screen resolution",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_IMAGE_RESIZE":
        if value != "none" and not (
            value.count("x") == 1 and all(part.isdigit() for part in value.split("x"))
        ):
            error_msg = await send_message(
                message,
                "Resize value must be 'none' or in the format 'widthxheight'!\nExample: none - keep original size\nExample: 1920x1080 - resize to Full HD",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_IMAGE_BACKGROUND":
        valid_colors = [
            "white",
            "black",
            "transparent",
            "red",
            "green",
            "blue",
            "yellow",
        ]
        if value not in valid_colors and not (
            value.startswith("#") and len(value) == 7
        ):
            error_msg = await send_message(
                message,
                f"Invalid background color! Common options are: {', '.join(valid_colors)} or hex code like #RRGGBB\nExample: white - white background\nExample: #FF0000 - red background",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_SUBTITLE_ENCODING":
        valid_encodings = ["utf-8", "utf-16", "ascii", "latin1", "cp1252"]
        if value not in valid_encodings:
            error_msg = await send_message(
                message,
                f"Invalid encoding! Common options are: {', '.join(valid_encodings)}\nExample: utf-8 - universal encoding\nExample: latin1 - for Western European languages",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_SUBTITLE_FONT":
        # Any font name is valid, but suggest common ones
        if value.strip() == "":
            error_msg = await send_message(
                message,
                "Font name cannot be empty!\nExample: Arial - widely available font\nExample: DejaVu Sans - good for multiple languages",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_SUBTITLE_FONT_SIZE":
        try:
            size = int(value)
            if size < 8 or size > 72:
                error_msg = await send_message(
                    message,
                    "Font size must be between 8 and 72!\nExample: 24 - medium size\nExample: 32 - larger size for better readability",
                )
                await auto_delete_message(error_msg, time=300)
                return
        except ValueError:
            error_msg = await send_message(
                message,
                "Font size must be an integer between 8 and 72!\nExample: 24 - medium size\nExample: 32 - larger size for better readability",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_SUBTITLE_FONT_COLOR" or option == "MERGE_SUBTITLE_BACKGROUND":
        valid_colors = [
            "white",
            "black",
            "yellow",
            "red",
            "green",
            "blue",
            "transparent",
        ]
        if value not in valid_colors and not (
            value.startswith("#") and len(value) == 7
        ):
            error_msg = await send_message(
                message,
                f"Invalid color! Common options are: {', '.join(valid_colors)} or hex code like #RRGGBB\nExample: white - white text\nExample: #FFFF00 - yellow text",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_DOCUMENT_PAPER_SIZE":
        valid_sizes = ["a4", "letter", "legal", "a3", "a5"]
        if value not in valid_sizes:
            error_msg = await send_message(
                message,
                f"Invalid paper size! Common options are: {', '.join(valid_sizes)}\nExample: a4 - standard international paper size\nExample: letter - standard US paper size",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_DOCUMENT_ORIENTATION":
        valid_orientations = ["portrait", "landscape"]
        if value not in valid_orientations:
            error_msg = await send_message(
                message,
                f"Invalid orientation! Valid options are: {', '.join(valid_orientations)}\nExample: portrait - vertical orientation\nExample: landscape - horizontal orientation",
            )
            await auto_delete_message(error_msg, time=300)
            return
    elif option == "MERGE_DOCUMENT_MARGIN":
        try:
            margin = int(value)
            if margin < 0 or margin > 100:
                error_msg = await send_message(
                    message,
                    "Margin must be between 0 and 100!\nExample: 50 - standard margin\nExample: 0 - no margin",
                )
                await auto_delete_message(error_msg, time=300)
                return
        except ValueError:
            error_msg = await send_message(
                message,
                "Margin must be an integer between 0 and 100!\nExample: 50 - standard margin\nExample: 0 - no margin",
            )
            await auto_delete_message(error_msg, time=300)
            return

    # Set handler_dict to False to signal that we've received input
    handler_dict[user_id] = False

    update_user_ldata(user_id, option, value)
    await delete_message(message)

    # If we're in a merge_config menu with pagination, extract the page number
    if (
        (
            option.startswith("MERGE_")
            or option in ["CONCAT_DEMUXER_ENABLED", "FILTER_COMPLEX_ENABLED"]
        )
        and hasattr(message, "reply_to_message")
        and message.reply_to_message
        and message.reply_to_message.text
        and "Page:" in message.reply_to_message.text
    ):
        try:
            page_info = (
                message.reply_to_message.text.split("Page:")[1].strip().split("/")[0]
            )
            page_no = int(page_info) - 1
            # Update the global merge_config_page variable
            global merge_config_page
            merge_config_page = page_no
            LOGGER.debug(
                f"Extracted page number from message text: {page_no}, updated global merge_config_page"
            )
            # Create a new rfunc that will return to the correct page
            await update_media_tools_settings(message, f"merge_config {page_no}")
        except (ValueError, IndexError) as e:
            LOGGER.error(f"Failed to extract page number from message text: {e}")
            await rfunc()
    else:
        await rfunc()

    await database.update_user_data(user_id)


async def event_handler(client, query, pfunc, rfunc, photo=False, document=False):
    """Handle user input events."""
    user_id = query.from_user.id
    handler_dict[user_id] = True
    start_time = 60  # seconds
    handler = None

    try:
        # Create a custom filter using the event_filter_func
        # We need to create a class to hold our filter method
        class CustomFilter:
            async def event_filter_func(self, _, update):
                # Check if update is a message and has the required attributes
                if (
                    not update
                    or not hasattr(update, "from_user")
                    or update.from_user is None
                ):
                    return False

                if update.from_user.id != user_id:
                    return False
                if photo and (not hasattr(update, "photo") or update.photo is None):
                    return False
                if document and (
                    not hasattr(update, "document") or update.document is None
                ):
                    return False
                return True

        # Create the filter using the method from our class
        custom_filter = create(CustomFilter().event_filter_func)

        # Add the handler with the custom filter
        handler = client.add_handler(
            MessageHandler(pfunc, filters=custom_filter), group=-1
        )

        # Wait for user input (up to start_time seconds)
        for _ in range(start_time):
            if not handler_dict[user_id]:
                break
            await sleep(1)

        # Clean up
        if handler_dict[user_id]:
            handler_dict[user_id] = False
            await auto_delete_message(query.message, time=300)
            # If we timed out, call rfunc to go back to the menu
            await rfunc()
    finally:
        # Always remove the handler, even if there was an exception
        if handler:
            client.remove_handler(*handler)


@new_task
async def media_tools_settings(_, message):
    """Show media tools settings."""
    msg, btns = await get_media_tools_settings(message.from_user)
    settings_msg = await send_message(message, msg, btns)
    # Auto-delete the command message immediately
    await delete_message(message)
    # Auto-delete the settings menu after 5 minutes
    await auto_delete_message(settings_msg, time=300)


@new_task
async def edit_media_tools_settings(client, query):
    """Handle media tools settings callback queries."""
    from_user = query.from_user
    user_id = from_user.id
    message = query.message
    data = query.data.split()
    handler_dict[user_id] = False
    user_dict = user_data.get(user_id, {})

    if user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
        return

    if data[2] == "back":
        await query.answer()
        await update_media_tools_settings(query)
    elif data[2] == "close":
        await query.answer()
        await delete_message(message)
    elif data[2] in ["watermark", "watermark_config", "merge"]:
        await query.answer()
        await update_media_tools_settings(query, data[2])
    elif data[2] == "merge_config" or (len(data) > 3 and data[2] == "merge_config"):
        await query.answer()
        # Declare global variable first
        global merge_config_page
        LOGGER.debug(f"Received merge_config callback with data: {data}")
        LOGGER.debug(
            f"Current global merge_config_page before processing: {merge_config_page}"
        )

        if len(data) > 3:
            # Page number is provided
            try:
                # Format: merge_config X
                page_no = int(data[3])
                # Update the global variable
                old_page = merge_config_page
                merge_config_page = page_no
                LOGGER.debug(
                    f"Pagination button clicked. Page: {page_no}, updated global merge_config_page from {old_page} to {merge_config_page}"
                )
                LOGGER.debug(
                    f"Calling update_media_tools_settings with stype='merge_config {page_no}'"
                )
                await update_media_tools_settings(query, f"merge_config {page_no}")
            except ValueError as e:
                LOGGER.error(
                    f"Invalid page number: {data[3]}, using global merge_config_page: {merge_config_page}. Error: {e}"
                )
                # If page number is not a valid integer, use the global variable
                LOGGER.debug(
                    f"Calling update_media_tools_settings with stype='merge_config {merge_config_page}'"
                )
                await update_media_tools_settings(
                    query, f"merge_config {merge_config_page}"
                )
        else:
            # No page number provided, use the global variable
            LOGGER.debug(
                f"No page number provided, using global merge_config_page: {merge_config_page}"
            )
            LOGGER.debug(
                f"Calling update_media_tools_settings with stype='merge_config {merge_config_page}'"
            )
            await update_media_tools_settings(
                query, f"merge_config {merge_config_page}"
            )
    elif data[2] == "tog":
        await query.answer()
        update_user_ldata(user_id, data[3], data[4] == "t")
        # Determine which menu to return to based on the toggled option
        if data[3].startswith("WATERMARK_"):
            await update_media_tools_settings(query, "watermark")
        elif data[3].startswith("MERGE_") or data[3] in [
            "CONCAT_DEMUXER_ENABLED",
            "FILTER_COMPLEX_ENABLED",
        ]:
            await update_media_tools_settings(query, "merge")
        else:
            await update_media_tools_settings(query)
        await database.update_user_data(user_id)
    elif data[2] == "menu":
        await query.answer()
        await get_menu(data[3], message, user_id)
    elif data[2] == "set":
        await query.answer()
        buttons = ButtonMaker()
        text = media_tools_text.get(
            data[3], f"Send a value for {data[3]}. Timeout: 60 sec"
        )
        buttons.data_button("Back", f"mediatools {user_id} menu {data[3]}", "footer")
        buttons.data_button("Close", f"mediatools {user_id} close", "footer")
        await edit_message(message, text, buttons.build_menu(1))

        # Set up function to handle user input
        rfunc = partial(get_menu, data[3], message, user_id)
        pfunc = partial(set_option, option=data[3], rfunc=rfunc)
        await event_handler(client, query, pfunc, rfunc)
    elif data[2] == "reset":
        await query.answer()
        if data[3] in user_dict:
            del user_dict[data[3]]
            await database.update_user_data(user_id)
        await get_menu(data[3], message, user_id)
    elif data[2] == "reset_watermark":
        await query.answer("Resetting all watermark settings to default...")
        # Remove all watermark settings from user_dict
        watermark_keys = [
            "WATERMARK_ENABLED",
            "WATERMARK_KEY",
            "WATERMARK_POSITION",
            "WATERMARK_SIZE",
            "WATERMARK_COLOR",
            "WATERMARK_FONT",
            "WATERMARK_PRIORITY",
            "WATERMARK_THREADING",
        ]
        for key in watermark_keys:
            if key in user_dict:
                del user_dict[key]
        await database.update_user_data(user_id)
        await update_media_tools_settings(query, "watermark")
    elif data[2] == "reset_merge":
        await query.answer("Resetting all merge settings to default...")
        # Remove all merge settings from user_dict
        merge_keys = [
            "MERGE_ENABLED",
            "CONCAT_DEMUXER_ENABLED",
            "FILTER_COMPLEX_ENABLED",
            "MERGE_OUTPUT_FORMAT_VIDEO",
            "MERGE_OUTPUT_FORMAT_AUDIO",
            "MERGE_OUTPUT_FORMAT_IMAGE",
            "MERGE_OUTPUT_FORMAT_DOCUMENT",
            "MERGE_OUTPUT_FORMAT_SUBTITLE",
            "MERGE_IMAGE_MODE",
            "MERGE_IMAGE_COLUMNS",
            "MERGE_IMAGE_QUALITY",
            "MERGE_IMAGE_DPI",
            "MERGE_IMAGE_RESIZE",
            "MERGE_IMAGE_BACKGROUND",
            "MERGE_VIDEO_CODEC",
            "MERGE_VIDEO_QUALITY",
            "MERGE_VIDEO_PRESET",
            "MERGE_VIDEO_CRF",
            "MERGE_VIDEO_PIXEL_FORMAT",
            "MERGE_VIDEO_TUNE",
            "MERGE_VIDEO_FASTSTART",
            "MERGE_AUDIO_CODEC",
            "MERGE_AUDIO_BITRATE",
            "MERGE_AUDIO_CHANNELS",
            "MERGE_AUDIO_SAMPLING",
            "MERGE_AUDIO_VOLUME",
            "MERGE_SUBTITLE_ENCODING",
            "MERGE_SUBTITLE_FONT",
            "MERGE_SUBTITLE_FONT_SIZE",
            "MERGE_SUBTITLE_FONT_COLOR",
            "MERGE_SUBTITLE_BACKGROUND",
            "MERGE_DOCUMENT_PAPER_SIZE",
            "MERGE_DOCUMENT_ORIENTATION",
            "MERGE_DOCUMENT_MARGIN",
            "MERGE_METADATA_TITLE",
            "MERGE_METADATA_AUTHOR",
            "MERGE_METADATA_COMMENT",
            "MERGE_PRIORITY",
            "MERGE_THREADING",
            "MERGE_THREAD_NUMBER",
            "MERGE_REMOVE_ORIGINAL",
        ]
        for key in merge_keys:
            if key in user_dict:
                del user_dict[key]
        await database.update_user_data(user_id)
        await update_media_tools_settings(query, "merge")
    elif data[2] == "remove_watermark":
        await query.answer("Setting all watermark settings to None...")
        # Set all watermark settings to None/False
        watermark_keys = [
            "WATERMARK_KEY",
            "WATERMARK_POSITION",
            "WATERMARK_SIZE",
            "WATERMARK_COLOR",
            "WATERMARK_FONT",
        ]
        update_user_ldata(user_id, "WATERMARK_ENABLED", False)
        for key in watermark_keys:
            update_user_ldata(user_id, key, "None")
        await database.update_user_data(user_id)
        await update_media_tools_settings(query, "watermark")
    elif data[2] == "remove_merge":
        await query.answer("Setting all merge settings to None...")
        # Set all merge settings to None/False
        merge_keys = [
            "CONCAT_DEMUXER_ENABLED",
            "FILTER_COMPLEX_ENABLED",
            "MERGE_OUTPUT_FORMAT_VIDEO",
            "MERGE_OUTPUT_FORMAT_AUDIO",
            "MERGE_OUTPUT_FORMAT_IMAGE",
            "MERGE_OUTPUT_FORMAT_DOCUMENT",
            "MERGE_OUTPUT_FORMAT_SUBTITLE",
            "MERGE_IMAGE_MODE",
            "MERGE_IMAGE_COLUMNS",
            "MERGE_IMAGE_QUALITY",
            "MERGE_IMAGE_DPI",
            "MERGE_IMAGE_RESIZE",
            "MERGE_IMAGE_BACKGROUND",
            "MERGE_VIDEO_CODEC",
            "MERGE_VIDEO_QUALITY",
            "MERGE_VIDEO_PRESET",
            "MERGE_VIDEO_CRF",
            "MERGE_VIDEO_PIXEL_FORMAT",
            "MERGE_VIDEO_TUNE",
            "MERGE_VIDEO_FASTSTART",
            "MERGE_AUDIO_CODEC",
            "MERGE_AUDIO_BITRATE",
            "MERGE_AUDIO_CHANNELS",
            "MERGE_AUDIO_SAMPLING",
            "MERGE_AUDIO_VOLUME",
            "MERGE_SUBTITLE_ENCODING",
            "MERGE_SUBTITLE_FONT",
            "MERGE_SUBTITLE_FONT_SIZE",
            "MERGE_SUBTITLE_FONT_COLOR",
            "MERGE_SUBTITLE_BACKGROUND",
            "MERGE_DOCUMENT_PAPER_SIZE",
            "MERGE_DOCUMENT_ORIENTATION",
            "MERGE_DOCUMENT_MARGIN",
            "MERGE_METADATA_TITLE",
            "MERGE_METADATA_AUTHOR",
            "MERGE_METADATA_COMMENT",
            "MERGE_THREAD_NUMBER",
        ]
        update_user_ldata(user_id, "MERGE_ENABLED", False)
        update_user_ldata(user_id, "MERGE_THREADING", False)
        update_user_ldata(user_id, "MERGE_REMOVE_ORIGINAL", False)
        for key in merge_keys:
            if key in [
                "MERGE_VIDEO_CRF",
                "MERGE_IMAGE_COLUMNS",
                "MERGE_IMAGE_QUALITY",
                "MERGE_IMAGE_DPI",
                "MERGE_AUDIO_CHANNELS",
                "MERGE_SUBTITLE_FONT_SIZE",
                "MERGE_DOCUMENT_MARGIN",
            ]:
                update_user_ldata(user_id, key, 0)
            elif key == "MERGE_AUDIO_VOLUME":
                update_user_ldata(user_id, key, 0.0)
            elif key == "MERGE_VIDEO_FASTSTART":
                update_user_ldata(user_id, key, False)
            else:
                update_user_ldata(user_id, key, "none")
        await database.update_user_data(user_id)
        await update_media_tools_settings(query, "merge")
    elif data[2] == "remove_all":
        await query.answer("Setting all media tools settings to None...")
        # Set all media tools settings to None/False
        watermark_keys = [
            "WATERMARK_KEY",
            "WATERMARK_POSITION",
            "WATERMARK_SIZE",
            "WATERMARK_COLOR",
            "WATERMARK_FONT",
        ]
        merge_keys = [
            "CONCAT_DEMUXER_ENABLED",
            "FILTER_COMPLEX_ENABLED",
            "MERGE_OUTPUT_FORMAT_VIDEO",
            "MERGE_OUTPUT_FORMAT_AUDIO",
            "MERGE_OUTPUT_FORMAT_IMAGE",
            "MERGE_OUTPUT_FORMAT_DOCUMENT",
            "MERGE_OUTPUT_FORMAT_SUBTITLE",
            "MERGE_IMAGE_MODE",
            "MERGE_IMAGE_COLUMNS",
            "MERGE_IMAGE_QUALITY",
            "MERGE_IMAGE_DPI",
            "MERGE_IMAGE_RESIZE",
            "MERGE_IMAGE_BACKGROUND",
            "MERGE_VIDEO_CODEC",
            "MERGE_VIDEO_QUALITY",
            "MERGE_VIDEO_PRESET",
            "MERGE_VIDEO_CRF",
            "MERGE_VIDEO_PIXEL_FORMAT",
            "MERGE_VIDEO_TUNE",
            "MERGE_VIDEO_FASTSTART",
            "MERGE_AUDIO_CODEC",
            "MERGE_AUDIO_BITRATE",
            "MERGE_AUDIO_CHANNELS",
            "MERGE_AUDIO_SAMPLING",
            "MERGE_AUDIO_VOLUME",
            "MERGE_SUBTITLE_ENCODING",
            "MERGE_SUBTITLE_FONT",
            "MERGE_SUBTITLE_FONT_SIZE",
            "MERGE_SUBTITLE_FONT_COLOR",
            "MERGE_SUBTITLE_BACKGROUND",
            "MERGE_DOCUMENT_PAPER_SIZE",
            "MERGE_DOCUMENT_ORIENTATION",
            "MERGE_DOCUMENT_MARGIN",
            "MERGE_METADATA_TITLE",
            "MERGE_METADATA_AUTHOR",
            "MERGE_METADATA_COMMENT",
            "MERGE_THREAD_NUMBER",
        ]
        update_user_ldata(user_id, "WATERMARK_ENABLED", False)
        update_user_ldata(user_id, "MERGE_ENABLED", False)
        for key in watermark_keys:
            update_user_ldata(user_id, key, "None")
        for key in merge_keys:
            if key in [
                "MERGE_VIDEO_CRF",
                "MERGE_IMAGE_COLUMNS",
                "MERGE_IMAGE_QUALITY",
                "MERGE_IMAGE_DPI",
                "MERGE_AUDIO_CHANNELS",
                "MERGE_SUBTITLE_FONT_SIZE",
                "MERGE_DOCUMENT_MARGIN",
            ]:
                update_user_ldata(user_id, key, 0)
            elif key == "MERGE_AUDIO_VOLUME":
                update_user_ldata(user_id, key, 0.0)
            elif key == "MERGE_VIDEO_FASTSTART":
                update_user_ldata(user_id, key, False)
            else:
                update_user_ldata(user_id, key, "none")
        await database.update_user_data(user_id)
        await update_media_tools_settings(query)
    elif data[2] == "reset_all":
        await query.answer("Resetting all media tools settings to default...")
        # Remove all media tools settings from user_dict
        media_tools_keys = [
            "WATERMARK_ENABLED",
            "WATERMARK_KEY",
            "WATERMARK_POSITION",
            "WATERMARK_SIZE",
            "WATERMARK_COLOR",
            "WATERMARK_FONT",
            "WATERMARK_PRIORITY",
            "WATERMARK_THREADING",
            "MERGE_ENABLED",
            "CONCAT_DEMUXER_ENABLED",
            "FILTER_COMPLEX_ENABLED",
            "MERGE_OUTPUT_FORMAT_VIDEO",
            "MERGE_OUTPUT_FORMAT_AUDIO",
            "MERGE_PRIORITY",
            "MERGE_THREADING",
            "MEDIA_TOOLS_PRIORITY",
        ]
        for key in media_tools_keys:
            if key in user_dict:
                del user_dict[key]
        await database.update_user_data(user_id)
        await update_media_tools_settings(query)
    elif data[2] == "toggle_concat_filter":
        # Toggle between concat demuxer and filter complex
        toggle_mode = data[3]  # 'both', 'concat', or 'filter'

        if toggle_mode == "both":
            # Enable both
            update_user_ldata(user_id, "CONCAT_DEMUXER_ENABLED", True)
            update_user_ldata(user_id, "FILTER_COMPLEX_ENABLED", True)
            await query.answer("Both Concat Demuxer and Filter Complex enabled")
        elif toggle_mode == "concat":
            # Enable only concat
            update_user_ldata(user_id, "CONCAT_DEMUXER_ENABLED", True)
            update_user_ldata(user_id, "FILTER_COMPLEX_ENABLED", False)
            await query.answer("Only Concat Demuxer enabled")
        elif toggle_mode == "filter":
            # Enable only filter
            update_user_ldata(user_id, "CONCAT_DEMUXER_ENABLED", False)
            update_user_ldata(user_id, "FILTER_COMPLEX_ENABLED", True)
            await query.answer("Only Filter Complex enabled")
        else:
            # Fallback - enable both
            update_user_ldata(user_id, "CONCAT_DEMUXER_ENABLED", True)
            update_user_ldata(user_id, "FILTER_COMPLEX_ENABLED", True)
            await query.answer("Both Concat Demuxer and Filter Complex enabled")

        await database.update_user_data(user_id)
        await update_media_tools_settings(query, "merge")


async def add_media_tools_button_to_bot_settings(buttons):
    """Add Media Tools button to bot settings."""
    buttons.data_button("Media Tools", "botset mediatools")
    return buttons

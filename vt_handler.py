from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from utils.ffmpeg import process_video
from database import user_flags

# Main handler to process /leech -vt command
async def handle_vt(client: Client, message: Message):
    user_id = message.from_user.id
    reply = message.reply_to_message

    if not reply or not (reply.video or reply.document or reply.text):
        await message.reply("Reply to a file or URL with `/leech -vt`", quote=True)
        return

    # Save the original message for later processing
    user_flags[user_id] = {
        "file_message": reply,
        "flags": [],
        "status": "selecting"
    }

    buttons = [
        [InlineKeyboardButton("✂️ Trim", callback_data="trim"),
         InlineKeyboardButton("❌ Remove Audio", callback_data="remove_audio")],
        [InlineKeyboardButton("🔄 Swap Audio", callback_data="swap_audio"),
         InlineKeyboardButton("🖼 Extract Frame", callback_data="extract_frame")],
        [InlineKeyboardButton("🔻 Split", callback_data="split"),
         InlineKeyboardButton("✅ Done", callback_data="done")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]

    await message.reply(
        "**Select what you want to do with this media:**",
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True
    )

# Callback handler to process button presses
async def handle_vt_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if user_id not in user_flags:
        await callback_query.answer("Session expired. Try /leech -vt again.", show_alert=True)
        return

    if data == "cancel":
        del user_flags[user_id]
        await callback_query.message.edit("❌ Cancelled.")
        return

    if data == "done":
        await callback_query.message.edit("✅ Processing started...")
        user_data = user_flags.pop(user_id)
        file_message = user_data["file_message"]
        flags = user_data["flags"]
        await process_video(client, callback_query.message, file_message, flags)
        return

    # Add selected flag to user session
    if data not in user_flags[user_id]["flags"]:
        user_flags[user_id]["flags"].append(data)

    await callback_query.answer(f"Selected: {data}", show_alert=False)

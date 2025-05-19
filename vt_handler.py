from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def handle_vt(client, message):
    if not message.reply_to_message and len(message.text.split()) == 1:
        return await message.reply("Reply to a file or link with `/leech -vt`")

    buttons = [
        [InlineKeyboardButton("Trim Video", callback_data="vt_trim")],
        [InlineKeyboardButton("Remove Audio/Video Stream", callback_data="vt_remove")],
        [InlineKeyboardButton("Swap Audio", callback_data="vt_swap")],
        [InlineKeyboardButton("Extract Frame", callback_data="vt_frame")],
        [InlineKeyboardButton("Split Media", callback_data="vt_split")],
        [InlineKeyboardButton("Extract Stream Format", callback_data="vt_stream")]
    ]
    await message.reply(
        "Choose processing options:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

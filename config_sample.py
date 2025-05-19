import os

from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.environ.get("API_ID", "27975779"))
API_HASH = os.environ.get("API_HASH", "378062eb0a32d8d6b1bbbe97cb63a75a")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")
ADMINS = [1416841137]  # Replace with your Telegram user ID

app = Client("leech-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

from manual_handler import handle_manual
from vt_handler import handle_vt


@app.on_message(filters.command("start") & filters.private)
async def start(_, msg: Message):
    await msg.reply_text("Welcome! Use `/leech <link> -vt` or manual options.")


@app.on_message(filters.private & filters.command("leech"))
async def leech_entry(client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply("Access Denied")

    text = message.text
    if "-vt" in text:
        await handle_vt(client, message)
        return None
    await handle_manual(client, message)
    return None


print("Bot running...")
app.run()

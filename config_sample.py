import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")
ADMINS = [123456789]  # Replace with your Telegram user ID

app = Client("leech-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

from handlers.vt_handler import handle_vt
from handlers.manual_handler import handle_manual

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
    else:
        await handle_manual(client, message)

print("Bot running...")
app.run()

import os import asyncio import subprocess from pyrogram import Client, filters from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton from yt_dlp import YoutubeDL

API_ID = int(os.environ.get("API_ID", "")) API_HASH = os.environ.get("API_HASH", "") BOT_TOKEN = os.environ.get("BOT_TOKEN", "") ADMINS = []

app = Client("leech-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DOWNLOADS_DIR = "downloads" os.makedirs(DOWNLOADS_DIR, exist_ok=True)

user_flags = {}

@app.on_message(filters.command("leech") & filters.reply | filters.regex("https?://")) async def leech_vt_handler(client: Client, message: Message): if message.from_user.id not in ADMINS: return await message.reply("Access Denied")

if "-vt" in message.text:
    url = None
    if message.reply_to_message and message.reply_to_message.text:
        url = message.reply_to_message.text.strip()
    else:
        args = message.text.split()
        url = next((x for x in args if x.startswith("http")), None)

    if not url:
        return await message.reply("No valid link found.")

    user_flags[message.from_user.id] = {"url": url, "flags": {}}

    buttons = [
        [InlineKeyboardButton("Trim", callback_data="vt_trim"), InlineKeyboardButton("Remove Stream", callback_data="vt_remove")],
        [InlineKeyboardButton("Swap Audio", callback_data="vt_swap"), InlineKeyboardButton("Extract Frame", callback_data="vt_frame")],
        [InlineKeyboardButton("Split Audio/Video", callback_data="vt_split")],
        [InlineKeyboardButton("Start Processing", callback_data="vt_start")],
    ]

    return await message.reply("Choose processing options:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("vt_")) async def handle_vt_callback(client, callback_query): user_id = callback_query.from_user.id data = callback_query.data

if user_id not in user_flags:
    return await callback_query.answer("Session expired.", show_alert=True)

if data == "vt_start":
    await callback_query.message.edit("Processing started...")
    await process_download(client, callback_query.message, user_flags[user_id])
    user_flags.pop(user_id, None)
    return

if data == "vt_trim":
    user_flags[user_id]["flags"]["trim"] = ("00:00:10", "00:00:30")
elif data == "vt_remove":
    user_flags[user_id]["flags"]["remove"] = ("audio", "0")
elif data == "vt_swap":
    user_flags[user_id]["flags"]["swap_audio"] = ("1", "0")
elif data == "vt_frame":
    user_flags[user_id]["flags"]["frame"] = "00:00:05"
elif data == "vt_split":
    user_flags[user_id]["flags"]["split"] = True

await callback_query.answer("Added option")

async def process_download(client, message, context): url = context["url"] flags = context["flags"] await message.reply("Downloading...") try: ydl_opts = {'outtmpl': f'{DOWNLOADS_DIR}/%(title)s.%(ext)s', 'format': 'best'} with YoutubeDL(ydl_opts) as ydl: info = ydl.extract_info(url, download=True) file_path = ydl.prepare_filename(info)

processed_path = os.path.join(DOWNLOADS_DIR, f"processed_{os.path.basename(file_path)}")

    cmd = ["ffmpeg", "-y", "-i", file_path]

    if "trim" in flags:
        start, end = flags["trim"]
        cmd += ["-ss", start, "-to", end]

    if "remove" in flags:
        stream_type, index = flags["remove"]
        cmd += ["-map", "0"]
        if stream_type == "audio":
            cmd += ["-map", f"-0:a:{index}"]
        elif stream_type == "video":
            cmd += ["-map", f"-0:v:{index}"]

    if "swap_audio" in flags:
        rem, keep = flags["swap_audio"]
        cmd += ["-map", "0", "-map", f"-0:a:{rem}", "-disposition:a:0", "default"]

    cmd += ["-c", "copy", processed_path]
    subprocess.run(cmd, check=True)

    if "frame" in flags:
        frame_time = flags["frame"]
        frame_path = processed_path.replace(".mp4", "_frame.jpg")
        subprocess.run(["ffmpeg", "-ss", frame_time, "-i", processed_path, "-vframes", "1", frame_path], check=True)
        await client.send_photo(message.chat.id, frame_path, caption="Captured Frame")
        os.remove(frame_path)

    if "split" in flags:
        audio_path = processed_path.replace(".mp4", ".mp3")
        subprocess.run(["ffmpeg", "-i", processed_path, "-q:a", "0", "-map", "a", audio_path], check=True)
        await client.send_document(message.chat.id, audio_path, caption="Audio Track")
        os.remove(audio_path)

    await client.send_document(message.chat.id, processed_path, caption="Processed File")
    os.remove(file_path)
    os.remove(processed_path)

except Exception as e:
    await message.reply(f"Error: {e}")

app.run()


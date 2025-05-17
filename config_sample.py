from pyrogram import Client, filters from pyrogram.types import Message import os import asyncio import yt_dlp import subprocess

API_ID = int(os.environ.get("API_ID", "27975779")) API_HASH = os.environ.get("API_HASH", "378062eb0a32d8d6b1bbbe97cb63a75a") BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token") ADMINS = [1416841137]  # Replace with your Telegram user ID

app = Client("leech-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DOWNLOADS_DIR = "downloads" os.makedirs(DOWNLOADS_DIR, exist_ok=True) MERGE_STATE = {} user_context = {}

@app.on_message(filters.private & filters.command("start")) async def start_handler(client: Client, message: Message): if message.from_user.id not in ADMINS: return await message.reply_text("Access Denied.") await message.reply_text("Welcome to the Leech Bot. Send a file, URL, or magnet link to begin.")

@app.on_message(filters.private & (filters.document | filters.video)) async def file_handler(client: Client, message: Message): if message.from_user.id not in ADMINS: return user_id = message.from_user.id

if user_id in MERGE_STATE:
    await message.reply_text("Downloading for merge...")
    file_path = await message.download(file_name=os.path.join(DOWNLOADS_DIR, f"merge_{user_id}_{len(MERGE_STATE[user_id]) + 1}.mp4"))
    MERGE_STATE[user_id].append(file_path)

    if len(MERGE_STATE[user_id]) == 2:
        await message.reply_text("Merging videos...")
        list_file = os.path.join(DOWNLOADS_DIR, f"list_{user_id}.txt")
        output_file = os.path.join(DOWNLOADS_DIR, f"merged_{user_id}.mp4")

        with open(list_file, "w") as f:
            for vid in MERGE_STATE[user_id]:
                f.write(f"file '{vid}'\n")

        subprocess.run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_file], check=True)

        await client.send_document(chat_id=message.chat.id, document=output_file, caption="Merged Video")

        for f in MERGE_STATE[user_id]:
            os.remove(f)
        os.remove(list_file)
        os.remove(output_file)
        del MERGE_STATE[user_id]
    else:
        await message.reply_text("1st video received. Send second video to merge.")
    return

context = user_context.get(user_id)
if context:
    command, args = context
    del user_context[user_id]

    file_path = await message.download(file_name=os.path.join(DOWNLOADS_DIR, message.document.file_name if message.document else "video.mp4"))
    if command == "extract":
        audio_path = os.path.join(DOWNLOADS_DIR, "audio.mp3")
        subprocess.run(["ffmpeg", "-i", file_path, "-q:a", "0", "-map", "a", audio_path], check=True)
        await client.send_document(message.chat.id, audio_path, caption="Extracted Audio")
        os.remove(file_path)
        os.remove(audio_path)
    elif command == "compress":
        output_file = os.path.join(DOWNLOADS_DIR, "compressed.mp4")
        subprocess.run(["ffmpeg", "-i", file_path, "-vcodec", "libx265", "-crf", "28", output_file], check=True)
        await client.send_document(message.chat.id, output_file, caption="Compressed Video")
        os.remove(file_path)
        os.remove(output_file)
    elif command == "watermark":
        if not args:
            return await message.reply_text("Please send watermark image first using /watermark")
        watermark_path = args[0]
        output_file = os.path.join(DOWNLOADS_DIR, "watermarked.mp4")
        subprocess.run(["ffmpeg", "-i", file_path, "-i", watermark_path, "-filter_complex", "overlay=10:10", output_file], check=True)
        await client.send_document(message.chat.id, output_file, caption="Video with Watermark")
        os.remove(file_path)
        os.remove(output_file)
    elif command == "rename":
        new_name = args[0]
        new_path = os.path.join(DOWNLOADS_DIR, new_name)
        os.rename(file_path, new_path)
        await client.send_document(message.chat.id, new_path, caption="Renamed File")
        os.remove(new_path)
    elif command == "metadata":
        title, desc = args
        output_file = os.path.join(DOWNLOADS_DIR, "metadata_updated.mp4")
        subprocess.run(["ffmpeg", "-i", file_path, "-metadata", f"title={title}", "-metadata", f"comment={desc}", "-codec", "copy", output_file], check=True)
        await client.send_document(message.chat.id, output_file, caption="Updated Metadata")
        os.remove(file_path)
        os.remove(output_file)
    return

await message.reply_text("File received. Use /rename, /metadata or other tools.")

@app.on_message(filters.private & filters.text & filters.regex(r"https?://")) async def url_handler(client: Client, message: Message): if message.from_user.id not in ADMINS: return url = message.text.strip() await message.reply_text(f"Downloading from URL: {url}") try: ydl_opts = { 'outtmpl': f'{DOWNLOADS_DIR}/%(title)s.%(ext)s', 'format': 'best' } with yt_dlp.YoutubeDL(ydl_opts) as ydl: info = ydl.extract_info(url, download=True) file_path = ydl.prepare_filename(info) await message.reply_document(file_path) os.remove(file_path) except Exception as e: await message.reply_text(f"Error: {e}")

@app.on_message(filters.private & filters.text & filters.regex(r"magnet:?xt=urn")) async def torrent_handler(client: Client, message: Message): if message.from_user.id not in ADMINS: return magnet = message.text.strip() await message.reply_text("Adding torrent...") try: subprocess.run(["qbittorrent-nox", "--save-path=downloads", magnet], check=True) await message.reply_text("Torrent started. You must fetch result manually from Render volume.") except Exception as e: await message.reply_text(f"Torrent error: {e}")

@app.on_message(filters.command("merge") & filters.private) async def merge_handler(client, message): if message.from_user.id not in ADMINS: return MERGE_STATE[message.from_user.id] = [] await message.reply_text("Send 2 video files one by one to merge.")

@app.on_message(filters.command("extract") & filters.private) async def extract_audio(client, message): if message.from_user.id not in ADMINS: return user_context[message.from_user.id] = ("extract", []) await message.reply_text("Send a video to extract audio")

@app.on_message(filters.command("compress") & filters.private) async def compress_video(client, message): if message.from_user.id not in ADMINS: return user_context[message.from_user.id] = ("compress", []) await message.reply_text("Send a video to compress")

@app.on_message(filters.command("watermark") & filters.private) async def watermark_image(client, message): if message.from_user.id not in ADMINS: return await message.reply_text("Send the watermark image now.") user_context[message.from_user.id] = ("watermark_wait", [])

@app.on_message(filters.private & filters.photo & (filters.create(lambda _, _, msg: user_context.get(msg.from_user.id, [None])[0] == "watermark_wait"))) async def receive_watermark_image(client, message): file_path = await message.download(file_name=os.path.join(DOWNLOADS_DIR, f"watermark{message.from_user.id}.png")) user_context[message.from_user.id] = ("watermark", [file_path]) await message.reply_text("Watermark image received. Now send a video to apply it.")

@app.on_message(filters.command("rename") & filters.private) async def rename_command(client, message): if message.from_user.id not in ADMINS: return if len(message.command) < 2: return await message.reply_text("Usage: /rename newfilename.ext") filename = message.text.split(maxsplit=1)[1] user_context[message.from_user.id] = ("rename", [filename]) await message.reply_text("Now send the file to rename.")

@app.on_message(filters.command("metadata") & filters.private) async def metadata_command(client, message): if message.from_user.id not in ADMINS: return try: args = message.text.split(maxsplit=2) title = args[1] desc = args[2] user_context[message.from_user.id] = ("metadata", [title, desc]) await message.reply_text("Now send the video to apply metadata.") except: await message.reply_text("Usage: /metadata <title> <description>")

if name == "main": print("Bot starting...") app.run()


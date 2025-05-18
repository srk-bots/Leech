import os import asyncio import subprocess from pyrogram import Client, filters from pyrogram.types import Message import yt_dlp

API_ID = int(os.environ.get("API_ID", "27975779")) API_HASH = os.environ.get("API_HASH", "378062eb0a32d8d6b1bbbe97cb63a75a") BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token") ADMINS = [1416841137]  # Replace with your Telegram user ID

app = Client("leech-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DOWNLOADS_DIR = "downloads" os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def run_ffmpeg_cmd(cmd): print("Running:", " ".join(cmd)) subprocess.run(cmd, check=True)

def parse_flags(text): args = text.split() flags = {} if "-trim" in args: i = args.index("-trim") flags["trim"] = (args[i+1], args[i+2]) if "-remove" in args: i = args.index("-remove") flags["remove"] = (args[i+1], args[i+2]) if "-swap_audio" in args: i = args.index("-swap_audio") flags["swap_audio"] = (args[i+1], args[i+2]) if "-burn_sub" in args: i = args.index("-burn_sub") flags["burn_sub"] = args[i+1] if "-resize" in args: i = args.index("-resize") flags["resize"] = args[i+1] if "-frame" in args: i = args.index("-frame") flags["frame"] = args[i+1] if "-thumb" in args: flags["thumb"] = True if "-split" in args: flags["split"] = True return flags

@app.on_message(filters.private & filters.command("start")) async def start_handler(client: Client, message: Message): if message.from_user.id not in ADMINS: return await message.reply_text("Access Denied.") await message.reply_text("Welcome to the Leech Bot.\nSend a link with processing flags to begin.")

@app.on_message(filters.private & filters.command("rename")) async def rename_handler(client: Client, message: Message): if message.reply_to_message and message.reply_to_message.document: new_name = message.text.split(" ", 1)[1] file = await message.reply_to_message.download() new_path = os.path.join(DOWNLOADS_DIR, new_name) os.rename(file, new_path) await message.reply_document(new_path, caption="Renamed File") os.remove(new_path)

@app.on_message(filters.private & filters.command("compress")) async def compress_handler(client: Client, message: Message): if message.reply_to_message and message.reply_to_message.document: file = await message.reply_to_message.download() compressed = file.replace(".mp4", "_compressed.mp4") run_ffmpeg_cmd(["ffmpeg", "-i", file, "-vcodec", "libx265", "-crf", "28", compressed]) await message.reply_document(compressed, caption="Compressed File") os.remove(file) os.remove(compressed)

@app.on_message(filters.private & filters.command("watermark")) async def watermark_handler(client: Client, message: Message): if message.reply_to_message and message.reply_to_message.document: file = await message.reply_to_message.download() output = file.replace(".mp4", "_wm.mp4") run_ffmpeg_cmd(["ffmpeg", "-i", file, "-vf", "drawtext=text='SRK':fontcolor=white:fontsize=24:x=10:y=10", output]) await message.reply_document(output, caption="Watermarked File") os.remove(file) os.remove(output)

@app.on_message(filters.private & filters.command("metadata")) async def metadata_handler(client: Client, message: Message): if message.reply_to_message and message.reply_to_message.document: file = await message.reply_to_message.download() output = file.replace(".mp4", "_meta.mp4") run_ffmpeg_cmd(["ffmpeg", "-i", file, "-metadata", "title=SRK Bot", "-metadata", "author=SRK", "-codec", "copy", output]) await message.reply_document(output, caption="Metadata Updated File") os.remove(file) os.remove(output)

@app.on_message(filters.private & filters.text & filters.regex(r"https?://")) async def leech_handler(client: Client, message: Message): if message.from_user.id not in ADMINS: return

url = message.text.split()[0]
flags = parse_flags(message.text)
await message.reply_text("Downloading...")

try:
    ydl_opts = {'outtmpl': f'{DOWNLOADS_DIR}/%(title)s.%(ext)s', 'format': 'best'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)

    processed_path = os.path.join(DOWNLOADS_DIR, f"processed_{os.path.basename(file_path)}")

    cmd = ["ffmpeg", "-y", "-i", file_path]

    # Burn subtitle
    if "burn_sub" in flags:
        if flags["burn_sub"] == "file":
            subtitle_file = os.path.join(DOWNLOADS_DIR, "sub.srt")
            cmd += ["-vf", f"subtitles={subtitle_file}"]
        else:
            cmd += ["-filter_complex", f"[0:v][0:s:{flags['burn_sub']}]overlay"]

    # Trim video
    if "trim" in flags:
        start, end = flags["trim"]
        cmd += ["-ss", start, "-to", end]

    # Resize
    if "resize" in flags:
        height = flags["resize"]
        vf_index = None
        for i, item in enumerate(cmd):
            if item == "-vf":
                vf_index = i + 1
        if vf_index:
            cmd[vf_index] += f",scale=-1:{height}"
        else:
            cmd += ["-vf", f"scale=-1:{height}"]

    # Remove stream
    if "remove" in flags:
        stream_type, index = flags["remove"]
        if stream_type == "audio":
            cmd += ["-map", "0", "-map", f"-0:a:{index}"]
        elif stream_type == "video":
            cmd += ["-map", "0", "-map", f"-0:v:{index}"]

    # Swap audio
    if "swap_audio" in flags:
        rem, keep = flags["swap_audio"]
        cmd += ["-map", "0", "-map", f"-0:a:{rem}", "-disposition:a:0", "default"]

    cmd += ["-c", "copy", processed_path]
    run_ffmpeg_cmd(cmd)

    # Frame capture
    if "frame" in flags:
        frame_time = flags["frame"]
        frame_path = processed_path.replace(".mp4", "_frame.jpg")
        run_ffmpeg_cmd(["ffmpeg", "-ss", frame_time, "-i", processed_path, "-vframes", "1", frame_path])
        await client.send_photo(message.chat.id, frame_path, caption="Captured Frame")
        os.remove(frame_path)

    # Thumbnail extract
    if "thumb" in flags:
        thumb_path = processed_path.replace(".mp4", "_thumb.jpg")
        run_ffmpeg_cmd(["ffmpeg", "-i", processed_path, "-ss", "00:00:02.000", "-vframes", "1", thumb_path])
        await client.send_photo(message.chat.id, thumb_path, caption="Video Thumbnail")
        os.remove(thumb_path)

    # Split video/audio
    if "split" in flags:
        audio_path = processed_path.replace(".mp4", ".mp3")
        run_ffmpeg_cmd(["ffmpeg", "-i", processed_path, "-q:a", "0", "-map", "a", audio_path])
        await client.send_document(message.chat.id, audio_path, caption="Audio Track")
        os.remove(audio_path)

    await client.send_document(message.chat.id, processed_path, caption="Processed File")
    os.remove(file_path)
    os.remove(processed_path)

except Exception as e:
    await message.reply_text(f"Error: {e}")

print("Bot starting...") app.run()


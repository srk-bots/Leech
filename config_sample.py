import os import asyncio import subprocess from pyrogram import Client, filters from pyrogram.types import Message import yt_dlp

API_ID = int(os.environ.get("API_ID", "27975779")) API_HASH = os.environ.get("API_HASH", "378062eb0a32d8d6b1bbbe97cb63a75a") BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token") ADMINS = [1416841137]

app = Client("leech-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DOWNLOADS_DIR = "downloads" os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def run_ffmpeg_cmd(cmd): print("Running:", " ".join(cmd)) subprocess.run(cmd, check=True)

def parse_flags(text): args = text.split() flags = {} if "-trim" in args: i = args.index("-trim") flags["trim"] = (args[i+1], args[i+2]) if "-remove" in args: i = args.index("-remove") flags["remove"] = (args[i+1], args[i+2]) if "-swap_audio" in args: i = args.index("-swap_audio") flags["swap_audio"] = (args[i+1], args[i+2]) if "-frame" in args: i = args.index("-frame") flags["frame"] = args[i+1] if "-split" in args: flags["split"] = True return flags

def parse_manual_command(text): args = text.split() manual = {} if "compress" in args: manual["compress"] = True if "watermark" in args: manual["watermark"] = True if "burn_sub" in args: manual["burn_sub"] = True if "resize" in args: i = args.index("resize") manual["resize"] = args[i+1] if "thumb" in args: manual["thumb"] = True if "rename" in args: i = args.index("rename") manual["rename"] = args[i+1] if "metadata" in args: manual["metadata"] = True return manual

@app.on_message(filters.private & filters.command("start")) async def start_handler(client: Client, message: Message): if message.from_user.id not in ADMINS: return await message.reply_text("Access Denied.") await message.reply_text("Welcome to the Leech Bot. Reply to a link or file with /leech -vt or manual flags.")

@app.on_message(filters.private & filters.command("leech")) async def leech_command(client: Client, message: Message): if message.from_user.id not in ADMINS: return

reply = message.reply_to_message
text = message.text
if not reply:
    return await message.reply("Please reply to a message with a file or link.")

is_vt = "-vt" in text
flags = parse_flags(text)
manual = parse_manual_command(text)

if reply.document or reply.video:
    file_path = await reply.download(DOWNLOADS_DIR)
elif reply.text and reply.text.startswith("http"):
    url = reply.text
    ydl_opts = {'outtmpl': f'{DOWNLOADS_DIR}/%(title)s.%(ext)s', 'format': 'best'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
else:
    return await message.reply("Invalid reply content.")

processed_path = os.path.join(DOWNLOADS_DIR, f"processed_{os.path.basename(file_path)}")
cmd = ["ffmpeg", "-y", "-i", file_path]

if is_vt:
    if "trim" in flags:
        start, end = flags["trim"]
        cmd += ["-ss", start, "-to", end]
    if "remove" in flags:
        stype, idx = flags["remove"]
        if stype == "audio":
            cmd += ["-map", "0", f"-map", f"-0:a:{idx}"]
        elif stype == "video":
            cmd += ["-map", "0", f"-map", f"-0:v:{idx}"]
    if "swap_audio" in flags:
        rem, keep = flags["swap_audio"]
        cmd += ["-map", "0", f"-map", f"-0:a:{rem}", "-disposition:a:0", "default"]
    cmd += ["-c:v", "copy", "-c:a", "copy", processed_path]
    run_ffmpeg_cmd(cmd)

    if "frame" in flags:
        frame_time = flags["frame"]
        frame_path = processed_path.replace(".mp4", "_frame.jpg")
        run_ffmpeg_cmd(["ffmpeg", "-ss", frame_time, "-i", processed_path, "-vframes", "1", frame_path])
        await client.send_photo(message.chat.id, frame_path)
        os.remove(frame_path)

    if "split" in flags:
        audio_path = processed_path.replace(".mp4", ".mp3")
        run_ffmpeg_cmd(["ffmpeg", "-i", processed_path, "-q:a", "0", "-map", "a", audio_path])
        await client.send_document(message.chat.id, audio_path)
        os.remove(audio_path)

    await client.send_document(message.chat.id, processed_path)
    os.remove(file_path)
    os.remove(processed_path)

elif manual:
    rename_to = os.path.basename(file_path)
    if "rename" in manual:
        rename_to = manual["rename"] + os.path.splitext(file_path)[1]
    processed_path = os.path.join(DOWNLOADS_DIR, rename_to)

    if "compress" in manual:
        cmd += ["-b:v", "1M", processed_path]
    elif "watermark" in manual:
        cmd += ["-i", "watermark.png", "-filter_complex", "overlay=10:10", processed_path]
    elif "burn_sub" in manual:
        cmd += ["-vf", "subtitles=sub.srt", processed_path]
    elif "resize" in manual:
        h = manual["resize"]
        cmd += ["-vf", f"scale=-1:{h}", processed_path]
    elif "thumb" in manual:
        thumb_path = processed_path.replace(".mp4", "_thumb.jpg")
        run_ffmpeg_cmd(["ffmpeg", "-i", file_path, "-ss", "00:00:02.000", "-vframes", "1", thumb_path])
        await client.send_photo(message.chat.id, thumb_path)
        os.remove(thumb_path)
        return
    elif "metadata" in manual:
        cmd = ["ffmpeg", "-y", "-i", file_path, "-metadata", "title=MyTitle", "-metadata", "author=Bot", processed_path]

    run_ffmpeg_cmd(cmd)
    await client.send_document(message.chat.id, processed_path)
    os.remove(file_path)
    os.remove(processed_path)

print("Bot Ready") app.run()


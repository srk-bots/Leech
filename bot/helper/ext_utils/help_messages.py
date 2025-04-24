from bot.core.aeon_client import TgClient
from bot.helper.telegram_helper.bot_commands import BotCommands

nsfw_keywords = [
    "porn",
    "onlyfans",
    "nsfw",
    "Brazzers",
    "adult",
    "xnxx",
    "xvideos",
    "nsfwcherry",
    "hardcore",
    "Pornhub",
    "xvideos2",
    "youporn",
    "pornrip",
    "playboy",
    "hentai",
    "erotica",
    "blowjob",
    "redtube",
    "stripchat",
    "camgirl",
    "nude",
    "fetish",
    "cuckold",
    "orgy",
    "horny",
    "swingers",
    "ullu",
]

mirror = """<b>Send link along with command line or </b>

/cmd link

<b>By replying to link/file</b>:

/cmd -n new name -e -up upload destination

<b>NOTE:</b>
1. Commands that start with <b>qb</b> are ONLY for torrents."""

yt = """<b>Send link along with command line</b>:

/cmd link
<b>By replying to link</b>:
/cmd -n new name -z password -opt x:y|x1:y1

Check here all supported <a href='https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md'>SITES</a>
Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L212'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options."""

clone = """Send Gdrive|Gdot|Filepress|Filebee|Appdrive|Gdflix link or rclone path along with command or by replying to the link/rc_path by command.
Use -sync to use sync method in rclone. Example: /cmd rcl/rclone_path -up rcl/rclone_path/rc -sync"""

new_name = """<b>New Name</b>: -n

/cmd link -n new name
Note: Doesn't work with torrents"""

multi_link = """<b>Multi links only by replying to first link/file</b>: -i

/cmd -i 10(number of links/files)"""

same_dir = """<b>Move file(s)/folder(s) to new folder</b>: -m

You can use this arg also to move multiple links/torrents contents to the same directory, so all links will be uploaded together as one task

/cmd link -m new folder (only one link inside new folder)
/cmd -i 10(number of links/files) -m folder name (all links contents in one folder)
/cmd -b -m folder name (reply to batch of message/file(each link on new line))

While using bulk you can also use this arg with different folder name along with the links in message or file batch
Example:
link1 -m folder1
link2 -m folder1
link3 -m folder2
link4 -m folder2
link5 -m folder3
link6
so link1 and link2 content will be uploaded from same folder which is folder1
link3 and link4 content will be uploaded from same folder also which is folder2
link5 will uploaded alone inside new folder named folder3
link6 will get uploaded normally alone
"""

thumb = """<b>Thumbnail for current task</b>: -t

/cmd link -t tg-message-link (doc or photo) or none (file without thumb)"""

split_size = """<b>Split size for current task</b>: -sp

/cmd link -sp (500mb or 2gb or 4000000000)
Note: Only mb and gb are supported or write in bytes without unit!"""

upload = """<b>Upload Destination</b>: -up

/cmd link -up rcl/gdl (rcl: to select rclone config, remote & path | gdl: To select token.pickle, gdrive id) using buttons
You can directly add the upload path: -up remote:dir/subdir or -up Gdrive_id or -up id/username (telegram) or -up id/username|topic_id (telegram)
If DEFAULT_UPLOAD is `rc` then you can pass up: `gd` to upload using gdrive tools to GDRIVE_ID.
If DEFAULT_UPLOAD is `gd` then you can pass up: `rc` to upload to RCLONE_PATH.

If you want to add path or gdrive manually from your config/token (UPLOADED FROM USETTING) add mrcc: for rclone and mtp: before the path/gdrive_id without space.
/cmd link -up mrcc:main:dump or -up mtp:gdrive_id <strong>or you can simply edit upload using owner/user token/config from usetting without adding mtp: or mrcc: before the upload path/id</strong>

To add leech destination:
-up id/@username/pm
-up b:id/@username/pm (b: means leech by bot) (id or username of the chat or write pm means private message so bot will send the files in private to you)
when you should use b:(leech by bot)? When your default settings is leech by user and you want to leech by bot for specific task.
-up u:id/@username(u: means leech by user) This incase OWNER added USER_SESSION_STRING.
-up h:id/@username(hybrid leech) h: to upload files by bot and user based on file size.
-up id/@username|topic_id(leech in specific chat and topic) add | without space and write topic id after chat id or username.

In case you want to specify whether using token.pickle or service accounts you can add tp:gdrive_id (using token.pickle) or sa:gdrive_id (using service accounts) or mtp:gdrive_id (using token.pickle uploaded from usetting).
DEFAULT_UPLOAD doesn't affect on leech cmds.
"""

user_download = """<b>User Download</b>: link

/cmd tp:link to download using owner token.pickle incase service account enabled.
/cmd sa:link to download using service account incase service account disabled.
/cmd tp:gdrive_id to download using token.pickle and file_id incase service account enabled.
/cmd sa:gdrive_id to download using service account and file_id incase service account disabled.
/cmd mtp:gdrive_id or mtp:link to download using user token.pickle uploaded from usetting
/cmd mrcc:remote:path to download using user rclone config uploaded from usetting
you can simply edit upload using owner/user token/config from usetting without adding mtp: or mrcc: before the path/id"""

rcf = """<b>Rclone Flags</b>: -rcf

/cmd link|path|rcl -up path|rcl -rcf --drive-starred-only|key|key:value
This will override all other flags except --exclude
Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>."""

bulk = """<b>Bulk Download</b>: -b

Bulk can be used only by replying to text message or text file contains links separated by new line.
Example:
link1 -n new name -up remote1:path1 -rcf |key:value|key:value
link2 -z -n new name -up remote2:path2
link3 -e -n new name -up remote2:path2
Reply to this example by this cmd -> /cmd -b(bulk)

Note: Any arg along with the cmd will be setted to all links
/cmd -b -up remote: -z -m folder name (all links contents in one zipped folder uploaded to one destination)
so you can't set different upload destinations along with link incase you have added -m along with cmd
You can set start and end of the links from the bulk like seed, with -b start:end or only end by -b :end or only start by -b start.
The default start is from zero(first link) to inf."""

rlone_dl = """<b>Rclone Download</b>:

Treat rclone paths exactly like links
/cmd main:dump/ubuntu.iso or rcl(To select config, remote and path)
Users can add their own rclone from user settings
If you want to add path manually from your config add mrcc: before the path without space
/cmd mrcc:main:dump/ubuntu.iso
You can simply edit using owner/user config from usetting without adding mrcc: before the path"""

extract_zip = """<b>Extract/Zip</b>: -e -z

/cmd link -e password (extract password protected)
/cmd link -z password (zip password protected)
/cmd link -z password -e (extract and zip password protected)
Note: When both extract and zip added with cmd it will extract first and then zip, so always extract first"""

join = """<b>Join Splitted Files</b>: -j

This option will only work before extract and zip, so mostly it will be used with -m argument (samedir)
By Reply:
/cmd -i 3 -j -m folder name
/cmd -b -j -m folder name
if u have link(folder) have splitted files:
/cmd link -j"""

tg_links = """<b>TG Links</b>:

Treat links like any direct link
Some links need user access so you must add USER_SESSION_STRING for it.
Three types of links:
Public: https://t.me/channel_name/message_id
Private: tg://openmessage?user_id=xxxxxx&message_id=xxxxx
Super: https://t.me/c/channel_id/message_id
Range: https://t.me/channel_name/first_message_id-last_message_id
Range Example: tg://openmessage?user_id=xxxxxx&message_id=555-560 or https://t.me/channel_name/100-150
Note: Range link will work only by replying cmd to it"""

sample_video = """<b>Sample Video</b>: -sv

Create sample video for one video or folder of videos.
/cmd -sv (it will take the default values which 60sec sample duration and part duration is 4sec).
You can control those values. Example: /cmd -sv 70:5(sample-duration:part-duration) or /cmd -sv :5 or /cmd -sv 70."""

screenshot = """<b>ScreenShots</b>: -ss

Create screenshots for one video or folder of videos.
/cmd -ss (it will take the default values which is 10 photos).
You can control this value. Example: /cmd -ss 6."""

seed = """<b>Bittorrent seed</b>: -d

/cmd link -d ratio:seed_time or by replying to file/link
To specify ratio and seed time add -d ratio:time.
Example: -d 0.7:10 (ratio and time) or -d 0.7 (only ratio) or -d :10 (only time) where time in minutes"""

zip_arg = """<b>Zip</b>: -z password

/cmd link -z (zip)
/cmd link -z password (zip password protected)"""

qual = """<b>Quality Buttons</b>: -s

In case default quality added from yt-dlp options using format option and you need to select quality for specific link or links with multi links feature.
/cmd link -s"""

yt_opt = """<b>Options</b>: -opt

/cmd link -opt {"format": "bv*+mergeall[vcodec=none]", "nocheckcertificate": True, "playliststart": 10, "fragment_retries": float("inf"), "matchtitle": "S13", "writesubtitles": True, "live_from_start": True, "postprocessor_args": {"ffmpeg": ["-threads", "4"]}, "wait_for_video": (5, 100), "download_ranges": [{"start_time": 0, "end_time": 10}]}
Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options."""

convert_media = """<b>Convert Media</b>: -ca -cv
/cmd link -ca mp3 -cv mp4 (convert all audios to mp3 and all videos to mp4)
/cmd link -ca mp3 (convert all audios to mp3)
/cmd link -cv mp4 (convert all videos to mp4)
/cmd link -ca mp3 + flac ogg (convert only flac and ogg audios to mp3)
/cmd link -cv mkv - webm flv (convert all videos to mp4 except webm and flv)"""

force_start = """<b>Force Start</b>: -f -fd -fu
/cmd link -f (force download and upload)
/cmd link -fd (force download only)
/cmd link -fu (force upload directly after download finish)"""

gdrive = """<b>Gdrive</b>: link
If DEFAULT_UPLOAD is `rc` then you can pass up: `gd` to upload using gdrive tools to GDRIVE_ID.
/cmd gdriveLink or gdl or gdriveId -up gdl or gdriveId or gd
/cmd tp:gdriveLink or tp:gdriveId -up tp:gdriveId or gdl or gd (to use token.pickle if service account enabled)
/cmd sa:gdriveLink or sa:gdriveId -p sa:gdriveId or gdl or gd (to use service account if service account disabled)
/cmd mtp:gdriveLink or mtp:gdriveId -up mtp:gdriveId or gdl or gd(if you have added upload gdriveId from usetting) (to use user token.pickle that uploaded by usetting)
You can simply edit using owner/user token from usetting without adding mtp: before the id"""

rclone_cl = """<b>Rclone</b>: path
If DEFAULT_UPLOAD is `gd` then you can pass up: `rc` to upload to RCLONE_PATH.
/cmd rcl/rclone_path -up rcl/rclone_path/rc -rcf flagkey:flagvalue|flagkey|flagkey:flagvalue
/cmd rcl or rclone_path -up rclone_path or rc or rcl
/cmd mrcc:rclone_path -up rcl or rc(if you have add rclone path from usetting) (to use user config)"""

name_sub = r"""<b>Name Substitution</b>: -ns

<blockquote>Dont understand? Then follow this <a href='https://t.me/aimupdate/190'>quide</a></blockquote>

/cmd link -ns script/code/s | mirror/leech | tea/ /s | clone | cpu/ | \[hello\]/hello | \\text\\/text/s
This will affect on all files. Format: wordToReplace/wordToReplaceWith/sensitiveCase
Word Subtitions. You can add pattern instead of normal text. Timeout: 60 sec
NOTE: You must add \ before any character, those are the characters: \^$.|?*+()[]{}-
1. script will get replaced by code with sensitive case
2. mirror will get replaced by leech
4. tea will get replaced by space with sensitive case
5. clone will get removed
6. cpu will get replaced by space
7. [hello] will get replaced by hello
8. \text\ will get replaced by text with sensitive case
"""

transmission = """<b>Tg transmission</b>: -hl -ut -bt
/cmd link -hl (leech by user and bot session with respect to size) (Hybrid Leech)
/cmd link -bt (leech by bot session)
/cmd link -ut (leech by user)"""

thumbnail_layout = """Thumbnail Layout: -tl
/cmd link -tl 3x3 (widthxheight) 3 photos in row and 3 photos in column"""

leech_as = """<b>Leech as</b>: -doc -med
/cmd link -doc (Leech as document)
/cmd link -med (Leech as media)"""

leech_filename = """<b>Leech Filename</b>:

Set a global filename template for all your leech files. The template supports dynamic variables like {season}, {episode}, and {quality}.

Example: Naruto S{season} E{episode} Q{quality}.mkv

This will rename all files to follow this pattern, automatically replacing the variables with the actual values from each file.

You can set this in your user settings by going to /usettings > Leech Settings > Leech Filename.

Note: Leech Caption still takes priority for display purposes, but this affects the actual filename of the files."""

font_styles = """<b>Font Styles</b>:
Use the /fonts or /fontstyles command to see available font styles for leech.

<b>Three Types of Font Styling:</b>
• <b>Unicode Styles</b>: Transform regular ASCII characters into special Unicode variants (serif, sans, script, etc.)
• <b>HTML Formatting</b>: Apply Telegram's supported HTML tags (bold, italic, code, etc.)
• <b>Google Fonts</b>: Use any Google Font name for styling (Roboto, Open Sans, Lato, etc.)

<blockquote expandable="expandable"><b>Google Fonts Support:</b>
You can use Google Fonts in two ways:

1. <b>Leech Font Setting</b>: Set a Google Font name as your leech font to apply it to all captions

2. <b>Leech Caption Templates</b>: Apply Google Fonts to specific parts of your caption using this syntax:
   <code>{{variable}font_name}</code> - Apply font_name to just that variable
   Example: <code>{{filename}Roboto} - Size: {size}</code>

3. <b>Available Google Fonts</b>: You can use any Google Font name, including:
   • Roboto, Open Sans, Lato, Montserrat, Oswald
   • Raleway, Source Sans Pro, Slabo, PT Sans
   • And many more - see fonts.google.com for the full list

4. <b>Font Weight Support</b>: You can specify font weight for leech caption:
   • <code>{{filename}Roboto:700}</code> - Bold Roboto
   • <code>{{filename}Open Sans:300}</code> - Light Open Sans
   • <code>{{filename}Montserrat:900}</code> - Black Montserrat

5. <b>Font Style Support</b>: You can specify font style for leech caption:
   • <code>{{filename}Roboto:italic}</code> - Italic Roboto
   • <code>{{filename}Open Sans:700italic}</code> - Bold Italic Open Sans

6. <b>Multiple Font Properties</b>: You can combine weight and style for leech caption:
   • <code>{{filename}Roboto:700italic}</code> - Bold Italic Roboto</blockquote>

<blockquote expandable="expandable"><b>Unicode Font Styles:</b>
Unicode font styles transform regular ASCII characters into special Unicode variants.

Available Unicode styles:
• <b>serif</b>: 𝐒𝐞𝐫𝐢𝐟 𝐭𝐞𝐱𝐭 (bold)
• <b>serif_i</b>: 𝑆𝑒𝑟𝑖𝑓 𝑖𝑡𝑎𝑙𝑖𝑐 𝑡𝑒𝑥𝑡
• <b>serif_b</b>: 𝑺𝒆𝒓𝒊𝒇 𝒃𝒐𝒍𝒅 𝒊𝒕𝒂𝒍𝒊𝒄 𝒕𝒆𝒙𝒕
• <b>sans</b>: 𝖲𝖺𝗇𝗌 𝗍𝖾𝗑𝗍
• <b>sans_i</b>: 𝘚𝘢𝘯𝘴 𝘪𝘵𝘢𝘭𝘪𝘤 𝘵𝘦𝘹𝘵
• <b>sans_b</b>: 𝗦𝗮𝗻𝘀 𝗯𝗼𝗹𝗱 𝘁𝗲𝘅𝘁
• <b>sans_bi</b>: 𝙎𝙖𝙣𝙨 𝙗𝙤𝙡𝙙 𝙞𝙩𝙖𝙡𝙞𝙘 𝙩𝙚𝙭𝙩
• <b>script</b>: 𝒮𝒸𝓇𝒾𝓅𝓉 𝓉𝑒𝓍𝓉
• <b>script_b</b>: 𝓢𝓬𝓻𝓲𝓹𝓽 𝓫𝓸𝓵𝓭 𝓽𝓮𝔁𝓽
• <b>fraktur</b>: 𝔉𝔯𝔞𝔨𝔱𝔲𝔯 𝔱𝔢𝔵𝔱
• <b>fraktur_b</b>: 𝕱𝖗𝖆𝖐𝖙𝖚𝖗 𝖇𝖔𝖑𝖉 𝖙𝖊𝖝𝖙
• <b>mono</b>: 𝙼𝚘𝚗𝚘𝚜𝚙𝚊𝚌𝚎 𝚝𝚎𝚡𝚝
• <b>double</b>: 𝔻𝕠𝕦𝕓𝕝𝕖-𝕤𝕥𝕣𝕦𝕔𝕜 𝕥𝕖𝕩𝕥
• <b>gothic</b>: 𝖆𝖇𝖈
• <b>small_caps</b>: ᴀʙᴄ
• <b>circled</b>: ⓐⓑⓒ
• <b>bubble</b>: ａｂｃ
• <b>inverted</b>: ɐqɔ
• <b>squared</b>: 🄰🄱🄲
• <b>regional</b>: 🇦🇧🇨
• <b>superscript</b>: ᵃᵇᶜ
• <b>subscript</b>: ₐₑₓ
• <b>wide</b>: ｗｉｄｅ
• <b>cursive</b>: 𝒶𝒷𝒸

<b>For Leech Font:</b>
Enter one of the Unicode style names like "serif", "sans_b", "script", etc.
Example: Enter sans_b to use 𝗦𝗮𝗻𝘀 𝗯𝗼𝗹𝗱 𝘁𝗲𝘅𝘁 for all your leech captions

<b>For Leech Caption:</b>
Use the template variable format: {{variable}unicode_style}
Example: {{filename}serif_b} - Size: {{size}mono}
This applies serif bold to the filename and monospace to the size

Remember that Unicode styling only works with basic Latin characters (A-Z, a-z) and won't affect numbers or special characters.</blockquote>

<blockquote expandable="expandable"><b>HTML Formatting:</b>
HTML formatting applies Telegram's supported HTML tags to your text.

Available HTML formats:
• <b>bold</b>: <b>Bold text</b>
• <b>italic</b>: <i>Italic text</i>
• <b>underline</b>: <u>Underlined text</u>
• <b>strike</b>: <s>Strikethrough text</s>
• <b>code</b>: <code>Monospace text</code>
• <b>pre</b>: Preformatted text
• <b>spoiler</b>: <tg-spoiler>Spoiler text</tg-spoiler>
• <b>quote</b>: Quoted text

You can combine HTML formats:
• <b>bold_italic</b>: <b><i>Bold italic text</i></b>
• <b>bold_underline</b>: <b><u>Bold underlined text</u></b>
• <b>italic_underline</b>: <i><u>Italic underlined text</u></b>
• <b>bold_italic_underline</b>: <b><i><u>Bold italic underlined text</u></i></b>
• <b>quote_expandable</b>: <b><i><u>The text will be in expaned formate</u></i></b>
• <b>bold_quote</b>: <b><i><u>Text will be bold in quote formate</u></i></b>

<b>or Leech Font:</b>
Enter an HTML format name like "bold", "italic", "code", etc.
Example: Enter 'bold' to use <b>Bold text</b> for all your leech captions

<b>For Leech Caption:</b>
Use the template variable format: {{variable}html_format}
Example: {{filename}bold} - Size: {{size}code}
You can also use html tags like this -> <b> <i> <s> <u> <code> <pre> <tg-spoiler> <blockquote> <blockquote expandable="expandable">. You can also nest them together.</blockquote>

<blockquote expandable="expandable"><b>Unicode Emojis and Special Characters:</b>

You can also use any single Unicode character or emoji as a style. Examples:
- 🔥: Will add the fire emoji before and after your text
- ⭐: Will add stars before and after your text
- Any other emoji or special character will be used similarly

<b>For Leech Font:</b>
Any single emoji: 🔥, ⭐, 🚀, etc.
Any single Unicode character
Unicode codepoints in U+XXXX format (e.g., U+1F525 for 🔥)
The emoji will be added before and after your text
Example: If leech font is "🔥" and text is "filename.mp4", it will appear as "🔥filename.mp4🔥"

<b>For Leech Caption:</b>
Use the template variable format: {{variable}unicode_emoji}
Example: {{filename}🔥}</blockquote>

<blockquote expandable="expandable"><b>Template Variables (For Leech Caption and Leech Filename):</b>

<b>Basic Variables:</b>
• <code>{filename}</code> - The name of the file without extension
• <code>{size}</code> - The size of the file (e.g., 1.5GB, 750MB)
• <code>{duration}</code> - The duration of media files (e.g., 01:30:45)
• <code>{quality}</code> - The quality of video files (e.g., 1080p, 720p)
• <code>{audios}</code> - Audio languages in the file (e.g., English, Hindi)
• <code>{subtitles}</code> - Subtitle languages in the file (e.g., English, Spanish)
• <code>{md5_hash}</code> - MD5 hash of the file

<b>TV Show Variables:</b>
• <code>{season}</code> - Season number (with leading zero for single digits)
• <code>{episode}</code> - Episode number (with leading zero for single digits)

<b>Media Information:</b>
• <code>{NumVideos}</code> - Number of video tracks
• <code>{NumAudios}</code> - Number of audio tracks
• <code>{NumSubtitles}</code> - Number of subtitle tracks
• <code>{year}</code> - Release year extracted from filename or metadata
• <code>{formate}</code> - File format/extension
• <code>{id}</code> - Unique ID of the file
• <code>{framerate}</code> - Video framerate
• <code>{codec}</code> - Codec information (Video, Audio, Subtitle)

"<b>Example Usage:</b>
• TV Show: <code>{filename} S{season}E{episode} [{quality}]</code>
• Detailed: <code>{filename} [{formate}] [{codec}] [{framerate}]</code></blockquote>

<blockquote expandable="expandable"><b>Usage Examples:</b>

1. <b>Setting a default font style for all leech captions:</b>
   • Use the /usettings or /settings command and select "LEECH_FONT"
   • Enter a font style name like "serif_b" or "Roboto"

2. <b>Using font styles in caption templates:</b>
   • <code>{{filename}serif_b} - Size: {size}</code>
   • <code>File: {{filename}Montserrat:700} | {size}</code>
   • <code>{{filename}bold} | {{size}italic}</code>

3. <b>Mixing different font styles:</b>
   • <code>{{filename}Roboto:700} | {{size}mono} | {{quality}script}</code>

4. <b>Using HTML formatting with variables:</b>
   • <code>{{filename}bold_italic} | {{size}code}</code>

5. <b>Combining Google Fonts with HTML formatting:</b>
   • <code>{{{filename}Roboto:700}bold}</code> - Bold Roboto with HTML bold</blockquote>

6. <b>Combining with unicode emoji:</b>
   • <code>{{{{filename}Roboto:700}bold}🔥}</code> - Bold Roboto with HTML bold and with unicode emoji</blockquote>

<blockquote expandable="expandable"><b>How to Find Google Fonts:</b>
1. Visit <a href='https://fonts.google.com/'>fonts.google.com</a>
2. Find a font you like
3. Use the exact font name in your leech font setting or caption template</blockquote>

<b>Important Notes:</b>
• Unicode font styles only work with basic Latin characters (A-Z, a-z)
• Google Fonts support depends on the rendering capabilities of the device
• HTML formatting is the most compatible across all devices
• Font styles are applied after template variables are processed
• User settings take priority over owner settings"""

ffmpeg_cmds = """<b>FFmpeg Commands</b>: -ff

<blockquote>Dont understand? Then follow this <a href='https://t.me/aimupdate/218'>quide</a></blockquote>

list of lists of ffmpeg commands. You can set multiple ffmpeg commands for all files before upload. Don't write ffmpeg at beginning, start directly with the arguments.
Notes:
1. Add <code>-del</code> to the list(s) which you want from the bot to delete the original files after command run complete!
2. To execute one of pre-added lists in bot like: ({"subtitle": ["-i mltb.mkv -c copy -c:s srt mltb.mkv"]}), you must use -ff subtitle (list key)
Examples: ["-i mltb.mkv -c copy -c:s srt mltb.mkv", "-i mltb.video -c copy -c:s srt mltb", "-i mltb.m4a -c:a libmp3lame -q:a 2 mltb.mp3", "-i mltb.audio -c:a libmp3lame -q:a 2 mltb.mp3", "-i mltb -map 0:a -c copy mltb.mka -map 0:s -c copy mltb.srt"]
Here I will explain how to use mltb.* which is reference to files you want to work on.
1. First cmd: the input is mltb.mkv so this cmd will work only on mkv videos and the output is mltb.mkv also so all outputs is mkv. -del will delete the original media after complete run of the cmd.
2. Second cmd: the input is mltb.video so this cmd will work on all videos and the output is only mltb so the extenstion is same as input files.
3. Third cmd: the input in mltb.m4a so this cmd will work only on m4a audios and the output is mltb.mp3 so the output extension is mp3.
4. Fourth cmd: the input is mltb.audio so this cmd will work on all audios and the output is mltb.mp3 so the output extension is mp3."""

YT_HELP_DICT = {
    "main": yt,
    "New-Name": f"{new_name}\nNote: Don't add file extension",
    "Zip": zip_arg,
    "Quality": qual,
    "Options": yt_opt,
    "Multi-Link": multi_link,
    "Same-Directory": same_dir,
    "Thumb": thumb,
    "Split-Size": split_size,
    "Upload-Destination": upload,
    "Rclone-Flags": rcf,
    "Bulk": bulk,
    "Sample-Video": sample_video,
    "Screenshot": screenshot,
    "Convert-Media": convert_media,
    "Force-Start": force_start,
    "Name-Substitute": name_sub,
    "TG-Transmission": transmission,
    "Thumb-Layout": thumbnail_layout,
    "Leech-Type": leech_as,
    "Leech-Filename": leech_filename,
    "FFmpeg-Cmds": ffmpeg_cmds,
}

# Merge flags guide has been moved to media_tools_help.py

# Watermark guide has been moved to media_tools_help.py

MIRROR_HELP_DICT = {
    "main": mirror,
    "New-Name": new_name,
    "DL-Auth": "<b>Direct link authorization</b>: -au -ap\n\n/cmd link -au username -ap password",
    "Headers": "<b>Direct link custom headers</b>: -h\n\n/cmd link -h key: value key1: value1",
    "Extract/Zip": extract_zip,
    "Select-Files": "<b>Bittorrent/JDownloader/Sabnzbd File Selection</b>: -s\n\n/cmd link -s or by replying to file/link",
    "Torrent-Seed": seed,
    "Multi-Link": multi_link,
    "Same-Directory": same_dir,
    "Thumb": thumb,
    "Split-Size": split_size,
    "Upload-Destination": upload,
    "Rclone-Flags": rcf,
    "Bulk": bulk,
    "Join": join,
    "Rclone-DL": rlone_dl,
    "Tg-Links": tg_links,
    "Sample-Video": sample_video,
    "Screenshot": screenshot,
    "Convert-Media": convert_media,
    "Force-Start": force_start,
    "User-Download": user_download,
    "Name-Substitute": name_sub,
    "TG-Transmission": transmission,
    "Thumb-Layout": thumbnail_layout,
    "Leech-Type": leech_as,
    "Leech-Filename": leech_filename,
    "FFmpeg-Cmds": ffmpeg_cmds,
}

CLONE_HELP_DICT = {
    "main": clone,
    "Multi-Link": multi_link,
    "Bulk": bulk,
    "Gdrive": gdrive,
    "Rclone": rclone_cl,
}

RSS_HELP_MESSAGE = """
Use this format to add feed url:
Title1 link (required)
Title2 link -c cmd -inf xx -exf xx
Title3 link -c cmd -d ratio:time -z password

-c command -up mrcc:remote:path/subdir -rcf key|key:value
-inf For included words filter.
-exf For excluded words filter.
-stv true or false (sensitive filter)

<b>Movie Websites with Auto Domain Detection:</b>
You can subscribe to these movie websites by just entering their name after clicking the Subscribe button. The bot will automatically detect the current domain:
• <code>movierulz</code> - MovieRulz (5movierulz.skin → current domain)
• <code>tamilmv</code> - 1TamilMV (1tamilmv.com → current domain)
• <code>tamilblasters</code> - 1TamilBlasters (1tamilblasters.net → current domain)

Examples:
movierulz
tamilmv -c mirror
tamilblasters -inf 1080p|Tamil

Just click the Subscribe button and enter one of these names. The bot will automatically find the current domain for these websites, so you don't need to worry about domain changes.

<b>Regular RSS Examples:</b>
Example: Title https://www.rss-url.com -inf 1080 or 720 or 144p|mkv or mp4|hevc -exf flv or web|xxx
This filter will parse links that its titles contain `(1080 or 720 or 144p) and (mkv or mp4) and hevc` and doesn't contain (flv or web) and xxx words. You can add whatever you want.

Another example: -inf  1080  or 720p|.web. or .webrip.|hvec or x264. This will parse titles that contain ( 1080  or 720p) and (.web. or .webrip.) and (hvec or x264). I have added space before and after 1080 to avoid wrong matching. If this `10805695` number in title it will match 1080 if added 1080 without spaces after it.

Filter Notes:
1. | means and.
2. Add `or` between similar keys, you can add it between qualities or between extensions, so don't add filter like this f: 1080|mp4 or 720|web because this will parse 1080 and (mp4 or 720) and web ... not (1080 and mp4) or (720 and web).
3. You can add `or` and `|` as much as you want.
4. Take a look at the title if it has a static special character after or before the qualities or extensions or whatever and use them in the filter to avoid wrong match.
Timeout: 60 sec.
"""

PASSWORD_ERROR_MESSAGE = """
<b>This link requires a password!</b>
- Insert <b>::</b> after the link and write the password after the sign.

<b>Example:</b> link::my password
"""


user_settings_text = {
    "METADATA_KEY": "Send your text for change mkv medias metadata (title only). Timeout: 60 sec",
    "METADATA_ALL": "Send metadata text to be used for all metadata fields (title, author, comment). This takes priority over individual settings. Timeout: 60 sec",
    "METADATA_TITLE": "Send metadata text to be used for the title field. Timeout: 60 sec",
    "METADATA_AUTHOR": "Send metadata text to be used for the author field. Timeout: 60 sec",
    "METADATA_COMMENT": "Send metadata text to be used for the comment field. Timeout: 60 sec",
    "USER_SESSION": "Send your pyrogram user session string for download from private telegram chat. Timeout: 60 sec",
    "USER_DUMP": "Send your channel or group id where you want to store your leeched files. Bot must have permission to send message in your chat. Timeout: 60 sec",
    "LEECH_FILENAME_CAPTION": """Send leech filename caption. Use /fontstyles for styling options and template variables.

<b>Basic Variables:</b> {filename}, {size}, {duration}, {quality}, {audios}, {subtitles}
<b>Media Info:</b> {season}, {episode}, {year}, {formate}, {framerate}, {codec}
<b>Track Counts:</b> {NumVideos}, {NumAudios}, {NumSubtitles}
<b>Other:</b> {id}, {md5_hash}

<b>Styling:</b> Use {{variable}style} format (e.g., {{filename}bold}, {{size}Roboto})

<b>Examples:</b>
• {filename} [{size}]
• {{filename}bold} S{season}E{episode}
• {{filename}Roboto} [{codec}]

Timeout: 60 sec""",
    "LEECH_SPLIT_SIZE": f"Send Leech split size in bytes or use gb or mb. Example: 40000000 or 2.5gb or 1000mb. IS_PREMIUM_USER: {TgClient.IS_PREMIUM_USER}. Timeout: 60 sec",
    "LEECH_DUMP_CHAT": """"Send leech destination ID/USERNAME/PM.
* b:id/@username/pm (b: means leech by bot) (id or username of the chat or write pm means private message so bot will send the files in private to you) when you should use b:(leech by bot)? When your default settings is leech by user and you want to leech by bot for specific task.
* u:id/@username(u: means leech by user) This incase OWNER added USER_SESSION_STRING.
* h:id/@username(hybrid leech) h: to upload files by bot and user based on file size.
* id/@username|topic_id(leech in specific chat and topic) add | without space and write topic id after chat id or username. Timeout: 60 sec""",
    "LEECH_FILENAME_PREFIX": r"Send Leech Filename Prefix. You can add HTML tags. Example: <code>@mychannel</code>. Timeout: 60 sec",
    "LEECH_SUFFIX": r"Send Leech Filename Suffix. You can add HTML tags. Example: <code>@mychannel</code>. Timeout: 60 sec",
    "LEECH_FONT": "Send Leech Font Style. Options: HTML formats (bold, italic), Unicode styles (serif, sans_b), Google Fonts (Roboto, Open Sans), or emojis (🔥). Use /fontstyles for full list. Timeout: 60 sec",
    "LEECH_FILENAME": "Send Leech Filename template. This will change the actual filename of all your leech files. Supports template variables like {season}, {episode}, {quality}. Example: Series S{season}E{episode} [{quality}]. Timeout: 60 sec",
    "THUMBNAIL_LAYOUT": "Send thumbnail layout (widthxheight, 2x2, 3x3, 2x4, 4x4, ...). Example: 3x3. Timeout: 60 sec",
    "RCLONE_PATH": "Send Rclone Path. If you want to use your rclone config edit using owner/user config from usetting or add mrcc: before rclone path. Example mrcc:remote:folder. Timeout: 60 sec",
    "RCLONE_FLAGS": "key:value|key|key|key:value . Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>\nEx: --drive-starred-only",
    "GDRIVE_ID": "Send Gdrive ID. If you want to use your token.pickle edit using owner/user token from usetting or add mtp: before the id. Example: mtp:F435RGGRDXXXXXX . Timeout: 60 sec",
    "INDEX_URL": "Send Index URL. Timeout: 60 sec",
    "UPLOAD_PATHS": "Send Dict of keys that have path values. Example: {'path 1': 'remote:rclonefolder', 'path 2': 'gdrive1 id', 'path 3': 'tg chat id', 'path 4': 'mrcc:remote:', 'path 5': b:@username} . Timeout: 60 sec",
    "EXCLUDED_EXTENSIONS": "Send exluded extenions separated by space without dot at beginning. Timeout: 60 sec",
    "NAME_SUBSTITUTE": r"""Word Subtitions. You can add pattern instead of normal text. Timeout: 60 sec
NOTE: You must add \ before any character, those are the characters: \^$.|?*+()[]{}-
Example: script/code/s | mirror/leech | tea/ /s | clone | cpu/ | \[mltb\]/mltb | \\text\\/text/s
1. script will get replaced by code with sensitive case
2. mirror will get replaced by leech
4. tea will get replaced by space with sensitive case
5. clone will get removed
6. cpu will get replaced by space
7. [mltb] will get replaced by mltb
8. \text\ will get replaced by text with sensitive case
""",
    "YT_DLP_OPTIONS": """Send dict of YT-DLP Options. Timeout: 60 sec
Format: {key: value, key: value, key: value}.
Example: {"format": "bv*+mergeall[vcodec=none]", "nocheckcertificate": True, "playliststart": 10, "fragment_retries": float("inf"), "matchtitle": "S13", "writesubtitles": True, "live_from_start": True, "postprocessor_args": {"ffmpeg": ["-threads", "4"]}, "wait_for_video": (5, 100), "download_ranges": [{"start_time": 0, "end_time": 10}]}
Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options.""",
    "FFMPEG_CMDS": """Read this guide. http://telegra.ph/Ffmpeg-guide-01-10""",
    "HELPER_TOKENS": """Send your helper bot tokens separated by space. These bots will be used for hyper download to speed up your downloads.
Example: 1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ 0987654321:ZYXWVUTSRQPONMLKJIHGFEDCBA

NOTE: You can add up to 20 helper bots. Make sure the bots are created using @BotFather and are not being used by any other bot.
To use these bots, you need to enable them using the 'Enable Helper Bots' button in the leech settings menu.
Timeout: 60 sec""",
    "ENABLE_HELPER_BOTS": """Enable or disable helper bots for hyper download.
When enabled, both your helper bots and the owner's helper bots will be used for downloads.
When disabled, only the owner's helper bots will be used.
Timeout: 60 sec""",
}

# Media Tools help text
media_tools_text = {
    # General Media Tools
    "MEDIA_TOOLS_PRIORITY": "Set priority for media tools processing. Lower number means higher priority. Example: 1 for highest priority. Timeout: 60 sec",
    # Watermark Settings
    "WATERMARK_ENABLED": "Enable or disable watermark feature. Send 'true' to enable or 'false' to disable. Timeout: 60 sec\n\nPriority:\n1. Global (enabled) & User (disabled) -> Apply global\n2. User (enabled) & Global (disabled) -> Apply user\n3. Global (enabled) & User (enabled) -> Apply user\n4. Global (disabled) & User (disabled) -> Don't apply\n\nUse the Reset button to reset all watermark settings to default.",
    "WATERMARK_KEY": "Send your text which will be added as watermark in all mkv videos. Timeout: 60 sec",
    "WATERMARK_POSITION": "Send watermark position. Valid options: top_left, top_right, bottom_left, bottom_right, center, top_center, bottom_center, left_center, right_center. Timeout: 60 sec",
    "WATERMARK_SIZE": "Send watermark font size (integer value). Example: 20. Timeout: 60 sec",
    "WATERMARK_COLOR": "Send watermark text color. Example: white, black, red, green, blue, yellow. Timeout: 60 sec",
    "WATERMARK_FONT": "Send font name for watermark text. You can use a Google Font name (like 'Roboto', 'Open Sans', etc.) or a font file name if available in the bot's directory. Default: default.otf. Timeout: 60 sec",
    "WATERMARK_PRIORITY": "Set priority for watermark processing. Lower number means higher priority. Example: 1 for highest priority. Timeout: 60 sec",
    "WATERMARK_THREADING": "Enable or disable threading for watermark processing. Send 'true' to enable or 'false' to disable. Timeout: 60 sec",
    # Merge Settings
    "MERGE_ENABLED": "Enable or disable merge feature. Send 'true' to enable or 'false' to disable. Timeout: 60 sec\n\nPriority:\n1. Global (enabled) & User (disabled) -> Apply global\n2. User (enabled) & Global (disabled) -> Apply user\n3. Global (enabled) & User (enabled) -> Apply user\n4. Global (disabled) & User (disabled) -> Don't apply\n\nUse the Reset button to reset all merge settings to default.",
    "CONCAT_DEMUXER_ENABLED": "Enable or disable concat demuxer for merging. Send 'true' to enable or 'false' to disable. Timeout: 60 sec",
    "FILTER_COMPLEX_ENABLED": "Enable or disable filter complex for merging. Send 'true' to enable or 'false' to disable. Timeout: 60 sec",
    # Output formats
    "MERGE_OUTPUT_FORMAT_VIDEO": "Set output format for merged videos. Common formats: mkv, mp4, avi, webm.\nExample: mkv - container that supports almost all codecs\nExample: mp4 - widely compatible format. Timeout: 60 sec",
    "MERGE_OUTPUT_FORMAT_AUDIO": "Set output format for merged audios. Common formats: mp3, m4a, flac, wav.\nExample: mp3 - widely compatible format\nExample: flac - lossless audio format. Timeout: 60 sec",
    "MERGE_OUTPUT_FORMAT_IMAGE": "Set output format for merged images. Common formats: jpg, png, webp, tiff.\nExample: jpg - good compression, smaller files\nExample: png - lossless format with transparency support. Timeout: 60 sec",
    "MERGE_OUTPUT_FORMAT_DOCUMENT": "Set output format for merged documents. Currently only pdf is supported.\nExample: pdf - standard document format. Timeout: 60 sec",
    "MERGE_OUTPUT_FORMAT_SUBTITLE": "Set output format for merged subtitles. Common formats: srt, vtt, ass.\nExample: srt - simple subtitle format\nExample: ass - advanced subtitle format with styling. Timeout: 60 sec",
    # Video settings
    "MERGE_VIDEO_CODEC": "Set the video codec for merged videos. Options: copy, h264, h265, vp9, av1.\nExample: copy - preserves original codec (fastest)\nExample: h264 - widely compatible codec. Timeout: 60 sec",
    "MERGE_VIDEO_QUALITY": "Set the quality preset for video encoding. Options: low, medium, high, veryhigh.\nExample: medium - balanced quality and file size\nExample: high - better quality but larger file size. Timeout: 60 sec",
    "MERGE_VIDEO_PRESET": "Set the encoding preset for video. Options: ultrafast to veryslow.\nExample: medium - balanced encoding speed and compression\nExample: slow - better compression but slower encoding. Timeout: 60 sec",
    "MERGE_VIDEO_CRF": "Set the Constant Rate Factor for video quality (0-51, lower is better).\nExample: 23 - default value, good balance\nExample: 18 - visually lossless quality. Timeout: 60 sec",
    "MERGE_VIDEO_PIXEL_FORMAT": "Set the pixel format for video. Common formats: yuv420p, yuv444p.\nExample: yuv420p - most compatible format\nExample: yuv444p - highest quality but larger file size. Timeout: 60 sec",
    "MERGE_VIDEO_TUNE": "Set the tuning parameter for video encoding. Options: film, animation, grain, etc.\nExample: film - for live-action content\nExample: animation - for animated content. Timeout: 60 sec",
    "MERGE_VIDEO_FASTSTART": "Enable or disable faststart flag for MP4 files. Allows videos to start playing before fully downloaded.\nExample: true - enable faststart\nExample: false - disable faststart. Timeout: 60 sec",
    # Audio settings
    "MERGE_AUDIO_CODEC": "Set the audio codec for merged audio. Options: copy, aac, mp3, opus, flac.\nExample: copy - preserves original codec (fastest)\nExample: aac - good quality and compatibility. Timeout: 60 sec",
    "MERGE_AUDIO_BITRATE": "Set the audio bitrate for merged audio. Examples: 128k, 192k, 320k.\nExample: 192k - good quality for most content\nExample: 320k - high quality audio. Timeout: 60 sec",
    "MERGE_AUDIO_CHANNELS": "Set the number of audio channels. Common values: 1 (mono), 2 (stereo).\nExample: 2 - stereo audio\nExample: 1 - mono audio. Timeout: 60 sec",
    "MERGE_AUDIO_SAMPLING": "Set the audio sampling rate in Hz. Common values: 44100, 48000.\nExample: 44100 - CD quality\nExample: 48000 - DVD/professional audio quality. Timeout: 60 sec",
    "MERGE_AUDIO_VOLUME": "Set the volume adjustment factor (0.0-10.0).\nExample: 1.0 - original volume\nExample: 2.0 - double volume. Timeout: 60 sec",
    # Image settings
    "MERGE_IMAGE_MODE": "Set the mode for image merging. Options: auto, horizontal, vertical, collage.\nExample: auto - choose based on number of images\nExample: collage - grid layout. Timeout: 60 sec",
    "MERGE_IMAGE_COLUMNS": "Set the number of columns for image collage mode.\nExample: 2 - two images per row\nExample: 3 - three images per row. Timeout: 60 sec",
    "MERGE_IMAGE_QUALITY": "Set the quality for image output (1-100). Higher values mean better quality but larger file size.\nExample: 90 - high quality\nExample: 75 - good balance of quality and size. Timeout: 60 sec",
    "MERGE_IMAGE_DPI": "Set the DPI (dots per inch) for merged images.\nExample: 300 - good for printing\nExample: 72 - standard screen resolution. Timeout: 60 sec",
    "MERGE_IMAGE_RESIZE": "Set the size to resize images to. Format: widthxheight or 'none'.\nExample: none - keep original size\nExample: 1920x1080 - resize to Full HD. Timeout: 60 sec",
    "MERGE_IMAGE_BACKGROUND": "Set the background color for image merging.\nExample: white - white background\nExample: #FF0000 - red background. Timeout: 60 sec",
    # Subtitle settings
    "MERGE_SUBTITLE_ENCODING": "Set the character encoding for subtitle files.\nExample: utf-8 - universal encoding\nExample: latin1 - for Western European languages. Timeout: 60 sec",
    "MERGE_SUBTITLE_FONT": "Set the font for subtitle rendering.\nExample: Arial - widely available font\nExample: DejaVu Sans - good for multiple languages. Timeout: 60 sec",
    "MERGE_SUBTITLE_FONT_SIZE": "Set the font size for subtitle rendering.\nExample: 24 - medium size\nExample: 32 - larger size for better readability. Timeout: 60 sec",
    "MERGE_SUBTITLE_FONT_COLOR": "Set the font color for subtitle text.\nExample: white - white text\nExample: #FFFF00 - yellow text. Timeout: 60 sec",
    "MERGE_SUBTITLE_BACKGROUND": "Set the background color for subtitle text.\nExample: black - black background\nExample: transparent - no background. Timeout: 60 sec",
    # Document settings
    "MERGE_DOCUMENT_PAPER_SIZE": "Set the paper size for document output.\nExample: a4 - standard international paper size\nExample: letter - standard US paper size. Timeout: 60 sec",
    "MERGE_DOCUMENT_ORIENTATION": "Set the orientation for document output.\nExample: portrait - vertical orientation\nExample: landscape - horizontal orientation. Timeout: 60 sec",
    "MERGE_DOCUMENT_MARGIN": "Set the margin size in points for document output.\nExample: 50 - standard margin\nExample: 0 - no margin. Timeout: 60 sec",
    # Metadata settings
    "MERGE_METADATA_TITLE": "Set the title metadata for the merged file.\nExample: My Video - sets the title to 'My Video'\nExample: empty - no title metadata. Timeout: 60 sec",
    "MERGE_METADATA_AUTHOR": "Set the author metadata for the merged file.\nExample: John Doe - sets the author to 'John Doe'\nExample: empty - no author metadata. Timeout: 60 sec",
    "MERGE_METADATA_COMMENT": "Set the comment metadata for the merged file.\nExample: Created with Telegram Bot - adds a comment\nExample: empty - no comment metadata. Timeout: 60 sec",
    # General settings
    "MERGE_REMOVE_ORIGINAL": "Enable or disable removing original files after successful merge.\nExample: true - remove original files after merge\nExample: false - keep original files. Timeout: 60 sec",
    "MERGE_PRIORITY": "Set priority for merge processing. Lower number means higher priority.\nExample: 1 - highest priority\nExample: 10 - lower priority. Timeout: 60 sec",
    "MERGE_THREADING": "Enable or disable threading for merge processing.\nExample: true - enable parallel processing\nExample: false - disable parallel processing. Timeout: 60 sec",
    "MERGE_THREAD_NUMBER": "Set the number of threads to use for merge processing.\nExample: 4 - process up to 4 files simultaneously\nExample: 1 - process one file at a time. Timeout: 60 sec",
}

help_string = f"""
NOTE: Try each command without any argument to see more detalis.
/{BotCommands.MirrorCommand[0]} or /{BotCommands.MirrorCommand[1]}: Start mirroring to cloud.
/{BotCommands.JdMirrorCommand[0]} or /{BotCommands.JdMirrorCommand[1]}: Start Mirroring to cloud using JDownloader.
/{BotCommands.NzbMirrorCommand[0]} or /{BotCommands.NzbMirrorCommand[1]}: Start Mirroring to cloud using Sabnzbd.
/{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirror yt-dlp supported link.
/{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Start leeching to Telegram. If helper bots are configured, hyper download will be used for faster downloads.
/{BotCommands.JdLeechCommand[0]} or /{BotCommands.JdLeechCommand[1]}: Start leeching using JDownloader.
/{BotCommands.NzbLeechCommand[0]} or /{BotCommands.NzbLeechCommand[1]}: Start leeching using Sabnzbd.
/{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Leech yt-dlp supported link.
/{BotCommands.CloneCommand} [drive_url]: Copy file/folder to Google Drive.
/{BotCommands.MediaInfoCommand[0]} or /{BotCommands.MediaInfoCommand[1]}: Get MediaInfo from telegram file or direct link.
/{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive.
/{BotCommands.DeleteCommand} [drive_url]: Delete file/folder from Google Drive (Only Owner & Sudo).
/{BotCommands.UserSetCommand[0]} or /{BotCommands.UserSetCommand[1]} or /{BotCommands.UserSetCommand[2]} [query]: Users settings.
/{BotCommands.MediaToolsCommand[0]} or /{BotCommands.MediaToolsCommand[1]}: Media tools settings for watermark and other media features.
/{BotCommands.MediaToolsHelpCommand[0]} or /{BotCommands.MediaToolsHelpCommand[1]}: View detailed help for merge and watermark features.
/{BotCommands.GenSessionCommand[0]} or /{BotCommands.GenSessionCommand[1]}: Generate a Pyrogram session string securely.
/{BotCommands.BotSetCommand} [query]: Bot settings.
/{BotCommands.FontStylesCommand[0]} or /{BotCommands.FontStylesCommand[1]}: View available font styles for leech.
/{BotCommands.SelectCommand}: Select files from torrents by gid or reply.
/{BotCommands.ForceStartCommand[0]} or /{BotCommands.ForceStartCommand[1]} [gid]: Force start task by gid or reply.
/{BotCommands.CancelAllCommand} [query]: Cancel all [status] tasks.
/{BotCommands.ListCommand} [query]: Search in Google Drive(s).
/{BotCommands.SearchCommand} [query]: Search for torrents with API.
/{BotCommands.StatusCommand[0]} or /{BotCommands.StatusCommand[1]} or /{BotCommands.StatusCommand[2]} or /{BotCommands.StatusCommand[3]}: Shows a status of all the downloads.
/{BotCommands.StatsCommand}: Show stats of the machine where the bot is hosted in.
/{BotCommands.IMDBCommand}: Search for movies or TV series info on IMDB.
/{BotCommands.CheckDeletionsCommand[0]} or /{BotCommands.CheckDeletionsCommand[1]}: Check and manage scheduled message deletions.
/{BotCommands.LoginCommand}: Login to the bot using password for permanent access.
/{BotCommands.RssCommand}: [Owner Only] Subscribe to RSS feeds. Supports easy subscription to movie websites (movierulz, tamilmv, tamilblasters) with auto domain detection and site name display.
"""

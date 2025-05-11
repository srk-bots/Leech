from bot.core.aeon_client import TgClient
from bot.helper.telegram_helper.bot_commands import BotCommands

# FFmpeg help message with concise and visual format
ffmpeg_help = """<b>FFmpeg Commands</b>: -ff

<blockquote>Need help? Follow this <a href='https://t.me/aimupdate/218'>guide</a></blockquote>

<blockquote>
<b>Basic Usage:</b>
• Start directly with FFmpeg arguments (don't write "ffmpeg")
• Add <code>-del</code> to delete original files after processing
• Use <code>-ff subtitle</code> to execute pre-added command lists
</blockquote>

<blockquote expandable="expandable">
<b>Dynamic Output Naming:</b>

<code>mltb-%d</code> → filename-1.mp4, filename-2.mp4
<code>mltb-%3d</code> → filename-  1.mp4, filename-  2.mp4
<code>mltb-%03d</code> → filename-001.mp4, filename-002.mp4

Perfect for extracting multiple streams with <code>-map</code> commands!
</blockquote>

<blockquote expandable="expandable">
<b>Examples:</b>

<code>-i mltb.video -map 0:v -c:v copy mltb-%d.mp4</code>
↳ Creates video-1.mp4, video-2.mp4 for each video stream

<code>-i mltb.mkv -map 0:a:0 -c:a copy mltb-%03d.mka -map 0:a:1 -c:a copy mltb-%03d.mka</code>
↳ Creates video-001.mka, video-002.mka with different audio tracks

<code>-i mltb.mkv -map 0:v -c:v copy -map 0:a -c:a copy -map 0:s -c:s copy mltb-%d.mkv</code>
↳ Creates video-1.mkv, video-2.mkv, video-3.mkv with different streams
</blockquote>

<blockquote expandable="expandable">
<b>Special Cases:</b>

• <b>🖼️ Image Sequences:</b> With <code>-vf fps=1</code>, format specifier is preserved
  <code>mltb-%03d.jpg</code> → <code>video-%03d.jpg</code>

• <b>📝 Subtitle Extraction:</b> Each subtitle stream goes to a separate file
  <code>-map 0:s -c:s srt mltb-%d_sub.srt</code> → video-1_sub.srt, video-2_sub.srt

• <b>🔄 Multiple Inputs:</b> Use the closest <code>-map</code> statement to determine which input file to use for naming
  <code>-i video1.mp4 -i video2.mp4 -map 0:v mltb-%d_v1.mp4 -map 1:v mltb-%d_v2.mp4</code>
</blockquote>

<blockquote expandable="expandable">
<b>Bulk & Multi-link Processing:</b>

• Each file processed with the same command
• Input automatically replaced with each downloaded file
• Use placeholders like mltb.video, mltb.audio for multiple inputs
• Dynamic output maintains the same order as provided in bulk/multi commands
</blockquote>"""

# Media tools text dictionary
media_tools_text = {
    "WATERMARK_KEY": "Set the watermark text to be applied to media files.\n\nExample: @username\nExample: Telegram Channel",
    "WATERMARK_POSITION": "Set the position of the watermark on the media.\n\nValid options: top_left, top_right, bottom_left, bottom_right, center, top_center, bottom_center, left_center, right_center",
    "WATERMARK_SIZE": "Set the size of the watermark text (font size).\n\nExample: 20 - medium size\nExample: 30 - larger size",
    "WATERMARK_COLOR": "Set the color of the watermark text.\n\nExample: white\nExample: black\nExample: red\nExample: #FF0000 (hex color code)",
    "WATERMARK_FONT": "Set the font file to use for the watermark text.\n\nOptions:\n- Default font: default.otf\n- Local font file: Arial.ttf, Roboto.ttf\n- Google Font name: Montserrat, Open Sans, Roboto\n\nExample: default.otf - use default font\nExample: Arial.ttf - use local font file\nExample: Montserrat - use Google Font\n\nGoogle Fonts will be automatically downloaded when used. To find Google Fonts, visit fonts.google.com and use the exact font name.",
    "WATERMARK_PRIORITY": "Set the priority of the watermark process in the media processing pipeline.\n\nLower numbers run earlier. Default order:\n1. Merge\n2. Watermark\n3. Convert\n4. Trim\n5. Compression\n6. Extract",
    "WATERMARK_THREADING": "Enable or disable threading for watermark processing.\n\nExample: true - process multiple files in parallel\nExample: false - process one file at a time",
    "WATERMARK_THREAD_NUMBER": "Set the number of threads to use for watermark processing.\n\nExample: 2 - use 2 threads\nExample: 4 - use 4 threads",
    "WATERMARK_QUALITY": "Set the quality value for watermark processing.\n\nExample: 23 - good quality (lower is better)\nExample: 18 - high quality\nExample: none - use default quality",
    "WATERMARK_SPEED": "Set the speed value for watermark processing.\n\nExample: ultrafast - fastest processing\nExample: medium - balanced speed and quality\nExample: veryslow - best quality\nExample: none - use default speed",
    "WATERMARK_OPACITY": "Set the opacity of the watermark text (0.0 to 1.0).\n\nExample: 1.0 - fully opaque\nExample: 0.5 - semi-transparent",
    "WATERMARK_REMOVE_ORIGINAL": 'Enable or disable removing original files after watermarking.\n\nExample: true - delete original files after watermarking\nExample: false - keep original files\n\nYou can also use the -del flag in commands to override this setting:\n/leech file.mp4 -watermark "My Channel" -del',
    "AUDIO_WATERMARK_INTERVAL": "Set the interval in seconds for audio watermarks.\n\nExample: 30 - add watermark every 30 seconds\nExample: 60 - add watermark every minute\nExample: 0 - disable interval (default)",
    "AUDIO_WATERMARK_VOLUME": 'Set the volume of the audio watermark relative to the original audio.\n\nRange: 0.0 (silent) to 1.0 (full volume)\nDefault: 0.0 (disabled)\nRecommended: 0.1-0.3 for subtle watermarking\n\nExample: 0.5 - half the volume of the original\nExample: 1.0 - same volume as the original\nExample: 0.2 - subtle watermark\n\nYou can also use the -vol flag in commands:\n/leech file.mp3 -watermark "My Channel" -vol 0.2',
    "SUBTITLE_WATERMARK_INTERVAL": "Set the interval in seconds for subtitle watermarks.\n\nExample: 30 - add watermark every 30 seconds\nExample: 60 - add watermark every minute\nExample: 0 - disable interval (default)",
    "SUBTITLE_WATERMARK_STYLE": 'Set the style of the subtitle watermark.\n\nOptions: none, normal, bold, italic, bold_italic, underline, strikethrough\nDefault: none (uses plain text)\n\nExample: normal - standard subtitle style\nExample: bold - bold text\nExample: italic - italic text\nExample: bold_italic - bold and italic text\nExample: underline - underlined text\nExample: strikethrough - text with strikethrough\n\nYou can also use the -style flag in commands:\n/leech file.srt -watermark "My Channel" -style bold\n\nFor ASS/SSA subtitles, supports more advanced styling and Google Fonts can be used.',
    "IMAGE_WATERMARK_ENABLED": "Enable or disable image watermark feature.\n\nExample: true - enable image watermark\nExample: false - disable image watermark\n\nWhen enabled, you can add image watermarks to videos and images using the -iwm flag or through the configured image path.",
    "IMAGE_WATERMARK_PATH": "Set the path to the watermark image file.\n\nExample: /path/to/watermark.png\n\nThe image should preferably be a PNG with transparency for best results. The path should be accessible to the bot.",
    "IMAGE_WATERMARK_SCALE": "Set the scale of the watermark image as a percentage of the video width.\n\nExample: 10 - watermark will be 10% of the video width\nExample: 20 - watermark will be 20% of the video width\n\nLarger values make the watermark bigger. The aspect ratio is maintained.",
    "IMAGE_WATERMARK_OPACITY": "Set the opacity of the watermark image.\n\nRange: 0.0 (completely transparent) to 1.0 (fully opaque)\nDefault: 1.0 (fully visible)\n\nExample: 0.7 - 70% opacity\nExample: 0.5 - 50% opacity\nExample: 1.0 - 100% opacity (fully visible)",
    "IMAGE_WATERMARK_POSITION": "Set the position of the watermark image on the media.\n\nValid options: top_left, top_right, bottom_left, bottom_right, center, top_center, bottom_center, left_center, right_center\nDefault: bottom_right\n\nExample: bottom_right - place in bottom right corner\nExample: center - place in the center of the video",
    "CONVERT_PRIORITY": "Set the priority of the convert process in the media processing pipeline.\n\nLower numbers run earlier. Default order:\n1. Merge\n2. Watermark\n3. Convert\n4. Trim\n5. Compression\n6. Extract",
    "EXTRACT_PRIORITY": "Set the priority of the extract process in the media processing pipeline.\n\nLower numbers run earlier. Default order:\n1. Merge\n2. Watermark\n3. Convert\n4. Trim\n5. Compression\n6. Extract",
    "EXTRACT_DELETE_ORIGINAL": "Enable or disable deleting original files after extraction.\n\nExample: true - delete original files after extraction\nExample: false - keep original files",
    "EXTRACT_VIDEO_CODEC": "Set the codec to use for video extraction.\n\nExample: copy - preserve original codec\nExample: h264 - convert to H.264\nExample: h265 - convert to H.265\nExample: none - don't set codec",
    "EXTRACT_VIDEO_FORMAT": "Set the output format for video extraction.\n\nExample: mp4 - MP4 container\nExample: mkv - MKV container\nExample: avi - AVI container\nExample: none - use default format",
    "EXTRACT_VIDEO_INDEX": "Set the video track index to extract. Leave empty to extract all video tracks.\n\nExample: 0 - extract first video track\nExample: 1 - extract second video track\nExample: 0,1 - extract first and second video tracks",
    "EXTRACT_VIDEO_QUALITY": "Set the quality (CRF value) for video extraction. Lower values mean better quality but larger file size.\n\nExample: 18 - high quality\nExample: 23 - good quality\nExample: 28 - lower quality\nExample: none - don't set quality",
    "EXTRACT_VIDEO_PRESET": "Set the encoding preset for video extraction. Faster presets result in larger files, slower presets in smaller files.\n\nExample: ultrafast - fastest encoding, largest files\nExample: medium - balanced speed and compression\nExample: veryslow - slowest encoding, smallest files\nExample: none - don't set preset",
    "EXTRACT_VIDEO_BITRATE": "Set the bitrate for video extraction.\n\nExample: 5M - 5 megabits per second\nExample: 500k - 500 kilobits per second\nExample: none - don't set bitrate",
    "EXTRACT_VIDEO_RESOLUTION": "Set the resolution for video extraction.\n\nExample: 1920x1080 - Full HD\nExample: 1280x720 - HD\nExample: none - don't set resolution",
    "EXTRACT_VIDEO_FPS": "Set the frame rate for video extraction.\n\nExample: 30 - 30 frames per second\nExample: 60 - 60 frames per second\nExample: none - don't set FPS",
    "EXTRACT_AUDIO_CODEC": "Set the codec to use for audio extraction.\n\nExample: copy - preserve original codec\nExample: aac - convert to AAC\nExample: mp3 - convert to MP3\nExample: none - don't set codec",
    "EXTRACT_AUDIO_FORMAT": "Set the output format for audio extraction.\n\nExample: mp3 - MP3 format\nExample: aac - AAC format\nExample: flac - FLAC format\nExample: none - use default format",
    "EXTRACT_AUDIO_INDEX": "Set the audio track index to extract. Leave empty to extract all audio tracks.\n\nExample: 0 - extract first audio track\nExample: 1 - extract second audio track\nExample: 0,1 - extract first and second audio tracks",
    "EXTRACT_AUDIO_BITRATE": "Set the bitrate for audio extraction.\n\nExample: 320k - high quality\nExample: 192k - good quality\nExample: 128k - acceptable quality\nExample: none - don't set bitrate",
    "EXTRACT_AUDIO_CHANNELS": "Set the number of audio channels for extraction.\n\nExample: 2 - stereo\nExample: 1 - mono\nExample: none - don't set channels",
    "EXTRACT_AUDIO_SAMPLING": "Set the sampling rate for audio extraction.\n\nExample: 48000 - high quality\nExample: 44100 - CD quality\nExample: none - don't set sampling rate",
    "EXTRACT_AUDIO_VOLUME": "Set the volume adjustment for audio extraction.\n\nExample: 1.0 - original volume\nExample: 2.0 - double volume\nExample: 0.5 - half volume\nExample: none - don't adjust volume",
    "EXTRACT_SUBTITLE_CODEC": "Set the codec to use for subtitle extraction.\n\nExample: copy - preserve original format\nExample: srt - convert to SRT format\nExample: ass - convert to ASS format\nExample: none - don't set codec",
    "EXTRACT_SUBTITLE_FORMAT": "Set the output format for subtitle extraction.\n\nExample: srt - SubRip format\nExample: ass - Advanced SubStation Alpha format\nExample: vtt - WebVTT format\nExample: none - use default format",
    "EXTRACT_SUBTITLE_INDEX": "Set the subtitle track index to extract. Leave empty to extract all subtitle tracks.\n\nExample: 0 - extract first subtitle track\nExample: 1 - extract second subtitle track\nExample: 0,1 - extract first and second subtitle tracks",
    "EXTRACT_SUBTITLE_LANGUAGE": "Set the language code for subtitle extraction.\n\nExample: eng - English\nExample: spa - Spanish\nExample: none - don't set language",
    "EXTRACT_SUBTITLE_ENCODING": "Set the character encoding for subtitle extraction.\n\nExample: utf-8 - UTF-8 encoding\nExample: latin1 - Latin-1 encoding\nExample: none - don't set encoding",
    "EXTRACT_SUBTITLE_FONT": "Set the font for subtitle extraction (for ASS/SSA subtitles).\n\nExample: Arial - use Arial font\nExample: DejaVu Sans - use DejaVu Sans font\nExample: none - don't set font",
    "EXTRACT_SUBTITLE_FONT_SIZE": "Set the font size for subtitle extraction (for ASS/SSA subtitles).\n\nExample: 24 - medium size\nExample: 32 - larger size\nExample: none - don't set font size",
    "EXTRACT_ATTACHMENT_FORMAT": "Set the output format for attachment extraction.\n\nExample: original - preserve original format\nExample: zip - compress attachments into a ZIP file\nExample: none - use default format",
    "EXTRACT_ATTACHMENT_INDEX": "Set the attachment index to extract. Leave empty to extract all attachments.\n\nExample: 0 - extract first attachment\nExample: 1 - extract second attachment\nExample: 0,1 - extract first and second attachments",
    "EXTRACT_ATTACHMENT_FILTER": "Set a filter pattern for attachment extraction.\n\nExample: *.ttf - extract only TTF font files\nExample: *.jpg - extract only JPG images\nExample: none - don't set filter",
    "EXTRACT_MAINTAIN_QUALITY": "Set quality for extraction.\n\nExample: true - high quality\nExample: false - normal quality",
    "ADD_ENABLED": "Enable or disable the add feature globally.\n\nExample: true - enable add feature\nExample: false - disable add feature\n\nWhen enabled, you can add media tracks to files using the -add flag or through the configured settings.",
    "ADD_PRIORITY": "Set the priority of the add process in the media processing pipeline.\n\nLower numbers run earlier. Default order:\n1. Merge\n2. Watermark\n3. Convert\n4. Trim\n5. Compression\n6. Extract\n7. Add (default: 7)\n\nExample: 3 - run add before convert\nExample: 8 - run add after extract",
    "ADD_DELETE_ORIGINAL": "Enable or disable deleting the original file after adding media.\n\nExample: true - delete original file after successful add operation\nExample: false - keep both original and modified files\n\nThis can be overridden by using the -del flag in the command.",
    "ADD_PRESERVE_TRACKS": "Enable or disable preserving existing tracks when adding new ones.\n\nExample: true - preserve existing tracks when adding new ones\nExample: false - allow existing tracks to be pushed to other indices\n\nThis can be overridden by using the -preserve flag in the command.",
    "ADD_REPLACE_TRACKS": "Enable or disable replacing existing tracks when adding new ones.\n\nExample: true - replace existing tracks with new ones\nExample: false - keep existing tracks and add new ones\n\nThis can be overridden by using the -replace flag in the command.",
    "ADD_VIDEO_ENABLED": "Enable or disable adding video tracks to media files.\n\nExample: true - enable video track addition\nExample: false - disable video track addition\n\nWhen enabled, video tracks will be added according to the specified settings.",
    "ADD_VIDEO_PATH": "Set the path to the video file to add as a track.\n\nExample: /path/to/video.mp4\nExample: none - no video file specified\n\nThe path should be accessible to the bot.",
    "ADD_VIDEO_INDEX": "Set the video track index to add. Leave empty to add all video tracks.\n\nExample: 0 - add first video track\nExample: 1 - add second video track\nExample: none - add all video tracks",
    "ADD_VIDEO_CODEC": "Set the codec to use for video track addition.\n\nExample: copy - preserve original codec (fastest, no quality loss)\nExample: libx264 - H.264 codec (good compatibility)\nExample: libx265 - H.265/HEVC codec (better compression)\nExample: none - use default codec",
    "ADD_VIDEO_QUALITY": "Set the quality (CRF value) for video track addition. Lower values mean better quality but larger file size.\n\nExample: 18 - high quality\nExample: 23 - good quality\nExample: 28 - lower quality\nExample: none - don't set quality",
    "ADD_VIDEO_PRESET": "Set the encoding preset for video track addition. Faster presets result in larger files, slower presets in smaller files.\n\nExample: ultrafast - fastest encoding, largest files\nExample: medium - balanced speed and compression\nExample: veryslow - slowest encoding, smallest files\nExample: none - don't set preset",
    "ADD_VIDEO_BITRATE": "Set the bitrate for video track addition.\n\nExample: 5M - 5 megabits per second\nExample: 500k - 500 kilobits per second\nExample: none - don't set bitrate",
    "ADD_VIDEO_RESOLUTION": "Set the resolution for video track addition.\n\nExample: 1920x1080 - Full HD\nExample: 1280x720 - HD\nExample: none - don't set resolution",
    "ADD_VIDEO_FPS": "Set the frame rate for video track addition.\n\nExample: 30 - 30 frames per second\nExample: 60 - 60 frames per second\nExample: none - don't set FPS",
    "ADD_AUDIO_ENABLED": "Enable or disable adding audio tracks to media files.\n\nExample: true - enable audio track addition\nExample: false - disable audio track addition\n\nWhen enabled, audio tracks will be added according to the specified settings.",
    "ADD_AUDIO_PATH": "Set the path to the audio file to add as a track.\n\nExample: /path/to/audio.mp3\nExample: none - no audio file specified\n\nThe path should be accessible to the bot.",
    "ADD_AUDIO_INDEX": "Set the audio track index to add. Leave empty to add all audio tracks.\n\nExample: 0 - add first audio track\nExample: 1 - add second audio track\nExample: none - add all audio tracks",
    "ADD_AUDIO_CODEC": "Set the codec to use for audio track addition.\n\nExample: copy - preserve original codec (fastest, no quality loss)\nExample: aac - AAC codec (good quality, compatibility)\nExample: libmp3lame - MP3 codec (widely compatible)\nExample: flac - FLAC codec (lossless)\nExample: none - use default codec",
    "ADD_AUDIO_BITRATE": "Set the bitrate for audio track addition.\n\nExample: 320k - high quality\nExample: 192k - good quality\nExample: 128k - acceptable quality\nExample: none - don't set bitrate",
    "ADD_AUDIO_CHANNELS": "Set the number of audio channels for track addition.\n\nExample: 2 - stereo\nExample: 1 - mono\nExample: none - don't set channels",
    "ADD_AUDIO_SAMPLING": "Set the sampling rate for audio track addition.\n\nExample: 48000 - high quality\nExample: 44100 - CD quality\nExample: none - don't set sampling rate",
    "ADD_AUDIO_VOLUME": "Set the volume adjustment for audio track addition.\n\nExample: 1.0 - original volume\nExample: 2.0 - double volume\nExample: 0.5 - half volume\nExample: none - don't adjust volume",
    "ADD_SUBTITLE_ENABLED": "Enable or disable adding subtitle tracks to media files.\n\nExample: true - enable subtitle track addition\nExample: false - disable subtitle track addition\n\nWhen enabled, subtitle tracks will be added according to the specified settings.",
    "ADD_SUBTITLE_PATH": "Set the path to the subtitle file to add as a track.\n\nExample: /path/to/subtitle.srt\nExample: none - no subtitle file specified\n\nThe path should be accessible to the bot.",
    "ADD_SUBTITLE_INDEX": "Set the subtitle track index to add. Leave empty to add all subtitle tracks.\n\nExample: 0 - add first subtitle track\nExample: 1 - add second subtitle track\nExample: none - add all subtitle tracks",
    "ADD_SUBTITLE_CODEC": "Set the codec to use for subtitle track addition.\n\nExample: copy - preserve original format\nExample: srt - convert to SRT format\nExample: ass - convert to ASS format\nExample: none - use default codec",
    "ADD_SUBTITLE_LANGUAGE": "Set the language code for subtitle track addition.\n\nExample: eng - English\nExample: spa - Spanish\nExample: none - don't set language",
    "ADD_SUBTITLE_ENCODING": "Set the character encoding for subtitle track addition.\n\nExample: utf-8 - UTF-8 encoding\nExample: latin1 - Latin-1 encoding\nExample: none - don't set encoding",
    "ADD_SUBTITLE_FONT": "Set the font for subtitle track addition (for ASS/SSA subtitles).\n\nExample: Arial - use Arial font\nExample: DejaVu Sans - use DejaVu Sans font\nExample: none - don't set font",
    "ADD_SUBTITLE_FONT_SIZE": "Set the font size for subtitle track addition (for ASS/SSA subtitles).\n\nExample: 24 - medium size\nExample: 32 - larger size\nExample: none - don't set font size",
    "ADD_ATTACHMENT_ENABLED": "Enable or disable adding attachments to media files.\n\nExample: true - enable attachment addition\nExample: false - disable attachment addition\n\nWhen enabled, attachments will be added according to the specified settings.",
    "ADD_ATTACHMENT_PATH": "Set the path to the attachment file to add.\n\nExample: /path/to/font.ttf\nExample: none - no attachment file specified\n\nThe path should be accessible to the bot.",
    "ADD_ATTACHMENT_INDEX": "Set the attachment index to add. Leave empty to add all attachments.\n\nExample: 0 - add first attachment\nExample: 1 - add second attachment\nExample: none - add all attachments",
    "ADD_ATTACHMENT_MIMETYPE": "Set the MIME type for attachment addition.\n\nExample: font/ttf - TrueType font\nExample: image/png - PNG image\nExample: none - don't set MIME type",
    "COMPRESSION_PRIORITY": "Set the priority of the compression process in the media processing pipeline.\n\nLower numbers run earlier. Default order:\n1. Merge\n2. Watermark\n3. Convert\n4. Trim\n5. Compression\n6. Extract\n7. Add",
    "MEDIA_TOOLS_PRIORITY": "Set the order of media processing tools.\n\nFormat: comma-separated list of tool names\nExample: merge,watermark,convert,trim,compression,extract\nExample: watermark,convert,trim,compression,extract,merge",
    # General Trim Settings
    "TRIM_ENABLED": "Enable or disable the trim feature globally.\n\nExample: true - enable trim feature\nExample: false - disable trim feature\n\nWhen enabled, you can trim media files using the -trim flag or through the configured start/end times.\n\nExample command: /leech https://example.com/video.mp4 -trim 00:01:30-00:02:45",
    "TRIM_PRIORITY": "Set the priority of the trim process in the media processing pipeline.\n\nLower numbers run earlier. Default order:\n1. Merge\n2. Watermark\n3. Convert\n4. Trim (default: 5)\n5. Compression\n6. Extract\n\nExample: 3 - run trim before convert\nExample: 7 - run trim after compression",
    "TRIM_START_TIME": "Set the default start time for trimming media files.\n\nFormat: HH:MM:SS or MM:SS or SS\nExample: 00:01:30 (1 minute 30 seconds)\nExample: 5:45 (5 minutes 45 seconds)\nExample: 90 (90 seconds)\n\nThis setting will be used when trim is enabled but no specific start time is provided in the command.\n\nExample command with custom start time: /leech https://example.com/video.mp4 -trim 00:02:15-00:05:30",
    "TRIM_END_TIME": "Set the default end time for trimming media files. Leave empty to trim to the end of the file.\n\nFormat: HH:MM:SS or MM:SS or SS\nExample: 00:02:30 (2 minutes 30 seconds)\nExample: 10:45 (10 minutes 45 seconds)\nExample: 180 (180 seconds)\n\nThis setting will be used when trim is enabled but no specific end time is provided in the command.\n\nExample command with custom end time: /leech https://example.com/video.mp4 -trim 00:00:00-00:03:45",
    "TRIM_DELETE_ORIGINAL": "Enable or disable deleting the original file after trimming.\n\nExample: true - delete original file after successful trimming\nExample: false - keep both original and trimmed files\n\nThis can be overridden by using the -del flag in the command.\n\nExample command with delete original: /leech https://example.com/video.mp4 -trim 00:01:30-00:02:45 -del",
    # Video Trim Settings
    "TRIM_VIDEO_ENABLED": "Enable or disable trimming for video files.\n\nExample: true - enable video trimming\nExample: false - disable video trimming\n\nWhen enabled, video files will be trimmed according to the specified start and end times.\n\nExample command: /leech https://example.com/movie.mp4 -trim 00:10:00-00:15:00",
    "TRIM_VIDEO_CODEC": "Set the codec to use for video trimming.\n\nExample: copy - preserve original codec (fastest, no quality loss)\nExample: libx264 - H.264 codec (good compatibility)\nExample: libx265 - H.265/HEVC codec (better compression)\nExample: none - use default codec\n\nThe 'copy' option is fastest but may not be precise at cut points. Other codecs will re-encode the video.\n\nExample command with video trimming: /mirror https://example.com/video.mkv -trim 00:05:30-00:08:45",
    "TRIM_VIDEO_PRESET": "Set the encoding preset for video trimming.\n\nExample: ultrafast - fastest encoding, largest files\nExample: fast - quick encoding with good compression\nExample: medium - balanced speed and compression\nExample: slow - better compression, slower encoding\nExample: veryslow - best compression, slowest encoding\nExample: none - use default preset\n\nThis setting only applies when re-encoding videos (not using 'copy' codec).\n\nExample of high-quality trim: /leech https://example.com/movie.mp4 -trim 01:15:30-01:25:45",
    "TRIM_VIDEO_FORMAT": "Set the output format for video trimming.\n\nExample: mp4 - MP4 container (best compatibility)\nExample: mkv - MKV container (supports more codecs/tracks)\nExample: webm - WebM container (good for web)\nExample: avi - AVI container (legacy format)\nExample: none - use same format as original\n\nChoosing the right format depends on your needs - MP4 for compatibility, MKV for preserving multiple tracks.\n\nExample command: /mirror https://example.com/movie.mkv -trim 00:45:10-01:15:20",
    # Audio Trim Settings
    "TRIM_AUDIO_ENABLED": "Enable or disable trimming for audio files.\n\nExample: true - enable audio trimming\nExample: false - disable audio trimming\n\nWhen enabled, audio files will be trimmed according to the specified start and end times.\n\nExample command: /leech https://example.com/podcast.mp3 -trim 00:05:30-00:15:45",
    "TRIM_AUDIO_CODEC": "Set the codec to use for audio trimming.\n\nExample: copy - preserve original codec (fastest, no quality loss)\nExample: aac - AAC codec (good quality, compatibility)\nExample: libmp3lame - MP3 codec (widely compatible)\nExample: flac - FLAC codec (lossless)\nExample: none - use default codec\n\nThe 'copy' option is fastest but may not be precise at cut points. Other codecs will re-encode the audio.\n\nExample command: /mirror https://example.com/audiobook.m4a -trim 01:30:00-01:45:30",
    "TRIM_AUDIO_PRESET": "Set the encoding preset for audio trimming.\n\nExample: fast - quick encoding\nExample: medium - balanced speed and quality\nExample: slow - better quality, slower encoding\nExample: none - use default preset\n\nThis setting only applies when re-encoding audio (not using 'copy' codec).\n\nExample command: /leech https://example.com/music.flac -trim 00:01:15-00:04:30",
    "TRIM_AUDIO_FORMAT": "Set the output format for audio trimming.\n\nExample: mp3 - MP3 format (widely compatible)\nExample: m4a - AAC in M4A container (good quality)\nExample: flac - FLAC format (lossless)\nExample: opus - Opus format (excellent quality/size ratio)\nExample: wav - WAV format (uncompressed)\nExample: none - use same format as original\n\nExample command: /mirror https://example.com/podcast.mp3 -trim 00:10:00-00:20:00",
    # Image Trim Settings
    "TRIM_IMAGE_ENABLED": "Enable or disable processing for image files.\n\nExample: true - enable image processing\nExample: false - disable image processing\n\nFor static images, 'trimming' means creating a copy with the specified quality and format settings.\n\nFor animated GIFs, trimming extracts the specified frame range.\n\nExample command for GIF: /leech https://example.com/animation.gif -trim 10-30",
    "TRIM_IMAGE_QUALITY": "Set the quality for image processing during trim operations (0-100).\n\nExample: 90 - high quality (default)\nExample: 75 - good balance of quality and size\nExample: 50 - smaller file size, reduced quality\nExample: 0 or 'none' - use original quality\n\nHigher values mean better quality but larger file size.\n\nExample command: /mirror https://example.com/photo.jpg -trim",
    "TRIM_IMAGE_FORMAT": "Set the output format for image processing.\n\nExample: jpg - JPEG format (good for photos)\nExample: png - PNG format (lossless, good for graphics)\nExample: webp - WebP format (better compression)\nExample: gif - GIF format (for animations)\nExample: none - use same format as original\n\nExample command: /leech https://example.com/image.png -trim",
    # Document Trim Settings
    "TRIM_DOCUMENT_ENABLED": "Enable or disable processing for document files.\n\nExample: true - enable document processing\nExample: false - disable document processing\n\nFor PDF files, trimming extracts the specified page range.\n\nExample command for PDF: /leech https://example.com/document.pdf -trim 5-10",
    "TRIM_DOCUMENT_QUALITY": "Set the quality for document processing during trim operations (0-100).\n\nExample: 90 - high quality (default)\nExample: 75 - good balance of quality and size\nExample: 50 - smaller file size, reduced quality\nExample: 0 or 'none' - use original quality\n\nHigher values mean better quality but larger file size.\n\nExample command: /mirror https://example.com/document.pdf -trim 1-5",
    "TRIM_DOCUMENT_FORMAT": "Set the output format for document processing.\n\nExample: pdf - PDF format\nExample: docx - Word document format\nExample: txt - Text format\nExample: none - use same format as original\n\nExample command: /leech https://example.com/document.pdf -trim 10-20",
    # Subtitle Trim Settings
    "TRIM_SUBTITLE_ENABLED": "Enable or disable trimming for subtitle files.\n\nExample: true - enable subtitle trimming\nExample: false - disable subtitle trimming\n\nWhen enabled, subtitle files will be trimmed to include only entries within the specified time range.\n\nExample command: /leech https://example.com/movie.srt -trim 00:05:00-00:15:00",
    "TRIM_SUBTITLE_ENCODING": "Set the character encoding for subtitle trimming.\n\nExample: utf-8 - UTF-8 encoding (recommended)\nExample: latin1 - Latin-1 encoding\nExample: none - use default encoding\n\nThis setting helps ensure proper character display in the trimmed subtitles.\n\nExample command: /mirror https://example.com/subtitles.srt -trim 00:10:00-00:20:00",
    "TRIM_SUBTITLE_FORMAT": "Set the output format for subtitle trimming.\n\nExample: srt - SubRip format (widely compatible)\nExample: ass - Advanced SubStation Alpha format\nExample: vtt - WebVTT format (for web videos)\nExample: none - use same format as original\n\nExample command: /leech https://example.com/subtitles.ass -trim 00:30:00-00:45:00",
    # Archive Trim Settings
    "TRIM_ARCHIVE_ENABLED": "Enable or disable processing for archive files.\n\nExample: true - enable archive processing\nExample: false - disable archive processing\n\nFor archives, 'trimming' means extracting specific files based on patterns and creating a new archive.\n\nExample command: /leech https://example.com/files.zip -trim",
    "TRIM_ARCHIVE_FORMAT": "Set the output format for archive processing.\n\nExample: zip - ZIP format\nExample: 7z - 7-Zip format (better compression)\nExample: tar - TAR format\nExample: none - use same format as original\n\nExample command: /mirror https://example.com/files.rar -trim",
}

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
Note: Only mb and gb are supported or write in bytes without unit!

<b>Equal Splits</b>: -es

/cmd link -es
This will split the file into equal parts based on the file size, regardless of the split size setting.
You can also enable Equal Splits in user settings > leech menu.
"""

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

/cmd link|path|rcl -up path|rcl -rcf --buffer-size:8M|--drive-starred-only|key|key:value
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
Skip Messages: Add -skip followed by a number to skip messages in a range
Skip Examples:
• https://t.me/channel_name/100-150 -skip 3 (will download messages 100, 103, 106, etc.)
• https://t.me/channel_name/100-150-skip3 (same result, more compact format)
• tg://openmessage?user_id=xxxxxx&message_id=555-560 -skip 2 (will download messages 555, 557, 559)
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

convert_media = """<b>Convert Media</b>: -ca -cv -cs -cd -cr

<blockquote>Dont understand? Then follow this <a href='https://t.me/aimupdate/218'>quide</a></blockquote>

Convert media files to different formats with customizable settings for video, audio, subtitles, documents, and archives.

<b>Basic Usage:</b>
- <code>-ca mp3</code>: Convert all audio files to MP3 format
- <code>-cv mp4</code>: Convert all video files to MP4 format
- <code>-cs srt</code>: Convert all subtitle files to SRT format
- <code>-cd pdf</code>: Convert all document files to PDF format
- <code>-cr zip</code>: Convert all archive files to ZIP format
- <code>-ca mp3 -cv mp4</code>: Convert all audios to MP3 and all videos to MP4

<b>Advanced Usage:</b>
- <code>-ca mp3 + flac ogg</code>: Convert only FLAC and OGG audios to MP3
- <code>-cv mkv - webm flv</code>: Convert all videos to MKV except WebM and FLV
- <code>-ca mp3 -del</code>: Convert all audios to MP3 and delete original files
- <code>-cv mp4 -del</code>: Convert all videos to MP4 and delete original files
- <code>-cs srt -del</code>: Convert all subtitles to SRT and delete original files
- <code>-cd pdf -del</code>: Convert all documents to PDF and delete original files
- <code>-cr zip -del</code>: Convert all archives to ZIP and delete original files

<b>Examples:</b>
/cmd link -ca mp3 -cv mp4
/cmd link -ca mp3 + flac ogg
/cmd link -cv mkv - webm flv
/cmd link -cs srt -cd pdf
/cmd link -cr zip -del

<b>Available Flags:</b>
• <code>-cv format</code>: Convert videos to specified format
• <code>-ca format</code>: Convert audios to specified format
• <code>-cs format</code>: Convert subtitles to specified format
• <code>-cd format</code>: Convert documents to specified format
• <code>-cr format</code>: Convert archives to specified format
• <code>-del</code>: Delete original files after conversion

<b>Important Notes:</b>
• The Convert feature must be enabled in both the bot settings and user settings
• The main Convert toggle and the specific media type toggles must be enabled
• Configure convert settings in Media Tools settings
• Convert priority can be set to control when it runs in the processing pipeline
• Each media type has its own specific settings and delete original option"""

add_media = """<b>Add Media</b>: -add -add-video -add-audio -add-subtitle -add-attachment

<blockquote>Add media tracks to existing files</blockquote>

Add specific tracks (video, audio, subtitle, attachment) to media files.

<b>Basic Usage:</b>
- <code>-add</code>: Add all enabled track types based on settings
- <code>-add-video</code>: Add only video tracks
- <code>-add-audio</code>: Add only audio tracks
- <code>-add-subtitle</code>: Add only subtitle tracks
- <code>-add-attachment</code>: Add only attachment tracks

<b>Track Handling Flags:</b>
- <code>-del</code>: Delete original file after processing
- <code>-preserve</code>: Preserve existing tracks when adding new ones
- <code>-replace</code>: Replace existing tracks with new ones

<b>Advanced Usage (Long Format):</b>
- <code>-add-video-path /path/to/video.mp4</code>: Specify video file to add
- <code>-add-audio-path /path/to/audio.mp3</code>: Specify audio file to add
- <code>-add-subtitle-path /path/to/subtitle.srt</code>: Specify subtitle file to add
- <code>-add-attachment-path /path/to/font.ttf</code>: Specify attachment file to add
- <code>-add-video-index 0,1,2</code>: Add video tracks at indices 0, 1, and 2
- <code>-add-audio-index 0,1</code>: Add audio tracks at indices 0 and 1
- <code>-add -del</code>: Add tracks and delete original file
- <code>-add -preserve</code>: Add tracks and preserve existing tracks
- <code>-add -replace</code>: Add tracks and replace existing tracks

<b>Track Index Selection:</b>
- <code>-add-video-index 0</code>: Add only the first video track from source
- <code>-add-audio-index 1</code>: Add only the second audio track from source
- <code>-add-subtitle-index 2</code>: Add only the third subtitle track from source
- <code>-add-attachment-index 0</code>: Add only the first attachment from source
- <code>-add-video-index 0,1,2</code>: Add multiple video tracks at specified indices
- <code>-add-audio-index 0,1,2</code>: Add multiple audio tracks at specified indices

<b>Advanced Usage (Short Format):</b>
- <code>-avp /path/to/video.mp4</code>: Specify video file to add
- <code>-aap /path/to/audio.mp3</code>: Specify audio file to add
- <code>-asp /path/to/subtitle.srt</code>: Specify subtitle file to add
- <code>-atp /path/to/font.ttf</code>: Specify attachment file to add
- <code>-avi 0</code>: Add only the first video track from source
- <code>-avi 0,1,2</code>: Add video tracks at indices 0, 1, and 2
- <code>-aai 1</code>: Add only the second audio track from source
- <code>-aai 0,1</code>: Add audio tracks at indices 0 and 1
- <code>-asi 2</code>: Add only the third subtitle track from source
- <code>-ati 0</code>: Add only the first attachment from source

<b>Additional Video Settings:</b>
- <code>-add-video-codec h264</code>: Set video codec (h264, h265, vp9, etc.)
- <code>-add-video-quality 18</code>: Set video quality (CRF value, lower is better)
- <code>-add-video-preset medium</code>: Set encoding preset (ultrafast, fast, medium, slow)
- <code>-add-video-bitrate 5M</code>: Set video bitrate
- <code>-add-video-resolution 1920x1080</code>: Set video resolution
- <code>-add-video-fps 30</code>: Set video frame rate

<b>Additional Audio Settings:</b>
- <code>-add-audio-codec aac</code>: Set audio codec (aac, mp3, opus, flac, etc.)
- <code>-add-audio-bitrate 320k</code>: Set audio bitrate
- <code>-add-audio-channels 2</code>: Set number of audio channels
- <code>-add-audio-sampling 48000</code>: Set audio sampling rate
- <code>-add-audio-volume 1.5</code>: Set audio volume (1.0 is normal)

<b>Additional Subtitle Settings:</b>
- <code>-add-subtitle-codec srt</code>: Set subtitle codec (srt, ass, etc.)
- <code>-add-subtitle-language eng</code>: Set subtitle language code
- <code>-add-subtitle-encoding UTF-8</code>: Set subtitle character encoding
- <code>-add-subtitle-font Arial</code>: Set subtitle font (for ASS/SSA)
- <code>-add-subtitle-font-size 24</code>: Set subtitle font size (for ASS/SSA)

<b>Attachment Settings:</b>
- <code>-add-attachment-mimetype font/ttf</code>: Set MIME type for attachment

<b>Examples:</b>
/cmd link -add
/cmd link -add-video -add-audio
/cmd link -avp /path/to/video.mp4 -aap /path/to/audio.mp3
/cmd link -add-subtitle -asp /path/to/subtitle.srt
/cmd link -add -del
/cmd link -add-video -add-video-codec h264 -add-video-quality 18
/cmd link -add-audio -add-audio-codec aac -add-audio-bitrate 320k
/cmd link -add-subtitle -add-subtitle-codec srt
/cmd link -add-video-index 0,1 -m (with multi-link feature)

<b>Multi-Link and Bulk Integration:</b>
- <code>/cmd link1 link2 link3 -add-video -m</code>: Add video from link2 to link1
- <code>/cmd link1 link2 link3 -add-video-index 0,1 -m</code>: Add videos from link2 at index 0 and link3 at index 1 to link1

<b>Important Notes:</b>
• The Add feature must be enabled in both the bot settings and user settings
• The main Add toggle and the specific track type toggles must be enabled
• Configure add settings in Media Tools settings
• Add priority can be set to control when it runs in the processing pipeline
• If no path is specified, the default paths from settings will be used
• You can use either long format (-add-video-path) or short format (-avp) flags
• When add is enabled through settings, original files are automatically deleted after processing
• Use the -del flag to delete original files after adding tracks (or -del f to keep original files)
• Settings with value 'none' will not be used in command generation
• If a specified index is not available, the system will use the first available index
• When using multiple indices with multi-link, tracks are added in the order of input files
"""

extract_media = """<b>Extract Media</b>: -extract -extract-video -extract-audio -extract-subtitle -extract-attachment

<blockquote>Extract specific tracks from media files</blockquote>

Extract specific tracks (video, audio, subtitle, attachment) from media files.

<b>Basic Usage:</b>
- <code>-extract</code>: Extract all enabled track types based on settings
- <code>-extract-video</code>: Extract only video tracks
- <code>-extract-audio</code>: Extract only audio tracks
- <code>-extract-subtitle</code>: Extract only subtitle tracks
- <code>-extract-attachment</code>: Extract only attachment tracks

<b>Advanced Usage (Long Format):</b>
- <code>-extract-video-index 0</code>: Extract only the first video track
- <code>-extract-audio-index 1</code>: Extract only the second audio track
- <code>-extract-subtitle-index 2</code>: Extract only the third subtitle track
- <code>-extract-attachment-index 0</code>: Extract only the first attachment
- <code>-extract -del</code>: Extract tracks and delete original file

<b>Multiple Track Indices:</b>
- <code>-extract-video-index 0,1</code>: Extract first and second video tracks
- <code>-extract-audio-index 0,2,3</code>: Extract first, third, and fourth audio tracks
- <code>-extract-subtitle-index 1,2</code>: Extract second and third subtitle tracks
- <code>-extract-attachment-index 0,1</code>: Extract first and second attachments

<b>Advanced Usage (Short Format):</b>
- <code>-vi 0</code>: Extract only the first video track
- <code>-ai 1</code>: Extract only the second audio track
- <code>-si 2</code>: Extract only the third subtitle track
- <code>-ati 0</code>: Extract only the first attachment
- <code>-vi 0,1 -ai 2,3</code>: Extract multiple tracks with short format

<b>Additional Video Settings:</b>
- <code>-extract-video-codec h264</code>: Set video codec (h264, h265, vp9, etc.)
- <code>-extract-video-quality 18</code>: Set video quality (CRF value, lower is better)
- <code>-extract-video-preset medium</code>: Set encoding preset (ultrafast, fast, medium, slow)
- <code>-extract-video-bitrate 5M</code>: Set video bitrate
- <code>-extract-video-resolution 1920x1080</code>: Set video resolution
- <code>-extract-video-fps 30</code>: Set video frame rate

<b>Additional Audio Settings:</b>
- <code>-extract-audio-codec aac</code>: Set audio codec (aac, mp3, opus, flac, etc.)
- <code>-extract-audio-bitrate 320k</code>: Set audio bitrate
- <code>-extract-audio-channels 2</code>: Set number of audio channels
- <code>-extract-audio-sampling 48000</code>: Set audio sampling rate
- <code>-extract-audio-volume 1.5</code>: Set audio volume (1.0 is normal)

<b>Additional Subtitle Settings:</b>
- <code>-extract-subtitle-codec srt</code>: Set subtitle codec (srt, ass, etc.)
- <code>-extract-subtitle-language eng</code>: Set subtitle language code
- <code>-extract-subtitle-encoding UTF-8</code>: Set subtitle character encoding
- <code>-extract-subtitle-font Arial</code>: Set subtitle font (for ASS/SSA)
- <code>-extract-subtitle-font-size 24</code>: Set subtitle font size (for ASS/SSA)

<b>Attachment Settings:</b>
- <code>-extract-attachment-filter *.ttf</code>: Filter attachments by pattern

<b>Examples:</b>
/cmd link -extract
/cmd link -extract-video -extract-audio
/cmd link -vi 0 -ai 1
/cmd link -extract-subtitle
/cmd link -extract -del
/cmd link -extract-video -extract-video-codec h264 -extract-video-quality 18
/cmd link -extract-audio -extract-audio-codec aac -extract-audio-bitrate 320k
/cmd link -extract-subtitle -extract-subtitle-codec srt

<b>Important Notes:</b>
• The Extract feature must be enabled in both the bot settings and user settings
• The main Extract toggle and the specific track type toggles must be enabled
• Configure extract settings in Media Tools settings
• Extract priority can be set to control when it runs in the processing pipeline
• Track indices start from 0 (first track is index 0)
• If no index is specified, all tracks of that type will be extracted
• You can use either long format (-extract-video-index) or short format (-vi) flags
• When extract is enabled through settings, original files are automatically deleted after extraction
• Only the specified track indices will be extracted when indices are provided
• Use the -del flag to delete original files after extraction (or -del f to keep original files)
• Settings with value 'none' will not be used in command generation
• For ASS/SSA subtitles, use 'copy' codec to preserve the original format or 'srt' to convert to SRT"""

force_start = """<b>Force Start</b>: -f -fd -fu
/cmd link -f (force download and upload)
/cmd link -fd (force download only)
/cmd link -fu (force upload directly after download finish)"""

media_tools_flag = """<b>Media Tools Flag</b>: -mt

/cmd link -mt (opens media tools settings before starting the task)

When you use the -mt flag with any command:
1. The bot will show the media tools settings menu
2. You can customize settings as needed
3. Click "Done" to start the task with your settings
4. Click "Cancel" to abort the task
5. If no action is taken within 60 seconds, the task will be cancelled

All command and cancellation messages are auto-deleted after 5 minutes.

Examples:
/mirror https://example.com/video.mp4 -mt
/leech https://example.com/files.zip -z -mt
/ytdl https://youtube.com/watch?v=example -mt
/mirror https://example.com/videos.zip -merge-video -mt"""

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

Set a global filename template for all your leech files. The template supports dynamic variables that are automatically extracted from filenames.

<b>Basic Variables:</b>
• <code>{filename}</code> - Original filename without extension
• <code>{ext}</code> - File extension (e.g., mkv, mp4)
• <code>{size}</code> - File size (e.g., 1.5GB)
• <code>{quality}</code> - Video quality (e.g., 1080p, 720p)

<b>TV Show Variables:</b>
• <code>{season}</code> - Season number extracted from filename
• <code>{episode}</code> - Episode number extracted from filename
• <code>{year}</code> - Release year extracted from filename

<b>Media Information:</b>
• <code>{codec}</code> - Video codec (e.g., HEVC, AVC)
• <code>{framerate}</code> - Video framerate
• <code>{format}</code> - Media container format
• <code>{formate}</code> - File extension in uppercase

<b>Examples:</b>
• <code>{filename} [{quality}]</code>
• <code>{filename} S{season}E{episode} [{quality}]</code>
• <code>{filename} ({year}) [{codec}]</code>
• <code>Series S{season}E{episode} [{quality}] [{codec}]</code>

You can set this in your user settings by going to /usettings > Leech Settings > Leech Filename.

Use /fontstyles to see all available template variables.

Note: This affects the actual filename of the files, while Leech Caption controls how they appear in Telegram messages."""

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

<blockquote expandable="expandable"><b>Unlimited Nesting Support:</b>
You can nest styles to any depth with any combination of styles!

1. <b>Basic Nesting (Two Styles):</b>
   • <code>{{{variable}style1}style2}</code>
   • Example: <code>{{{filename}bold}italic}</code> - Bold then italic

2. <b>Triple Nesting (Three Styles):</b>
   • <code>{{{{variable}style1}style2}style3}</code>
   • Example: <code>{{{{filename}bold}italic}🔥}</code> - Bold, italic, then fire emoji

3. <b>Advanced Nesting (Four or More Styles):</b>
   • <code>{{{{{variable}style1}style2}style3}style4}</code>
   • Example: <code>{{{{{filename}bold}italic}code}underline}</code> - Four nested styles

4. <b>Master Nesting (Any Number of Styles):</b>
   • You can continue nesting to any depth
   • Example: <code>{{{{{{{{filename}bold}italic}code}underline}strike}🔥}Roboto}</code>
   • Styles are applied from innermost to outermost: bold → italic → code → underline → strike → 🔥 → Roboto</blockquote>

<blockquote expandable="expandable"><b>How to Find Google Fonts:</b>
1. Visit <a href='https://fonts.google.com/'>fonts.google.com</a>
2. Find a font you like
3. Use the exact font name in your leech font setting or caption template</blockquote>

<b>Important Notes:</b>
• Unicode font styles only work with basic Latin characters (A-Z, a-z)
• Google Fonts support depends on the rendering capabilities of the device
• HTML formatting is the most compatible across all devices
• Font styles are applied after template variables are processed
• User settings take priority over owner settings
• Unlimited nesting of styles is supported - combine any number of styles in any order
• For complex nested styles, apply them in order from innermost to outermost"""

ffmpeg_cmds = ffmpeg_help


ai_help = """<b>AI Chatbot</b>:

Chat with AI models using the bot commands.

<b>Available AI Models:</b>
Use the /ask command with any of the following AI providers:
- <b>Mistral AI</b>
- <b>DeepSeek AI</b>

<b>Usage:</b>
/ask your question here

<b>Configuration:</b>
1. <b>Bot Owner</b>: Configure API Keys or API URLs and default AI provider in bot settings
2. <b>Users</b>: Configure your own API Keys or API URLs and default AI provider in user settings

<b>Features:</b>
- Uses powerful language models
- Supports both direct API access and custom API endpoints
- User settings take priority over bot owner settings
- Messages auto-delete after 5 minutes
- Automatically selects the configured AI provider

<b>Examples:</b>
/ask What is the capital of France?
/ask Write a short poem about nature
/ask Explain how quantum computing works
/ask Translate this text to Spanish: Hello world
"""

user_cookies_help = """<b>User Cookies</b>:

You can provide your own cookies for YouTube and other yt-dlp downloads to access restricted content.

1. Go to /usettings > Leech Settings > User Cookies
2. Upload your cookies.txt file (create it using browser extensions)
3. Your cookies will be used for all your yt-dlp downloads

When you upload your cookies, they will be used instead of the owner's cookies. This helps with errors like login requirements or subscriber-only content.

To remove your cookies and use the owner's cookies again, click the Remove button."""

YT_HELP_DICT = {
    "main": yt,
    "New-Name": f"{new_name}\nNote: Don't add file extension",
    "Zip": zip_arg,
    "Quality": qual,
    "Options": yt_opt,
    "User-Cookies": user_cookies_help,
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
    "Media-Tools-Flag": media_tools_flag,
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
    "Media-Tools-Flag": media_tools_flag,
    "AI-Chatbot": ai_help,
}

CLONE_HELP_DICT = {
    "main": clone,
    "Multi-Link": multi_link,
    "Bulk": bulk,
    "Gdrive": gdrive,
    "Rclone": rclone_cl,
}

AI_HELP_DICT = {
    "main": ai_help,
}

RSS_HELP_MESSAGE = """
Use this format to add feed url:
Title1 link (required)
Title2 link -c cmd -inf xx -exf xx
Title3 link -c cmd -d ratio:time -z password

-c command -up mrcc:remote:path/subdir -rcf --buffer-size:8M|key|key:value
-inf For included words filter.
-exf For excluded words filter.
-stv true or false (sensitive filter)

<b>RSS Examples:</b>
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
    "DEFAULT_AI_PROVIDER": "Select the default AI provider to use with the /ask command. Options: mistral, deepseek. Timeout: 60 sec",
    "MISTRAL_API_KEY": "Send your Mistral AI API key. This will be used to access the Mistral AI API directly. Leave empty to use the bot owner's API key. Timeout: 60 sec",
    "MISTRAL_API_URL": "Send your custom Mistral AI API URL. This will be used as a fallback if the API key is not provided or fails. Leave empty to use the bot owner's API URL. Timeout: 60 sec",
    "DEEPSEEK_API_KEY": "Send your DeepSeek AI API key. This will be used to access the DeepSeek AI API directly. Leave empty to use the bot owner's API key. Timeout: 60 sec",
    "DEEPSEEK_API_URL": "Send your custom DeepSeek AI API URL. This will be used as a fallback if the API key is not provided or fails. Leave empty to use the bot owner's API URL. Timeout: 60 sec",
    "METADATA_KEY": "Send your text for change mkv medias metadata (title only). This is a legacy option, consider using the specific metadata options instead. Timeout: 60 sec",
    "METADATA_ALL": "Send metadata text to be used for all metadata fields (title, author, comment) for all track types. This takes priority over all other metadata settings. Timeout: 60 sec",
    "METADATA_TITLE": "Send metadata text to be used for the global title field. Timeout: 60 sec",
    "METADATA_AUTHOR": "Send metadata text to be used for the global author field. Timeout: 60 sec",
    "METADATA_COMMENT": "Send metadata text to be used for the global comment field. Timeout: 60 sec",
    "METADATA_VIDEO_TITLE": "Send metadata text to be used specifically for video track titles. Timeout: 60 sec",
    "METADATA_VIDEO_AUTHOR": "Send metadata text to be used specifically for video track authors. Timeout: 60 sec",
    "METADATA_VIDEO_COMMENT": "Send metadata text to be used specifically for video track comments. Timeout: 60 sec",
    "METADATA_AUDIO_TITLE": "Send metadata text to be used specifically for audio track titles. Timeout: 60 sec",
    "METADATA_AUDIO_AUTHOR": "Send metadata text to be used specifically for audio track authors. Timeout: 60 sec",
    "METADATA_AUDIO_COMMENT": "Send metadata text to be used specifically for audio track comments. Timeout: 60 sec",
    "METADATA_SUBTITLE_TITLE": "Send metadata text to be used specifically for subtitle track titles. Timeout: 60 sec",
    "METADATA_SUBTITLE_AUTHOR": "Send metadata text to be used specifically for subtitle track authors. Timeout: 60 sec",
    "METADATA_SUBTITLE_COMMENT": "Send metadata text to be used specifically for subtitle track comments. Timeout: 60 sec",
    "USER_SESSION": "Send your pyrogram user session string for download from private telegram chat. Timeout: 60 sec",
    "USER_DUMP": "Send your channel or group id where you want to store your leeched files. Bot must have permission to send message in your chat. Timeout: 60 sec",
    "USER_COOKIES": "Send your cookies.txt file for YouTube and other yt-dlp downloads. This will be used instead of the owner's cookies file. Create it using browser extensions like 'Get cookies.txt' or 'EditThisCookie'. Timeout: 60 sec",
    "LEECH_FILENAME_CAPTION": """Send caption template for all your leech files.

<b>Basic Variables:</b>
• <code>{filename}</code> - Filename without extension
• <code>{ext}</code> - File extension
• <code>{size}</code> - File size
• <code>{quality}</code> - Video quality
• <code>{duration}</code> - Media duration
• <code>{season}</code>, <code>{episode}</code> - TV show info

<b>Styling:</b>
• HTML: <code>{{filename}bold}</code>
• Google Fonts: <code>{{filename}Roboto}</code>
• Unicode: <code>{{filename}serif_b}</code>
• Emoji: <code>{{filename}🔥}</code>

<b>Examples:</b>
• <code>📁 {{filename}bold} | 💾 {size}</code>
• <code>🎬 {{filename}Roboto:700} [{quality}]</code>

Use /fontstyles for more options.

Timeout: 60 sec""",
    "LEECH_SPLIT_SIZE": f"Send Leech split size in bytes or use gb or mb. Example: 40000000 or 2.5gb or 1000mb. IS_PREMIUM_USER: {TgClient.IS_PREMIUM_USER}. Timeout: 60 sec",
    "LEECH_DUMP_CHAT": """"Send leech destination ID/USERNAME/PM. You can specify multiple destinations separated by commas.
* b:id/@username/pm (b: means leech by bot) (id or username of the chat or write pm means private message so bot will send the files in private to you) when you should use b:(leech by bot)? When your default settings is leech by user and you want to leech by bot for specific task.
* u:id/@username(u: means leech by user) This incase OWNER added USER_SESSION_STRING.
* h:id/@username(hybrid leech) h: to upload files by bot and user based on file size.
* For multiple destinations, use comma-separated values: -100123456789,-100987654321
* id/@username|topic_id(leech in specific chat and topic) add | without space and write topic id after chat id or username. Timeout: 60 sec""",
    "LOG_CHAT_ID": "Send log chat ID for mirror tasks. You can specify multiple chat IDs separated by commas (e.g., -100123456789,-100987654321). Timeout: 60 sec",
    "LEECH_FILENAME_PREFIX": r"Send Leech Filename Prefix. You can add HTML tags. Example: <code>@mychannel</code>. Timeout: 60 sec",
    "LEECH_SUFFIX": r"Send Leech Filename Suffix. You can add HTML tags. Example: <code>@mychannel</code>. Timeout: 60 sec",
    "LEECH_FONT": "Send Leech Font Style. Options: HTML formats (bold, italic), Unicode styles (serif, sans_b), Google Fonts (Roboto, Open Sans), or emojis (🔥). Use /fontstyles for full list. Timeout: 60 sec",
    "LEECH_FILENAME": """Send Leech Filename template. This will change the actual filename of all your leech files.

<b>Basic Variables:</b>
• <code>{filename}</code> - Original filename without extension
• <code>{ext}</code> - File extension (e.g., mkv, mp4)
• <code>{size}</code> - File size (e.g., 1.5GB)
• <code>{quality}</code> - Video quality (e.g., 1080p, 720p)

<b>TV Show Variables:</b>
• <code>{season}</code> - Season number extracted from filename
• <code>{episode}</code> - Episode number extracted from filename
• <code>{year}</code> - Release year extracted from filename

<b>Media Information:</b>
• <code>{codec}</code> - Video codec (e.g., HEVC, AVC)
• <code>{framerate}</code> - Video framerate
• <code>{format}</code> - Media container format
• <code>{formate}</code> - File extension in uppercase

<b>Examples:</b>
• <code>{filename} [{quality}]</code>
• <code>{filename} S{season}E{episode} [{quality}]</code>
• <code>{filename} ({year}) [{codec}]</code>
• <code>Series S{season}E{episode} [{quality}] [{codec}]</code>

Use /fontstyles to see all available template variables.

Timeout: 60 sec""",
    "THUMBNAIL_LAYOUT": "Send thumbnail layout (widthxheight, 2x2, 3x3, 2x4, 4x4, ...). Example: 3x3. Timeout: 60 sec",
    "RCLONE_PATH": "Send Rclone Path. If you want to use your rclone config edit using owner/user config from usetting or add mrcc: before rclone path. Example mrcc:remote:folder. Timeout: 60 sec",
    "RCLONE_FLAGS": "key:value|key|key|key:value . Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>\nEx: --buffer-size:8M|--drive-starred-only",
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
    # WATERMARK_MAINTAIN_QUALITY has been removed, use WATERMARK_QUALITY instead
    "WATERMARK_OPACITY": "Set the opacity level for watermark text (0.0-1.0). Lower values make the watermark more transparent. Example: 0.5 for 50% opacity. Timeout: 60 sec",
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
    # Convert Settings
    "CONVERT_ENABLED": "Enable or disable convert feature. Send 'true' to enable or 'false' to disable. Timeout: 60 sec\n\nPriority:\n1. Global (enabled) & User (disabled) -> Apply global\n2. User (enabled) & Global (disabled) -> Apply user\n3. Global (enabled) & User (enabled) -> Apply user\n4. Global (disabled) & User (disabled) -> Don't apply\n\nUse the Reset button to reset all convert settings to default.",
    "CONVERT_PRIORITY": "Set priority for convert processing. Lower number means higher priority.\nExample: 1 - highest priority\nExample: 10 - lower priority. Timeout: 60 sec",
    # Video Convert Settings
    "CONVERT_VIDEO_FORMAT": "Set the output format for converted videos. Common formats: mp4, mkv, avi, webm.\nExample: mp4 - widely compatible format\nExample: mkv - container that supports almost all codecs. Timeout: 60 sec",
    "CONVERT_VIDEO_CODEC": "Set the video codec for converted videos. Common codecs: libx264, libx265, libvpx-vp9.\nExample: libx264 - widely compatible codec\nExample: libx265 - better compression but less compatible. Timeout: 60 sec",
    "CONVERT_VIDEO_QUALITY": "Set the quality preset for video encoding. Options: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow.\nExample: medium - balanced encoding speed and compression\nExample: slow - better compression but slower encoding. Timeout: 60 sec",
    "CONVERT_VIDEO_CRF": "Set the Constant Rate Factor for video quality (0-51, lower is better).\nExample: 23 - default value, good balance\nExample: 18 - visually lossless quality. Timeout: 60 sec",
    "CONVERT_VIDEO_PRESET": "Set the encoding preset for video. Options: ultrafast to veryslow.\nExample: medium - balanced encoding speed and compression\nExample: slow - better compression but slower encoding. Timeout: 60 sec",
    "CONVERT_VIDEO_MAINTAIN_QUALITY": "Enable or disable maintaining high quality for video conversion.\nExample: true - use higher quality settings\nExample: false - use standard quality settings. Timeout: 60 sec",
    # Audio Convert Settings
    "CONVERT_AUDIO_FORMAT": "Set the output format for converted audio. Common formats: mp3, m4a, flac, wav, ogg.\nExample: mp3 - widely compatible format\nExample: flac - lossless audio format. Timeout: 60 sec",
    "CONVERT_AUDIO_CODEC": "Set the audio codec for converted audio. Common codecs: libmp3lame, aac, libopus, flac.\nExample: libmp3lame - for MP3 encoding\nExample: aac - good quality and compatibility. Timeout: 60 sec",
    "CONVERT_AUDIO_BITRATE": "Set the audio bitrate for converted audio. Examples: 128k, 192k, 320k.\nExample: 192k - good quality for most content\nExample: 320k - high quality audio. Timeout: 60 sec",
    "CONVERT_AUDIO_CHANNELS": "Set the number of audio channels. Common values: 1 (mono), 2 (stereo).\nExample: 2 - stereo audio\nExample: 1 - mono audio. Timeout: 60 sec",
    "CONVERT_AUDIO_SAMPLING": "Set the audio sampling rate in Hz. Common values: 44100, 48000.\nExample: 44100 - CD quality\nExample: 48000 - DVD/professional audio quality. Timeout: 60 sec",
    "CONVERT_AUDIO_VOLUME": "Set the volume adjustment factor (0.0-10.0).\nExample: 1.0 - original volume\nExample: 2.0 - double volume. Timeout: 60 sec",
    # Compression Settings
    "COMPRESSION_ENABLED": "Enable or disable compression feature. Send 'true' to enable or 'false' to disable. Timeout: 60 sec\n\nPriority:\n1. Global (enabled) & User (disabled) -> Apply global\n2. User (enabled) & Global (disabled) -> Apply user\n3. Global (enabled) & User (enabled) -> Apply user\n4. Global (disabled) & User (disabled) -> Don't apply\n\nUse the Reset button to reset all compression settings to default.",
    "COMPRESSION_PRIORITY": "Set priority for compression processing. Lower number means higher priority.\nExample: 1 - highest priority\nExample: 10 - lower priority. Timeout: 60 sec",
    "COMPRESSION_DELETE_ORIGINAL": "Enable or disable deleting original files after compression. Send 'true' to enable or 'false' to disable.\nExample: true - delete original files after compression\nExample: false - keep original files after compression. Timeout: 60 sec",
    # Video Compression Settings
    "COMPRESSION_VIDEO_ENABLED": "Enable or disable video compression. Send 'true' to enable or 'false' to disable. Timeout: 60 sec",
    "COMPRESSION_VIDEO_PRESET": "Set the compression preset for videos. Options: fast, medium, slow.\nExample: fast - faster compression but lower quality\nExample: slow - better quality but slower compression. Timeout: 60 sec",
    "COMPRESSION_VIDEO_CRF": "Set the Constant Rate Factor for video quality (0-51, lower is better).\nExample: 23 - default value, good balance\nExample: 28 - more compression, lower quality. Timeout: 60 sec",
    "COMPRESSION_VIDEO_CODEC": "Set the video codec for compression. Common codecs: libx264, libx265.\nExample: libx264 - widely compatible codec\nExample: libx265 - better compression but less compatible. Timeout: 60 sec",
    "COMPRESSION_VIDEO_TUNE": "Set the tuning parameter for video compression. Options: film, animation, grain, etc.\nExample: film - for live-action content\nExample: animation - for animated content. Timeout: 60 sec",
    "COMPRESSION_VIDEO_PIXEL_FORMAT": "Set the pixel format for video compression. Common formats: yuv420p, yuv444p.\nExample: yuv420p - most compatible format\nExample: yuv444p - highest quality but larger file size. Timeout: 60 sec",
    "COMPRESSION_VIDEO_BITDEPTH": "Set the bit depth for video compression. Common values: 8, 10, 12.\nExample: 8 - standard 8-bit video (most compatible)\nExample: 10 - 10-bit video (better color gradients)\nExample: none - use default bit depth. Timeout: 60 sec",
    "COMPRESSION_VIDEO_BITRATE": "Set the bitrate for video compression. Examples: 1M, 5M, 10M.\nExample: 5M - 5 Mbps (good for 1080p)\nExample: 2M - 2 Mbps (good for 720p)\nExample: none - use automatic bitrate based on CRF. Timeout: 60 sec",
    "COMPRESSION_VIDEO_RESOLUTION": "Set the resolution for video compression. Format: widthxheight or 'none'.\nExample: 1920x1080 - Full HD\nExample: 1280x720 - HD\nExample: none - keep original resolution. Timeout: 60 sec",
    "COMPRESSION_VIDEO_FORMAT": "Set the output format for compressed videos. Common formats: mp4, mkv, avi, webm.\nExample: mp4 - widely compatible format\nExample: mkv - container that supports almost all codecs\nExample: none - keep original format. Timeout: 60 sec",
    # Audio Compression Settings
    "COMPRESSION_AUDIO_ENABLED": "Enable or disable audio compression. Send 'true' to enable or 'false' to disable. Timeout: 60 sec",
    "COMPRESSION_AUDIO_PRESET": "Set the compression preset for audio. Options: fast, medium, slow.\nExample: fast - faster compression but lower quality\nExample: slow - better quality but slower compression. Timeout: 60 sec",
    "COMPRESSION_AUDIO_CODEC": "Set the audio codec for compression. Common codecs: aac, mp3, opus.\nExample: aac - good quality and compatibility\nExample: opus - better compression. Timeout: 60 sec",
    "COMPRESSION_AUDIO_BITRATE": "Set the audio bitrate for compression. Examples: 64k, 128k, 192k.\nExample: 128k - good balance of quality and size\nExample: 64k - smaller files but lower quality. Timeout: 60 sec",
    "COMPRESSION_AUDIO_CHANNELS": "Set the number of audio channels for compression. Common values: 1 (mono), 2 (stereo).\nExample: 2 - stereo audio\nExample: 1 - mono audio (smaller files). Timeout: 60 sec",
    "COMPRESSION_AUDIO_BITDEPTH": "Set the bit depth for audio compression. Common values: 16, 24, 32.\nExample: 16 - standard CD quality (most compatible)\nExample: 24 - high-resolution audio\nExample: none - use default bit depth. Timeout: 60 sec",
    "COMPRESSION_AUDIO_FORMAT": "Set the output format for compressed audio. Common formats: mp3, m4a, ogg, flac.\nExample: mp3 - widely compatible format\nExample: aac - good quality and compatibility\nExample: none - keep original format. Timeout: 60 sec",
    # Image Compression Settings
    "COMPRESSION_IMAGE_ENABLED": "Enable or disable image compression. Send 'true' to enable or 'false' to disable. Timeout: 60 sec",
    "COMPRESSION_IMAGE_PRESET": "Set the compression preset for images. Options: fast, medium, slow.\nExample: fast - faster compression but lower quality\nExample: slow - better quality but slower compression. Timeout: 60 sec",
    "COMPRESSION_IMAGE_QUALITY": "Set the quality for image compression (1-100). Higher values mean better quality but larger file size.\nExample: 80 - good balance of quality and size\nExample: 50 - more compression, lower quality. Timeout: 60 sec",
    "COMPRESSION_IMAGE_RESIZE": "Set the size to resize images to during compression. Format: widthxheight or 'none'.\nExample: none - keep original size\nExample: 1280x720 - resize to HD. Timeout: 60 sec",
    "COMPRESSION_IMAGE_FORMAT": "Set the output format for compressed images. Common formats: jpg, png, webp.\nExample: jpg - good compression, smaller files\nExample: png - lossless format with transparency support\nExample: none - keep original format. Timeout: 60 sec",
    # Document Compression Settings
    "COMPRESSION_DOCUMENT_ENABLED": "Enable or disable document compression. Send 'true' to enable or 'false' to disable. Timeout: 60 sec",
    "COMPRESSION_DOCUMENT_PRESET": "Set the compression preset for documents. Options: fast, medium, slow.\nExample: fast - faster compression but lower quality\nExample: slow - better quality but slower compression. Timeout: 60 sec",
    "COMPRESSION_DOCUMENT_DPI": "Set the DPI (dots per inch) for document compression.\nExample: 150 - good balance of quality and size\nExample: 72 - more compression, lower quality. Timeout: 60 sec",
    "COMPRESSION_DOCUMENT_FORMAT": "Set the output format for compressed documents. Common formats: pdf, docx, txt.\nExample: pdf - standard document format\nExample: docx - Microsoft Word format\nExample: none - keep original format. Timeout: 60 sec",
    # Subtitle Compression Settings
    "COMPRESSION_SUBTITLE_ENABLED": "Enable or disable subtitle compression. Send 'true' to enable or 'false' to disable. Timeout: 60 sec",
    "COMPRESSION_SUBTITLE_PRESET": "Set the compression preset for subtitles. Options: fast, medium, slow.\nExample: fast - faster compression but lower quality\nExample: slow - better quality but slower compression. Timeout: 60 sec",
    "COMPRESSION_SUBTITLE_ENCODING": "Set the character encoding for subtitle compression.\nExample: utf-8 - universal encoding\nExample: ascii - more compression but limited character support. Timeout: 60 sec",
    "COMPRESSION_SUBTITLE_FORMAT": "Set the output format for compressed subtitles. Common formats: srt, ass, vtt.\nExample: srt - simple subtitle format\nExample: ass - advanced subtitle format with styling\nExample: none - keep original format. Timeout: 60 sec",
    # Archive Compression Settings
    "COMPRESSION_ARCHIVE_ENABLED": "Enable or disable archive compression. Send 'true' to enable or 'false' to disable. Timeout: 60 sec",
    "COMPRESSION_ARCHIVE_PRESET": "Set the compression preset for archives. Options: fast, medium, slow.\nExample: fast - faster compression but lower compression ratio\nExample: slow - better compression ratio but slower. Timeout: 60 sec",
    "COMPRESSION_ARCHIVE_LEVEL": "Set the compression level for archives (1-9). Higher values mean better compression but slower processing.\nExample: 5 - good balance of speed and compression\nExample: 9 - maximum compression. Timeout: 60 sec",
    "COMPRESSION_ARCHIVE_METHOD": "Set the compression method for archives. Options: deflate, store, bzip2, lzma.\nExample: deflate - good balance of speed and compression\nExample: lzma - best compression but slowest. Timeout: 60 sec",
    "COMPRESSION_ARCHIVE_FORMAT": "Set the output format for compressed archives. Common formats: zip, 7z, tar.gz.\nExample: zip - widely compatible format\nExample: 7z - better compression but less compatible\nExample: none - keep original format. Timeout: 60 sec",
    # Trim Settings
    "TRIM_ENABLED": "Enable or disable trim feature. Send 'true' to enable or 'false' to disable. Timeout: 60 sec\n\nPriority:\n1. Global (enabled) & User (disabled) -> Apply global\n2. User (enabled) & Global (disabled) -> Apply user\n3. Global (enabled) & User (enabled) -> Apply user\n4. Global (disabled) & User (disabled) -> Don't apply\n\nUse the Reset button to reset all trim settings to default.",
    "TRIM_PRIORITY": "Set priority for trim processing. Lower number means higher priority.\nExample: 1 - highest priority\nExample: 10 - lower priority. Timeout: 60 sec",
    "TRIM_START_TIME": "Set the start time for trimming media files. Format: HH:MM:SS, MM:SS, or SS.\nExample: 00:01:30 (1 minute 30 seconds)\nExample: 5:45 (5 minutes 45 seconds)\nExample: 90 (90 seconds)\nLeave empty or set to 00:00:00 to start from the beginning. Timeout: 60 sec",
    "TRIM_END_TIME": "Set the end time for trimming media files. Format: HH:MM:SS, MM:SS, or SS.\nExample: 00:02:30 (2 minutes 30 seconds)\nExample: 10:45 (10 minutes 45 seconds)\nExample: 180 (180 seconds)\nLeave empty to trim until the end of the file. Timeout: 60 sec",
    "TRIM_DELETE_ORIGINAL": "Enable or disable deleting the original file after trimming. Send 'true' to enable or 'false' to disable. When enabled, the original file will be deleted after successful trimming. When disabled, both the original and trimmed files will be kept. Timeout: 60 sec",
    "TRIM_VIDEO_FORMAT": "Set the output format for video trimming. This determines the container format of the trimmed video file.\nExample: mp4, mkv, avi, webm\nSet to 'none' to use the same format as the original file. Timeout: 60 sec",
    "TRIM_AUDIO_FORMAT": "Set the output format for audio trimming. This determines the container format of the trimmed audio file.\nExample: mp3, m4a, flac, opus, wav\nSet to 'none' to use the same format as the original file. Timeout: 60 sec",
    "TRIM_IMAGE_FORMAT": "Set the output format for image trimming. This determines the format of the trimmed image file.\nExample: jpg, png, webp, gif\nSet to 'none' to use the same format as the original file. Timeout: 60 sec",
    "TRIM_IMAGE_QUALITY": "Set the quality for image processing during trim operations (0-100). Higher values mean better quality but larger file size.\nExample: 90 - high quality (default)\nExample: 75 - good balance of quality and size\nExample: 0 or 'none' - use original quality. Timeout: 60 sec",
    "TRIM_DOCUMENT_FORMAT": "Set the output format for document trimming. This determines the format of the trimmed document file.\nExample: pdf, docx, txt\nSet to 'none' to use the same format as the original file. Timeout: 60 sec",
    "TRIM_DOCUMENT_QUALITY": "Set the quality for document processing during trim operations (0-100). Higher values mean better quality but larger file size.\nExample: 90 - high quality (default)\nExample: 75 - good balance of quality and size\nExample: 0 or 'none' - use original quality. Timeout: 60 sec",
    "TRIM_SUBTITLE_FORMAT": "Set the output format for subtitle trimming. This determines the format of the trimmed subtitle file.\nExample: srt, ass, vtt\nSet to 'none' to use the same format as the original file. Timeout: 60 sec",
    "TRIM_ARCHIVE_FORMAT": "Set the output format for archive trimming. This determines the format of the trimmed archive file.\nExample: zip, 7z, tar\nSet to 'none' to use the same format as the original file. Timeout: 60 sec",
    # Extract Settings
    "EXTRACT_ENABLED": "Enable or disable the extract feature. Send 'true' to enable or 'false' to disable. When enabled, media tracks can be extracted from container files.\n\nExample: true - enable extract feature\nExample: false - disable extract feature\n\nPriority:\n1. Global (enabled) & User (disabled) -> Apply global\n2. User (enabled) & Global (disabled) -> Apply user\n3. Global (enabled) & User (enabled) -> Apply user\n4. Global (disabled) & User (disabled) -> Don't apply\n\nTimeout: 60 sec",
    "EXTRACT_PRIORITY": "Set the priority for extract processing in the media tools pipeline. Lower number means higher priority.\n\nExample: 1 - highest priority (runs before other tools)\nExample: 5 - medium priority\nExample: 10 - lowest priority (runs after other tools)\n\nDefault: 6\nTimeout: 60 sec",
    "EXTRACT_DELETE_ORIGINAL": "Choose whether to delete the original file after extraction. Send 'true' to delete or 'false' to keep.\n\nExample: true - delete original file after extraction\nExample: false - keep original file after extraction\n\nDefault: true\nTimeout: 60 sec",
    "EXTRACT_MAINTAIN_QUALITY": "Choose whether to maintain quality when extracting and converting tracks. Send 'true' to maintain quality or 'false' to use default settings.\n\nExample: true - use high quality settings for extracted tracks\nExample: false - use default quality settings\n\nDefault: true\nTimeout: 60 sec",
    # Video Extract Settings
    "EXTRACT_VIDEO_ENABLED": "Enable or disable video track extraction. Send 'true' to enable or 'false' to disable.\n\nExample: true - extract video tracks\nExample: false - don't extract video tracks\n\nTimeout: 60 sec",
    "EXTRACT_VIDEO_CODEC": "Set the codec to use for extracted video tracks. Common codecs: copy, h264, h265, vp9.\n\nExample: copy - preserve original codec (fastest)\nExample: h264 - convert to H.264 (widely compatible)\nExample: h265 - convert to H.265 (better compression)\nExample: none - don't specify codec (use default)\n\nTimeout: 60 sec",
    "EXTRACT_VIDEO_FORMAT": "Set the container format for extracted video tracks. Common formats: mp4, mkv, webm.\n\nExample: mp4 - use MP4 container (widely compatible)\nExample: mkv - use MKV container (supports more features)\nExample: none - use default format based on codec\n\nTimeout: 60 sec",
    "EXTRACT_VIDEO_INDEX": "Specify which video track(s) to extract by index (0-based). Leave empty or set to 'none' to extract all video tracks.\n\nExample: 0 - extract first video track only\nExample: 1 - extract second video track only\nExample: 0,1,2 - extract first, second, and third video tracks\nExample: all - extract all video tracks\n\nTimeout: 60 sec",
    "EXTRACT_VIDEO_QUALITY": "Set the quality for extracted video tracks (CRF value). Lower values mean higher quality.\n\nExample: 18 - high quality (larger file size)\nExample: 23 - medium quality (balanced)\nExample: 28 - lower quality (smaller file size)\nExample: none - use default quality\n\nTimeout: 60 sec",
    "EXTRACT_VIDEO_PRESET": "Set the encoding preset for extracted video tracks. Affects encoding speed vs compression efficiency.\n\nExample: ultrafast - fastest encoding, lowest compression\nExample: medium - balanced speed and compression\nExample: veryslow - slowest encoding, best compression\nExample: none - use default preset\n\nTimeout: 60 sec",
    "EXTRACT_VIDEO_BITRATE": "Set the bitrate for extracted video tracks. Higher values mean better quality but larger files.\n\nExample: 5M - 5 Mbps (good for 1080p)\nExample: 2M - 2 Mbps (good for 720p)\nExample: none - use default bitrate\n\nTimeout: 60 sec",
    "EXTRACT_VIDEO_RESOLUTION": "Set the resolution for extracted video tracks. Lower resolution means smaller file size.\n\nExample: 1920x1080 - Full HD\nExample: 1280x720 - HD\nExample: 640x480 - SD\nExample: none - keep original resolution\n\nTimeout: 60 sec",
    "EXTRACT_VIDEO_FPS": "Set the frame rate for extracted video tracks. Lower FPS means smaller file size.\n\nExample: 30 - 30 frames per second\nExample: 60 - 60 frames per second\nExample: none - keep original frame rate\n\nTimeout: 60 sec",
    # Audio Extract Settings
    "EXTRACT_AUDIO_ENABLED": "Enable or disable audio track extraction. Send 'true' to enable or 'false' to disable.\n\nExample: true - extract audio tracks\nExample: false - don't extract audio tracks\n\nTimeout: 60 sec",
    "EXTRACT_AUDIO_CODEC": "Set the codec to use for extracted audio tracks. Common codecs: copy, aac, mp3, opus, flac.\n\nExample: copy - preserve original codec (fastest)\nExample: mp3 - convert to MP3 (widely compatible)\nExample: aac - convert to AAC (good quality/size ratio)\nExample: flac - convert to FLAC (lossless)\nExample: none - don't specify codec (use default)\n\nTimeout: 60 sec",
    "EXTRACT_AUDIO_FORMAT": "Set the container format for extracted audio tracks. Common formats: mp3, m4a, ogg, flac.\n\nExample: mp3 - use MP3 container (widely compatible)\nExample: m4a - use M4A container (good for AAC)\nExample: none - use default format based on codec\n\nTimeout: 60 sec",
    "EXTRACT_AUDIO_INDEX": "Specify which audio track(s) to extract by index (0-based). Leave empty or set to 'none' to extract all audio tracks.\n\nExample: 0 - extract first audio track only\nExample: 1 - extract second audio track only\nExample: 0,1,2 - extract first, second, and third audio tracks\nExample: all - extract all audio tracks\n\nTimeout: 60 sec",
    "EXTRACT_AUDIO_BITRATE": "Set the bitrate for extracted audio tracks. Higher values mean better quality but larger files.\n\nExample: 320k - 320 kbps (high quality)\nExample: 192k - 192 kbps (good quality)\nExample: 128k - 128 kbps (acceptable quality)\nExample: none - use default bitrate\n\nTimeout: 60 sec",
    "EXTRACT_AUDIO_CHANNELS": "Set the number of audio channels for extracted audio tracks.\n\nExample: 2 - stereo\nExample: 1 - mono\nExample: 6 - 5.1 surround\nExample: none - keep original channels\n\nTimeout: 60 sec",
    "EXTRACT_AUDIO_SAMPLING": "Set the sampling rate for extracted audio tracks. Common values: 44100, 48000.\n\nExample: 44100 - CD quality (44.1 kHz)\nExample: 48000 - DVD quality (48 kHz)\nExample: none - keep original sampling rate\n\nTimeout: 60 sec",
    "EXTRACT_AUDIO_VOLUME": "Set the volume adjustment for extracted audio tracks. Values above 1 increase volume, below 1 decrease it.\n\nExample: 1.5 - increase volume by 50%\nExample: 0.8 - decrease volume by 20%\nExample: none - keep original volume\n\nTimeout: 60 sec",
    # Subtitle Extract Settings
    "EXTRACT_SUBTITLE_ENABLED": "Enable or disable subtitle track extraction. Send 'true' to enable or 'false' to disable.\n\nExample: true - extract subtitle tracks\nExample: false - don't extract subtitle tracks\n\nTimeout: 60 sec",
    "EXTRACT_SUBTITLE_CODEC": "Set the codec to use for extracted subtitle tracks. Common codecs: copy, srt, ass.\n\nExample: copy - preserve original codec (fastest)\nExample: srt - convert to SRT (widely compatible)\nExample: ass - convert to ASS (supports styling)\nExample: none - don't specify codec (use default)\n\nTimeout: 60 sec",
    "EXTRACT_SUBTITLE_FORMAT": "Set the format for extracted subtitle tracks. Common formats: srt, ass, vtt.\n\nExample: srt - SubRip format (widely compatible)\nExample: ass - Advanced SubStation Alpha (supports styling)\nExample: vtt - WebVTT format (for web videos)\nExample: none - use default format based on codec\n\nTimeout: 60 sec",
    "EXTRACT_SUBTITLE_INDEX": "Specify which subtitle track(s) to extract by index (0-based). Leave empty or set to 'none' to extract all subtitle tracks.\n\nExample: 0 - extract first subtitle track only\nExample: 1 - extract second subtitle track only\nExample: 0,1,2 - extract first, second, and third subtitle tracks\nExample: all - extract all subtitle tracks\n\nTimeout: 60 sec",
    "EXTRACT_SUBTITLE_LANGUAGE": "Set the language tag for extracted subtitle tracks. Uses ISO 639-2 codes.\n\nExample: eng - English\nExample: spa - Spanish\nExample: fre - French\nExample: none - keep original language tag\n\nTimeout: 60 sec",
    "EXTRACT_SUBTITLE_ENCODING": "Set the character encoding for extracted subtitle tracks. Common encodings: utf-8, latin1.\n\nExample: utf-8 - Unicode (recommended)\nExample: latin1 - Western European\nExample: none - auto-detect encoding\n\nTimeout: 60 sec",
    "EXTRACT_SUBTITLE_FONT": "Set the font for extracted subtitle tracks (only works with ASS/SSA subtitles).\n\nExample: Arial - use Arial font\nExample: none - use default font\n\nTimeout: 60 sec",
    "EXTRACT_SUBTITLE_FONT_SIZE": "Set the font size for extracted subtitle tracks (only works with ASS/SSA subtitles).\n\nExample: 24 - larger font size\nExample: 18 - medium font size\nExample: none - use default font size\n\nTimeout: 60 sec",
    # Attachment Extract Settings
    "EXTRACT_ATTACHMENT_ENABLED": "Enable or disable attachment extraction. Send 'true' to enable or 'false' to disable. When enabled, attachments (like fonts, images) will be extracted from media files.\n\nExample: true - extract attachments\nExample: false - don't extract attachments\n\nTimeout: 60 sec",
    "EXTRACT_ATTACHMENT_FORMAT": "Set the format for extracted attachments. Usually not needed as attachments keep their original format.\n\nExample: none - keep original format (recommended)\n\nTimeout: 60 sec",
    "EXTRACT_ATTACHMENT_INDEX": "Specify which attachment(s) to extract by index (0-based). Leave empty or set to 'none' to extract all attachments.\n\nExample: 0 - extract first attachment only\nExample: 1 - extract second attachment only\nExample: 0,1,2 - extract first, second, and third attachments\nExample: all - extract all attachments\n\nTimeout: 60 sec",
    "EXTRACT_ATTACHMENT_FILTER": "Set a filter pattern for extracting attachments. Only attachments matching the pattern will be extracted.\n\nExample: *.ttf - extract only font files\nExample: *.png - extract only PNG images\nExample: none - extract all attachments\n\nTimeout: 60 sec",
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
/{BotCommands.MusicSearchCommand[0]} or /{BotCommands.MusicSearchCommand[1]}: Search for music files in configured channels.
/{BotCommands.CheckDeletionsCommand[0]} or /{BotCommands.CheckDeletionsCommand[1]}: Check and manage scheduled message deletions.
/{BotCommands.AskCommand}: Chat with AI using the bot (Mistral or DeepSeek).
/{BotCommands.LoginCommand}: Login to the bot using password for permanent access.
/{BotCommands.RssCommand}: [Owner Only] Subscribe to RSS feeds.
"""

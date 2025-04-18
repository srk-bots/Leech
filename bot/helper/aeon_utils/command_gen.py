import os
import aiohttp
import asyncio
from bot import LOGGER
import json
from time import time

from bot import cpu_no
from bot.helper.ext_utils.bot_utils import cmd_exec


async def get_streams(file):
    cmd = [
        "ffprobe",
        "-hide_banner",
        "-loglevel",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        file,
    ]

    # Generate a unique process ID for tracking
    process_id = f"ffprobe_streams_{time()}"

    # Execute the command with resource limits
    stdout, stderr, code = await cmd_exec(
        cmd, apply_limits=True, process_id=process_id, task_type="FFprobe"
    )

    if code != 0:
        LOGGER.error(f"Error getting stream info: {stderr}")
        return None

    try:
        return json.loads(stdout)["streams"]
    except KeyError:
        LOGGER.error(
            f"No streams found in the ffprobe output: {stdout}",
        )
        return None


async def download_google_font(font_name):
    """Download a font from Google Fonts API.

    Args:
        font_name: Name of the Google Font to download

    Returns:
        str: Path to the downloaded font file or default font if download fails
    """
    try:
        # Create fonts directory if it doesn't exist
        os.makedirs("fonts", exist_ok=True)

        # Check if font already exists
        font_path = f"fonts/{font_name}.ttf"
        if os.path.exists(font_path):
            return font_path

        # Format the font name for the Google Fonts API URL
        api_font_name = font_name.replace(" ", "+")
        font_url = (
            f"https://fonts.googleapis.com/css2?family={api_font_name}&display=swap"
        )

        async with aiohttp.ClientSession() as session:
            # Get the CSS file which contains the font URL
            async with session.get(
                font_url, headers={"User-Agent": "Mozilla/5.0"}
            ) as response:
                if response.status != 200:
                    LOGGER.error(
                        f"Failed to fetch Google Font CSS for {font_name}: {response.status}"
                    )
                    return "default.otf"

                css = await response.text()

                # Extract the font URL from the CSS
                font_url_start = css.find("src: url(")
                if font_url_start == -1:
                    LOGGER.error(f"Could not find font URL in CSS for {font_name}")
                    return "default.otf"

                font_url_start += 9  # Length of "src: url("
                font_url_end = css.find(")", font_url_start)
                font_url = css[font_url_start:font_url_end]

                # Download the font file
                async with session.get(font_url) as font_response:
                    if font_response.status != 200:
                        LOGGER.error(
                            f"Failed to download font file for {font_name}: {font_response.status}"
                        )
                        return "default.otf"

                    with open(font_path, "wb") as f:
                        f.write(await font_response.read())

                    LOGGER.info(f"Successfully downloaded Google Font: {font_name}")
                    return font_path
    except Exception as e:
        LOGGER.error(f"Error downloading Google Font {font_name}: {str(e)}")
        return "default.otf"


async def get_watermark_cmd(
    file, key, position="top_left", size=20, color="white", font="default.otf"
):
    """Generate FFmpeg command for adding watermark to video or image.

    Args:
        file: Path to the input file
        key: Watermark text
        position: Position of watermark (top_left, top_right, bottom_left, bottom_right, center, etc.)
        size: Font size
        color: Font color
        font: Font file name or Google Font name

    Returns:
        tuple: FFmpeg command and temporary output file path, or None, None if not supported
    """
    from bot.helper.ext_utils.resource_manager import get_optimal_thread_count

    # Import the function to determine media type
    from bot.helper.ext_utils.media_utils import get_media_type_for_watermark

    # Determine the media type
    media_type = await get_media_type_for_watermark(file)
    if not media_type:
        LOGGER.warning(f"Unsupported file type for watermarking: {file}")
        return None, None

    # Determine output file extension based on input file
    file_ext = os.path.splitext(file)[1].lower()

    # For videos, always use .mkv as temp extension for maximum compatibility
    if media_type == "video":
        temp_file = f"{file}.temp.mkv"
    else:
        # For images, preserve the original extension
        temp_file = f"{file}.temp{file_ext}"

    # Check if font is a Google Font or a local file
    if font.endswith(".ttf") or font.endswith(".otf"):
        font_path = font
    else:
        # Assume it's a Google Font name and try to download it
        font_path = await download_google_font(font)

    # Set position coordinates based on position parameter
    if position == "top_left":
        x_pos, y_pos = "10", "10"
    elif position == "top_right":
        x_pos, y_pos = "w-tw-10", "10"
    elif position == "bottom_left":
        x_pos, y_pos = "10", "h-th-10"
    elif position == "bottom_right":
        x_pos, y_pos = "w-tw-10", "h-th-10"
    elif position == "center":
        x_pos, y_pos = "(w-tw)/2", "(h-th)/2"
    elif position == "top_center":
        x_pos, y_pos = "(w-tw)/2", "10"
    elif position == "bottom_center":
        x_pos, y_pos = "(w-tw)/2", "h-th-10"
    elif position == "left_center":
        x_pos, y_pos = "10", "(h-th)/2"
    elif position == "right_center":
        x_pos, y_pos = "w-tw-10", "(h-th)/2"
    else:  # Default to top_left if invalid position
        x_pos, y_pos = "10", "10"

    # Create the drawtext filter with shadow for better visibility
    # Add a shadow effect to make text more readable on any background
    shadow_color = "black" if color.lower() != "black" else "white"
    drawtext_filter = (
        f"drawtext=text='{key}':fontfile={font_path}:fontsize={size}:"
        f"fontcolor={color}:x={x_pos}:y={y_pos}:shadowcolor={shadow_color}:shadowx=1:shadowy=1"
    )

    # Base command for all media types
    cmd = [
        "xtra",
        "-hide_banner",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-i",
        file,
        "-ignore_unknown",
    ]

    # Add media-specific parameters
    if media_type == "video":
        # For videos, use the drawtext filter and copy audio streams
        # Also preserve subtitles and other streams
        # Get optimal thread count based on system load if dynamic threading is enabled
        thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

        cmd.extend(
            [
                "-vf",
                drawtext_filter,
                "-c:a",
                "copy",  # Copy audio streams
                "-c:s",
                "copy",  # Copy subtitle streams
                "-map",
                "0",  # Map all streams from input
                "-threads",
                f"{thread_count}",
                temp_file,
            ]
        )
    elif media_type == "image":
        # For static images, use the drawtext filter with appropriate output format
        # Use higher quality settings for better results
        if file_ext in [".jpg", ".jpeg"]:
            # For JPEG, use quality parameter
            # Get optimal thread count based on system load if dynamic threading is enabled
            thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

            cmd.extend(
                [
                    "-vf",
                    drawtext_filter,
                    "-q:v",
                    "1",  # Highest quality (1-31, lower is better)
                    "-threads",
                    f"{thread_count}",
                    temp_file,
                ]
            )
        elif file_ext in [".png", ".webp"]:
            # For PNG and WebP, preserve transparency
            # Get optimal thread count based on system load if dynamic threading is enabled
            thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

            cmd.extend(
                [
                    "-vf",
                    drawtext_filter,
                    "-compression_level",
                    "0",  # Lossless compression
                    "-threads",
                    f"{thread_count}",
                    temp_file,
                ]
            )
        else:
            # For other image formats, use general high quality settings
            # Get optimal thread count based on system load if dynamic threading is enabled
            thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

            cmd.extend(
                [
                    "-vf",
                    drawtext_filter,
                    "-q:v",
                    "2",  # High quality
                    "-threads",
                    f"{thread_count}",
                    temp_file,
                ]
            )
    elif media_type == "animated_image":
        # For animated images (GIFs), we need to use a different approach
        # The issue with the previous approach was that we can't use both -vf and -lavfi
        # Instead, we'll incorporate the drawtext filter into the complex filtergraph

        # Create a complex filtergraph that includes both the watermark and palette generation
        complex_filter = (
            f"[0:v]{drawtext_filter}[marked];"
            f"[marked]split[v1][v2];"
            f"[v1]palettegen=reserve_transparent=1[pal];"
            f"[v2][pal]paletteuse=alpha_threshold=128"
        )

        # Get optimal thread count based on system load if dynamic threading is enabled
        thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

        cmd.extend(
            [
                "-lavfi",
                complex_filter,
                "-threads",
                f"{thread_count}",
                temp_file,
            ]
        )
    else:
        # This should not happen as we already checked media_type
        LOGGER.error(f"Unknown media type: {media_type}")
        return None, None

    # Log the generated command for debugging
    LOGGER.debug(f"Generated watermark command for {media_type}: {' '.join(cmd)}")

    return cmd, temp_file


async def get_metadata_cmd(
    file_path, key, title=None, author=None, comment=None, metadata_all=None
):
    """Processes a single file to update metadata.

    Args:
        file_path: Path to the file to process
        key: Legacy metadata key (for backward compatibility)
        title: Title metadata value
        author: Author metadata value
        comment: Comment metadata value
        metadata_all: Value to use for all metadata fields (takes priority)
    """
    from bot.helper.ext_utils.resource_manager import get_optimal_thread_count

    temp_file = f"{file_path}.temp.mkv"
    streams = await get_streams(file_path)
    if not streams:
        return None, None

    languages = {
        stream["index"]: stream["tags"]["language"]
        for stream in streams
        if "tags" in stream and "language" in stream["tags"]
    }

    # Get optimal thread count based on system load if dynamic threading is enabled
    thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

    # Determine which metadata values to use
    # metadata_all takes priority over individual settings
    if metadata_all:
        title_value = author_value = comment_value = metadata_all
    else:
        # Use individual values if provided, otherwise fall back to legacy key
        title_value = title if title else key
        author_value = author if author else key
        comment_value = comment if comment else key

    cmd = [
        "xtra",
        "-hide_banner",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-i",
        file_path,
        "-ignore_unknown",
        "-c",
        "copy",
        # Global metadata for the file
        "-metadata",
        f"title={title_value}",
    ]

    # Add author and comment metadata if they exist
    if author_value:
        cmd.extend(["-metadata", f"artist={author_value}"])
        cmd.extend(["-metadata", f"author={author_value}"])

    if comment_value:
        cmd.extend(["-metadata", f"comment={comment_value}"])

    cmd.extend(["-threads", f"{thread_count}"])

    audio_index = 0
    subtitle_index = 0
    first_video = False

    for stream in streams:
        stream_index = stream["index"]
        stream_type = stream["codec_type"]

        if stream_type == "video":
            if not first_video:
                cmd.extend(["-map", f"0:{stream_index}"])
                first_video = True
            cmd.extend([f"-metadata:s:v:{stream_index}", f"title={title_value}"])
            if stream_index in languages:
                cmd.extend(
                    [
                        f"-metadata:s:v:{stream_index}",
                        f"language={languages[stream_index]}",
                    ],
                )
        elif stream_type == "audio":
            cmd.extend(
                [
                    "-map",
                    f"0:{stream_index}",
                    f"-metadata:s:a:{audio_index}",
                    f"title={title_value}",
                ],
            )
            if author_value:
                cmd.extend(
                    [
                        f"-metadata:s:a:{audio_index}",
                        f"artist={author_value}",
                    ],
                )
            if comment_value:
                cmd.extend(
                    [
                        f"-metadata:s:a:{audio_index}",
                        f"comment={comment_value}",
                    ],
                )
            if stream_index in languages:
                cmd.extend(
                    [
                        f"-metadata:s:a:{audio_index}",
                        f"language={languages[stream_index]}",
                    ],
                )
            audio_index += 1
        elif stream_type == "subtitle":
            codec_name = stream.get("codec_name", "unknown")
            if codec_name in ["webvtt", "unknown"]:
                LOGGER.warning(
                    f"Skipping unsupported subtitle metadata modification: {codec_name} for stream {stream_index}",
                )
            else:
                cmd.extend(
                    [
                        "-map",
                        f"0:{stream_index}",
                        f"-metadata:s:s:{subtitle_index}",
                        f"title={title_value}",
                    ],
                )
                if comment_value:
                    cmd.extend(
                        [
                            f"-metadata:s:s:{subtitle_index}",
                            f"comment={comment_value}",
                        ],
                    )
                if stream_index in languages:
                    cmd.extend(
                        [
                            f"-metadata:s:s:{subtitle_index}",
                            f"language={languages[stream_index]}",
                        ],
                    )
                subtitle_index += 1
        else:
            cmd.extend(["-map", f"0:{stream_index}"])

    cmd.extend(["-threads", f"{max(1, cpu_no // 2)}", temp_file])
    return cmd, temp_file


# TODO later
async def get_embed_thumb_cmd(file, attachment_path):
    from bot.helper.ext_utils.resource_manager import get_optimal_thread_count

    temp_file = f"{file}.temp.mkv"
    attachment_ext = attachment_path.split(".")[-1].lower()
    mime_type = "application/octet-stream"
    if attachment_ext in ["jpg", "jpeg"]:
        mime_type = "image/jpeg"
    elif attachment_ext == "png":
        mime_type = "image/png"

    # Get optimal thread count based on system load if dynamic threading is enabled
    thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

    cmd = [
        "xtra",
        "-hide_banner",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-i",
        file,
        "-ignore_unknown",
        "-attach",
        attachment_path,
        "-metadata:s:t",
        f"mimetype={mime_type}",
        "-c",
        "copy",
        "-map",
        "0",
        "-threads",
        f"{thread_count}",
        temp_file,
    ]

    return cmd, temp_file


async def get_media_type(file_path):
    """Determine if a file is video, audio, or subtitle.

    Args:
        file_path: Path to the file

    Returns:
        str: 'video', 'audio', 'subtitle', or None if can't determine
    """
    streams = await get_streams(file_path)
    if not streams:
        return None

    # Check for video streams
    for stream in streams:
        if stream.get("codec_type") == "video":
            # Check if it's not just a cover art
            if not (
                stream.get("disposition")
                and stream.get("disposition").get("attached_pic") == 1
            ):
                return "video"

    # Check for audio streams
    for stream in streams:
        if stream.get("codec_type") == "audio":
            return "audio"

    # Check for subtitle streams
    for stream in streams:
        if stream.get("codec_type") == "subtitle":
            return "subtitle"

    return None


async def get_merge_concat_demuxer_cmd(files, output_format="mkv", media_type=None):
    """Generate FFmpeg command for merging files using concat demuxer.

    Args:
        files: List of file paths to merge
        output_format: Output file format (default: mkv)
        media_type: Type of media ('video', 'audio', 'subtitle', 'image') for specialized handling

    Returns:
        tuple: FFmpeg command and output file path
    """
    from bot.helper.ext_utils.resource_manager import get_optimal_thread_count

    if not files:
        return None, None

    # Use files in the order they were provided
    # (No sorting to preserve user's intended order)

    # Check if all files have the same codec for video and audio
    # This is important for concat demuxer to work properly
    if media_type in ["video", "audio"]:
        try:
            import json
            import subprocess

            # Get codec information for all files
            codecs = []
            for file_path in files:
                cmd = [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v" if media_type == "video" else "a",
                    "-show_entries",
                    "stream=codec_name",
                    "-of",
                    "json",
                    file_path,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if "streams" in data and data["streams"]:
                        codecs.append(data["streams"][0].get("codec_name", ""))
                    else:
                        # If we can't determine codec, assume it's different
                        codecs.append(f"unknown_{len(codecs)}")
                else:
                    # If ffprobe fails, assume it's a different codec
                    codecs.append(f"unknown_{len(codecs)}")

            # Check if all codecs are the same
            if len(set(codecs)) > 1:
                LOGGER.warning(
                    f"Files have different codecs: {codecs}. Concat demuxer may not work properly."
                )
        except Exception as e:
            LOGGER.warning(
                f"Error checking codecs: {e}. Proceeding with concat demuxer anyway."
            )

    # Create a temporary file list for concat demuxer
    concat_list_path = "concat_list.txt"
    with open(concat_list_path, "w") as f:
        for file_path in files:
            # Escape single quotes in file paths
            escaped_path = file_path.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")

    # Determine output path based on first file and media type
    base_dir = os.path.dirname(files[0])
    if media_type == "video":
        output_file = os.path.join(base_dir, f"merged_video.{output_format}")
    elif media_type == "audio":
        output_file = os.path.join(base_dir, f"merged_audio.{output_format}")
    elif media_type == "subtitle":
        output_file = os.path.join(base_dir, f"merged_subtitle.{output_format}")
    else:
        output_file = os.path.join(base_dir, f"merged.{output_format}")

    # Basic command for concat demuxer
    cmd = [
        "xtra",
        "-hide_banner",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_list_path,
        "-ignore_unknown",
    ]

    # Add specialized options based on media type
    if media_type == "video":
        # For video files, we need to handle potential codec issues
        # Check if all files have the same codec
        streams_list = []
        for file_path in files:
            streams = await get_streams(file_path)
            if streams:
                streams_list.append(streams)

        # Check if all files have the same codecs
        same_codecs = True
        same_resolution = True
        reference_width = None
        reference_height = None

        # Always add -map 0 to preserve all streams from the input
        cmd.extend(["-map", "0"])

        if streams_list:
            reference_streams = streams_list[0]
            # Check for video dimensions in the first file
            for stream in reference_streams:
                if stream.get("codec_type") == "video" and not stream.get(
                    "disposition", {}
                ).get("attached_pic"):
                    reference_width = stream.get("width")
                    reference_height = stream.get("height")
                    break

            # Compare codecs and dimensions with other files
            for streams in streams_list[1:]:
                if len(streams) != len(reference_streams):
                    same_codecs = False

                # Check for resolution differences
                for stream in streams:
                    if stream.get("codec_type") == "video" and not stream.get(
                        "disposition", {}
                    ).get("attached_pic"):
                        if (
                            stream.get("width") != reference_width
                            or stream.get("height") != reference_height
                        ):
                            same_resolution = False
                        break

                # Check for codec differences
                for i, stream in enumerate(streams):
                    if i >= len(reference_streams):
                        break
                    if stream.get("codec_name") != reference_streams[i].get(
                        "codec_name"
                    ) or stream.get("codec_type") != reference_streams[i].get(
                        "codec_type"
                    ):
                        same_codecs = False
                        break

        LOGGER.info(
            f"Video merge analysis: same_codecs={same_codecs}, same_resolution={same_resolution}"
        )

        if same_codecs and same_resolution:
            # All files have the same codecs and resolution, we can use copy
            # Use -map 0 to preserve all streams including video, audio, and subtitles
            cmd.extend(["-c", "copy"])
            LOGGER.info(
                "Using direct stream copy for identical video files, preserving all streams"
            )
        else:
            # Files have different codecs or resolutions, we need to transcode
            # Use high-quality settings for video and audio, but preserve all streams
            if output_format in ["mp4", "mov"]:
                # For MP4 output, use H.264 for maximum compatibility
                cmd.extend(
                    [
                        # No need to add -map 0 again, it's already added above
                        "-c",
                        "copy",  # Start with copying all streams
                        "-c:v",  # Override video codec only
                        "libx264",
                        "-crf",
                        "18",  # High quality
                        "-preset",
                        "slow",  # Better compression
                        "-c:a",  # Override audio codec only if needed
                        "aac",
                        "-b:a",
                        "192k",
                        "-c:s",  # Override subtitle codec for MP4 compatibility
                        "mov_text",
                    ]
                )
                LOGGER.info(
                    "Using H.264/AAC encoding for MP4 output while preserving all streams"
                )
            elif output_format == "webm":
                # For WebM output, use VP9 and Opus
                cmd.extend(
                    [
                        # No need to add -map 0 again, it's already added above
                        "-c:v",
                        "libvpx-vp9",
                        "-crf",
                        "30",
                        "-b:v",
                        "0",
                        "-c:a",
                        "libopus",
                        "-b:a",
                        "128k",
                        # WebM doesn't support many subtitle formats, so we don't specify -c:s
                    ]
                )
                LOGGER.info(
                    "Using VP9/Opus encoding for WebM output while preserving compatible streams"
                )
            else:
                # For MKV and other formats, use H.264 with high quality
                # MKV supports virtually all codecs, so we can preserve more
                cmd.extend(
                    [
                        # No need to add -map 0 again, it's already added above
                        "-c",
                        "copy",  # Start with copying all streams
                        "-c:v",  # Override video codec only
                        "libx264",
                        "-crf",
                        "18",
                        "-preset",
                        "slow",
                        "-c:a",  # Override audio codec only if needed
                        "aac",
                        "-b:a",
                        "192k",
                        # Keep subtitle copying as is
                    ]
                )
                LOGGER.info(
                    "Using H.264/AAC encoding for MKV output while preserving all streams"
                )

            # If resolutions differ, we need to handle that in filter_complex instead
            if not same_resolution and not same_codecs:
                LOGGER.info(
                    "Videos have different resolutions and codecs, consider using filter_complex instead"
                )
    elif media_type == "audio":
        # For audio files, check if we need to transcode
        streams_list = []
        for file_path in files:
            streams = await get_streams(file_path)
            if streams:
                streams_list.append(streams)

        # Check if all files have the same audio codec
        same_codec = True
        audio_codec = None
        for streams in streams_list:
            for stream in streams:
                if stream.get("codec_type") == "audio":
                    if audio_codec is None:
                        audio_codec = stream.get("codec_name")
                    elif audio_codec != stream.get("codec_name"):
                        same_codec = False
                        break

        LOGGER.info(
            f"Audio merge analysis: same_codec={same_codec}, codec={audio_codec}"
        )

        if same_codec and audio_codec:
            # All files have the same audio codec, we can use copy
            cmd.extend(["-c", "copy"])
            LOGGER.info(
                f"Using direct stream copy for identical audio files with codec {audio_codec}"
            )
        else:
            # Files have different audio codecs, we need to transcode
            # Use high-quality settings for audio based on output format
            if output_format == "mp3":
                cmd.extend(["-c:a", "libmp3lame", "-q:a", "0"])  # Highest quality MP3
                LOGGER.info("Using MP3 encoding with highest quality")
            elif output_format == "aac" or output_format == "m4a":
                cmd.extend(["-c:a", "aac", "-b:a", "320k"])  # High bitrate AAC
                LOGGER.info("Using AAC encoding with 320k bitrate")
            elif output_format == "flac":
                cmd.extend(["-c:a", "flac"])  # Lossless FLAC
                LOGGER.info("Using lossless FLAC encoding")
            elif output_format == "opus":
                cmd.extend(["-c:a", "libopus", "-b:a", "256k"])  # High quality Opus
                LOGGER.info("Using Opus encoding with 256k bitrate")
            elif output_format == "ogg":
                cmd.extend(["-c:a", "libvorbis", "-q:a", "10"])  # High quality Vorbis
                LOGGER.info("Using Vorbis encoding with quality level 10")
            else:
                # Default to AAC for other formats
                cmd.extend(["-c:a", "aac", "-b:a", "320k"])
                LOGGER.info("Using default AAC encoding with 320k bitrate")
    elif media_type == "subtitle":
        # For subtitle files, we need to handle different formats
        # Check the output format and set appropriate codec
        if output_format == "srt":
            cmd.extend(["-c:s", "srt"])
            LOGGER.info("Using SRT subtitle format")
        elif output_format == "ass" or output_format == "ssa":
            cmd.extend(["-c:s", "ass"])
            LOGGER.info("Using ASS/SSA subtitle format")
        elif output_format == "vtt":
            cmd.extend(["-c:s", "webvtt"])
            LOGGER.info("Using WebVTT subtitle format")
        else:
            # Default to copy for other formats
            cmd.extend(["-c:s", "copy"])
            LOGGER.info("Using copy for subtitle format")
    elif media_type == "image":
        # For image files, we need to use a different approach
        # This is just a placeholder as concat demuxer doesn't work well for images
        # The actual image merging will be handled by PIL in a separate function
        LOGGER.info(
            "Concat demuxer not suitable for images, use filter_complex or PIL instead"
        )
        return None, None
    else:
        # Default to copy for unknown media types
        cmd.extend(["-c", "copy"])
        LOGGER.info(f"Using copy for unknown media type: {media_type}")

    # Add threading and output file
    # Get optimal thread count based on system load if dynamic threading is enabled
    thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)
    cmd.extend(
        [
            "-threads",
            f"{thread_count}",
            output_file,
        ]
    )

    return cmd, output_file


async def get_merge_filter_complex_cmd(files, media_type, output_format=None):
    """Generate FFmpeg command for merging files using filter_complex.

    Args:
        files: List of file paths to merge
        media_type: Type of media ('video', 'audio', 'subtitle')
        output_format: Output file format (default: based on media_type)

    Returns:
        tuple: FFmpeg command and output file path
    """
    from bot.helper.ext_utils.resource_manager import get_optimal_thread_count

    if not files:
        return None, None

    # Use files in the order they were provided
    # (No sorting to preserve user's intended order)

    # Set default output format based on media type if not specified
    if not output_format:
        if media_type == "video":
            output_format = "mkv"
        elif media_type == "audio":
            output_format = "mp3"
        else:
            output_format = "srt"

    # For video and audio, check if we need to handle different resolutions or sample rates
    if media_type in ["video", "audio"]:
        try:
            import json
            import subprocess

            # Get media information for all files
            media_info = []
            for file_path in files:
                info = {}
                # Get codec information
                cmd = [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v" if media_type == "video" else "a",
                    "-show_entries",
                    "stream=codec_name,width,height,sample_rate,channels",
                    "-of",
                    "json",
                    file_path,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if "streams" in data and data["streams"]:
                        stream = data["streams"][0]
                        info["codec"] = stream.get("codec_name", "")
                        if media_type == "video":
                            info["width"] = int(stream.get("width", 0))
                            info["height"] = int(stream.get("height", 0))
                        else:  # audio
                            info["sample_rate"] = int(stream.get("sample_rate", 0))
                            info["channels"] = int(stream.get("channels", 0))
                media_info.append(info)

            # Log the media information for debugging
            LOGGER.info(f"Media info for {media_type} files: {media_info}")
        except Exception as e:
            LOGGER.warning(
                f"Error getting media info: {e}. Proceeding with basic filter_complex."
            )
            media_info = []

    # Determine output path based on first file and media type
    base_dir = os.path.dirname(files[0])
    if media_type == "video":
        output_file = os.path.join(base_dir, f"merged_video.{output_format}")
    elif media_type == "audio":
        output_file = os.path.join(base_dir, f"merged_audio.{output_format}")
    elif media_type == "subtitle":
        output_file = os.path.join(base_dir, f"merged_subtitle.{output_format}")
    else:
        output_file = os.path.join(base_dir, f"merged.{output_format}")

    # Build input arguments
    input_args = []
    for file_path in files:
        input_args.extend(["-i", file_path])

    # Build filter complex string based on media type
    if media_type == "video":
        # For video files, we need to check each file for video and audio streams
        filter_complex = ""
        video_inputs = []
        audio_inputs = []
        subtitle_streams = []  # Track subtitle streams for mapping

        # First, identify which files have video and audio streams
        for i, file_path in enumerate(files):
            streams = await get_streams(file_path)
            if not streams:
                continue

            # Find video, audio, and subtitle streams
            video_stream = None
            audio_stream = None
            for stream in streams:
                if stream.get("codec_type") == "video" and not stream.get(
                    "disposition", {}
                ).get("attached_pic"):
                    video_stream = stream
                elif stream.get("codec_type") == "audio":
                    audio_stream = stream
                elif stream.get("codec_type") == "subtitle":
                    # Track subtitle streams for mapping
                    subtitle_streams.append((i, stream.get("index", 0)))

            # Add video stream if found
            if video_stream:
                video_index = video_stream.get("index", 0)
                video_inputs.append((i, video_index))

            # Add audio stream if found
            if audio_stream:
                audio_index = audio_stream.get("index", 0)
                audio_inputs.append((i, audio_index))

        # If we have video streams, create a video concat filter
        if video_inputs:
            # Check if we need to scale videos to the same dimensions
            need_scaling = False
            target_width = None
            target_height = None

            # Get dimensions of all videos
            video_dimensions = []
            for i, file_path in enumerate(files):
                streams = await get_streams(file_path)
                if not streams:
                    continue

                for stream in streams:
                    if stream.get("codec_type") == "video" and not stream.get(
                        "disposition", {}
                    ).get("attached_pic"):
                        width = stream.get("width")
                        height = stream.get("height")
                        if width and height:
                            video_dimensions.append((i, width, height))
                            if target_width is None or target_height is None:
                                target_width = width
                                target_height = height
                            elif width != target_width or height != target_height:
                                need_scaling = True

            # If videos have different dimensions, we need to scale them
            if need_scaling and target_width and target_height:
                # Create a new filter complex with scaling
                scaled_inputs = []
                for i, width, height in video_dimensions:
                    if width != target_width or height != target_height:
                        filter_complex += (
                            f"[{i}:v]scale={target_width}:{target_height}[v{i}];"
                        )
                        scaled_inputs.append(f"[v{i}]")
                    else:
                        scaled_inputs.append(f"[{i}:v]")

                # Use scaled inputs for concat
                video_filter = (
                    "".join(scaled_inputs)
                    + f"concat=n={len(scaled_inputs)}:v=1:a=0[outv]"
                )
            else:
                # Use original inputs for concat
                video_filter = (
                    "".join([f"[{i}:v:{idx}]" for i, idx in video_inputs])
                    + f"concat=n={len(video_inputs)}:v=1:a=0[outv]"
                )

            if filter_complex and not filter_complex.endswith(";"):
                filter_complex += ";"
            filter_complex += video_filter

        # If we have audio streams, create an audio concat filter
        if audio_inputs:
            if filter_complex and not filter_complex.endswith(";"):
                filter_complex += ";"  # Separator for multiple filters

            # Use a safer approach for audio inputs
            # First check if the audio stream exists in each file
            valid_audio_inputs = []
            for i, file_path in enumerate(files):
                streams = await get_streams(file_path)
                if not streams:
                    continue

                # Find all audio streams in each file
                audio_stream_count = 0
                for stream in streams:
                    if stream.get("codec_type") == "audio":
                        # Use actual stream index for more reliable mapping
                        stream_index = stream.get("index", audio_stream_count)
                        valid_audio_inputs.append((i, stream_index))
                        audio_stream_count += 1
                        LOGGER.info(
                            f"Found audio stream in file {i}: index={stream_index}, codec={stream.get('codec_name')}"
                        )

            if valid_audio_inputs:
                # Group audio inputs by file to preserve all audio tracks
                audio_inputs_by_file = {}
                for i, idx in valid_audio_inputs:
                    if i not in audio_inputs_by_file:
                        audio_inputs_by_file[i] = []
                    audio_inputs_by_file[i].append(idx)

                # Create separate concat filters for each audio track position
                audio_track_count = max(
                    len(inputs) for inputs in audio_inputs_by_file.values()
                )
                LOGGER.info(
                    f"Found {audio_track_count} audio track positions across {len(audio_inputs_by_file)} files"
                )

                # If we have multiple audio tracks, create a separate concat filter for each position
                if audio_track_count > 0:
                    for track_pos in range(audio_track_count):
                        # Collect inputs for this track position from each file
                        track_inputs = []
                        for file_idx, track_indices in audio_inputs_by_file.items():
                            if track_pos < len(track_indices):
                                track_inputs.append(
                                    (file_idx, track_indices[track_pos])
                                )

                        if track_inputs:
                            # Create concat filter for this track position
                            if filter_complex and not filter_complex.endswith(";"):
                                filter_complex += ";"
                            audio_filter = (
                                "".join([f"[{i}:a:{idx}]" for i, idx in track_inputs])
                                + f"concat=n={len(track_inputs)}:v=0:a=1[outa{track_pos}]"
                            )
                            filter_complex += audio_filter
                            LOGGER.info(
                                f"Created audio concat filter for track position {track_pos} with {len(track_inputs)} inputs"
                            )
                else:
                    LOGGER.warning("No valid audio tracks found for filter complex")
            else:
                LOGGER.warning("No valid audio streams found for filter complex")

        # Set up mapping based on available streams
        map_args = []

        # First map the merged video stream
        if video_inputs:
            map_args.extend(["-map", "[outv]"])
            # Set video codec based on output format
            if output_format == "mp4":
                map_args.extend(["-c:v", "libx264", "-crf", "18"])
            elif output_format == "webm":
                map_args.extend(["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0"])
            else:  # Default for mkv and others
                map_args.extend(["-c:v", "libx264", "-crf", "18"])

        # Map audio streams from filter_complex outputs
        # Check for [outaX] patterns in filter_complex
        import re

        outa_pattern = r"\[outa(\d*)\]"
        outa_matches = re.findall(outa_pattern, filter_complex)

        if outa_matches:
            # Map all audio outputs from filter_complex
            for match in outa_matches:
                track_num = match if match else "0"
                map_args.extend(["-map", f"[outa{track_num}]"])
                LOGGER.info(
                    f"Mapping audio track from filter_complex: [outa{track_num}]"
                )
        elif "[outa]" in filter_complex:
            # Legacy single audio track
            map_args.extend(["-map", "[outa]"])
            LOGGER.info("Mapping single audio track from filter_complex: [outa]")
        else:
            # Otherwise, map all audio streams from all input files directly
            audio_track_count = 0
            for i, file_path in enumerate(files):
                streams = await get_streams(file_path)
                if not streams:
                    continue

                # Find and map all audio streams
                for stream in streams:
                    if stream.get("codec_type") == "audio":
                        audio_index = stream.get("index", 0)
                        map_args.extend(
                            ["-map", f"{i}:a:{audio_index}?"]
                        )  # Add ? to make it optional
                        audio_track_count += 1

            LOGGER.info(
                f"Directly mapping {audio_track_count} audio tracks from input files"
            )

        # Set audio codec based on output format
        if output_format == "mp4":
            map_args.extend(["-c:a", "aac", "-b:a", "192k"])
        elif output_format == "webm":
            map_args.extend(["-c:a", "libopus", "-b:a", "128k"])
        else:  # Default for mkv and others
            map_args.extend(["-c:a", "aac", "-b:a", "192k"])

        # Now map all subtitle streams from all input files
        # This preserves all subtitle tracks in the merged output
        for i, file_path in enumerate(files):
            streams = await get_streams(file_path)
            if not streams:
                continue

            # Find and map all subtitle streams
            for stream in streams:
                if stream.get("codec_type") == "subtitle":
                    subtitle_index = stream.get("index", 0)
                    map_args.extend(["-map", f"{i}:s:{subtitle_index}"])
                    LOGGER.info(
                        f"Mapping subtitle track from file {i}: index={subtitle_index}, codec={stream.get('codec_name')}"
                    )

        # Set subtitle codec based on output format
        if output_format == "mp4":
            map_args.extend(["-c:s", "mov_text"])  # MP4 compatible subtitles
        else:  # For MKV and other formats that support most subtitle formats
            map_args.extend(["-c:s", "copy"])  # Copy subtitle streams as is

        # Add metadata to indicate this is a merged file
        map_args.extend(["-metadata", "title=Merged Video"])

        # If no valid streams found, use a simpler approach
        if not filter_complex:
            return None, None

    elif media_type == "audio":
        # For audio files, check if we need to normalize audio levels
        normalize_audio = False  # Set to True to enable audio normalization

        if normalize_audio:
            # First pass: analyze audio levels
            filter_complex = ""
            for i, _ in enumerate(files):
                filter_complex += f"[{i}:a:0]loudnorm=print_format=json[a{i}];"

            # Second pass: normalize and concat
            for i, _ in enumerate(files):
                filter_complex += f"[a{i}]"
            filter_complex += f"concat=n={len(files)}:v=0:a=1[outa]"
        else:
            # Simple concat without normalization
            filter_complex = ""
            for i, _ in enumerate(files):
                filter_complex += f"[{i}:a:0]"
            filter_complex += f"concat=n={len(files)}:v=0:a=1[outa]"

        map_args = ["-map", "[outa]"]

        # Set audio codec based on output format
        if output_format == "mp3":
            map_args.extend(["-c:a", "libmp3lame", "-q:a", "0"])
        elif output_format == "aac" or output_format == "m4a":
            map_args.extend(["-c:a", "aac", "-b:a", "320k"])
        elif output_format == "flac":
            map_args.extend(["-c:a", "flac"])
        elif output_format == "opus":
            map_args.extend(["-c:a", "libopus", "-b:a", "256k"])
        else:
            # Default to AAC for other formats
            map_args.extend(["-c:a", "aac", "-b:a", "320k"])

    elif media_type == "subtitle":
        # For subtitle files, we'll use a custom approach for merging
        # This is a more advanced approach than just copying the first file

        # Check the subtitle formats
        subtitle_formats = [os.path.splitext(f)[1][1:].lower() for f in files]
        LOGGER.info(f"Merging subtitle files with formats: {subtitle_formats}")

        # Check if we need to convert formats
        need_conversion = len(set(subtitle_formats)) > 1
        if need_conversion:
            LOGGER.info(
                "Different subtitle formats detected, will convert to SRT before merging"
            )

            # For SRT files or if we need to convert to SRT
            # For SRT files, we can use a special approach to merge them
            # We'll create a temporary script to merge SRT files with proper timing
            # Use raw string to avoid escape sequence issues
            merge_script = r"""#!/usr/bin/env python3
import sys
import re

def parse_time(time_str):
    h, m, s = time_str.replace(',', '.').split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')

def parse_srt(content):
    pattern = r'(\\d+)\\s+(\\d{2}:\\d{2}:\\d{2},\\d{3}) --> (\\d{2}:\\d{2}:\\d{2},\\d{3})\\s+(.*?)(?=\\n\\d+\\s+\\d{2}:\\d{2}:\\d{2},\\d{3}|$)'
    matches = re.findall(pattern, content, re.DOTALL)
    return [(int(idx), start, end, text.strip()) for idx, start, end, text in matches]

def parse_vtt(content):
    # Remove WEBVTT header if present
    if content.startswith('WEBVTT'):
        content = '\n'.join(content.split('\n')[2:])

    # VTT format: HH:MM:SS.mmm --> HH:MM:SS.mmm
    pattern = r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})\s+(.*?)(?=\n\n|$)'
    matches = re.findall(pattern, content, re.DOTALL)

    # Convert to SRT-like format with indices
    result = []
    for i, (start, end, text) in enumerate(matches, 1):
        # Convert VTT timestamp format to SRT format
        start_srt = start.replace('.', ',')
        end_srt = end.replace('.', ',')
        result.append((i, start_srt, end_srt, text.strip()))

    return result

def parse_ass(content):
    # Extract events section
    events_section = re.search(r'\[Events\].*?Format:.*?\n(.*)', content, re.DOTALL)
    if not events_section:
        return []

    events_text = events_section.group(1)

    # Extract dialogue lines
    dialogue_pattern = r'Dialogue: [^,]*,([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),(.*)'
    matches = re.findall(dialogue_pattern, events_text)

    result = []
    for i, match in enumerate(matches, 1):
        start_time = match[1].strip()
        end_time = match[2].strip()
        text = match[8].strip()

        # Convert ASS timestamp format (H:MM:SS.cc) to SRT format (HH:MM:SS,mmm)
        start_parts = start_time.split(':')
        if len(start_parts) == 2:  # MM:SS.cc
            start_srt = f"00:{start_parts[0]}:{start_parts[1]}".replace('.', ',')
        else:  # H:MM:SS.cc
            h = start_parts[0].zfill(2)
            start_srt = f"{h}:{start_parts[1]}:{start_parts[2]}".replace('.', ',')

        end_parts = end_time.split(':')
        if len(end_parts) == 2:  # MM:SS.cc
            end_srt = f"00:{end_parts[0]}:{end_parts[1]}".replace('.', ',')
        else:  # H:MM:SS.cc
            h = end_parts[0].zfill(2)
            end_srt = f"{h}:{end_parts[1]}:{end_parts[2]}".replace('.', ',')

        result.append((i, start_srt, end_srt, text))

    return result

def detect_subtitle_format(file_path):
    # Detect subtitle format based on file extension and content
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.srt':
        return 'srt'
    elif ext == '.vtt':
        return 'vtt'
    elif ext in ['.ass', '.ssa']:
        return 'ass'

    # If extension is not recognized, try to detect from content
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(1000)  # Read first 1000 chars

        if content.startswith('WEBVTT'):
            return 'vtt'
        elif '[Script Info]' in content and '[Events]' in content:
            return 'ass'
        elif re.search(r'\d+\s+\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', content):
            return 'srt'
    except Exception:
        pass

    # Default to SRT if we can't determine
    return 'srt'

def merge_subtitle_files(file_paths):
    all_subtitles = []
    current_offset = 0

    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Detect format and parse accordingly
            format_type = detect_subtitle_format(file_path)
            if format_type == 'srt':
                subtitles = parse_srt(content)
            elif format_type == 'vtt':
                subtitles = parse_vtt(content)
            elif format_type == 'ass':
                subtitles = parse_ass(content)
            else:
                # Default to SRT parser
                subtitles = parse_srt(content)

            if not subtitles:
                continue

            # Get the last end time from previous file
            if all_subtitles:
                last_end_time = parse_time(all_subtitles[-1][2])
            else:
                last_end_time = 0

            # Adjust timing for current file
            for idx, start, end, text in subtitles:
                start_time = parse_time(start) + current_offset
                end_time = parse_time(end) + current_offset

                # Handle overlapping timestamps
                if all_subtitles and start_time < last_end_time:
                    # Option 1: Shift this subtitle to start after the last one
                    start_time = last_end_time + 0.1
                    end_time = max(end_time, start_time + 1.0)  # Ensure at least 1 second duration

                all_subtitles.append((len(all_subtitles) + 1, format_time(start_time), format_time(end_time), text))
                last_end_time = end_time

            # Update offset for next file
            if subtitles:
                current_offset = parse_time(all_subtitles[-1][2]) + 0.5  # Add a small gap between files
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue

    # Sort subtitles by start time to handle any potential overlaps
    all_subtitles.sort(key=lambda x: parse_time(x[1]))

    # Renumber subtitles after sorting
    all_subtitles = [(i+1, start, end, text) for i, (_, start, end, text) in enumerate(all_subtitles)]

    # Generate merged SRT content
    merged_content = ""
    for idx, start, end, text in all_subtitles:
        merged_content += f"{idx}\n{start} --> {end}\n{text}\n\n"

    return merged_content

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python merge_srt.py output.srt input1.srt input2.srt ...")
        sys.exit(1)

    output_file = sys.argv[1]
    input_files = sys.argv[2:]

    merged_content = merge_subtitle_files(input_files)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(merged_content)
"""

            # Save the merge script
            script_path = "merge_srt.py"
            with open(script_path, "w") as f:
                f.write(merge_script)

            # Create a command to run the script
            cmd = ["python3", script_path, output_file, *files]

            # Run the script to merge SRT files
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            await process.communicate()

            # Check if the output file was created
            if os.path.exists(output_file):
                return ["echo", "Subtitle merge completed"], output_file
            else:
                # Fallback to copying the first subtitle file
                cmd = [
                    "xtra",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-progress",
                    "pipe:1",
                    "-i",
                    files[0],
                    "-c",
                    "copy",
                    "-threads",
                    f"{max(1, cpu_no // 2)}",
                    output_file,
                ]
                return cmd, output_file
        else:
            # For other subtitle formats, just copy the first file as a placeholder
            cmd = [
                "xtra",
                "-hide_banner",
                "-loglevel",
                "error",
                "-progress",
                "pipe:1",
                "-i",
                files[0],
                "-c",
                "copy",
                "-threads",
                f"{max(1, cpu_no // 2)}",
                output_file,
            ]
            return cmd, output_file
    else:
        return None, None

    # Get optimal thread count based on system load if dynamic threading is enabled
    thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

    cmd = [
        "xtra",
        "-hide_banner",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        *input_args,
        "-ignore_unknown",
        "-filter_complex",
        filter_complex,
        *map_args,
        "-threads",
        f"{thread_count}",
        output_file,
    ]

    return cmd, output_file


async def get_merge_mixed_cmd(
    video_files,
    audio_files,
    subtitle_files,
    output_format="mkv",
    # codec_groups parameter removed - will be added back when implemented
):
    import os
    from bot.helper.ext_utils.resource_manager import get_optimal_thread_count

    """Generate FFmpeg command for merging mixed media types.

    Args:
        video_files: List of video file paths
        audio_files: List of audio file paths
        subtitle_files: List of subtitle file paths
        output_format: Output file format (default: mkv)

    Returns:
        tuple: FFmpeg command and output file path
    """
    # Note: codec_groups parameter is reserved for future use to optimize codec selection
    if not video_files and not audio_files:
        return None, None

    # Use files in the order they were provided
    # (No sorting to preserve user's intended order)
    video_files = video_files if video_files else []
    audio_files = audio_files if audio_files else []
    subtitle_files = subtitle_files if subtitle_files else []

    # Determine output path based on first available file and media types
    base_files = video_files or audio_files or subtitle_files
    base_dir = os.path.dirname(base_files[0])

    # Determine appropriate output file name based on media types
    if video_files:
        output_file = os.path.join(base_dir, f"merged_video.{output_format}")
    elif audio_files:
        output_file = os.path.join(base_dir, f"merged_audio.{output_format}")
    elif subtitle_files:
        output_file = os.path.join(base_dir, f"merged_subtitle.{output_format}")
    else:
        output_file = os.path.join(base_dir, f"merged.{output_format}")

    # For mixed media types, we have several approaches:
    # 1. If we have multiple video files, merge them first, then add audio and subtitles
    # 2. If we have one video file and multiple audio files, use the video as base and add all audio tracks
    # 3. If we have multiple audio files only, merge them using filter_complex

    # Approach 1: Multiple video files with or without audio/subtitles
    if len(video_files) > 1:
        # First, merge all video files using concat demuxer
        # Create a temporary file list for concat demuxer
        concat_list_path = "concat_list.txt"
        with open(concat_list_path, "w") as f:
            for file_path in video_files:
                # Escape single quotes in file paths
                escaped_path = file_path.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        # Create a temporary merged video file
        temp_video_output = os.path.join(base_dir, f"temp_merged_video.{output_format}")
        video_cmd = [
            "xtra",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_path,
            "-map",
            "0",  # Map all streams from input to preserve all video and audio tracks
            "-c",
            "copy",
            "-metadata",
            "title=Merged Video",
            "-threads",
            f"{max(1, cpu_no // 2)}",
            temp_video_output,
        ]

        # If we have audio files, add them to the merged video
        if audio_files:
            # Build input arguments
            input_args = ["-i", temp_video_output]  # Merged video as first input
            map_args = [
                "-map",
                "0",
            ]  # Map all streams from merged video to preserve all tracks

            # Add audio files
            for i, audio_file in enumerate(audio_files):
                input_args.extend(["-i", audio_file])
                map_args.extend(
                    [
                        "-map",
                        f"{i + 1}:a:0",
                        f"-metadata:s:a:{i}",
                        f"title=Audio Track {i + 1}",
                    ]
                )

            # Add subtitle files if supported by the output format
            if subtitle_files and output_format in ["mkv", "mp4"]:
                for i, sub_file in enumerate(subtitle_files):
                    input_args.extend(["-i", sub_file])
                    map_args.extend(
                        [
                            "-map",
                            f"{i + 1 + len(audio_files)}:s?",
                            f"-metadata:s:s:{i}",
                            f"title=Subtitle Track {i + 1}",
                        ]
                    )

            # Get optimal thread count based on system load if dynamic threading is enabled
            thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

            # Create final command
            cmd = [
                "xtra",
                "-hide_banner",
                "-loglevel",
                "error",
                "-progress",
                "pipe:1",
                *input_args,
                "-ignore_unknown",
                *map_args,  # Map all streams including video, audio, and subtitle streams
                "-c",
                "copy",
                "-threads",
                f"{thread_count}",
                output_file,
            ]

            return cmd, output_file
        else:
            # Just return the merged video command
            return video_cmd, temp_video_output

    # Approach 2: Single video file with multiple audio/subtitle tracks
    elif len(video_files) == 1:
        # Use the video file as the base
        video_base = video_files[0]

        # Get video stream info
        video_streams = await get_streams(video_base)
        if not video_streams:
            return None, None

        # Log video stream info for debugging
        LOGGER.info(f"Using video file as base: {video_base}")
        video_info = {}
        for stream in video_streams:
            if stream.get("codec_type") == "video":
                video_info["codec"] = stream.get("codec_name")
                video_info["width"] = stream.get("width")
                video_info["height"] = stream.get("height")
                video_info["duration"] = stream.get("duration")
                break
        LOGGER.info(f"Video base info: {video_info}")

        # Build input arguments
        input_args = ["-i", video_base]
        map_args = [
            "-map",
            "0",
        ]  # Map all streams from the video file to preserve all tracks

        # Count audio tracks in video file for metadata
        audio_tracks_in_video = 0
        for stream in video_streams:
            if stream.get("codec_type") == "audio":
                audio_tracks_in_video += 1

        has_audio_in_video = audio_tracks_in_video > 0

        # Add external audio files
        audio_track_num = 1 if has_audio_in_video else 0
        for i, audio_file in enumerate(audio_files):
            input_args.extend(["-i", audio_file])
            map_args.extend(
                [
                    "-map",
                    f"{i + 1}:a:0",
                    f"-metadata:s:a:{audio_track_num}",
                    f"title=External Audio {i + 1}",
                ]
            )
            audio_track_num += 1

        # Add subtitle files if supported by the output format
        if subtitle_files and output_format in ["mkv", "mp4"]:
            sub_offset = len(audio_files) + 1
            for i, sub_file in enumerate(subtitle_files):
                # Get subtitle format
                sub_format = os.path.splitext(sub_file)[1].lower()

                # Handle subtitles differently based on format
                if sub_format in [".srt", ".vtt", ".ass", ".ssa"]:
                    # For text-based subtitles, we need to handle them specially to fix duration issues
                    # First, get video duration
                    video_duration = None
                    video_streams = await get_streams(video_base)
                    if video_streams:
                        for stream in video_streams:
                            if stream.get("codec_type") == "video":
                                # Try to get duration from stream or format info
                                try:
                                    import json
                                    import subprocess

                                    cmd = [
                                        "ffprobe",
                                        "-v",
                                        "error",
                                        "-show_entries",
                                        "format=duration",
                                        "-of",
                                        "json",
                                        video_base,
                                    ]
                                    result = subprocess.run(
                                        cmd, capture_output=True, text=True
                                    )
                                    if result.returncode == 0:
                                        data = json.loads(result.stdout)
                                        if (
                                            "format" in data
                                            and "duration" in data["format"]
                                        ):
                                            video_duration = float(
                                                data["format"]["duration"]
                                            )
                                except Exception as e:
                                    LOGGER.warning(f"Error getting video duration: {e}")

                    # If we have video duration, create a temporary subtitle file with correct duration
                    if video_duration:
                        LOGGER.info(
                            f"Using video duration {video_duration} for subtitle"
                        )
                        # Create a temporary subtitle file with adjusted timestamps
                        try:
                            import tempfile
                            import re
                            import os

                            # Create a temporary file for the adjusted subtitle
                            temp_sub_file = tempfile.NamedTemporaryFile(
                                suffix=".srt", delete=False
                            )
                            temp_sub_path = temp_sub_file.name
                            temp_sub_file.close()

                            # Read the original subtitle file
                            with open(sub_file, "r", encoding="utf-8") as f:
                                content = f.read()

                            # Find the last timestamp in the subtitle file
                            last_timestamp_match = re.findall(
                                r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
                                content,
                            )
                            if last_timestamp_match:
                                # Get the last end timestamp
                                last_end_time = last_timestamp_match[-1][1]

                                # Convert timestamp to seconds
                                h, m, s = last_end_time.split(":")[0:3]
                                s, ms = s.split(",")
                                last_time_seconds = (
                                    int(h) * 3600
                                    + int(m) * 60
                                    + int(s)
                                    + int(ms) / 1000
                                )

                                # If the last subtitle timestamp is beyond video duration or too short, adjust all timestamps
                                if (
                                    last_time_seconds > video_duration
                                    or last_time_seconds < (video_duration * 0.5)
                                ):
                                    # If subtitle is too short, extend it. If too long, compress it.
                                    scale_factor = video_duration / last_time_seconds
                                    LOGGER.info(
                                        f"Adjusting subtitle timing with scale factor {scale_factor:.2f} (subtitle duration: {last_time_seconds:.2f}s, video duration: {video_duration:.2f}s)"
                                    )

                                    # Function to adjust timestamp
                                    def adjust_timestamp(timestamp, scale):
                                        h, m, s = timestamp.split(":")[0:3]
                                        s, ms = s.split(",")
                                        total_seconds = (
                                            int(h) * 3600
                                            + int(m) * 60
                                            + int(s)
                                            + int(ms) / 1000
                                        ) * scale

                                        new_h = int(total_seconds // 3600)
                                        new_m = int((total_seconds % 3600) // 60)
                                        new_s = int(total_seconds % 60)
                                        new_ms = int((total_seconds * 1000) % 1000)

                                        return f"{new_h:02d}:{new_m:02d}:{new_s:02d},{new_ms:03d}"

                                    # Adjust all timestamps in the subtitle file
                                    adjusted_content = re.sub(
                                        r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
                                        lambda m: f"{adjust_timestamp(m.group(1), scale_factor)} --> {adjust_timestamp(m.group(2), scale_factor)}",
                                        content,
                                    )

                                    # Write the adjusted subtitle to the temporary file
                                    with open(
                                        temp_sub_path, "w", encoding="utf-8"
                                    ) as f:
                                        f.write(adjusted_content)

                                    # Use the temporary subtitle file instead
                                    sub_file = temp_sub_path
                                    LOGGER.info(
                                        f"Created adjusted subtitle file with scale factor {scale_factor}"
                                    )
                        except Exception as e:
                            LOGGER.warning(f"Error adjusting subtitle timestamps: {e}")

                        # Add input with the adjusted subtitle file
                        input_args.extend(["-i", sub_file])
                        map_args.extend(
                            [
                                "-map",
                                f"{sub_offset + i}:s?",
                                f"-metadata:s:s:{i}",
                                f"title=External Subtitle {i + 1}",
                                # Force subtitle duration to match video
                                "-c:s",
                                "copy",
                            ]
                        )
                    else:
                        # Fallback to standard mapping
                        input_args.extend(["-i", sub_file])
                        map_args.extend(
                            [
                                "-map",
                                f"{sub_offset + i}:s?",
                                f"-metadata:s:s:{i}",
                                f"title=External Subtitle {i + 1}",
                                "-c:s",
                                "copy",
                            ]
                        )
                else:
                    # For other subtitle formats, use standard mapping
                    input_args.extend(["-i", sub_file])
                    map_args.extend(
                        [
                            "-map",
                            f"{sub_offset + i}:s?",
                            f"-metadata:s:s:{i}",
                            f"title=External Subtitle {i + 1}",
                        ]
                    )

        # Get optimal thread count based on system load if dynamic threading is enabled
        thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

        # Create final command
        cmd = [
            "xtra",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            *input_args,
            "-ignore_unknown",
            *map_args,  # Map all streams including video, audio, and subtitle streams
            "-c",
            "copy",
            "-threads",
            f"{thread_count}",
            output_file,
        ]

        return cmd, output_file

    # Approach 3: Audio files only
    elif audio_files:
        # For audio-only merge, use filter_complex
        filter_complex = ""
        for i, _ in enumerate(audio_files):
            filter_complex += f"[{i}:a:0]"
        filter_complex += f"concat=n={len(audio_files)}:v=0:a=1[outa]"

        # Build input arguments
        input_args = []
        for file_path in audio_files:
            input_args.extend(["-i", file_path])

        # Set audio codec based on output format
        codec_args = []
        if output_format == "mp3":
            codec_args = ["-c:a", "libmp3lame", "-q:a", "0"]
        elif output_format == "aac" or output_format == "m4a":
            codec_args = ["-c:a", "aac", "-b:a", "320k"]
        elif output_format == "flac":
            codec_args = ["-c:a", "flac"]
        elif output_format == "opus":
            codec_args = ["-c:a", "libopus", "-b:a", "256k"]
        else:
            # Default to AAC for other formats
            codec_args = ["-c:a", "aac", "-b:a", "320k"]

        # Get optimal thread count based on system load if dynamic threading is enabled
        thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

        cmd = [
            "xtra",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            *input_args,
            "-filter_complex",
            filter_complex,
            "-map",
            "[outa]",
            *codec_args,
            "-threads",
            f"{thread_count}",
            output_file,
        ]

        return cmd, output_file

    # Fallback to a simpler approach if needed
    # This approach works for a single video file with a single audio file and optional subtitle
    if len(video_files) == 1 and len(audio_files) <= 1:
        # Build input arguments
        input_args = ["-i", video_files[0]]  # Video file
        map_args = [
            "-map",
            "0",
        ]  # Map all streams from video file to preserve all tracks

        # Add external audio file if available
        if audio_files:
            input_args.extend(["-i", audio_files[0]])
            map_args.extend(
                ["-map", "1:a:0", "-metadata:s:a:0", "title=External Audio"]
            )

        # Add subtitle file if available and supported by the output format
        if subtitle_files and output_format in ["mkv", "mp4"]:
            sub_file = subtitle_files[0]
            # Get subtitle format
            sub_format = os.path.splitext(sub_file)[1].lower()

            # Handle subtitles differently based on format
            if sub_format in [".srt", ".vtt", ".ass", ".ssa"]:
                # For text-based subtitles, we need to handle them specially to fix duration issues
                # First, get video duration
                video_duration = None
                video_streams = await get_streams(video_files[0])
                if video_streams:
                    try:
                        import json
                        import subprocess

                        cmd = [
                            "ffprobe",
                            "-v",
                            "error",
                            "-show_entries",
                            "format=duration",
                            "-of",
                            "json",
                            video_files[0],
                        ]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            data = json.loads(result.stdout)
                            if "format" in data and "duration" in data["format"]:
                                video_duration = float(data["format"]["duration"])
                                LOGGER.info(
                                    f"Using video duration {video_duration} for subtitle"
                                )
                    except Exception as e:
                        LOGGER.warning(f"Error getting video duration: {e}")

                # Create a temporary subtitle file with adjusted timestamps
                try:
                    # Read the original subtitle file
                    with open(sub_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Find the last timestamp in the subtitle file
                    last_timestamp_match = re.findall(
                        r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
                        content,
                    )
                    if last_timestamp_match:
                        # Get the last end timestamp
                        last_end_time = last_timestamp_match[-1][1]

                        # Convert timestamp to seconds
                        h, m, s = last_end_time.split(":")[0:3]
                        s, ms = s.split(",")
                        last_time_seconds = (
                            int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
                        )

                        # If the last subtitle timestamp is beyond video duration, adjust all timestamps
                        if last_time_seconds > video_duration:
                            scale_factor = video_duration / last_time_seconds

                            # Function to adjust timestamp
                            def adjust_timestamp(timestamp, scale):
                                h, m, s = timestamp.split(":")[0:3]
                                s, ms = s.split(",")
                                total_seconds = (
                                    int(h) * 3600
                                    + int(m) * 60
                                    + int(s)
                                    + int(ms) / 1000
                                ) * scale

                                new_h = int(total_seconds // 3600)
                                new_m = int((total_seconds % 3600) // 60)
                                new_s = int(total_seconds % 60)
                                new_ms = int((total_seconds * 1000) % 1000)

                                return (
                                    f"{new_h:02d}:{new_m:02d}:{new_s:02d},{new_ms:03d}"
                                )

                            # Adjust all timestamps in the subtitle file
                            adjusted_content = re.sub(
                                r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
                                lambda m: f"{adjust_timestamp(m.group(1), scale_factor)} --> {adjust_timestamp(m.group(2), scale_factor)}",
                                content,
                            )

                            # Create a temporary file for the adjusted subtitle
                            temp_sub_file = tempfile.NamedTemporaryFile(
                                suffix=".srt", delete=False
                            )
                            temp_sub_path = temp_sub_file.name
                            temp_sub_file.close()

                            # Write the adjusted subtitle to the temporary file
                            with open(temp_sub_path, "w", encoding="utf-8") as f:
                                f.write(adjusted_content)

                            # Use the temporary subtitle file instead
                            sub_file = temp_sub_path
                            LOGGER.info(
                                f"Created adjusted subtitle file with scale factor {scale_factor}"
                            )
                except Exception as e:
                    LOGGER.warning(f"Error adjusting subtitle timestamps: {e}")

                # Add input with the adjusted subtitle file
                input_args.extend(["-i", sub_file])

                # Map subtitle with appropriate options
                map_args.extend(
                    [
                        "-map",
                        f"{1 + (1 if audio_files else 0)}:s?",
                        "-metadata:s:s:0",
                        "title=External Subtitle",
                        # Force subtitle duration to match video
                        "-c:s",
                        "copy",
                    ]
                )
            else:
                # For other subtitle formats, use standard mapping
                input_args.extend(["-i", sub_file])
                map_args.extend(
                    [
                        "-map",
                        f"{1 + (1 if audio_files else 0)}:s?",
                        "-metadata:s:s:0",
                        "title=External Subtitle",
                    ]
                )

        cmd = [
            "xtra",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            *input_args,
            *map_args,
            "-c",
            "copy",
            "-threads",
            f"{max(1, cpu_no // 2)}",
            output_file,
        ]

        return cmd, output_file

    # If all else fails, use a very simple approach
    # Just use the first video file and preserve all its tracks
    if video_files:
        cmd = [
            "xtra",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-i",
            video_files[0],
            "-map",
            "0",  # Map all streams to preserve all video, audio, and subtitle tracks
            "-c",
            "copy",
            "-threads",
            f"{max(1, cpu_no // 2)}",
            output_file,
        ]
        return cmd, output_file

    # If no video files, use the first audio file and preserve all its tracks
    if audio_files:
        cmd = [
            "xtra",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-i",
            audio_files[0],
            "-map",
            "0",  # Map all streams to preserve all audio tracks
            "-c",
            "copy",
            "-threads",
            f"{max(1, cpu_no // 2)}",
            output_file,
        ]
        return cmd, output_file

    return None, None


async def analyze_media_for_merge(files):
    """Analyze media files and categorize them for merging.

    Args:
        files: List of file paths

    Returns:
        dict: Dictionary with categorized files and recommended merge approach
    """
    video_files = []
    audio_files = []
    subtitle_files = []
    image_files = []
    document_files = []
    unknown_files = []

    # Detailed media info for advanced analysis
    video_info = []
    audio_info = []
    subtitle_info = []
    image_info = []
    document_info = []

    # Categorize files by media type with detailed info
    for file_path in files:
        # Check file extension first for faster categorization
        ext = os.path.splitext(file_path)[1].lower()

        # Categorize images by extension
        if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"]:
            image_files.append(file_path)
            image_info.append(
                {
                    "path": file_path,
                    "format": ext[1:],  # Remove the dot
                    "size": os.path.getsize(file_path),
                }
            )
            continue

        # Categorize documents by extension
        if ext in [".pdf", ".doc", ".docx", ".odt", ".txt", ".rtf"]:
            document_files.append(file_path)
            document_info.append(
                {
                    "path": file_path,
                    "format": ext[1:],  # Remove the dot
                    "size": os.path.getsize(file_path),
                }
            )
            continue

        # For other files, use FFprobe to determine media type
        media_type = await get_media_type(file_path)
        if media_type == "video":
            video_files.append(file_path)
            # Get detailed video info
            streams = await get_streams(file_path)
            if streams:
                video_info.append(
                    {
                        "path": file_path,
                        "streams": streams,
                        "format": os.path.splitext(file_path)[1][1:].lower(),
                        "size": os.path.getsize(file_path),
                    }
                )
        elif media_type == "audio":
            audio_files.append(file_path)
            # Get detailed audio info
            streams = await get_streams(file_path)
            if streams:
                audio_info.append(
                    {
                        "path": file_path,
                        "streams": streams,
                        "format": os.path.splitext(file_path)[1][1:].lower(),
                        "size": os.path.getsize(file_path),
                    }
                )
        elif media_type == "subtitle":
            subtitle_files.append(file_path)
            # Get subtitle format
            subtitle_info.append(
                {
                    "path": file_path,
                    "format": os.path.splitext(file_path)[1][1:].lower(),
                    "size": os.path.getsize(file_path),
                }
            )
        else:
            unknown_files.append(file_path)

    # Check for codec compatibility in video files
    video_codec_groups = {}
    video_resolution_groups = {}

    for info in video_info:
        video_codec = None
        audio_codec = None
        width = None
        height = None

        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video" and not stream.get(
                "disposition", {}
            ).get("attached_pic"):
                video_codec = stream.get("codec_name")
                width = stream.get("width")
                height = stream.get("height")
            elif stream.get("codec_type") == "audio":
                audio_codec = stream.get("codec_name")

        # Group by video codec for better merge strategy
        codec_key = f"{video_codec}_{audio_codec}"
        if codec_key not in video_codec_groups:
            video_codec_groups[codec_key] = []
        video_codec_groups[codec_key].append(info["path"])

        # Group by resolution for better scaling decisions
        if width and height:
            resolution_key = f"{width}x{height}"
            if resolution_key not in video_resolution_groups:
                video_resolution_groups[resolution_key] = []
            video_resolution_groups[resolution_key].append(info["path"])

    # Check for codec compatibility in audio files
    audio_codec_groups = {}
    for info in audio_info:
        audio_codec = None
        # Note: We collect these properties for future enhancements
        # sample_rate and channels could be used for advanced audio merging

        for stream in info.get("streams", []):
            if stream.get("codec_type") == "audio":
                audio_codec = stream.get("codec_name")
                # These properties are collected but not used yet
                # sample_rate = stream.get("sample_rate")
                # channels = stream.get("channels")
                break

        # Group by audio codec and properties for better merge strategy
        codec_key = audio_codec or "unknown"
        if codec_key not in audio_codec_groups:
            audio_codec_groups[codec_key] = []
        audio_codec_groups[codec_key].append(info["path"])

    # Group subtitle files by format
    subtitle_format_groups = {}
    for info in subtitle_info:
        subtitle_format = info["format"]
        if subtitle_format not in subtitle_format_groups:
            subtitle_format_groups[subtitle_format] = []
        subtitle_format_groups[subtitle_format].append(info["path"])

    # Group image files by format
    image_format_groups = {}
    for info in image_info:
        image_format = info["format"]
        if image_format not in image_format_groups:
            image_format_groups[image_format] = []
        image_format_groups[image_format].append(info["path"])

    # Group document files by format
    document_format_groups = {}
    for info in document_info:
        document_format = info["format"]
        if document_format not in document_format_groups:
            document_format_groups[document_format] = []
        document_format_groups[document_format].append(info["path"])

    # Determine recommended merge approach based on detailed analysis
    total_media_files = (
        len(video_files)
        + len(audio_files)
        + len(subtitle_files)
        + len(image_files)
        + len(document_files)
    )

    if total_media_files == 0:
        recommended_approach = None
        LOGGER.info("No media files found for merging")
    elif (
        len(video_files) > 0
        and len(audio_files) == 0
        and len(subtitle_files) == 0
        and len(image_files) == 0
        and len(document_files) == 0
    ):
        # All videos - check if we can use concat demuxer (same codec and resolution)
        if len(video_codec_groups) == 1 and len(video_resolution_groups) == 1:
            # All videos have same codec and resolution - can use concat demuxer
            recommended_approach = "concat_demuxer"
            LOGGER.info(
                "All videos have same codec and resolution - using concat demuxer"
            )
        elif len(video_resolution_groups) > 1:
            # Different resolutions - need to use filter_complex with scaling
            recommended_approach = "filter_complex"
            LOGGER.info(
                "Videos have different resolutions - using filter_complex with scaling"
            )
        else:
            # Different codecs but same resolution - can try concat demuxer with transcoding
            recommended_approach = "concat_demuxer"
            LOGGER.info(
                "Videos have different codecs but same resolution - using concat demuxer with transcoding"
            )
    elif (
        len(audio_files) > 0
        and len(video_files) == 0
        and len(subtitle_files) == 0
        and len(image_files) == 0
        and len(document_files) == 0
    ):
        # All audios - check if we can use concat demuxer (same codec)
        if len(audio_codec_groups) == 1:
            # All audios have same codec - can use concat demuxer
            recommended_approach = "concat_demuxer"
            LOGGER.info("All audio files have same codec - using concat demuxer")
        else:
            # Different codecs - need to use filter_complex
            recommended_approach = "filter_complex"
            LOGGER.info("Audio files have different codecs - using filter_complex")
    elif (
        len(subtitle_files) > 0
        and len(video_files) == 0
        and len(audio_files) == 0
        and len(image_files) == 0
        and len(document_files) == 0
    ):
        # All subtitles - check if we can use concat demuxer (same format)
        if len(subtitle_format_groups) == 1:
            # All subtitles have same format - can use concat demuxer
            recommended_approach = "concat_demuxer"
            LOGGER.info("All subtitle files have same format - using concat demuxer")
        else:
            # Different formats - need special handling
            recommended_approach = "subtitle_special"
            LOGGER.info(
                "Subtitle files have different formats - using special handling"
            )
    elif (
        len(image_files) > 0
        and len(video_files) == 0
        and len(audio_files) == 0
        and len(subtitle_files) == 0
        and len(document_files) == 0
    ):
        # All images - use PIL for merging
        recommended_approach = "image_merge"
        LOGGER.info("Found image files - using PIL for merging")
    elif (
        len(document_files) > 0
        and len(video_files) == 0
        and len(audio_files) == 0
        and len(subtitle_files) == 0
        and len(image_files) == 0
    ):
        # All documents - use PDF merging
        recommended_approach = "document_merge"
        LOGGER.info("Found document files - using PDF merging")
    else:
        # Mixed media types - need to use filter_complex or mixed approach
        if len(video_files) > 0 and (len(audio_files) > 0 or len(subtitle_files) > 0):
            recommended_approach = "mixed"
            LOGGER.info(
                "Found mixed media types (video, audio, subtitles) - using mixed approach"
            )
        elif len(video_files) > 0 and len(image_files) > 0:
            # Video and images - can create a slideshow
            recommended_approach = "slideshow"
            LOGGER.info("Found video and image files - can create a slideshow")
        else:
            # Other combinations - use separate merges
            recommended_approach = "separate"
            LOGGER.info(
                "Found incompatible media types - will merge separately by type"
            )

    return {
        "video_files": video_files,
        "audio_files": audio_files,
        "subtitle_files": subtitle_files,
        "image_files": image_files,
        "document_files": document_files,
        "unknown_files": unknown_files,
        "video_codec_groups": video_codec_groups,
        "video_resolution_groups": video_resolution_groups,
        "audio_codec_groups": audio_codec_groups,
        "subtitle_format_groups": subtitle_format_groups,
        "image_format_groups": image_format_groups,
        "document_format_groups": document_format_groups,
        "recommended_approach": recommended_approach,
    }

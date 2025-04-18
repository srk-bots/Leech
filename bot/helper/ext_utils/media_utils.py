import contextlib
import resource
from asyncio import create_subprocess_exec, gather, sleep, wait_for
from asyncio.subprocess import PIPE
from os import path as ospath
from re import escape
from re import search as re_search
from time import time

from aiofiles.os import makedirs, remove
from aiofiles.os import path as aiopath
from aioshutil import rmtree
from PIL import Image

from bot import DOWNLOAD_DIR, LOGGER, cpu_no
from bot.core.config_manager import Config

from .bot_utils import cmd_exec, sync_to_async
from .files_utils import get_mime_type, is_archive, is_archive_split
from .status_utils import time_to_seconds


# Function to limit memory usage for PIL operations
def limit_memory_for_pil():
    """Apply memory limits for PIL operations based on config."""
    try:
        # Get memory limit from config
        memory_limit = Config.FFMPEG_MEMORY_LIMIT

        if memory_limit > 0:
            # Convert MB to bytes for resource limit
            memory_limit_bytes = memory_limit * 1024 * 1024

            # Set soft limit (warning) and hard limit (error)
            resource.setrlimit(
                resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes)
            )
            LOGGER.debug(
                f"Applied memory limit of {memory_limit} MB for image processing"
            )

        return True
    except Exception as e:
        LOGGER.error(f"Error setting memory limit for PIL: {e}")
        return False


async def create_thumb(msg, _id=""):
    if not _id:
        _id = time()
        path = f"{DOWNLOAD_DIR}thumbnails"
    else:
        path = "thumbnails"
    await makedirs(path, exist_ok=True)
    photo_dir = await msg.download()
    output = ospath.join(path, f"{_id}.jpg")

    # Apply memory limits for PIL operations
    limit_memory_for_pil()

    # Process the image with memory limits applied
    await sync_to_async(Image.open(photo_dir).convert("RGB").save, output, "JPEG")
    await remove(photo_dir)
    return output


async def get_media_info(path):
    try:
        result = await cmd_exec(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-print_format",
                "json",
                "-show_format",
                path,
            ],
        )
    except Exception as e:
        LOGGER.error(f"Get Media Info: {e}. Mostly File not found! - File: {path}")
        return 0, None, None
    if result[0] and result[2] == 0:
        fields = eval(result[0]).get("format")
        if fields is None:
            LOGGER.error(f"get_media_info: {result}")
            return 0, None, None
        duration = round(float(fields.get("duration", 0)))
        tags = fields.get("tags", {})
        artist = tags.get("artist") or tags.get("ARTIST") or tags.get("Artist")
        title = tags.get("title") or tags.get("TITLE") or tags.get("Title")
        return duration, artist, title
    return 0, None, None


async def get_document_type(path):
    is_video, is_audio, is_image = False, False, False
    if (
        is_archive(path)
        or is_archive_split(path)
        or re_search(r".+(\.|_)(rar|7z|zip|bin)(\.0*\d+)?$", path)
    ):
        return is_video, is_audio, is_image
    mime_type = await get_mime_type(path)
    if mime_type.startswith("image"):
        return False, False, True
    try:
        result = await cmd_exec(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                path,
            ],
        )
        if result[1] and mime_type.startswith("video"):
            is_video = True
    except Exception as e:
        LOGGER.error(
            f"Get Document Type: {e}. Mostly File not found! - File: {path}",
        )
        if mime_type.startswith("audio"):
            return False, True, False
        if not mime_type.startswith("video") and not mime_type.endswith(
            "octet-stream",
        ):
            return is_video, is_audio, is_image
        if mime_type.startswith("video"):
            is_video = True
        return is_video, is_audio, is_image
    if result[0] and result[2] == 0:
        fields = eval(result[0]).get("streams")
        if fields is None:
            LOGGER.error(f"get_document_type: {result}")
            return is_video, is_audio, is_image
        is_video = False
        for stream in fields:
            if stream.get("codec_type") == "video":
                is_video = True
            elif stream.get("codec_type") == "audio":
                is_audio = True
    return is_video, is_audio, is_image


async def take_ss(video_file, ss_nb) -> bool:
    duration = (await get_media_info(video_file))[0]
    if duration != 0:
        dirpath, name = video_file.rsplit("/", 1)
        name, _ = ospath.splitext(name)
        dirpath = f"{dirpath}/{name}_ss"
        await makedirs(dirpath, exist_ok=True)
        interval = duration // (ss_nb + 1)
        cap_time = interval
        cmds = []
        for i in range(ss_nb):
            output = f"{dirpath}/SS.{name}_{i:02}.png"
            from .resource_manager import get_optimal_thread_count

            # Get optimal thread count based on system load if dynamic threading is enabled
            thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

            cmd = [
                "xtra",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{cap_time}",
                "-i",
                video_file,
                "-ignore_unknown",
                "-q:v",
                "1",
                "-frames:v",
                "1",
                "-threads",
                f"{thread_count}",
                output,
            ]
            cap_time += interval
            cmds.append(cmd_exec(cmd))
        try:
            resutls = await wait_for(gather(*cmds), timeout=60)
            if resutls[0][2] != 0:
                LOGGER.error(
                    f"Error while creating sreenshots from video. Path: {video_file}. stderr: {resutls[0][1]}",
                )
                await rmtree(dirpath, ignore_errors=True)
                return False
        except Exception:
            LOGGER.error(
                f"Error while creating sreenshots from video. Path: {video_file}. Error: Timeout some issues with ffmpeg with specific arch!",
            )
            await rmtree(dirpath, ignore_errors=True)
            return False
        return dirpath
    LOGGER.error("take_ss: Can't get the duration of video")
    return False


async def get_audio_thumbnail(audio_file, user_id=None):
    output_dir = f"{DOWNLOAD_DIR}thumbnails"
    await makedirs(output_dir, exist_ok=True)
    output = ospath.join(output_dir, f"{time()}.jpg")

    # We'll check for user and owner thumbnails when needed

    # Create default thumbnail as last resort
    default_thumb = await create_default_audio_thumbnail(output_dir, user_id)

    # Check if the file exists and is accessible
    if not await aiopath.exists(audio_file):
        LOGGER.debug(f"Audio file not found: {audio_file}. Using default thumbnail.")
        return default_thumb

    # Handle special characters in filenames by creating a symlink with a safe name
    safe_audio_file = audio_file
    temp_link_created = False

    # Check if filename contains special characters that might cause issues with FFmpeg
    if any(c in audio_file for c in ["\\", "|", ":", '"', "?", "*", "<", ">", "|"]):
        try:
            # Create a temporary symlink with a safe name
            safe_audio_file = ospath.join(
                ospath.dirname(audio_file),
                f"temp_{int(time())}{ospath.splitext(audio_file)[1]}",
            )
            import os

            os.symlink(audio_file, safe_audio_file)
            LOGGER.info(
                f"Created temporary symlink for file with special characters: {safe_audio_file}",
            )
        except Exception as e:
            LOGGER.warning(
                f"Failed to create symlink for file with special characters: {e}",
            )
            safe_audio_file = audio_file  # Fallback to original file

    # Get file extension to handle different audio formats
    file_ext = ospath.splitext(safe_audio_file)[1].lower()

    # First try to extract embedded cover art - method depends on file type
    if file_ext in [".mp3", ".flac", ".m4a"]:
        # Method 1: Extract embedded album art
        from .resource_manager import get_optimal_thread_count

        # Get optimal thread count based on system load if dynamic threading is enabled
        thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

        cmd = [
            "xtra",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            audio_file,
            "-ignore_unknown",
            "-an",
            "-vcodec",
            "copy",
            "-threads",
            f"{thread_count}",
            output,
        ]
    else:  # For .aac, .wav, etc.
        # Method 1: Alternative extraction for other formats
        # Reuse the thread count from above or get it if this is the first call
        if "thread_count" not in locals():
            from .resource_manager import get_optimal_thread_count

            thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

        cmd = [
            "xtra",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            audio_file,
            "-ignore_unknown",
            "-vf",
            "scale=320:320",
            "-frames:v",
            "1",
            "-threads",
            f"{thread_count}",
            output,
        ]

    try:
        _, err, code = await wait_for(cmd_exec(cmd), timeout=60)
        if code != 0 or not await aiopath.exists(output):
            # First method failed, try with a different approach
            LOGGER.debug(
                f"First thumbnail extraction method failed for audio: {audio_file}. Error: {err}. Trying alternative method.",
            )

            # Try to extract cover art using a different method
            # Reuse the thread count from above or get it if this is the first call
            if "thread_count" not in locals():
                from .resource_manager import get_optimal_thread_count

                thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

            cmd = [
                "xtra",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                audio_file,
                "-ignore_unknown",
                "-map",
                "0:v",
                "-map",
                "-0:a",
                "-c",
                "copy",
                "-threads",
                f"{thread_count}",
                output,
            ]
            _, err, code = await wait_for(cmd_exec(cmd), timeout=60)

            if code != 0 or not await aiopath.exists(output):
                # Try a third method for specific formats
                LOGGER.debug(
                    f"Second thumbnail extraction method failed for audio: {audio_file}. Error: {err}. Trying third method.",
                )

                # Reuse the thread count from above or get it if this is the first call
                if "thread_count" not in locals():
                    from .resource_manager import get_optimal_thread_count

                    thread_count = await get_optimal_thread_count() or max(
                        1, cpu_no // 2
                    )

                cmd = [
                    "xtra",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    audio_file,
                    "-ignore_unknown",
                    "-f",
                    "image2",
                    "-frames:v",
                    "1",
                    "-threads",
                    f"{thread_count}",
                    output,
                ]
                _, err, code = await wait_for(cmd_exec(cmd), timeout=60)

                if code != 0 or not await aiopath.exists(output):
                    # All extraction methods failed, try user thumbnail, then owner thumbnail, then default
                    LOGGER.debug(
                        f"All thumbnail extraction methods failed for audio: {audio_file}. Error: {err}. Trying user/owner thumbnails.",
                    )

                    # Try user thumbnail first if available
                    if user_id and await aiopath.exists(f"thumbnails/{user_id}.jpg"):
                        LOGGER.debug(f"Using user thumbnail for audio: {audio_file}")
                        result = f"thumbnails/{user_id}.jpg"
                    # Then try owner thumbnail
                    elif await aiopath.exists(f"thumbnails/{Config.OWNER_ID}.jpg"):
                        LOGGER.debug(f"Using owner thumbnail for audio: {audio_file}")
                        result = f"thumbnails/{Config.OWNER_ID}.jpg"
                    # Finally use default thumbnail
                    else:
                        LOGGER.debug(f"Using default thumbnail for audio: {audio_file}")
                        result = default_thumb

                    # Clean up temporary symlink if created
                    try:
                        if temp_link_created and await aiopath.exists(
                            safe_audio_file,
                        ):
                            await remove(safe_audio_file)
                            LOGGER.info(
                                f"Removed temporary symlink: {safe_audio_file}",
                            )
                    except Exception as e:
                        LOGGER.warning(f"Failed to remove temporary symlink: {e}")

                    return result
    except Exception as e:
        LOGGER.debug(
            f"Exception while extracting thumbnail from audio: {audio_file}. Error: {e!s}",
        )
        # Try user thumbnail first if available
        if user_id and await aiopath.exists(f"thumbnails/{user_id}.jpg"):
            LOGGER.debug(
                f"Using user thumbnail for audio after exception: {audio_file}"
            )
            result = f"thumbnails/{user_id}.jpg"
        # Then try owner thumbnail
        elif await aiopath.exists(f"thumbnails/{Config.OWNER_ID}.jpg"):
            LOGGER.debug(
                f"Using owner thumbnail for audio after exception: {audio_file}"
            )
            result = f"thumbnails/{Config.OWNER_ID}.jpg"
        # Finally use default thumbnail
        else:
            LOGGER.debug(
                f"Using default thumbnail for audio after exception: {audio_file}"
            )
            result = default_thumb
    else:
        result = output

    # Clean up temporary symlink if created
    try:
        if temp_link_created and await aiopath.exists(safe_audio_file):
            await remove(safe_audio_file)
            LOGGER.info(f"Removed temporary symlink: {safe_audio_file}")
    except Exception as e:
        LOGGER.warning(f"Failed to remove temporary symlink: {e}")

    return result


async def create_default_audio_thumbnail(output_dir, user_id=None):
    # Try user thumbnail first if available
    if user_id and await aiopath.exists(f"thumbnails/{user_id}.jpg"):
        LOGGER.debug("Using user thumbnail for audio file")
        return f"thumbnails/{user_id}.jpg"
    # Then try owner thumbnail
    elif await aiopath.exists(f"thumbnails/{Config.OWNER_ID}.jpg"):
        LOGGER.debug("Using owner thumbnail for audio file")
        return f"thumbnails/{Config.OWNER_ID}.jpg"

    # Create a default audio thumbnail if no user/owner thumbnail
    default_thumb = ospath.join(output_dir, "default_audio.jpg")

    # First check if the default thumbnail already exists
    if await aiopath.exists(default_thumb):
        return default_thumb

    # Try to create the default thumbnail using FFmpeg
    try:
        # Make sure the output directory exists
        await makedirs(output_dir, exist_ok=True)

        # Create a simple default audio thumbnail
        cmd = [
            "xtra",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=320x320",
            "-ignore_unknown",
            "-frames:v",
            "1",
            default_thumb,
        ]

        # Generate a unique process ID for tracking
        process_id = f"ffmpeg_default_audio_{time()}"

        # Execute the command with resource limits
        _, err, code = await cmd_exec(
            cmd, apply_limits=True, process_id=process_id, task_type="Default Thumbnail"
        )

        if code != 0 or not await aiopath.exists(default_thumb):
            LOGGER.debug(f"Failed to create default audio thumbnail: {err}")
            # Try with a different approach
            cmd = [
                "xtra",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=320x320",
                "-ignore_unknown",
                "-y",  # Overwrite output file
                "-frames:v",
                "1",
                default_thumb,
            ]

            # Generate a unique process ID for tracking
            process_id = f"ffmpeg_default_audio_retry_{time()}"

            # Execute the command with resource limits
            _, err, code = await cmd_exec(
                cmd,
                apply_limits=True,
                process_id=process_id,
                task_type="Default Thumbnail",
            )

            if code != 0 or not await aiopath.exists(default_thumb):
                LOGGER.debug(
                    f"Failed to create default audio thumbnail with second method: {err}",
                )
                # As a last resort, try to create a simple image file directly
                try:
                    # Create a simple blue image (320x320 pixel) and save it
                    from PIL import Image

                    # Apply memory limits for PIL operations
                    limit_memory_for_pil()

                    img = Image.new("RGB", (320, 320), color=(0, 0, 255))
                    img.save(default_thumb)
                    LOGGER.debug("Created default audio thumbnail using PIL")
                except Exception as e:
                    LOGGER.debug(
                        f"Failed to create default audio thumbnail with PIL: {e}",
                    )
                    # Create an even simpler fallback image
                    try:
                        # Create a tiny blue image and save it
                        # Apply memory limits for PIL operations
                        limit_memory_for_pil()

                        img = Image.new("RGB", (32, 32), color=(0, 0, 255))
                        img.save(default_thumb)
                        LOGGER.debug("Created tiny default audio thumbnail using PIL")
                    except Exception as e2:
                        LOGGER.debug(f"All thumbnail creation methods failed: {e2}")
                        return None
    except Exception as e:
        LOGGER.debug(f"Error creating default audio thumbnail: {e}")
        return None

    # Final check to make sure the thumbnail exists
    if await aiopath.exists(default_thumb):
        return default_thumb
    return None


async def get_video_thumbnail(video_file, duration, user_id=None):
    output_dir = f"{DOWNLOAD_DIR}thumbnails"
    await makedirs(output_dir, exist_ok=True)
    output = ospath.join(output_dir, f"{time()}.jpg")

    # We'll check for user and owner thumbnails when needed

    # Check if the file exists and is accessible
    if not await aiopath.exists(video_file):
        LOGGER.error(f"Video file not found: {video_file}")
        # Try user thumbnail first if available
        if user_id and await aiopath.exists(f"thumbnails/{user_id}.jpg"):
            LOGGER.debug(f"Using user thumbnail for missing video: {video_file}")
            return f"thumbnails/{user_id}.jpg"
        # Then try owner thumbnail
        elif await aiopath.exists(f"thumbnails/{Config.OWNER_ID}.jpg"):
            LOGGER.debug(f"Using owner thumbnail for missing video: {video_file}")
            return f"thumbnails/{Config.OWNER_ID}.jpg"
        # Finally use default thumbnail
        else:
            return await create_default_text_thumbnail(output_dir)

    # Check if the file is a text file or other non-video format
    file_ext = ospath.splitext(video_file)[1].lower()
    text_extensions = [
        ".nfo",
        ".txt",
        ".srt",
        ".sub",
        ".idx",
        ".md",
        ".log",
        ".json",
        ".xml",
        ".html",
        ".htm",
        ".css",
        ".js",
    ]

    if file_ext in text_extensions:
        LOGGER.warning(f"Skipping thumbnail extraction for text file: {video_file}")
        return await create_default_text_thumbnail(output_dir, user_id)

    # Check if it's a binary file that's not a video
    try:
        mime_type = await get_mime_type(video_file)
        if not mime_type.startswith(("video/", "audio/", "image/")):
            LOGGER.warning(
                f"Skipping thumbnail extraction for non-media file: {video_file} (MIME: {mime_type})",
            )
            return await create_default_text_thumbnail(output_dir, user_id)
    except Exception as e:
        LOGGER.warning(
            f"Error checking MIME type: {e!s}. Continuing with thumbnail extraction.",
        )
        # Continue with thumbnail extraction instead of returning early

    if duration is None:
        duration = (await get_media_info(video_file))[0]
    if duration == 0:
        duration = 3
    duration = duration // 2

    from .resource_manager import get_optimal_thread_count

    # Get optimal thread count based on system load if dynamic threading is enabled
    thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

    # First try with basic parameters (no vf filter)
    cmd = [
        "xtra",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{duration}",
        "-i",
        video_file,
        "-ignore_unknown",
        "-q:v",
        "2",
        "-vframes",
        "1",
        "-threads",
        f"{thread_count}",
        output,
    ]
    try:
        _, err, code = await wait_for(cmd_exec(cmd), timeout=60)
        if code != 0 or not await aiopath.exists(output):
            # If first attempt fails, try with scale filter
            LOGGER.warning(
                f"First thumbnail attempt failed for {video_file}. Trying with scale filter. Error: {err}",
            )
            # Reuse the thread count from above
            cmd = [
                "xtra",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{duration}",
                "-i",
                video_file,
                "-ignore_unknown",
                "-vf",
                "scale=640:-1",
                "-q:v",
                "5",
                "-vframes",
                "1",
                "-threads",
                f"{thread_count}",
                output,
            ]
            _, err, code = await wait_for(cmd_exec(cmd), timeout=60)
            if code != 0 or not await aiopath.exists(output):
                # If both attempts fail, try with a third approach for problematic videos
                LOGGER.warning(
                    f"Second thumbnail attempt failed for {video_file}. Trying with simpler parameters.",
                )
                # Reuse the thread count from above
                cmd = [
                    "xtra",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{duration}",
                    "-i",
                    video_file,
                    "-frames:v",
                    "1",
                    "-f",
                    "mjpeg",
                    "-threads",
                    f"{thread_count}",
                    output,
                ]
                _, err, code = await wait_for(cmd_exec(cmd), timeout=60)
                if code != 0 or not await aiopath.exists(output):
                    LOGGER.error(
                        f"Error while extracting thumbnail from video. Name: {video_file} stderr: {err}",
                    )
                    # Check for special file formats that often cause issues
                    # Try user thumbnail first if available
                    if user_id and await aiopath.exists(f"thumbnails/{user_id}.jpg"):
                        LOGGER.debug(
                            f"Using user thumbnail for video with extraction failure: {video_file}"
                        )
                        return f"thumbnails/{user_id}.jpg"
                    # Then try owner thumbnail
                    elif await aiopath.exists(f"thumbnails/{Config.OWNER_ID}.jpg"):
                        LOGGER.debug(
                            f"Using owner thumbnail for video with extraction failure: {video_file}"
                        )
                        return f"thumbnails/{Config.OWNER_ID}.jpg"
                    # Finally use appropriate default thumbnail based on file type
                    else:
                        if file_ext.lower() in [".cr3", ".cr2", ".arw", ".nef", ".dng"]:
                            LOGGER.warning(
                                f"Detected camera RAW format {file_ext}. Using default image thumbnail."
                            )
                            return await create_default_image_thumbnail(
                                output_dir, user_id
                            )
                        elif file_ext.lower() in [
                            ".mp3",
                            ".m4a",
                            ".flac",
                            ".wav",
                            ".ogg",
                            ".opus",
                        ]:
                            return await create_default_audio_thumbnail(
                                output_dir, user_id
                            )
                        elif file_ext.lower() in [
                            ".mp4",
                            ".mkv",
                            ".avi",
                            ".mov",
                            ".webm",
                        ]:
                            return await create_default_video_thumbnail(
                                output_dir, user_id
                            )
                        else:
                            return await create_default_text_thumbnail(
                                output_dir, user_id
                            )
    except Exception as e:
        LOGGER.error(
            f"Error while extracting thumbnail from video. Name: {video_file}. Error: {e!s}",
        )
        # Try user thumbnail first if available
        if user_id and await aiopath.exists(f"thumbnails/{user_id}.jpg"):
            LOGGER.debug(
                f"Using user thumbnail for video after exception: {video_file}"
            )
            return f"thumbnails/{user_id}.jpg"
        # Then try owner thumbnail
        elif await aiopath.exists(f"thumbnails/{Config.OWNER_ID}.jpg"):
            LOGGER.debug(
                f"Using owner thumbnail for video after exception: {video_file}"
            )
            return f"thumbnails/{Config.OWNER_ID}.jpg"
        # Finally use default thumbnail
        else:
            return await create_default_text_thumbnail(output_dir, user_id)
    return output


async def create_default_text_thumbnail(output_dir, user_id=None):
    # Try user thumbnail first if available
    if user_id and await aiopath.exists(f"thumbnails/{user_id}.jpg"):
        LOGGER.debug("Using user thumbnail for text file")
        return f"thumbnails/{user_id}.jpg"
    # Then try owner thumbnail
    elif await aiopath.exists(f"thumbnails/{Config.OWNER_ID}.jpg"):
        LOGGER.debug("Using owner thumbnail for text file")
        return f"thumbnails/{Config.OWNER_ID}.jpg"

    # Create a default thumbnail for text files if no user/owner thumbnail
    default_thumb = ospath.join(output_dir, "default_text.jpg")
    if not await aiopath.exists(default_thumb):
        # Create a simple default text file thumbnail
        cmd = [
            "xtra",
            "-f",
            "lavfi",
            "-i",
            "color=c=gray:s=320x320",
            "-frames:v",
            "1",
            default_thumb,
        ]
        _, _, code = await cmd_exec(cmd)

        if code != 0 or not await aiopath.exists(default_thumb):
            # If FFmpeg fails, try with PIL
            try:
                # Apply memory limits for PIL operations
                limit_memory_for_pil()

                # Create a simple gray image
                img = Image.new("RGB", (320, 320), color=(128, 128, 128))
                img.save(default_thumb)
                LOGGER.debug("Created default text thumbnail using PIL")
            except Exception as e:
                LOGGER.debug(f"Failed to create default text thumbnail with PIL: {e}")
                return None

    if await aiopath.exists(default_thumb):
        return default_thumb
    return None


async def create_default_video_thumbnail(output_dir, user_id=None):
    # Try user thumbnail first if available
    if user_id and await aiopath.exists(f"thumbnails/{user_id}.jpg"):
        LOGGER.debug("Using user thumbnail for video file")
        return f"thumbnails/{user_id}.jpg"
    # Then try owner thumbnail
    elif await aiopath.exists(f"thumbnails/{Config.OWNER_ID}.jpg"):
        LOGGER.debug("Using owner thumbnail for video file")
        return f"thumbnails/{Config.OWNER_ID}.jpg"

    # Create a default thumbnail for video files if no user/owner thumbnail
    default_thumb = ospath.join(output_dir, "default_video.jpg")
    if not await aiopath.exists(default_thumb):
        # Create a simple default video thumbnail
        cmd = [
            "xtra",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=640x360",
            "-vf",
            "drawtext=text='Video':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2",
            "-frames:v",
            "1",
            default_thumb,
        ]
        _, _, code = await cmd_exec(cmd)

        if code != 0 or not await aiopath.exists(default_thumb):
            # If FFmpeg fails, try with PIL
            try:
                # Apply memory limits for PIL operations
                limit_memory_for_pil()

                # Create a simple black image
                img = Image.new("RGB", (640, 360), color=(0, 0, 0))
                img.save(default_thumb)
                LOGGER.debug("Created default video thumbnail using PIL")
            except Exception as e:
                LOGGER.debug(f"Failed to create default video thumbnail with PIL: {e}")
                return None

    if await aiopath.exists(default_thumb):
        return default_thumb
    return None


async def create_default_image_thumbnail(output_dir, user_id=None):
    # Try user thumbnail first if available
    if user_id and await aiopath.exists(f"thumbnails/{user_id}.jpg"):
        LOGGER.debug("Using user thumbnail for image file")
        return f"thumbnails/{user_id}.jpg"
    # Then try owner thumbnail
    elif await aiopath.exists(f"thumbnails/{Config.OWNER_ID}.jpg"):
        LOGGER.debug("Using owner thumbnail for image file")
        return f"thumbnails/{Config.OWNER_ID}.jpg"

    # Create a default thumbnail for image files if no user/owner thumbnail
    default_thumb = ospath.join(output_dir, "default_image.jpg")
    if not await aiopath.exists(default_thumb):
        # Create a simple default image thumbnail
        cmd = [
            "xtra",
            "-f",
            "lavfi",
            "-i",
            "color=c=purple:s=640x360",
            "-vf",
            "drawtext=text='Image':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2",
            "-frames:v",
            "1",
            default_thumb,
        ]
        _, _, code = await cmd_exec(cmd)

        if code != 0 or not await aiopath.exists(default_thumb):
            # If FFmpeg fails, try with PIL
            try:
                # Apply memory limits for PIL operations
                limit_memory_for_pil()

                # Create a simple purple image
                img = Image.new("RGB", (640, 360), color=(128, 0, 128))
                img.save(default_thumb)
                LOGGER.debug("Created default image thumbnail using PIL")
            except Exception as e:
                LOGGER.debug(f"Failed to create default image thumbnail with PIL: {e}")
                return None

    if await aiopath.exists(default_thumb):
        return default_thumb
    return None


async def get_multiple_frames_thumbnail(
    video_file, layout, keep_screenshots, user_id=None
):
    ss_nb = layout.split("x")
    ss_nb = int(ss_nb[0]) * int(ss_nb[1])
    dirpath = await take_ss(video_file, ss_nb)
    if not dirpath:
        # Try user thumbnail first if available
        if user_id and await aiopath.exists(f"thumbnails/{user_id}.jpg"):
            LOGGER.debug(
                f"Using user thumbnail for multiple frames failure: {video_file}"
            )
            return f"thumbnails/{user_id}.jpg"
        # Then try owner thumbnail
        elif await aiopath.exists(f"thumbnails/{Config.OWNER_ID}.jpg"):
            LOGGER.debug(
                f"Using owner thumbnail for multiple frames failure: {video_file}"
            )
            return f"thumbnails/{Config.OWNER_ID}.jpg"
        # Finally return None
        else:
            return None
    output_dir = f"{DOWNLOAD_DIR}thumbnails"
    await makedirs(output_dir, exist_ok=True)
    output = ospath.join(output_dir, f"{time()}.jpg")

    from .resource_manager import get_optimal_thread_count

    # Get optimal thread count based on system load if dynamic threading is enabled
    thread_count = await get_optimal_thread_count() or max(1, cpu_no // 2)

    # First try with simpler tile filter
    cmd = [
        "xtra",
        "-hide_banner",
        "-loglevel",
        "error",
        "-pattern_type",
        "glob",
        "-i",
        f"{escape(dirpath)}/*.png",
        "-vf",
        f"tile={layout}",
        "-q:v",
        "2",
        "-frames:v",
        "1",
        "-f",
        "mjpeg",
        "-threads",
        f"{thread_count}",
        output,
    ]
    try:
        _, err, code = await wait_for(cmd_exec(cmd), timeout=60)
        if code != 0 or not await aiopath.exists(output):
            # If first attempt fails, try with different parameters
            LOGGER.warning(
                f"First thumbnail tile attempt failed for {video_file}. Trying with different parameters. Error: {err}",
            )
            # Reuse the thread count from above
            cmd = [
                "xtra",
                "-hide_banner",
                "-loglevel",
                "error",
                "-pattern_type",
                "glob",
                "-i",
                f"{escape(dirpath)}/*.png",
                "-filter_complex",
                f"tile={layout}",
                "-q:v",
                "2",
                "-frames:v",
                "1",
                "-threads",
                f"{thread_count}",
                output,
            ]
            _, err, code = await wait_for(cmd_exec(cmd), timeout=60)
            if code != 0 or not await aiopath.exists(output):
                LOGGER.error(
                    f"Error while combining thumbnails for video. Name: {video_file} stderr: {err}",
                )
                # Try user thumbnail first if available
                if user_id and await aiopath.exists(f"thumbnails/{user_id}.jpg"):
                    LOGGER.debug(
                        f"Using user thumbnail for multiple frames combination failure: {video_file}"
                    )
                    return f"thumbnails/{user_id}.jpg"
                # Then try owner thumbnail
                elif await aiopath.exists(f"thumbnails/{Config.OWNER_ID}.jpg"):
                    LOGGER.debug(
                        f"Using owner thumbnail for multiple frames combination failure: {video_file}"
                    )
                    return f"thumbnails/{Config.OWNER_ID}.jpg"
                # Finally return None
                else:
                    return None
    except Exception as e:
        LOGGER.error(
            f"Error while combining thumbnails from video. Name: {video_file}. Error: {e!s}",
        )
        # Try user thumbnail first if available
        if user_id and await aiopath.exists(f"thumbnails/{user_id}.jpg"):
            LOGGER.debug(
                f"Using user thumbnail for multiple frames exception: {video_file}"
            )
            return f"thumbnails/{user_id}.jpg"
        # Then try owner thumbnail
        elif await aiopath.exists(f"thumbnails/{Config.OWNER_ID}.jpg"):
            LOGGER.debug(
                f"Using owner thumbnail for multiple frames exception: {video_file}"
            )
            return f"thumbnails/{Config.OWNER_ID}.jpg"
        # Finally return None
        else:
            return None
    finally:
        if not keep_screenshots:
            await rmtree(dirpath, ignore_errors=True)
    return output


def is_mkv(file):
    """Legacy function name, now checks if file is a supported media format for watermarking.

    Args:
        file: Path to the file

    Returns:
        bool: True if the file is a supported media format for watermarking
    """
    # Video formats (expanded list for better compatibility)
    video_extensions = [
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".webm",
        ".flv",
        ".wmv",
        ".m4v",
        ".ts",
        ".3gp",
        ".mpg",
        ".mpeg",
        ".vob",
        ".divx",
        ".asf",
        ".m2ts",
        ".mts",
    ]
    # Image formats (expanded list for better compatibility)
    image_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".webp",
        ".tiff",
        ".tif",
        ".svg",
        ".heic",
        ".heif",
        ".gif",
        ".apng",
        ".mng",
    ]

    # Check if the file has a supported extension
    file_lower = file.lower()
    return any(file_lower.endswith(ext) for ext in video_extensions + image_extensions)


async def get_media_type_for_watermark(file):
    """Determine if a file is an image or video for watermarking purposes.

    Args:
        file: Path to the file

    Returns:
        str: 'image', 'video', 'animated_image', or None if not supported
    """
    import os  # Import os module for path operations

    # Video formats (expanded list for better compatibility)
    video_extensions = [
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".webm",
        ".flv",
        ".wmv",
        ".m4v",
        ".ts",
        ".3gp",
        ".mpg",
        ".mpeg",
        ".vob",
        ".divx",
        ".asf",
        ".m2ts",
        ".mts",
    ]
    # Image formats (expanded list for better compatibility)
    image_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".webp",
        ".tiff",
        ".tif",
        ".svg",
        ".heic",
        ".heif",
    ]
    # Animated image formats (special handling)
    animated_extensions = [
        ".gif",
        ".apng",
        ".mng",
    ]

    # Check if file exists
    if not os.path.exists(file):
        LOGGER.error(f"File not found for watermarking: {file}")
        return None

    file_lower = file.lower()

    # First try to determine type by extension
    if any(file_lower.endswith(ext) for ext in video_extensions):
        return "video"
    elif any(file_lower.endswith(ext) for ext in image_extensions):
        return "image"
    elif any(file_lower.endswith(ext) for ext in animated_extensions):
        return "animated_image"

    # If extension doesn't match, try to determine by file content using ffprobe
    try:
        import json
        from .bot_utils import cmd_exec

        # Use ffprobe to get file information
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_type,codec_name,width,height,avg_frame_rate",
            "-of",
            "json",
            file,
        ]

        # Generate a unique process ID for tracking
        process_id = f"ffprobe_media_type_{time()}"

        # Execute the command with resource limits
        stdout, _, code = await cmd_exec(
            cmd, apply_limits=True, process_id=process_id, task_type="FFprobe"
        )

        if code == 0:
            data = json.loads(stdout)
            if "streams" in data and data["streams"]:
                stream = data["streams"][0]
                codec_type = stream.get("codec_type")
                codec_name = stream.get("codec_name")
                avg_frame_rate = stream.get("avg_frame_rate")

                if codec_type == "video":
                    # Check if it's an animated image
                    if codec_name in ["gif", "apng"]:
                        return "animated_image"
                    # Check if it's a single frame (likely an image)
                    elif avg_frame_rate == "0/0" or avg_frame_rate == "1/1":
                        return "image"
                    else:
                        return "video"
    except Exception as e:
        LOGGER.warning(f"Error determining media type for {file}: {str(e)}")

    # If all else fails, return None
    LOGGER.warning(f"Could not determine media type for watermarking: {file}")
    return None


class FFMpeg:
    def __init__(self, listener):
        self._listener = listener
        self._processed_bytes = 0
        self._last_processed_bytes = 0
        self._processed_time = 0
        self._last_processed_time = 0
        self._speed_raw = 0
        self._progress_raw = 0
        self._total_time = 0
        self._eta_raw = 0
        self._time_rate = 0.1
        self._start_time = 0

    @property
    def processed_bytes(self):
        return self._processed_bytes

    @property
    def speed_raw(self):
        return self._speed_raw

    @property
    def progress_raw(self):
        return self._progress_raw

    @property
    def eta_raw(self):
        return self._eta_raw

    def clear(self):
        self._start_time = time()
        self._processed_bytes = 0
        self._processed_time = 0
        self._speed_raw = 0
        self._progress_raw = 0
        self._eta_raw = 0
        self._time_rate = 0.1
        self._last_processed_time = 0
        self._last_processed_bytes = 0

    async def _ffmpeg_progress(self):
        while not (
            self._listener.subproc.returncode is not None
            or self._listener.is_cancelled
            or self._listener.subproc.stdout.at_eof()
        ):
            try:
                line = await wait_for(self._listener.subproc.stdout.readline(), 60)
            except Exception:
                break
            line = line.decode().strip()
            if not line:
                break
            if "=" in line:
                key, value = line.split("=", 1)
                if value != "N/A":
                    if key == "total_size":
                        self._processed_bytes = int(value) + self._last_processed_bytes
                        self._speed_raw = self._processed_bytes / (
                            time() - self._start_time
                        )
                    elif key == "speed":
                        self._time_rate = max(0.1, float(value.strip("x")))
                    elif key == "out_time":
                        self._processed_time = (
                            time_to_seconds(value) + self._last_processed_time
                        )
                        try:
                            self._progress_raw = (
                                self._processed_time / self._total_time * 100
                            )
                            self._eta_raw = (
                                self._total_time - self._processed_time
                            ) / self._time_rate
                        except Exception:
                            self._progress_raw = 0
                            self._eta_raw = 0
            await sleep(0.05)

    async def ffmpeg_cmds(self, ffmpeg, f_path):
        from .resource_manager import apply_resource_limits, cleanup_process

        self.clear()
        self._total_time = (await get_media_info(f_path))[0]
        base_name, ext = ospath.splitext(f_path)
        dir, base_name = base_name.rsplit("/", 1)
        indices = [
            index
            for index, item in enumerate(ffmpeg)
            if item.startswith("mltb") or item == "mltb"
        ]
        outputs = []
        for index in indices:
            output_file = ffmpeg[index]
            if output_file != "mltb" and output_file.startswith("mltb"):
                bo, oext = ospath.splitext(output_file)
                if oext:
                    if ext == oext:
                        prefix = f"ffmpeg{index}." if bo == "mltb" else ""
                    else:
                        prefix = ""
                    ext = ""
                else:
                    prefix = ""
            else:
                prefix = f"ffmpeg{index}."
            output = f"{dir}/{prefix}{output_file.replace('mltb', base_name)}{ext}"
            outputs.append(output)
            ffmpeg[index] = output

        if self._listener.is_cancelled:
            return False

        # Generate a unique process ID for tracking
        process_id = f"ffmpeg_{self._listener.mid}_{time()}"

        # Apply resource limits to the FFmpeg command
        limited_cmd = await apply_resource_limits(ffmpeg, process_id, "FFmpeg")

        # Execute the command with resource limits
        self._listener.subproc = await create_subprocess_exec(
            *limited_cmd,
            stdout=PIPE,
            stderr=PIPE,
        )

        await self._ffmpeg_progress()
        _, stderr = await self._listener.subproc.communicate()
        code = self._listener.subproc.returncode

        # Clean up process tracking
        cleanup_process(process_id)

        if self._listener.is_cancelled:
            return False
        if code == 0:
            return outputs
        if code == -9:
            self._listener.is_cancelled = True
            return False
        try:
            stderr = stderr.decode().strip()
        except Exception:
            stderr = "Unable to decode the error!"
        LOGGER.error(
            f"{stderr}. Something went wrong while running ffmpeg cmd, mostly file requires different/specific arguments. Path: {f_path}",
        )
        for op in outputs:
            if await aiopath.exists(op):
                await remove(op)
        return False

    async def metadata_watermark_cmds(self, ffmpeg, f_path):
        from .resource_manager import apply_resource_limits, cleanup_process

        self.clear()
        self._total_time = (await get_media_info(f_path))[0]
        if self._listener.is_cancelled:
            return False

        # Generate a unique process ID for tracking
        process_id = f"ffmpeg_{self._listener.mid}_{time()}"

        # Apply resource limits to the FFmpeg command
        limited_cmd = await apply_resource_limits(
            ffmpeg, process_id, "Metadata/Watermark"
        )

        # Execute the command with resource limits
        self._listener.subproc = await create_subprocess_exec(
            *limited_cmd,
            stdout=PIPE,
            stderr=PIPE,
        )

        await self._ffmpeg_progress()
        _, stderr = await self._listener.subproc.communicate()
        code = self._listener.subproc.returncode

        # Clean up process tracking
        cleanup_process(process_id)

        if self._listener.is_cancelled:
            return False
        if code == 0:
            return True
        if code == -9:
            self._listener.is_cancelled = True
            return False
        try:
            stderr = stderr.decode().strip()
        except Exception:
            stderr = "Unable to decode the error!"
        LOGGER.error(
            f"{stderr}. Something went wrong while running ffmpeg cmd, mostly file requires different/specific arguments. Path: {f_path}",
        )
        return False

    async def convert_video(self, video_file, ext, retry=False):
        from .resource_manager import apply_resource_limits, cleanup_process

        self.clear()
        self._total_time = (await get_media_info(video_file))[0]
        base_name = ospath.splitext(video_file)[0]
        output = f"{base_name}.{ext}"
        if retry:
            cmd = [
                "xtra",
                "-hide_banner",
                "-loglevel",
                "error",
                "-progress",
                "pipe:1",
                "-i",
                video_file,
                "-map",
                "0",
                "-ignore_unknown",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-threads",
                f"{max(1, cpu_no // 2)}",
                output,
            ]
            if ext == "mp4":
                cmd[17:17] = ["-c:s", "mov_text"]
            elif ext == "mkv":
                cmd[17:17] = ["-c:s", "ass"]
            else:
                cmd[17:17] = ["-c:s", "copy"]
        else:
            cmd = [
                "xtra",
                "-hide_banner",
                "-loglevel",
                "error",
                "-progress",
                "pipe:1",
                "-i",
                video_file,
                "-map",
                "0",
                "-ignore_unknown",
                "-c",
                "copy",
                "-threads",
                f"{max(1, cpu_no // 2)}",
                output,
            ]
        if self._listener.is_cancelled:
            return False

        # Generate a unique process ID for tracking
        process_id = f"ffmpeg_{self._listener.mid}_{time()}"

        # Apply resource limits to the FFmpeg command
        limited_cmd = await apply_resource_limits(cmd, process_id, "Convert")

        # Execute the command with resource limits
        self._listener.subproc = await create_subprocess_exec(
            *limited_cmd,
            stdout=PIPE,
            stderr=PIPE,
        )

        await self._ffmpeg_progress()
        _, stderr = await self._listener.subproc.communicate()
        code = self._listener.subproc.returncode

        # Clean up process tracking
        cleanup_process(process_id)

        if self._listener.is_cancelled:
            return False
        if code == 0:
            return output
        if code == -9:
            self._listener.is_cancelled = True
            return False
        if await aiopath.exists(output):
            await remove(output)
        if not retry:
            return await self.convert_video(video_file, ext, True)
        try:
            stderr = stderr.decode().strip()
        except Exception:
            stderr = "Unable to decode the error!"
        LOGGER.error(
            f"{stderr}. Something went wrong while converting video, mostly file need specific codec. Path: {video_file}",
        )
        return False

    async def convert_audio(self, audio_file, ext):
        from .resource_manager import apply_resource_limits, cleanup_process

        self.clear()
        self._total_time = (await get_media_info(audio_file))[0]
        base_name = ospath.splitext(audio_file)[0]
        output = f"{base_name}.{ext}"
        cmd = [
            "xtra",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-i",
            audio_file,
            "-threads",
            f"{max(1, cpu_no // 2)}",
            output,
        ]
        if self._listener.is_cancelled:
            return False

        # Generate a unique process ID for tracking
        process_id = f"ffmpeg_{self._listener.mid}_{time()}"

        # Apply resource limits to the FFmpeg command
        limited_cmd = await apply_resource_limits(cmd, process_id, "Convert")

        # Execute the command with resource limits
        self._listener.subproc = await create_subprocess_exec(
            *limited_cmd,
            stdout=PIPE,
            stderr=PIPE,
        )

        await self._ffmpeg_progress()
        _, stderr = await self._listener.subproc.communicate()
        code = self._listener.subproc.returncode

        # Clean up process tracking
        cleanup_process(process_id)

        if self._listener.is_cancelled:
            return False
        if code == 0:
            return output
        if code == -9:
            self._listener.is_cancelled = True
            return False
        try:
            stderr = stderr.decode().strip()
        except Exception:
            stderr = "Unable to decode the error!"
        LOGGER.error(
            f"{stderr}. Something went wrong while converting audio, mostly file need specific codec. Path: {audio_file}",
        )
        if await aiopath.exists(output):
            await remove(output)
        return False

    async def sample_video(self, video_file, sample_duration, part_duration):
        from .resource_manager import apply_resource_limits, cleanup_process

        self.clear()
        self._total_time = sample_duration
        dir, name = video_file.rsplit("/", 1)
        output_file = f"{dir}/SAMPLE.{name}"
        segments = [(0, part_duration)]
        duration = (await get_media_info(video_file))[0]
        remaining_duration = duration - (part_duration * 2)
        parts = (sample_duration - (part_duration * 2)) // part_duration
        time_interval = remaining_duration // parts
        next_segment = time_interval
        for _ in range(parts):
            segments.append((next_segment, next_segment + part_duration))
            next_segment += time_interval
        segments.append((duration - part_duration, duration))

        filter_complex = ""
        for i, (start, end) in enumerate(segments):
            filter_complex += (
                f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]; "
            )
            filter_complex += (
                f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]; "
            )

        for i in range(len(segments)):
            filter_complex += f"[v{i}][a{i}]"

        filter_complex += f"concat=n={len(segments)}:v=1:a=1[vout][aout]"

        cmd = [
            "xtra",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-i",
            video_file,
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-threads",
            f"{max(1, cpu_no // 2)}",
            output_file,
        ]

        if self._listener.is_cancelled:
            return False

        # Generate a unique process ID for tracking
        process_id = f"ffmpeg_{self._listener.mid}_{time()}"

        # Apply resource limits to the FFmpeg command
        limited_cmd = await apply_resource_limits(cmd, process_id, "Sample Video")

        # Execute the command with resource limits
        self._listener.subproc = await create_subprocess_exec(
            *limited_cmd,
            stdout=PIPE,
            stderr=PIPE,
        )

        await self._ffmpeg_progress()
        _, stderr = await self._listener.subproc.communicate()
        code = self._listener.subproc.returncode

        # Clean up process tracking
        cleanup_process(process_id)

        if self._listener.is_cancelled:
            return False
        if code == -9:
            self._listener.is_cancelled = True
            return False
        if code == 0:
            return output_file
        try:
            stderr = stderr.decode().strip()
        except Exception:
            stderr = "Unable to decode the error!"
        LOGGER.error(
            f"{stderr}. Something went wrong while creating sample video, mostly file is corrupted. Path: {video_file}",
        )
        if await aiopath.exists(output_file):
            await remove(output_file)
        return False

    async def split(self, f_path, file_, parts, split_size):
        from .resource_manager import apply_resource_limits, cleanup_process

        self.clear()
        multi_streams = True
        self._total_time = duration = (await get_media_info(f_path))[0]
        base_name, extension = ospath.splitext(file_)
        split_size -= 3000000
        start_time = 0
        i = 1
        while i <= parts or start_time < duration - 4:
            out_path = f_path.replace(file_, f"{base_name}.part{i:03}{extension}")
            cmd = [
                "xtra",
                "-hide_banner",
                "-loglevel",
                "error",
                "-progress",
                "pipe:1",
                "-ss",
                str(start_time),
                "-i",
                f_path,
                "-fs",
                str(split_size),
                "-map",
                "0",
                "-map_chapters",
                "-1",
                "-async",
                "1",
                "-strict",
                "-2",
                "-c",
                "copy",
                "-threads",
                f"{max(1, cpu_no // 2)}",
                out_path,
            ]
            if not multi_streams:
                del cmd[12]
                del cmd[12]
            if self._listener.is_cancelled:
                return False

            # Generate a unique process ID for tracking
            process_id = f"ffmpeg_{self._listener.mid}_{time()}"

            # Apply resource limits to the FFmpeg command
            limited_cmd = await apply_resource_limits(cmd, process_id, "Split")

            # Execute the command with resource limits
            self._listener.subproc = await create_subprocess_exec(
                *limited_cmd,
                stdout=PIPE,
                stderr=PIPE,
            )

            await self._ffmpeg_progress()
            _, stderr = await self._listener.subproc.communicate()
            code = self._listener.subproc.returncode

            # Clean up process tracking
            cleanup_process(process_id)

            if self._listener.is_cancelled:
                return False
            if code == -9:
                self._listener.is_cancelled = True
                return False
            if code != 0:
                try:
                    stderr = stderr.decode().strip()
                except Exception:
                    stderr = "Unable to decode the error!"
                with contextlib.suppress(Exception):
                    await remove(out_path)
                if multi_streams:
                    LOGGER.warning(
                        f"{stderr}. Retrying without map, -map 0 not working in all situations. Path: {f_path}",
                    )
                    multi_streams = False
                    continue
                LOGGER.warning(
                    f"{stderr}. Unable to split this video, if it's size less than {self._listener.max_split_size} will be uploaded as it is. Path: {f_path}",
                )
                return False
            out_size = await aiopath.getsize(out_path)
            if out_size > self._listener.max_split_size:
                # Calculate a more appropriate reduction based on the overage percentage
                overage = out_size - self._listener.max_split_size
                overage_percent = overage / self._listener.max_split_size
                # Adjust reduction based on overage percentage
                if overage_percent > 0.2:  # If more than 20% over
                    reduction = overage + 10000000  # 10MB extra buffer
                else:
                    reduction = overage + 5000000  # 5MB extra buffer

                split_size -= reduction
                LOGGER.warning(
                    f"Part size is {out_size} bytes ({round(out_size / 1024 / 1024, 2)} MB), which exceeds max split size. "
                    f"Reducing split size by {round(reduction / 1024 / 1024, 2)} MB for next attempt. Path: {f_path}",
                )
                await remove(out_path)
                continue
            lpd = (await get_media_info(out_path))[0]
            if lpd == 0:
                LOGGER.error(
                    f"Something went wrong while splitting, mostly file is corrupted. Path: {f_path}",
                )
                break
            if duration == lpd:
                LOGGER.warning(
                    f"This file has been splitted with default stream and audio, so you will only see one part with less size from orginal one because it doesn't have all streams and audios. This happens mostly with MKV videos. Path: {f_path}",
                )
                break
            if lpd <= 3:
                await remove(out_path)
                break
            self._last_processed_time += lpd
            self._last_processed_bytes += out_size
            start_time += lpd - 3
            i += 1

        return True

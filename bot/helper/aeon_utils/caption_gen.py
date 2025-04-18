import json
import os
import re
from contextlib import suppress
from hashlib import md5

from aiofiles.os import path as aiopath
from langcodes import Language

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import cmd_exec
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    get_readable_time,
)
from bot.helper.ext_utils.template_processor import process_template


class DefaultDict(dict):
    def __missing__(self, key):
        return "Unknown"


async def generate_caption(filename, directory, caption_template):
    file_path = os.path.join(directory, filename)

    # Initialize variables to track temporary resources
    temp_file_created = False
    file_path_to_use = file_path
    temp_dir = None

    try:
        # Generate a unique process ID for tracking
        process_id = (
            f"mediainfo_{os.path.basename(file_path)}_{os.path.getmtime(file_path)}"
        )

        # Check if filename contains special characters that might cause issues with shell commands
        if any(
            c in file_path
            for c in [
                "(",
                ")",
                "[",
                "]",
                "'",
                '"',
                ";",
                "&",
                "|",
                "<",
                ">",
                "$",
                "`",
                "\\",
            ]
        ) and os.path.exists(file_path):
            LOGGER.debug(f"File path contains special characters: {file_path}")
            # Create a temporary file with a safe name
            import tempfile
            from time import time

            # Try to create a temp directory in the same filesystem as the original file
            # This helps avoid cross-device link errors
            parent_dir = os.path.dirname(file_path)
            try:
                temp_dir = tempfile.mkdtemp(dir=parent_dir)
                same_filesystem = True
            except Exception:
                # Fall back to system temp directory if we can't create in the parent dir
                temp_dir = tempfile.mkdtemp()
                same_filesystem = False

            safe_name = f"temp_mediainfo_{int(time())}{os.path.splitext(filename)[1]}"
            safe_path = os.path.join(temp_dir, safe_name)
            # We'll use the temp_dir variable for cleanup later

            if same_filesystem:
                try:
                    # If on same filesystem, try a hard link for better performance
                    os.link(file_path, safe_path)
                    LOGGER.debug(
                        f"Created temporary link for file with special characters: {safe_path}"
                    )
                    file_path_to_use = safe_path
                    temp_file_created = True
                except Exception as e:
                    LOGGER.debug(
                        f"Failed to create link for file with special characters: {e}"
                    )
                    # Fall back to copying a portion of the file
                    try:
                        # Only copy a small portion of the file for MediaInfo analysis
                        # This is much faster than copying the entire file
                        with open(file_path, "rb") as src_file:
                            # Read the first 10MB of the file (enough for MediaInfo)
                            data = src_file.read(10 * 1024 * 1024)
                            with open(safe_path, "wb") as dst_file:
                                dst_file.write(data)
                        LOGGER.debug(
                            f"Created temporary copy for file with special characters: {safe_path}"
                        )
                        file_path_to_use = safe_path
                        temp_file_created = True
                    except Exception as copy_error:
                        LOGGER.debug(
                            f"Failed to create copy for file with special characters: {copy_error}"
                        )
                        file_path_to_use = file_path
            else:
                # If on different filesystem, just copy a portion of the file
                try:
                    # Only copy a small portion of the file for MediaInfo analysis
                    with open(file_path, "rb") as src_file:
                        # Read the first 10MB of the file (enough for MediaInfo)
                        data = src_file.read(10 * 1024 * 1024)
                        with open(safe_path, "wb") as dst_file:
                            dst_file.write(data)
                    LOGGER.debug(
                        f"Created temporary copy for file with special characters: {safe_path}"
                    )
                    file_path_to_use = safe_path
                    temp_file_created = True
                except Exception as copy_error:
                    LOGGER.debug(
                        f"Failed to create copy for file with special characters: {copy_error}"
                    )
                    file_path_to_use = file_path

        # Execute the command with resource limits
        result = await cmd_exec(
            ["mediainfo", "--Output=JSON", file_path_to_use],
            apply_limits=True,
            process_id=process_id,
            task_type="MediaInfo",
        )

        if result[1]:
            LOGGER.info(f"MediaInfo command output: {result[1]}")

        mediainfo_data = json.loads(result[0])  # Parse JSON output
    except Exception as error:
        LOGGER.error(f"Failed to retrieve media info: {error}. File may not exist!")
        # Clean up temporary file if created
        if temp_file_created and os.path.exists(file_path_to_use):
            try:
                os.remove(file_path_to_use)
                LOGGER.debug(f"Removed temporary file: {file_path_to_use}")
            except Exception as e:
                LOGGER.warning(f"Failed to remove temporary file: {e}")
        return filename

    media_data = mediainfo_data.get("media", {})
    track_data = media_data.get("track", [])
    general_metadata = next(
        (track for track in track_data if track["@type"] == "General"),
        {},
    )
    video_metadata_list = [track for track in track_data if track["@type"] == "Video"]
    video_metadata = next(iter(video_metadata_list), {})
    audio_metadata = [track for track in track_data if track["@type"] == "Audio"]
    subtitle_metadata = [track for track in track_data if track["@type"] == "Text"]

    # Extract basic metadata
    video_duration = round(float(video_metadata.get("Duration", 0)))
    video_quality = get_video_quality(video_metadata.get("Height", None))

    # Extract audio and subtitle languages
    audio_languages = ", ".join(
        parse_audio_language("", audio)
        for audio in audio_metadata
        if audio.get("Language")
    )
    subtitle_languages = ", ".join(
        parse_subtitle_language("", subtitle)
        for subtitle in subtitle_metadata
        if subtitle.get("Language")
    )

    audio_languages = audio_languages if audio_languages else "Unknown"
    subtitle_languages = subtitle_languages if subtitle_languages else "Unknown"
    video_quality = video_quality if video_quality else "Unknown"
    file_md5_hash = calculate_md5(file_path)

    # Extract season and episode information from filename
    season_num = ""
    episode_num = ""

    # Try to extract season number with improved patterns
    season_patterns = [
        r"[Ss]([0-9]{1,2})",  # S01, s01
        r"Season\s*([0-9]{1,2})",  # Season 01, Season01
        r"\bS(\d{1,2})\b",  # S1, S01 (word boundary)
        r"\bSeason\s*(\d{1,2})\b",  # Season 1, Season 01
        r"\b(\d{1,2})nd Season\b",  # 2nd Season
        r"\b(\d{1,2})rd Season\b",  # 3rd Season
        r"\b(\d{1,2})th Season\b",  # 4th Season
        r"\bPart\s*(\d{1,2})\b",  # Part 1, Part 2 (for anime)
    ]

    for pattern in season_patterns:
        season_match = re.search(pattern, filename, re.IGNORECASE)
        if season_match:
            season_num = season_match.group(1).zfill(2)  # Add leading zero if needed
            break

    # Default to "01" if no season found and it looks like a series
    if not season_num and (
        re.search(r"[Ee]\d+|Episode|\bEP\d+\b", filename, re.IGNORECASE)
    ):
        season_num = "01"

    # Try to extract episode number with improved patterns
    episode_patterns = [
        r"[Ee]([0-9]{1,2})",  # E01, e01
        r"Episode\s*([0-9]{1,2})",  # Episode 01, Episode01
        r"\bEP(\d{1,2})\b",  # EP1, EP01 (word boundary)
        r"\bEpisode\s*(\d{1,2})\b",  # Episode 1, Episode 01
        r"\b(\d{1,2})\s*of\s*\d{1,2}\b",  # 1 of 12, 01 of 12
        r"\b(\d{2,3})\b",  # Standalone numbers like 001, 01 (common in anime)
        r"\s-\s(\d{1,3})\s",  # - 01 - (common in anime)
    ]

    for pattern in episode_patterns:
        episode_match = re.search(pattern, filename, re.IGNORECASE)
        if episode_match:
            episode_num = episode_match.group(1).zfill(2)  # Add leading zero if needed
            break

    # Special case for anime titles with episode numbers at the end
    # Example: "[SanKyuu] Ore dake Level Up na Ken (Solo Leveling) - 01.mkv"
    if not episode_num:
        anime_ep_pattern = r"\s-\s(\d{1,3})(?:\.[a-zA-Z0-9]+)?$"
        anime_match = re.search(anime_ep_pattern, filename)
        if anime_match:
            episode_num = anime_match.group(1).zfill(2)
            # If we found an episode but no season, assume it's season 1
            if not season_num:
                season_num = "01"

    # Extract file format
    file_format = os.path.splitext(filename)[1].lstrip(".").upper()
    if not file_format:
        file_format = general_metadata.get("FileExtension", "").upper()

    # Extract year from filename or metadata with improved patterns
    year = ""
    # Try multiple patterns for year extraction
    year_patterns = [
        r"\b(19|20)\d{2}\b",  # Standard year with word boundaries
        r"\[(19|20)\d{2}\]",  # Year in brackets
        r"\((19|20)\d{2}\)",  # Year in parentheses
    ]

    for pattern in year_patterns:
        year_match = re.search(pattern, filename)
        if year_match:
            # Extract just the 4 digits
            year_digits = re.search(r"(19|20)\d{2}", year_match.group(0))
            if year_digits:
                year = year_digits.group(0)
                break

    # If not found in filename, try metadata
    if not year and "Released_Date" in general_metadata:
        year_match = re.search(r"(19|20)\d{2}", general_metadata["Released_Date"])
        if year_match:
            year = year_match.group(0)

    # If still not found, try other metadata fields
    if not year and "Movie_name" in general_metadata:
        year_match = re.search(r"(19|20)\d{2}", general_metadata["Movie_name"])
        if year_match:
            year = year_match.group(0)

    # Try title field as last resort
    if not year and "Title" in general_metadata:
        year_match = re.search(r"(19|20)\d{2}", general_metadata["Title"])
        if year_match:
            year = year_match.group(0)

    # Extract framerate
    framerate = video_metadata.get("FrameRate", "")
    if framerate:
        try:
            framerate = f"{float(framerate):.2f} fps"
        except (ValueError, TypeError):
            framerate = f"{framerate} fps"

    # Build codec information
    codec_info = []
    if video_metadata:
        video_codec = video_metadata.get("Format", "")
        if video_codec:
            codec_info.append(f"Video: {video_codec}")

    if audio_metadata:
        audio_codec = audio_metadata[0].get("Format", "")
        if audio_codec:
            codec_info.append(f"Audio: {audio_codec}")

    if subtitle_metadata:
        subtitle_codec = subtitle_metadata[0].get("Format", "")
        if subtitle_codec:
            codec_info.append(f"Subtitle: {subtitle_codec}")

    codec_str = ", ".join(codec_info)

    # Create caption data dictionary
    caption_data = DefaultDict(
        filename=filename,
        size=get_readable_file_size(await aiopath.getsize(file_path)),
        duration=get_readable_time(video_duration, True),
        quality=video_quality,
        audios=audio_languages,
        subtitles=subtitle_languages,
        md5_hash=file_md5_hash,
        # New template variables
        season=season_num,
        episode=episode_num,
        NumAudios=str(len(audio_metadata)).zfill(2)
        if len(audio_metadata) < 10
        else str(len(audio_metadata)),
        NumVideos=str(len(video_metadata_list)).zfill(2)
        if len(video_metadata_list) < 10
        else str(len(video_metadata_list)),
        NumSubtitles=str(len(subtitle_metadata)).zfill(2)
        if len(subtitle_metadata) < 10
        else str(len(subtitle_metadata)),
        year=year,
        formate=file_format,
        id=general_metadata.get("UniqueID", "") or file_md5_hash[:10],
        framerate=framerate,
        codec=codec_str,
    )

    # Log the extracted metadata for debugging
    LOGGER.debug(f"Extracted metadata for {filename}:")
    LOGGER.debug(f"Season: {season_num}, Episode: {episode_num}, Year: {year}")
    LOGGER.debug(f"Format: {file_format}, Framerate: {framerate}, Codec: {codec_str}")
    LOGGER.debug(
        f"Quality: {video_quality}, Audio tracks: {len(audio_metadata)}, Subtitle tracks: {len(subtitle_metadata)}"
    )

    # Log a summary of the extracted metadata at INFO level
    metadata_summary = []
    if season_num:
        metadata_summary.append(f"S{season_num}")
    if episode_num:
        metadata_summary.append(f"E{episode_num}")
    if year:
        metadata_summary.append(f"{year}")
    if video_quality and video_quality != "Unknown":
        metadata_summary.append(f"{video_quality}")
    if codec_str:
        metadata_summary.append(f"{codec_str}")

    if metadata_summary:
        LOGGER.info(f"Media info for {filename}: {' | '.join(metadata_summary)}")

    # Clean up the caption data by removing empty values
    cleaned_caption_data = {
        k: v for k, v in caption_data.items() if v and str(v).strip()
    }

    # First try the advanced template processor for Google Fonts and nested variables
    try:
        processed_caption = await process_template(
            caption_template, cleaned_caption_data
        )
        # Clean up empty lines and format the caption
        processed_caption = clean_caption(processed_caption)
        # Log successful caption generation at INFO level
        LOGGER.info(f"Successfully applied leech caption template for: {filename}")
        # Clean up temporary resources
        if temp_file_created and os.path.exists(file_path_to_use):
            try:
                os.remove(file_path_to_use)
                LOGGER.debug(f"Removed temporary file: {file_path_to_use}")
            except Exception as e:
                LOGGER.debug(f"Failed to remove temporary file: {e}")

        # Clean up temporary directory if created
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil

                shutil.rmtree(temp_dir)
                LOGGER.debug(f"Removed temporary directory: {temp_dir}")
            except Exception as e:
                LOGGER.debug(f"Failed to remove temporary directory: {e}")
        return processed_caption
    except Exception as e:
        LOGGER.error(f"Error processing template with advanced processor: {e}")
        # Fall back to the simple format_map method if advanced processing fails
        try:
            # Create a custom format string that skips empty variables
            custom_template = caption_template
            for key, value in caption_data.items():
                if not value or not str(value).strip():
                    # Replace the variable and its line if it's on its own line
                    pattern = r"^\s*{" + key + r"}\s*$"
                    custom_template = re.sub(
                        pattern, "", custom_template, flags=re.MULTILINE
                    )
                    # Replace the variable if it's part of a line
                    custom_template = custom_template.replace("{" + key + "}", "")

            result = custom_template.format_map(cleaned_caption_data)
            # Clean up empty lines and format the caption
            result = clean_caption(result)
            # Log successful caption generation at INFO level
            LOGGER.info(
                f"Successfully applied leech caption template (fallback method) for: {filename}"
            )
            # Clean up temporary resources
            if temp_file_created and os.path.exists(file_path_to_use):
                try:
                    os.remove(file_path_to_use)
                    LOGGER.debug(f"Removed temporary file: {file_path_to_use}")
                except Exception as e:
                    LOGGER.debug(f"Failed to remove temporary file: {e}")

            # Clean up temporary directory if created
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil

                    shutil.rmtree(temp_dir)
                    LOGGER.debug(f"Removed temporary directory: {temp_dir}")
                except Exception as e:
                    LOGGER.debug(f"Failed to remove temporary directory: {e}")
            return result
        except Exception as e:
            LOGGER.error(f"Error formatting caption template: {e}")
            # Log that we're falling back to just the filename
            LOGGER.info(
                f"Using filename as caption due to template processing errors: {filename}"
            )
            # Clean up temporary resources
            if temp_file_created and os.path.exists(file_path_to_use):
                try:
                    os.remove(file_path_to_use)
                    LOGGER.debug(f"Removed temporary file: {file_path_to_use}")
                except Exception as e:
                    LOGGER.debug(f"Failed to remove temporary file: {e}")

            # Clean up temporary directory if created
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil

                    shutil.rmtree(temp_dir)
                    LOGGER.debug(f"Removed temporary directory: {temp_dir}")
                except Exception as e:
                    LOGGER.debug(f"Failed to remove temporary directory: {e}")
            return filename


def clean_caption(caption):
    """Clean up caption by removing empty lines and extra whitespace."""
    if not caption:
        return caption

    # Replace multiple consecutive newlines with a single newline
    cleaned = re.sub(r"\n\s*\n+", "\n", caption)

    # Remove leading and trailing whitespace
    cleaned = cleaned.strip()

    # Remove lines that only contain whitespace
    cleaned = re.sub(r"^\s*$\n", "", cleaned, flags=re.MULTILINE)

    return cleaned


def get_video_quality(height):
    if height:
        quality_map = {
            480: "480p",
            540: "540p",
            720: "720p",
            1080: "1080p",
            2160: "2160p",
            4320: "4320p",
            8640: "8640p",
        }
        for threshold, quality in sorted(quality_map.items()):
            if int(height) <= threshold:
                return quality
    return "Unknown"


def parse_audio_language(existing_languages, audio_stream):
    language_code = audio_stream.get("Language")
    if language_code:
        with suppress(Exception):
            language_name = Language.get(language_code).display_name()
            if language_name not in existing_languages:
                LOGGER.debug(f"Parsed audio language: {language_name}")
                existing_languages += f"{language_name}, "
    return existing_languages.strip(", ")


def parse_subtitle_language(existing_subtitles, subtitle_stream):
    subtitle_code = subtitle_stream.get("Language")
    if subtitle_code:
        with suppress(Exception):
            subtitle_name = Language.get(subtitle_code).display_name()
            if subtitle_name not in existing_subtitles:
                LOGGER.debug(f"Parsed subtitle language: {subtitle_name}")
                existing_subtitles += f"{subtitle_name}, "
    return existing_subtitles.strip(", ")


def calculate_md5(file_path):
    md5_hash = md5()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

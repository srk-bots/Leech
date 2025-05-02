"""
File tracking module for duplicate prevention.

This module provides functions to track and identify duplicate files
using various methods like hash-based matching, filename comparison,
content-based detection, size comparison, etc.
"""

import asyncio
import hashlib
import os
import re
from datetime import datetime
from logging import getLogger
from typing import Dict, List, Optional, Tuple, Union

from bot.helper.ext_utils.db_handler import database
from bot.core.config_manager import Config

LOGGER = getLogger(__name__)

# Constants for matching types
MATCH_HASH = "hash"
MATCH_NAME = "name"
MATCH_SIZE = "size"
MATCH_TORRENT = "torrent"
MATCH_TELEGRAM = "telegram"
MATCH_METADATA = "metadata"
MATCH_FUZZY = "fuzzy"


async def calculate_file_hash(file_path: str, block_size: int = 65536) -> str:
    """Calculate MD5 hash of a file.

    Args:
        file_path: Path to the file
        block_size: Size of blocks to read

    Returns:
        MD5 hash of the file
    """
    if not os.path.exists(file_path):
        return ""

    try:
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(block_size), b""):
                md5_hash.update(block)
        return md5_hash.hexdigest()
    except Exception as e:
        LOGGER.error(f"Error calculating hash for {file_path}: {e}")
        return ""


async def calculate_partial_hash(file_path: str, block_size: int = 65536, blocks: int = 3) -> str:
    """Calculate partial MD5 hash of a file (first, middle and last blocks).

    Args:
        file_path: Path to the file
        block_size: Size of blocks to read
        blocks: Number of blocks to read from start and end

    Returns:
        Partial MD5 hash of the file
    """
    if not os.path.exists(file_path):
        return ""

    try:
        file_size = os.path.getsize(file_path)
        if file_size <= block_size * blocks * 2:
            # For small files, just calculate the full hash
            return await calculate_file_hash(file_path, block_size)

        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            # Read first blocks
            for _ in range(blocks):
                data = f.read(block_size)
                md5_hash.update(data)

            # Seek to middle
            f.seek(file_size // 2)
            md5_hash.update(f.read(block_size))

            # Read last blocks
            f.seek(max(0, file_size - (block_size * blocks)))
            for _ in range(blocks):
                data = f.read(block_size)
                if data:  # Check if we've reached EOF
                    md5_hash.update(data)

        return md5_hash.hexdigest()
    except Exception as e:
        LOGGER.error(f"Error calculating partial hash for {file_path}: {e}")
        return ""


def normalize_filename(filename: str) -> str:
    """Normalize a filename for comparison.

    Args:
        filename: Filename to normalize

    Returns:
        Normalized filename
    """
    # Remove common prefixes/suffixes and special characters
    filename = filename.lower()
    # Remove extension
    filename = os.path.splitext(filename)[0]
    # Remove common prefixes like [group] or (group)
    filename = re.sub(r'^\[.*?\]|\(.*?\)', '', filename)
    # Remove special characters and extra spaces
    filename = re.sub(r'[^\w\s]', ' ', filename)
    # Replace multiple spaces with a single space
    filename = re.sub(r'\s+', ' ', filename)
    return filename.strip()


def calculate_filename_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two filenames.

    Args:
        name1: First filename
        name2: Second filename

    Returns:
        Similarity score between 0 and 1
    """
    # Normalize filenames
    norm1 = normalize_filename(name1)
    norm2 = normalize_filename(name2)

    # If either normalized name is empty, return 0
    if not norm1 or not norm2:
        return 0

    # If normalized names are identical, return 1
    if norm1 == norm2:
        return 1

    # Calculate Levenshtein distance
    try:
        from rapidfuzz.distance import Levenshtein

        # Calculate similarity based on Levenshtein distance
        distance = Levenshtein.distance(norm1, norm2)
        max_len = max(len(norm1), len(norm2))

        # Convert distance to similarity score (0-1)
        if max_len == 0:
            return 0
        return 1 - (distance / max_len)
    except ImportError:
        # Fallback to simple matching if rapidfuzz is not available
        # Check if one name contains the other
        if norm1 in norm2 or norm2 in norm1:
            return 0.8

        # Check for common words
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        common_words = words1.intersection(words2)

        if not common_words:
            return 0

        # Calculate Jaccard similarity
        return len(common_words) / len(words1.union(words2))


async def track_file(
    file_path: str,
    file_name: str,
    file_size: int,
    user_id: int,
    drive_id: str = "",
    telegram_id: str = "",
    torrent_hash: str = "",
    metadata: Dict = None,
) -> None:
    """Track a file in the database.

    Args:
        file_path: Path to the file
        file_name: Name of the file
        file_size: Size of the file in bytes
        user_id: User ID
        drive_id: Google Drive ID (optional)
        telegram_id: Telegram file ID (optional)
        torrent_hash: Torrent hash (optional)
        metadata: Additional metadata (optional)
    """
    if not Config.STOP_DUPLICATE or not database.db:
        return

    try:
        # Calculate file hash (partial for large files)
        file_hash = ""
        if os.path.exists(file_path) and os.path.isfile(file_path):
            if file_size > 100 * 1024 * 1024:  # 100MB
                file_hash = await calculate_partial_hash(file_path)
            else:
                file_hash = await calculate_file_hash(file_path)

        # Prepare document
        doc = {
            "name": file_name,
            "size": file_size,
            "user_id": user_id,
            "timestamp": datetime.now()
        }

        if file_hash:
            doc["hash"] = file_hash

        if drive_id:
            doc["drive_id"] = drive_id

        if telegram_id:
            doc["telegram_id"] = telegram_id

        if torrent_hash:
            doc["torrent_hash"] = torrent_hash

        if metadata:
            doc["metadata"] = metadata

        # Insert into database
        await database.db.file_tracker.insert_one(doc)
        LOGGER.info(f"Tracked file: {file_name}")
    except Exception as e:
        LOGGER.error(f"Error tracking file {file_name}: {e}")


async def check_duplicate(
    file_name: str,
    file_size: int = 0,
    file_path: str = "",
    telegram_id: str = "",
    torrent_hash: str = "",
    metadata: Dict = None,
    user_id: int = 0,
) -> Tuple[bool, str, List[Dict]]:
    """Check if a file is a duplicate.

    Args:
        file_name: Name of the file
        file_size: Size of the file in bytes (optional)
        file_path: Path to the file (optional)
        telegram_id: Telegram file ID (optional)
        torrent_hash: Torrent hash (optional)
        metadata: Additional metadata (optional)
        user_id: User ID (optional)

    Returns:
        Tuple of (is_duplicate, match_type, matches)
    """
    if not Config.STOP_DUPLICATE or not database.db:
        return False, "", []

    try:
        matches = []
        match_type = ""

        # 1. Check by torrent hash (most reliable)
        if torrent_hash:
            cursor = database.db.file_tracker.find({"torrent_hash": torrent_hash})
            torrent_matches = await cursor.to_list(length=5)
            if torrent_matches:
                return True, MATCH_TORRENT, torrent_matches

        # 2. Check by Telegram file ID
        if telegram_id:
            cursor = database.db.file_tracker.find({"telegram_id": telegram_id})
            telegram_matches = await cursor.to_list(length=5)
            if telegram_matches:
                return True, MATCH_TELEGRAM, telegram_matches

        # 3. Check by file hash if file exists
        file_hash = ""
        if file_path and os.path.exists(file_path) and os.path.isfile(file_path):
            if file_size > 100 * 1024 * 1024:  # 100MB
                file_hash = await calculate_partial_hash(file_path)
            else:
                file_hash = await calculate_file_hash(file_path)

            if file_hash:
                cursor = database.db.file_tracker.find({"hash": file_hash})
                hash_matches = await cursor.to_list(length=5)
                if hash_matches:
                    return True, MATCH_HASH, hash_matches

        # 4. Check by file size (as a preliminary filter)
        if file_size > 0:
            # Find files with similar size (±1%)
            size_min = int(file_size * 0.99)
            size_max = int(file_size * 1.01)
            cursor = database.db.file_tracker.find({
                "size": {"$gte": size_min, "$lte": size_max}
            })
            size_matches = await cursor.to_list(length=20)

            if size_matches:
                # Further filter by filename similarity
                for match in size_matches:
                    similarity = calculate_filename_similarity(file_name, match["name"])
                    if similarity > 0.8:  # High similarity threshold
                        match["similarity"] = similarity
                        matches.append(match)

                if matches:
                    return True, MATCH_SIZE, sorted(matches, key=lambda x: x.get("similarity", 0), reverse=True)[:5]

        # 5. Check by filename similarity (fuzzy matching)
        normalized_name = normalize_filename(file_name)
        if len(normalized_name) > 3:  # Only check if normalized name is meaningful
            # Use regex for partial matching
            regex_pattern = f".*{re.escape(normalized_name)}.*"
            cursor = database.db.file_tracker.find({
                "name": {"$regex": regex_pattern, "$options": "i"}
            })
            name_matches = await cursor.to_list(length=20)

            if name_matches:
                # Calculate similarity for each match
                for match in name_matches:
                    similarity = calculate_filename_similarity(file_name, match["name"])
                    if similarity > 0.85:  # Higher threshold for name-only matching
                        match["similarity"] = similarity
                        matches.append(match)

                if matches:
                    return True, MATCH_FUZZY, sorted(matches, key=lambda x: x.get("similarity", 0), reverse=True)[:5]

        # 6. Check by metadata if provided
        if metadata and isinstance(metadata, dict):
            # Extract key metadata fields
            meta_queries = []

            if "title" in metadata and metadata["title"]:
                meta_queries.append({"metadata.title": metadata["title"]})

            if "artist" in metadata and metadata["artist"]:
                meta_queries.append({"metadata.artist": metadata["artist"]})

            if "album" in metadata and metadata["album"]:
                meta_queries.append({"metadata.album": metadata["album"]})

            if meta_queries:
                cursor = database.db.file_tracker.find({"$or": meta_queries})
                meta_matches = await cursor.to_list(length=5)
                if meta_matches:
                    return True, MATCH_METADATA, meta_matches

        return False, "", []
    except Exception as e:
        LOGGER.error(f"Error checking duplicate for {file_name}: {e}")
        return False, "", []


async def format_duplicate_message(
    match_type: str,
    matches: List[Dict],
    file_name: str
) -> Tuple[str, Dict]:
    """Format a message for duplicate files.

    Args:
        match_type: Type of match
        matches: List of matching files
        file_name: Name of the file being checked

    Returns:
        Tuple of (message, button)
    """
    from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_telegraph_list

    match_type_desc = {
        MATCH_HASH: "identical hash",
        MATCH_NAME: "identical name",
        MATCH_SIZE: "identical size and similar name",
        MATCH_TORRENT: "identical torrent",
        MATCH_TELEGRAM: "identical Telegram file",
        MATCH_METADATA: "identical metadata",
        MATCH_FUZZY: "similar name",
    }

    desc = match_type_desc.get(match_type, "duplicate")

    msg = f"File with {desc} already exists in the database.\n\n"
    msg += f"File: <code>{file_name}</code>\n\n"
    msg += f"Found {len(matches)} potential duplicate(s):\n\n"

    telegraph_content = []
    content = ""

    for i, match in enumerate(matches, 1):
        match_name = match.get("name", "Unknown")
        match_size = get_readable_file_size(match.get("size", 0))
        match_date = match.get("timestamp", datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        similarity = match.get("similarity", 1.0) * 100

        entry = f"<b>{i}. {match_name}</b>\n"
        entry += f"Size: {match_size}\n"
        entry += f"Added: {match_date}\n"

        if "similarity" in match:
            entry += f"Similarity: {similarity:.1f}%\n"

        if "drive_id" in match:
            drive_url = f"https://drive.google.com/file/d/{match['drive_id']}/view"
            entry += f"<a href='{drive_url}'>Drive Link</a>\n"

        entry += "\n"
        content += entry

        if len(content.encode('utf-8')) > 39000:
            telegraph_content.append(content)
            content = ""

    if content:
        telegraph_content.append(content)

    button = await get_telegraph_list(telegraph_content)

    return msg, button


async def remove_file_tracking(
    file_name: str = None,
    file_hash: str = None,
    telegram_id: str = None,
    torrent_hash: str = None,
    user_id: int = None
) -> int:
    """Remove file tracking entries from the database.

    Args:
        file_name: Name of the file (optional)
        file_hash: Hash of the file (optional)
        telegram_id: Telegram file ID (optional)
        torrent_hash: Torrent hash (optional)
        user_id: User ID (optional)

    Returns:
        Number of entries deleted
    """
    if not database.db:
        return 0

    try:
        # Build query based on provided parameters
        query = {}

        if file_name:
            query["name"] = file_name

        if file_hash:
            query["hash"] = file_hash

        if telegram_id:
            query["telegram_id"] = telegram_id

        if torrent_hash:
            query["torrent_hash"] = torrent_hash

        if user_id:
            query["user_id"] = user_id

        # If no parameters provided, return
        if not query:
            return 0

        # Delete matching entries
        result = await database.db.file_tracker.delete_many(query)
        deleted_count = result.deleted_count

        if deleted_count > 0:
            LOGGER.info(f"Removed {deleted_count} file tracking entries")

        return deleted_count
    except Exception as e:
        LOGGER.error(f"Error removing file tracking entries: {e}")
        return 0

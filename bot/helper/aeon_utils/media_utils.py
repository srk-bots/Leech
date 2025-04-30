"""
Media utilities for the Aeon Utils module.
This file provides compatibility with the existing codebase.
"""

from bot.helper.ext_utils.media_utils import (
    FFMpeg,
    get_media_info,
    get_media_type,
    get_streams,
)

# Re-export the functions from ext_utils.media_utils
__all__ = ["FFMpeg", "get_media_info", "get_media_type", "get_streams"]

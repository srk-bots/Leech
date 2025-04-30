"""
Media utilities for the Aeon Utils module.
This file provides compatibility with the existing codebase.
"""

from bot.helper.ext_utils.media_utils import get_streams, get_media_info, get_media_type, FFMpeg

# Re-export the functions from ext_utils.media_utils
__all__ = ["get_streams", "get_media_info", "get_media_type", "FFMpeg"]

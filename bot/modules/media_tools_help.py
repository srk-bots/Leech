#!/usr/bin/env python3
from asyncio import create_task
from logging import getLogger

from bot.helper.telegram_helper.button_build import ButtonMaker

# No need to import help_messages as we've included the content directly
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_message,
    edit_message,
    send_message,
)

LOGGER = getLogger(__name__)


# Define page content functions
def get_page_content(page_num):
    pages = {
        # Merge pages
        1: get_merge_intro_page(),
        2: get_merge_video_page(),
        3: get_merge_audio_page(),
        4: get_merge_subtitle_page(),
        5: get_merge_image_page(),
        6: get_merge_document_page(),
        7: get_merge_mixed_page(),
        8: get_merge_notes_page(),
        # Watermark pages
        9: get_watermark_intro_page(),
        10: get_watermark_settings_page(),
        # Other pages
        11: get_priority_guide_page(),
        12: get_usage_examples_page(),
        # Metadata page
        13: get_metadata_guide_page(),
    }
    return pages.get(page_num, "Invalid page")


def get_merge_intro_page():
    msg = "<b>Merge Feature Guide (1/13)</b>\n\n"
    msg += "<b>Merge Flags</b>: -merge-video -merge-audio -merge-subtitle -merge-image -merge-pdf -merge-all\n\n"

    msg += '<blockquote expandable="expandable"><b>Multi-Link Usage (reply to first link or file)</b>:\n'
    msg += "<code>/cmd link -m folder_name -merge-video</code> (merge only video files)\n"
    msg += "<code>/cmd link -m folder_name -merge-audio</code> (merge only audio files)\n"
    msg += "<code>/cmd -b -m folder_name -merge-subtitle</code>\n\n"

    msg += "or\n\n"

    msg += (
        "<b>Bulk Usage (reply to text file with links or message with links)</b>:\n"
    )
    msg += "<code>/cmd -b -m folder_name -merge-image</code>\n"
    msg += "<code>/cmd -b -m folder_name -merge-pdf</code>\n"
    msg += "<code>/cmd -b -m folder_name -merge-all</code>\n\n"

    msg += "This allows you to download multiple files from different sources and merge them together. The <code>-m folder_name</code> argument is important as it places all files in the same directory for merging.</blockquote>\n\n"

    msg += '<blockquote expandable="expandable"><b>Examples</b>:\n'
    msg += "<code>/leech https://example.com/videos.zip -merge-video</code> (merge only video files)\n"
    msg += "<code>/mirror https://example.com/music.zip -merge-audio</code> (merge only audio files)\n"
    msg += "<code>/mirror https://example.com/subtitle.zip -merge-subtitle</code> (merge only subtitle files)\n"
    msg += "<code>/leech https://example.com/images.zip -merge-image</code> (creates a collage or grid)\n"
    msg += "<code>/mirror https://example.com/documents.zip -merge-pdf</code> (combines PDFs into one file)\n"
    msg += "<code>/leech https://example.com/alltypes.zip -merge-all</code> (merge all files by type)\n\n"

    msg += "These flags help control which files to merge when using the merge feature. If no flag is specified, the system will automatically analyze the files and choose the best approach.</blockquote>\n\n"

    msg += "<b>Supported Merge Types:</b>\n"
    msg += "• Video + Video + Video + ... (creates a single video file)\n"
    msg += "  - Use <code>-merge-video</code> to preserve all video and subtitle tracks\n"
    msg += "• Audio + Audio + Audio + ... (creates a single audio file)\n"
    msg += "• Subtitle + Subtitle + ... (creates a single subtitle file)\n"
    msg += "• Video + Audio + Subtitle (adds audio and subtitle tracks to video)\n"
    msg += "• Images (creates a collage or horizontal/vertical image)\n"
    msg += "• Documents (combines PDFs into a single document)\n"
    msg += "  - Use <code>-merge-all</code> to preserve all video, audio, and subtitle tracks\n\n"

    msg += '<blockquote expandable="expandable"><b>File Order Preservation</b>:\n'
    msg += (
        "• All files are merged in the same order as they are provided by the user\n"
    )
    msg += "• This applies to all file types: videos, audios, subtitles, images, and documents\n"
    msg += "• The order is especially important for sequential content like video episodes or chapters</blockquote>\n\n"

    return msg


def get_merge_video_page():
    msg = "<b>Video Merging (2/13)</b>\n\n"
    msg += "<b>Video Merging Features:</b>\n"
    msg += "• Combines multiple video files into a single video file\n"
    msg += "• Preserves video quality and aspect ratio when possible\n"
    msg += "• Preserves all video and subtitle tracks when using -merge-video flag\n"
    msg += "• Supports different codecs (h264, h265, vp9, av1)\n"
    msg += "• Can handle videos with different resolutions and framerates\n"
    msg += "• Output format and codec can be configured in Media Tools settings\n"
    msg += "• Supports both concat demuxer (fast) and filter complex (compatible) methods\n\n"

    msg += "<b>Supported Video Formats:</b>\n"
    msg += "• Input: MP4, MKV, AVI, MOV, WebM, FLV, WMV, M4V, TS, 3GP\n"
    msg += "• Output: MKV (default), MP4, WebM, AVI\n"
    msg += "• Codecs: copy (default), h264, h265, vp9, av1\n\n"

    msg += '<blockquote expandable="expandable"><b>Video Merging Tips:</b>\n'
    msg += "• Use MKV container for best compatibility with different codecs\n"
    msg += "• The 'copy' codec is fastest and preserves quality but requires similar source files\n"
    msg += "• Use -merge-video flag to preserve all video and subtitle tracks\n"
    msg += (
        "• For files with different codecs or formats, use filter complex method\n"
    )
    msg += "• Set video quality in Media Tools settings for transcoding operations\n"
    msg += "• Higher CRF values mean lower quality but smaller file size\n"
    msg += "• Recommended CRF values: 18-23 for high quality, 23-28 for medium quality</blockquote>\n\n"

    return msg


def get_merge_audio_page():
    msg = "<b>Audio Merging (3/13)</b>\n\n"
    msg += "<b>Audio Merging Features:</b>\n"
    msg += "• Combines multiple audio files into a single audio file\n"
    msg += "• Preserves audio quality when possible\n"
    msg += "• Supports various audio codecs (AAC, MP3, OPUS, FLAC)\n"
    msg += "• Can handle different bitrates, sampling rates, and channel layouts\n"
    msg += "• Volume normalization available through settings\n"
    msg += "• Output format and codec can be configured in Media Tools settings\n\n"

    msg += "<b>Supported Audio Formats:</b>\n"
    msg += "• Input: MP3, M4A, AAC, FLAC, WAV, OGG, OPUS, WMA\n"
    msg += "• Output: MP3 (default), M4A, FLAC, WAV, OGG\n"
    msg += "• Codecs: copy (default), aac, mp3, opus, flac\n\n"

    msg += '<blockquote expandable="expandable"><b>Audio Merging Tips:</b>\n'
    msg += "• MP3 format is widely compatible but lossy\n"
    msg += "• FLAC format preserves audio quality but results in larger files\n"
    msg += "• AAC offers good quality-to-size ratio for most content\n"
    msg += "• Volume normalization helps balance audio levels across different sources\n"
    msg += "• For audiobooks or podcasts, consider mono audio (1 channel) to reduce file size\n"
    msg += "• 192kbps is a good balance between quality and file size for most content</blockquote>\n\n"

    return msg


def get_merge_subtitle_page():
    msg = "<b>Subtitle Merging (4/13)</b>\n\n"
    msg += "<b>Subtitle Merging Features:</b>\n"
    msg += "• Supports merging multiple subtitle files into a single file\n"
    msg += "• Preserves timing and sequence of subtitles\n"
    msg += "• Can merge different subtitle formats (SRT, VTT, ASS, SSA)\n"
    msg += "• Maintains styling information when merging advanced formats like ASS\n"
    msg += "• Output format can be configured in Media Tools settings\n\n"

    msg += "<b>Supported Subtitle Formats:</b>\n"
    msg += "• Input: SRT, VTT, ASS, SSA, SUB, SBV, LRC, TTML\n"
    msg += "• Output: SRT (default), VTT, ASS, SSA\n"
    msg += "• Features: Text formatting, timing preservation, language detection\n\n"

    msg += '<blockquote expandable="expandable"><b>Subtitle Merging Tips:</b>\n'
    msg += "• SRT format is most widely compatible but lacks styling options\n"
    msg += (
        "• ASS/SSA formats support advanced styling (colors, positioning, fonts)\n"
    )
    msg += "• When merging subtitles with different timings, they will be concatenated sequentially\n"
    msg += "• For multi-language subtitles, use language codes in filenames (movie.en.srt, movie.es.srt)\n"
    msg += "• Subtitle encoding can be configured in Media Tools settings (UTF-8 recommended)\n"
    msg += "• Merged subtitles can be embedded into video files using the mixed media merging feature</blockquote>\n\n"

    return msg


def get_merge_image_page():
    msg = "<b>Image Merging (5/13)</b>\n\n"
    msg += "<b>Image Merging Modes:</b>\n"
    msg += (
        "• <b>Collage Mode</b> - Creates a grid of images (default for 3+ images)\n"
    )
    msg += "• <b>Horizontal Mode</b> - Places images side by side (default for 2 images)\n"
    msg += "• <b>Vertical Mode</b> - Stacks images on top of each other\n\n"

    msg += "<b>Supported Image Formats:</b>\n"
    msg += "• Input: JPG, JPEG, PNG, GIF, BMP, WebP, TIFF, HEIC\n"
    msg += "• Output: JPG (default), PNG, WebP, TIFF\n"
    msg += "• Features: Resolution preservation, quality settings, metadata handling\n\n"

    msg += '<blockquote expandable="expandable"><b>Image Merging Tips:</b>\n'
    msg += "• JPG format offers good compression but is lossy (quality loss)\n"
    msg += "• PNG format preserves quality but results in larger files\n"
    msg += "• WebP offers good balance between quality and file size\n"
    msg += "• For collage mode, you can configure the number of columns in Media Tools settings\n"
    msg += (
        "• Background color for image merging can be customized (default: white)\n"
    )
    msg += "• Images can be resized to a uniform size before merging for better appearance</blockquote>\n\n"

    return msg


def get_merge_document_page():
    msg = "<b>Document Merging (6/13)</b>\n\n"
    msg += "<b>Document Merging Features:</b>\n"
    msg += "• Currently supports merging PDF files\n"
    msg += "• All PDF pages are preserved in the merged document\n"
    msg += "• Maintains original page order\n"
    msg += "• Preserves document metadata when possible\n\n"

    msg += "<b>Supported Document Formats:</b>\n"
    msg += "• Input: PDF\n"
    msg += "• Output: PDF\n"
    msg += "• Features: Page order preservation, metadata retention, bookmark handling\n\n"

    msg += '<blockquote expandable="expandable"><b>Document Merging Tips:</b>\n'
    msg += "• PDF merging works best with similar document types\n"
    msg += "• Page size and orientation are preserved from original documents\n"
    msg += "• Document properties like title and author can be configured in Media Tools settings\n"
    msg += "• Bookmarks from original PDFs are preserved in the merged document\n"
    msg += "• Password-protected PDFs may not merge correctly\n"
    msg += "• Future updates may add support for other document formats</blockquote>\n\n"

    return msg


def get_merge_mixed_page():
    msg = "<b>Mixed Media Merging (7/13)</b>\n\n"
    msg += "<b>Mixed Media Merging Features:</b>\n"
    msg += "• <b>Video + Audio</b>: Adds audio tracks to video files\n"
    msg += "• <b>Video + Subtitle</b>: Embeds subtitle tracks in video files\n"
    msg += "• <b>Video + Audio + Subtitle</b>: Creates complete media package with all tracks\n"
    msg += "• <b>Multiple Audio Tracks</b>: Adds multiple language/quality audio options\n"
    msg += "• <b>Multiple Subtitle Tracks</b>: Embeds multiple language subtitle options\n\n"

    msg += "<b>Mixed Merging Guide:</b>\n"
    msg += "1. Place all files in the same directory using <code>-m folder_name</code>\n"
    msg += "2. Use <code>-merge-all</code> to automatically detect and merge compatible files\n"
    msg += "3. File naming is important for proper track matching:\n"
    msg += "   • Use similar base names (video.mp4, video.srt, video.mp3)\n"
    msg += "   • Or use language codes (movie.mp4, movie.en.srt, movie.es.srt)\n\n"

    msg += '<blockquote expandable="expandable"><b>Advanced Configuration:</b>\n'
    msg += "Use Media Tools settings to configure:\n"
    msg += "• Track selection and ordering\n"
    msg += "• Default audio/subtitle language\n"
    msg += "• Forced subtitle handling\n"
    msg += "• Audio sync adjustment\n"
    msg += "• Default subtitle encoding\n"
    msg += "• Audio normalization options\n"
    msg += "• Video container format (MKV recommended for mixed media)\n"
    msg += "• Metadata preservation options</blockquote>\n\n"

    return msg


def get_merge_notes_page():
    msg = "<b>Merge Notes & Advanced Features (8/13)</b>\n\n"

    msg += "<b>Important Considerations:</b>\n"
    msg += "• File order is preserved during merging (important for sequential content)\n"
    msg += "• Both <code>-merge-video</code> and <code>-merge-all</code> flags preserve all tracks\n"
    msg += "• Mixed media merging works best with MKV container format\n"
    msg += "• Some combinations may require transcoding which affects quality\n"
    msg += "• Large files may require more processing time and resources\n"
    msg += "• Certain format combinations may have compatibility limitations\n"
    msg += "• Original files can be preserved or removed after merging (configurable)\n\n"

    msg += '<blockquote expandable="expandable"><b>Best Practices:</b>\n'
    msg += "• Use MKV container for most versatile track support\n"
    msg += "• Keep filenames consistent for better automatic matching\n"
    msg += "• Use language codes in filenames for multi-language content\n"
    msg += "• Process similar files together for best results\n"
    msg += "• Test settings with smaller files before large merges\n"
    msg += "• Use the -merge-all flag for automatic format detection\n"
    msg += "• Both -merge-video and -merge-all preserve all existing tracks\n"
    msg += "• Configure default settings in Media Tools for consistent results\n"
    msg += "• If merge fails, try using filter complex method\n"
    msg += '• Use "copy" codec when possible to preserve quality</blockquote>\n\n'

    msg += '<blockquote expandable="expandable"><b>Advanced Features</b>:\n'
    msg += "• <b>Concat Demuxer</b>: Fast merging for files with identical codecs\n"
    msg += (
        "• <b>Filter Complex</b>: Advanced merging for files with different codecs\n"
    )
    msg += "• <b>Output Format</b>: Choose the format for merged files (mkv, mp4, mp3, etc.)\n"
    msg += "• <b>Threading</b>: Process multiple files simultaneously\n"
    msg += "• <b>Thread Number</b>: Control parallel processing threads</blockquote>\n\n"

    msg += "<b>Important Notes:</b>\n"
    msg += "• For best results, use the -m flag to place all files in the same directory\n"
    msg += "• The rename flag (-n) will not work with merge operations\n"
    msg += "• Files with identical filenames may cause issues during merging\n"
    msg += "• Original files are removed after successful merge if enabled in settings\n"
    msg += "• User settings take priority over owner settings\n"
    msg += "• Default settings are used if no others are specified\n"

    return msg


def get_watermark_intro_page():
    msg = "<b>Watermark Feature Guide (9/13)</b>\n\n"
    msg += "<b>Watermark Feature</b>\n"
    msg += "Add text overlays to videos and images with customizable appearance.\n\n"

    msg += "<b>Important:</b> Make sure to enable watermark in Media Tools settings before using this feature.\n\n"

    msg += "<b>How to Use</b>:\n"
    msg += "Add the <code>-watermark</code> flag followed by your text in quotes:\n"
    msg += '<code>/leech https://example.com/video.mp4 -watermark "© My Channel"</code>\n\n'

    msg += "You can also use it without any flags. You can set the text and other settings in Media Tools settings. Then run the command:\n"
    msg += "<code>/leech https://example.com/video.mp4</code>\n\n"

    msg += "<b>Supported Media Types</b>:\n"
    msg += "• <b>Videos</b>: MKV, MP4, AVI, MOV, WebM, FLV, WMV, M4V, TS, 3GP\n"
    msg += "• <b>Images</b>: JPG, JPEG, PNG, BMP, WebP, GIF\n\n"

    msg += '<blockquote expandable="expandable"><b>Priority Settings</b>:\n'
    msg += "Watermark follows the same priority settings as the merge feature:\n"
    msg += "• Command line watermark text takes highest priority\n"
    msg += "• User settings take priority over owner settings\n"
    msg += "• Owner settings are used as fallback\n"
    msg += "• Default settings are used if no others are specified\n"
    msg += "• By Default watermark priority is 2 which means it will run after merge feature.</blockquote>\n\n"

    return msg


def get_watermark_settings_page():
    msg = "<b>Watermark Settings (10/13)</b>\n\n"

    msg += "<b>Customizable Settings</b>:\n"
    msg += "• <b>Text</b>: The text to display as watermark\n"
    msg += "• <b>Position</b>: Where to place the watermark\n"
    msg += "• <b>Size</b>: Font size of the watermark text (default: 20)\n"
    msg += "• <b>Color</b>: Color of the watermark text\n"
    msg += "• <b>Font</b>: Font file to use (supports Google Fonts)\n\n"

    msg += '<blockquote expandable="expandable"><b>Position Options</b>:\n'
    msg += "• <b>top_left</b>: Upper left corner\n"
    msg += "• <b>top_right</b>: Upper right corner\n"
    msg += "• <b>bottom_left</b>: Lower left corner\n"
    msg += "• <b>bottom_right</b>: Lower right corner\n"
    msg += "• <b>center</b>: Middle of the video/image\n"
    msg += "• <b>top_center</b>: Top middle\n"
    msg += "• <b>bottom_center</b>: Bottom middle\n"
    msg += "• <b>left_center</b>: Middle left side\n"
    msg += "• <b>right_center</b>: Middle right side</blockquote>\n\n"

    msg += '<blockquote expandable="expandable"><b>Color Options</b>:\n'
    msg += "• <b>Basic Colors</b>: white, black, red, blue, green, yellow, etc.\n"
    msg += "• <b>Hex Colors</b>: #RRGGBB format (e.g., #FF0000 for red)\n"
    msg += "• <b>RGBA Colors</b>: rgba(r,g,b,a) format for transparency\n"
    msg += "• <b>Recommended</b>: White or yellow with black outline for visibility</blockquote>\n\n"

    msg += '<blockquote expandable="expandable"><b>Font Options</b>:\n'
    msg += "• <b>Default</b>: System default sans-serif font\n"
    msg += "• <b>Google Fonts</b>: Any Google Font name (e.g., Roboto, Open Sans)\n"
    msg += "• <b>Custom Fonts</b>: Path to .ttf or .otf file\n"
    msg += "• <b>Recommended</b>: Sans-serif fonts for better readability</blockquote>\n\n"

    msg += '<blockquote expandable="expandable"><b>Advanced Settings</b>:\n'
    msg += "• <b>Opacity</b>: Transparency level of the watermark\n"
    msg += "• <b>Padding</b>: Space between watermark and edge\n"
    msg += "• <b>Shadow</b>: Enable/disable text shadow\n"
    msg += "• <b>Outline</b>: Enable/disable text outline\n"
    msg += "• <b>Threading</b>: Process multiple files simultaneously\n"
    msg += "• <b>Thread Number</b>: Number of parallel processing threads</blockquote>\n\n"

    return msg


def get_priority_guide_page():
    msg = "<b>Media Tools Priority Guide (11/13)</b>\n\n"
    msg += "<b>Understanding Priority Settings:</b>\n"
    msg += "Media tools (merge, watermark) use a priority system to determine the order of processing.\n\n"

    msg += "<b>Priority Values:</b>\n"
    msg += "• Lower number = Higher priority (runs first)\n"
    msg += "• Default merge priority: 1 (runs first)\n"
    msg += "• Default watermark priority: 2 (runs second)\n\n"

    msg += "<b>Priority Hierarchy:</b>\n"
    msg += "1. Command line settings (highest priority)\n"
    msg += "2. User settings (from /usettings)\n"
    msg += "3. Owner settings (from /bsettings)\n"
    msg += "4. Default settings (lowest priority)\n\n"

    msg += "<b>Setting Priority:</b>\n"
    msg += "• Use /mediatools command to set priority\n"
    msg += "• Select 'Media Tools Priority' option\n"
    msg += "• Enter a number (1 for highest priority)\n\n"

    msg += "<b>Example Scenarios:</b>\n"
    msg += "• If merge priority=1 and watermark priority=2:\n"
    msg += "  Files will be merged first, then watermarked\n\n"
    msg += "• If merge priority=2 and watermark priority=1:\n"
    msg += "  Files will be watermarked first, then merged\n\n"

    msg += "<b>Note:</b> Equal priority values will process in default order (merge then watermark)"

    return msg


def get_metadata_guide_page():
    msg = "<b>Metadata Feature Guide (13/13)</b>\n\n"
    msg += "<b>Metadata Feature</b>\n"
    msg += "Add custom metadata to your media files (videos, audio, images) to enhance organization and information.\n\n"

    msg += "<b>How to Use</b>:\n"
    msg += "Add metadata to your files using the following methods:\n"
    msg += "• <code>/leech https://example.com/video.mp4 -metadata 'My Custom Title'</code> (legacy method)\n"
    msg += "• <code>/mirror https://example.com/audio.mp3 -metadata-title 'Song Title'</code>\n"
    msg += "• <code>/leech https://example.com/video.mp4 -metadata-author 'Creator Name'</code>\n"
    msg += "• <code>/mirror https://example.com/audio.mp3 -metadata-comment 'Additional info'</code>\n"
    msg += "• <code>/leech https://example.com/video.mp4 -metadata-all 'Apply to all fields'</code>\n\n"

    msg += "<b>Metadata Types</b>:\n"
    msg += "• <b>Title</b>: The title of the media (shown in players and file managers)\n"
    msg += "• <b>Author</b>: Creator or artist information\n"
    msg += "• <b>Comment</b>: Additional notes or information\n"
    msg += "• <b>All</b>: Single value applied to all metadata fields\n\n"

    msg += "<b>Priority Order</b>:\n"
    msg += "1. Command line arguments (highest priority)\n"
    msg += "2. User settings from /usettings menu\n"
    msg += "3. Global settings from bot owner\n"
    msg += "4. Default values (if any)\n\n"

    msg += '<blockquote expandable="expandable"><b>Supported File Types</b>:\n'
    msg += "• <b>Video</b>: MP4, MKV, WebM, AVI, MOV, etc.\n"
    msg += "• <b>Audio</b>: MP3, M4A, FLAC, OGG, WAV, etc.\n"
    msg += "• <b>Images</b>: JPG, PNG, WebP (limited metadata support)\n"
    msg += "• <b>Documents</b>: PDF (title, author, subject)\n\n"

    msg += "Different file formats support different metadata fields. Some formats may have limitations on which metadata can be modified.</blockquote>\n\n"

    msg += '<blockquote expandable="expandable"><b>Tips for Using Metadata</b>:\n'
    msg += "• Use quotes around metadata values with spaces\n"
    msg += "• Keep metadata concise for better compatibility\n"
    msg += "• Use -metadata-all for quick application to all fields\n"
    msg += "• Individual field settings (-metadata-title, etc.) override -metadata-all\n"
    msg += "• Some players and devices may only display certain metadata fields\n"
    msg += (
        "• Metadata is preserved during file transfers and uploads</blockquote>\n\n"
    )

    msg += '<blockquote expandable="expandable"><b>Examples</b>:\n'
    msg += "• <code>/leech https://example.com/music.zip -metadata-title 'Album Name'</code>\n"
    msg += "  Adds title metadata to all audio files\n\n"
    msg += "• <code>/mirror https://example.com/video.mp4 -metadata-author 'Channel Name'</code>\n"
    msg += "  Sets the author/artist metadata field\n\n"
    msg += "• <code>/leech https://example.com/podcast.mp3 -metadata-all 'My Podcast'</code>\n"
    msg += "  Sets all metadata fields to 'My Podcast'\n\n"
    msg += "• <code>/mirror https://example.com/video.mp4 -metadata-title 'Episode 1' -metadata-author 'My Channel'</code>\n"
    msg += "  Sets multiple metadata fields with different values</blockquote>\n\n"

    msg += "<b>Managing Metadata</b>:\n"
    msg += "• Configure default metadata in your user settings with /usettings\n"
    msg += "• Access the metadata settings page from the main menu\n"
    msg += "• Set different values for different metadata fields\n"
    msg += "• Reset all metadata settings with the 'Reset All Metadata' button\n"

    return msg


def get_usage_examples_page():
    msg = "<b>Media Tools Usage Examples (12/13)</b>\n\n"

    msg += "<b>Merge Examples:</b>\n"
    msg += "• <code>/leech https://example.com/videos.zip -merge-video</code>\n"
    msg += "  Merges all video files in the archive while preserving all video and subtitle tracks\n\n"
    msg += "• <code>/mirror https://example.com/videos.zip -merge-video</code>\n"
    msg += "  Merges videos with multiple video tracks and subtitles preserved\n\n"
    msg += "• <code>/mirror https://example.com/music.zip -merge-audio</code>\n"
    msg += "  Combines all audio files into a single audio file\n\n"
    msg += "• <code>/leech https://example.com/files.zip -m folder_name -merge-all</code>\n"
    msg += "  Merges all files by type in a custom folder while preserving all tracks\n\n"

    msg += "<b>Watermark Examples:</b>\n"
    msg += '• <code>/leech https://example.com/video.mp4 -wm "My Watermark"</code>\n'
    msg += "  Adds text watermark to the video\n\n"
    msg += '• <code>/mirror https://example.com/videos.zip -wm "© 2023"</code>\n'
    msg += "  Adds copyright watermark to all videos\n\n"
    msg += '• <code>/leech https://example.com/images.zip -wm "My Logo" -wm-position 5</code>\n'
    msg += "  Adds watermark at position 5 (bottom-right) to all images\n\n"

    msg += "<b>Combined Usage:</b>\n"
    msg += '• <code>/leech https://example.com/videos.zip -merge-video -wm "My Channel"</code>\n'
    msg += "  Merges videos first, then adds watermark (default priority)\n\n"
    msg += '• <code>/mirror https://example.com/files.zip -m folder -merge-all -wm "© 2023"</code>\n'
    msg += (
        "  Merges files by type while preserving all tracks, then adds watermark\n\n"
    )

    msg += "<b>Note:</b> Use /mediatools command to configure advanced settings"

    return msg


def get_pagination_buttons(current_page):
    buttons = ButtonMaker()

    # Total number of pages
    total_pages = 13

    # Add navigation buttons
    if current_page > 1:
        buttons.data_button("⬅️ Previous", f"mthelp_page_{current_page - 1}")

    # Page indicator
    buttons.data_button(f"Page {current_page}/{total_pages}", "mthelp_current")

    if current_page < total_pages:
        buttons.data_button("Next ➡️", f"mthelp_page_{current_page + 1}")

    # Close button
    buttons.data_button("Close", "mthelp_close", "footer")

    return buttons.build_menu(3)


async def media_tools_help_cmd(_, message):
    """
    Display media tools help with pagination
    """
    # Debug message
    LOGGER.info(
        f"Media tools help command called by {message.from_user.id if message.from_user else 'Unknown user'}",
    )

    # Delete the command message immediately
    await delete_message(message)

    # Start with page 1
    current_page = 1
    content = get_page_content(current_page)
    buttons = get_pagination_buttons(current_page)

    # Send the first page
    help_msg = await send_message(message, content, buttons)

    # Schedule auto-deletion after 5 minutes
    create_task(auto_delete_message(help_msg, time=300))


async def media_tools_help_callback(_, callback_query):
    """
    Handle callback queries for media tools help pagination
    """
    message = callback_query.message
    data = callback_query.data
    user_id = callback_query.from_user.id

    # Debug message
    LOGGER.debug(f"Media tools help callback: {data} from user {user_id}")

    # Handle close button
    if data == "mthelp_close":
        await delete_message(message)
        await callback_query.answer()
        return

    # Skip processing for current page indicator
    if data == "mthelp_current":
        await callback_query.answer("Current page")
        return

    # Extract page number from callback data
    if data.startswith("mthelp_page_"):
        try:
            page_num = int(data.split("_")[-1])
            LOGGER.debug(f"Loading page {page_num}")
            content = get_page_content(page_num)
            buttons = get_pagination_buttons(page_num)

            # Edit the message with new page content
            LOGGER.debug(f"Updating message with page {page_num} content")
            await edit_message(message, content, buttons)
            await callback_query.answer(f"Page {page_num}")
        except Exception as e:
            LOGGER.error(f"Error in media_tools_help_callback: {e!s}")
            await callback_query.answer("Error processing request")


# Handler will be added in core/handlers.py
# Also need to register the callback handler

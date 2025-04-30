#!/usr/bin/env python3
import os
from os import path as ospath
from aiofiles.os import path as aiopath
from aiofiles.os import remove
import shutil

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import cmd_exec

async def apply_document_metadata(file_path, title=None, author=None, comment=None):
    """Apply metadata to document files like PDF using appropriate tools.

    Args:
        file_path: Path to the document file
        title: Title metadata to apply
        author: Author metadata to apply
        comment: Comment metadata to apply

    Returns:
        bool: True if metadata was successfully applied, False otherwise
    """
    ext = ospath.splitext(file_path)[1].lower()

    # Create a temporary file with the same extension
    if ".temp" not in file_path:
        temp_file = f"{file_path}.temp{ext}"
    else:
        temp_file = file_path

    # Handle different document types
    if ext == ".pdf":
        return await apply_pdf_metadata(file_path, temp_file, title, author, comment)
    elif ext in [".epub", ".mobi", ".azw", ".azw3"]:
        return await apply_ebook_metadata(file_path, temp_file, title, author, comment)
    elif ext in [".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp"]:
        return await apply_office_metadata(file_path, temp_file, title, author, comment)
    elif ext in [".txt", ".md", ".csv", ".rtf"]:
        return await apply_text_metadata(file_path, temp_file, title, author, comment)
    else:
        # Try exiftool for other document types
        return await apply_exiftool_metadata(file_path, temp_file, title, author, comment)

async def apply_pdf_metadata(file_path, temp_file, title=None, author=None, comment=None):
    """Apply metadata to PDF files.

    Args:
        file_path: Path to the PDF file
        temp_file: Path to the temporary file
        title: Title metadata to apply
        author: Author metadata to apply
        comment: Comment metadata to apply

    Returns:
        bool: True if metadata was successfully applied, False otherwise
    """
    try:
        # First check if pdftk is installed
        pdftk_check = await cmd_exec(["which", "pdftk"])

        if pdftk_check[0]:  # pdftk is available
            LOGGER.info(f"Using pdftk to apply metadata to {file_path}")

            # Create a temporary info file
            info_file = f"{file_path}.info"
            with open(info_file, "w") as f:
                if title:
                    f.write(f"InfoKey: Title\nInfoValue: {title}\n")
                if author:
                    f.write(f"InfoKey: Author\nInfoValue: {author}\n")
                if comment:
                    f.write(f"InfoKey: Subject\nInfoValue: {comment}\n")

            # Apply metadata
            cmd = [
                "pdftk", file_path,
                "update_info", info_file,
                "output", temp_file
            ]

            result = await cmd_exec(cmd)

            # Clean up
            if await aiopath.exists(info_file):
                await remove(info_file)

            if result[2] == 0 and await aiopath.exists(temp_file):
                os.replace(temp_file, file_path)
                return True
            else:
                if await aiopath.exists(temp_file):
                    await remove(temp_file)
                LOGGER.error(f"pdftk failed: {result[1]}")
                # Fall back to exiftool
                return await apply_exiftool_metadata(file_path, temp_file, title, author, comment)
        else:
            # Fall back to exiftool
            return await apply_exiftool_metadata(file_path, temp_file, title, author, comment)

    except Exception as e:
        LOGGER.error(f"Error applying PDF metadata: {e}")
        # Fall back to exiftool
        return await apply_exiftool_metadata(file_path, temp_file, title, author, comment)

async def apply_ebook_metadata(file_path, temp_file, title=None, author=None, comment=None):
    """Apply metadata to e-book files.

    Args:
        file_path: Path to the e-book file
        temp_file: Path to the temporary file
        title: Title metadata to apply
        author: Author metadata to apply
        comment: Comment metadata to apply

    Returns:
        bool: True if metadata was successfully applied, False otherwise
    """
    try:
        # Check if ebook-meta is available
        ebook_meta_check = await cmd_exec(["which", "ebook-meta"])

        if ebook_meta_check[0]:  # ebook-meta is available
            LOGGER.info(f"Using ebook-meta to apply metadata to {file_path}")

            # Create a copy of the file first
            shutil.copy2(file_path, temp_file)

            # Build the command
            cmd = ["ebook-meta", temp_file]
            if title:
                cmd.extend(["--title", title])
            if author:
                cmd.extend(["--author", author])
            if comment:
                cmd.extend(["--comments", comment])

            result = await cmd_exec(cmd)

            if result[2] == 0:
                os.replace(temp_file, file_path)
                return True
            else:
                if await aiopath.exists(temp_file):
                    await remove(temp_file)
                LOGGER.error(f"ebook-meta failed: {result[1]}")
                # Fall back to exiftool
                return await apply_exiftool_metadata(file_path, temp_file, title, author, comment)
        else:
            # Fall back to exiftool
            return await apply_exiftool_metadata(file_path, temp_file, title, author, comment)

    except Exception as e:
        LOGGER.error(f"Error applying e-book metadata: {e}")
        # Fall back to exiftool
        return await apply_exiftool_metadata(file_path, temp_file, title, author, comment)

async def apply_office_metadata(file_path, temp_file, title=None, author=None, comment=None):
    """Apply metadata to office document files.

    Args:
        file_path: Path to the office document file
        temp_file: Path to the temporary file
        title: Title metadata to apply
        author: Author metadata to apply
        comment: Comment metadata to apply

    Returns:
        bool: True if metadata was successfully applied, False otherwise
    """
    # For office documents, use exiftool
    return await apply_exiftool_metadata(file_path, temp_file, title, author, comment)

async def apply_text_metadata(file_path, temp_file, title=None, author=None, comment=None):
    """Apply metadata to text files by adding a header.

    Args:
        file_path: Path to the text file
        temp_file: Path to the temporary file
        title: Title metadata to apply
        author: Author metadata to apply
        comment: Comment metadata to apply

    Returns:
        bool: True if metadata was successfully applied, False otherwise
    """
    try:
        # For text files, we can add metadata as comments at the top of the file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f_in:
            content = f_in.read()

        with open(temp_file, 'w', encoding='utf-8') as f_out:
            # Add metadata as comments
            if title or author or comment:
                f_out.write("/*\n")
                if title:
                    f_out.write(f"Title: {title}\n")
                if author:
                    f_out.write(f"Author: {author}\n")
                if comment:
                    f_out.write(f"Comment: {comment}\n")
                f_out.write("*/\n\n")

            # Write the original content
            f_out.write(content)

        # Replace the original file
        os.replace(temp_file, file_path)
        return True

    except Exception as e:
        LOGGER.error(f"Error applying text file metadata: {e}")
        if await aiopath.exists(temp_file):
            await remove(temp_file)
        return False

async def apply_exiftool_metadata(file_path, temp_file, title=None, author=None, comment=None):
    """Apply metadata using exiftool.

    Args:
        file_path: Path to the file
        temp_file: Path to the temporary file
        title: Title metadata to apply
        author: Author metadata to apply
        comment: Comment metadata to apply

    Returns:
        bool: True if metadata was successfully applied, False otherwise
    """
    try:
        # Check if exiftool is available
        exiftool_check = await cmd_exec(["which", "exiftool"])

        if exiftool_check[0]:  # exiftool is available
            LOGGER.info(f"Using exiftool to apply metadata to {file_path}")

            cmd = ["exiftool"]
            if title:
                cmd.extend(["-Title=" + title])
            if author:
                cmd.extend(["-Author=" + author, "-Creator=" + author])
            if comment:
                cmd.extend(["-Subject=" + comment, "-Description=" + comment])

            # Add output file
            cmd.extend(["-o", temp_file, file_path])

            result = await cmd_exec(cmd)

            if result[2] == 0 and await aiopath.exists(temp_file):
                os.replace(temp_file, file_path)
                return True
            else:
                if await aiopath.exists(temp_file):
                    await remove(temp_file)
                LOGGER.error(f"exiftool failed: {result[1]}")
                return False
        else:
            LOGGER.warning("exiftool is not available for document metadata")
            return False

    except Exception as e:
        LOGGER.error(f"Error applying exiftool metadata: {e}")
        if await aiopath.exists(temp_file):
            await remove(temp_file)
        return False

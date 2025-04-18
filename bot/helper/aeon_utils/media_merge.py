import logging
import os
import resource
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PyPDF2 import PdfMerger, PdfReader, PdfWriter

from bot.core.config_manager import Config

LOGGER = logging.getLogger(__name__)


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


async def merge_images(
    files, output_format="jpg", mode="collage", columns=None, quality=85
):
    """
    Merge multiple image files into a single image.

    Args:
        files: List of image file paths
        output_format: Output format (jpg, png, etc.)
        mode: 'collage' or 'vertical' or 'horizontal'
        columns: Number of columns for collage mode (auto-calculated if None)
        quality: Output image quality (1-100, only for jpg)

    Returns:
        str: Path to the merged image file
    """
    if not files:
        LOGGER.error("No image files provided for merging")
        return None

    # Apply memory limits for PIL operations
    limit_memory_for_pil()

    try:
        # Use files in the order they were provided
        # (No sorting to preserve user's intended order)
        LOGGER.info(
            f"Merging {len(files)} images in {mode} mode with output format {output_format}"
        )

        # Open all images with error handling
        images = []
        for f in files:
            try:
                img = Image.open(f)

                # Convert to RGB if needed (handle more color modes)
                if img.mode == "RGBA" and output_format.lower() in ["jpg", "jpeg"]:
                    # Create white background for transparent images
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(
                        img, mask=img.split()[3]
                    )  # Use alpha channel as mask
                    img = background
                elif img.mode != "RGB" and output_format.lower() in ["jpg", "jpeg"]:
                    img = img.convert("RGB")

                # Log image details for debugging
                LOGGER.debug(f"Image {f}: size={img.size}, mode={img.mode}")

                images.append(img)
            except Exception as e:
                LOGGER.error(f"Error opening image {f}: {e}")
                # Skip invalid images
                continue

        if not images:
            LOGGER.error("No valid images found for merging")
            return None

        if mode == "vertical":
            # Calculate total height and maximum width
            total_height = sum(img.height for img in images)
            max_width = max(img.width for img in images)

            # Check if we need to resize images to match width
            need_resize = any(img.width != max_width for img in images)
            if need_resize:
                LOGGER.info(f"Resizing images to match width: {max_width}px")
                resized_images = []
                for img in images:
                    if img.width != max_width:
                        # Calculate new height maintaining aspect ratio
                        new_height = int(img.height * (max_width / img.width))
                        resized_img = img.resize(
                            (max_width, new_height), Image.LANCZOS
                        )
                        resized_images.append(resized_img)
                    else:
                        resized_images.append(img)

                # Recalculate total height with resized images
                total_height = sum(img.height for img in resized_images)
                images = resized_images

            # Create a new image with the calculated dimensions
            merged_image = Image.new("RGB", (max_width, total_height))

            # Paste images vertically
            y_offset = 0
            for img in images:
                merged_image.paste(img, (0, y_offset))
                y_offset += img.height

        elif mode == "horizontal":
            # Calculate total width and maximum height
            total_width = sum(img.width for img in images)
            max_height = max(img.height for img in images)

            # Check if we need to resize images to match height
            need_resize = any(img.height != max_height for img in images)
            if need_resize:
                LOGGER.info(f"Resizing images to match height: {max_height}px")
                resized_images = []
                for img in images:
                    if img.height != max_height:
                        # Calculate new width maintaining aspect ratio
                        new_width = int(img.width * (max_height / img.height))
                        resized_img = img.resize(
                            (new_width, max_height), Image.LANCZOS
                        )
                        resized_images.append(resized_img)
                    else:
                        resized_images.append(img)

                # Recalculate total width with resized images
                total_width = sum(img.width for img in resized_images)
                images = resized_images

            # Create a new image with the calculated dimensions
            merged_image = Image.new("RGB", (total_width, max_height))

            # Paste images horizontally
            x_offset = 0
            for img in images:
                merged_image.paste(img, (x_offset, 0))
                x_offset += img.width

        else:  # collage mode
            # Determine number of columns and rows
            if columns is None:
                columns = int(len(images) ** 0.5)  # Square-ish grid

            columns = max(1, min(columns, len(images)))  # Ensure valid column count
            rows = (len(images) + columns - 1) // columns  # Ceiling division

            LOGGER.info(f"Creating collage with {columns}x{rows} grid")

            # Find the average dimensions for better proportions
            avg_width = sum(img.width for img in images) // len(images)
            avg_height = sum(img.height for img in images) // len(images)

            # Decide on cell dimensions - can use average or maximum
            # Using average dimensions with a margin for better aesthetics
            cell_width = int(avg_width * 1.1)  # 10% margin
            cell_height = int(avg_height * 1.1)  # 10% margin

            # Resize all images to fit the cell size while maintaining aspect ratio
            resized_images = []
            for img in images:
                # Calculate scaling factor to fit within cell
                width_ratio = cell_width / img.width
                height_ratio = cell_height / img.height
                scale_factor = min(
                    width_ratio, height_ratio
                )  # Use smaller ratio to fit

                # Calculate new dimensions
                new_width = int(img.width * scale_factor)
                new_height = int(img.height * scale_factor)

                # Resize the image
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)

                # Create a blank cell-sized image with padding
                padded_img = Image.new(
                    "RGB", (cell_width, cell_height), (255, 255, 255)
                )

                # Calculate position to center the image in the cell
                x_offset = (cell_width - new_width) // 2
                y_offset = (cell_height - new_height) // 2

                # Paste the resized image onto the padded image
                padded_img.paste(resized_img, (x_offset, y_offset))
                resized_images.append(padded_img)

            # Update images list with resized images
            images = resized_images

            # Create a new image with the calculated dimensions
            merged_image = Image.new(
                "RGB", (cell_width * columns, cell_height * rows)
            )

            # Paste images in a grid
            for i, img in enumerate(images):
                if i >= len(images):
                    break  # Safety check

                row = i // columns
                col = i % columns
                merged_image.paste(img, (col * cell_width, row * cell_height))

        # Check if we have any valid images
        if not images:
            LOGGER.error("No valid images to merge")
            return None

        # Determine output path
        base_dir = os.path.dirname(files[0])
        output_file = os.path.join(base_dir, f"merged.{output_format}")

        # Ensure output format is compatible with the image mode
        output_format = output_format.lower()

        # Convert image mode if needed for the output format
        if output_format in ["jpg", "jpeg"]:
            if merged_image.mode != "RGB":
                LOGGER.info(
                    f"Converting image mode from {merged_image.mode} to RGB for JPEG output"
                )
                merged_image = merged_image.convert("RGB")
            merged_image.save(output_file, quality=quality)
        elif output_format == "png":
            # PNG supports RGB and RGBA
            merged_image.save(output_file, optimize=True)
        elif output_format == "webp":
            # WebP supports RGB and RGBA with quality setting
            merged_image.save(output_file, quality=quality)
        elif output_format == "gif":
            # GIF requires special handling for transparency
            if merged_image.mode == "RGBA":
                # Convert to P mode with transparency for GIF
                merged_image = merged_image.convert(
                    "P", palette=Image.ADAPTIVE, colors=255
                )
                # Use transparency mask for GIF
                mask = Image.eval(
                    merged_image.split()[3], lambda a: 255 if a <= 128 else 0
                )
                merged_image.save(
                    output_file, transparency=255, optimize=True, mask=mask
                )
            else:
                merged_image.save(output_file)
        else:
            # Default save for other formats
            merged_image.save(output_file)

        LOGGER.info(f"Successfully merged {len(images)} images into {output_file}")
        return output_file

    except Exception as e:
        LOGGER.error(f"Error merging images: {e}")
        return None


async def merge_pdfs(files, output_filename="merged.pdf"):
    """
    Merge multiple PDF files into a single PDF.

    Args:
        files: List of PDF file paths
        output_filename: Name of the output PDF file

    Returns:
        str: Path to the merged PDF file
    """
    if not files:
        LOGGER.error("No PDF files provided for merging")
        return None

    try:
        # Use files in the order they were provided
        # (No sorting to preserve user's intended order)

        # Create a PDF merger object
        merger = PdfMerger()

        # Add each PDF to the merger with error handling
        valid_pdfs = 0
        for pdf in files:
            try:
                # Check if the PDF is valid and not password-protected
                with open(pdf, "rb") as pdf_file:
                    reader = PdfReader(pdf_file)
                    if reader.is_encrypted:
                        LOGGER.warning(f"Skipping encrypted PDF: {pdf}")
                        continue

                # Add the PDF to the merger
                merger.append(pdf)
                valid_pdfs += 1
            except Exception as pdf_error:
                LOGGER.error(f"Error processing PDF {pdf}: {pdf_error}")
                continue

        if valid_pdfs == 0:
            LOGGER.error("No valid PDFs found for merging")
            return None

        # Determine output path
        base_dir = os.path.dirname(files[0])
        output_file = os.path.join(base_dir, output_filename)

        # Write the merged PDF to file
        with open(output_file, "wb") as f:
            merger.write(f)

        # Close the merger
        merger.close()

        LOGGER.info(f"Successfully merged {valid_pdfs} PDFs into {output_file}")
        return output_file

    except Exception as e:
        LOGGER.error(f"Error merging PDFs: {e}")
        return None


async def merge_documents(files, output_format="pdf"):
    """
    Merge multiple document files into a single document.
    Supports PDF merging and converting images to PDF.

    Args:
        files: List of document file paths
        output_format: Output format (currently only 'pdf' is supported)

    Returns:
        str: Path to the merged document file
    """
    if not files:
        LOGGER.error("No document files provided for merging")
        return None

    if output_format.lower() != "pdf":
        LOGGER.error(
            f"Unsupported output format: {output_format}. Only PDF is supported."
        )
        return None

    # Apply memory limits for PIL operations (for image processing)
    limit_memory_for_pil()

    # Group files by extension with validation
    file_groups = {}
    valid_files = []

    for file_path in files:
        # Check if file exists
        if not os.path.exists(file_path):
            LOGGER.error(f"Document file not found: {file_path}")
            continue

        # Get file extension
        ext = Path(file_path).suffix.lower()[1:]  # Remove the dot
        if not ext:
            LOGGER.error(f"File has no extension: {file_path}")
            continue

        # Group by extension
        if ext not in file_groups:
            file_groups[ext] = []
        file_groups[ext].append(file_path)
        valid_files.append(file_path)

    if not valid_files:
        LOGGER.error("No valid files found for merging")
        return None

    # Determine base directory for output
    base_dir = os.path.dirname(valid_files[0])
    output_file = os.path.join(base_dir, "merged.pdf")

    # Case 1: Only PDF files
    if len(file_groups) == 1 and "pdf" in file_groups:
        LOGGER.info("Merging PDF files only")
        return await merge_pdfs(file_groups["pdf"])

    # Case 2: Only image files
    image_extensions = ["jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp"]
    image_files = []
    for ext in image_extensions:
        if ext in file_groups:
            image_files.extend(file_groups[ext])

    if len(image_files) == len(valid_files):
        LOGGER.info("Converting and merging image files to PDF")
        return await create_pdf_from_images(image_files, output_file)

    # Case 3: Mixed file types (PDFs and images)
    LOGGER.info("Merging mixed file types (PDFs and images)")

    # Create a PDF writer for the final output
    writer = PdfWriter()

    # Process PDF files first
    pdf_count = 0
    if "pdf" in file_groups:
        for pdf_path in file_groups["pdf"]:
            try:
                # Check if the PDF is valid and not password-protected
                with open(pdf_path, "rb") as pdf_file:
                    reader = PdfReader(pdf_file)
                    if reader.is_encrypted:
                        LOGGER.warning(f"Skipping encrypted PDF: {pdf_path}")
                        continue

                    # Add all pages from this PDF
                    for page in reader.pages:
                        writer.add_page(page)

                    pdf_count += 1
            except Exception as e:
                LOGGER.error(f"Error processing PDF {pdf_path}: {e}")
                continue

    # Process image files
    image_count = 0
    for img_path in image_files:
        try:
            # Try to open as an image
            img = Image.open(img_path)

            # Convert to RGB if needed
            if img.mode == "RGBA":
                # Create white background for transparent images
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(
                    img, mask=img.split()[3]
                )  # Use alpha channel as mask
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Create a temporary file for the image
            temp_pdf = f"{img_path}.temp.pdf"

            # Save the image as a PDF with better quality
            img.save(temp_pdf, "PDF", resolution=300.0, quality=95)

            # Add the PDF to the writer
            reader = PdfReader(temp_pdf)
            writer.add_page(reader.pages[0])

            # Remove the temporary file
            os.remove(temp_pdf)
            image_count += 1

        except Exception as e:
            LOGGER.error(f"Error processing image {img_path}: {e}")
            continue

    # Check if we have any valid files to merge
    if pdf_count == 0 and image_count == 0:
        LOGGER.error("No valid files found for merging")
        return None

    # Write the merged PDF
    try:
        with open(output_file, "wb") as f:
            writer.write(f)

        LOGGER.info(
            f"Successfully merged {pdf_count} PDFs and {image_count} images into {output_file}"
        )
        return output_file
    except Exception as e:
        LOGGER.error(f"Error writing merged PDF: {e}")
        return None


async def create_pdf_from_images(
    image_files, output_file="merged.pdf", page_size=None
):
    """
    Create a PDF from multiple image files.

    Args:
        image_files: List of image file paths
        output_file: Path to the output PDF file
        page_size: Size of the PDF pages (default: letter size)

    Returns:
        str: Path to the created PDF file
    """
    # Default to letter size if not specified
    if page_size is None:
        page_size = (612, 792)  # Standard letter size
    if not image_files:
        LOGGER.error("No image files provided for PDF creation")
        return None

    # Apply memory limits for PIL operations
    limit_memory_for_pil()

    try:
        # Use files in the order they were provided
        # (No sorting to preserve user's intended order)

        # Create a PDF writer
        writer = PdfWriter()

        # Add each image as a page with improved error handling
        valid_images = 0
        for img_path in image_files:
            try:
                # Check if the file exists
                if not os.path.exists(img_path):
                    LOGGER.error(f"Image file not found: {img_path}")
                    continue

                # Check if the file is a valid image
                try:
                    # Open the image
                    img = Image.open(img_path)

                    # Verify it's a valid image by accessing its properties
                    img.verify()
                    # Need to reopen after verify
                    img = Image.open(img_path)
                except Exception as img_error:
                    LOGGER.error(f"Invalid image file {img_path}: {img_error}")
                    continue

                # Convert to RGB if needed (handle more color modes)
                if img.mode == "RGBA":
                    # Create white background for transparent images
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(
                        img, mask=img.split()[3]
                    )  # Use alpha channel as mask
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Create a temporary file for the image
                temp_pdf = f"{img_path}.temp.pdf"

                # Save the image as a PDF with better quality
                img.save(temp_pdf, "PDF", resolution=300.0, quality=95)

                # Add the PDF to the writer
                reader = PdfReader(temp_pdf)
                writer.add_page(reader.pages[0])

                # Remove the temporary file
                os.remove(temp_pdf)
                valid_images += 1

            except Exception as e:
                LOGGER.error(f"Error processing image {img_path}: {e}")
                continue

        if valid_images == 0:
            LOGGER.error("No valid images found for PDF creation")
            return None

        # Determine output path if not specified
        if not output_file:
            base_dir = os.path.dirname(image_files[0])
            output_file = os.path.join(base_dir, "merged.pdf")

        # Write the merged PDF to file
        with open(output_file, "wb") as f:
            writer.write(f)

        LOGGER.info(
            f"Successfully created PDF from {valid_images} images: {output_file}"
        )
        return output_file

    except Exception as e:
        LOGGER.error(f"Error creating PDF from images: {e}")
        return None


async def add_text_to_image(
    image_path,
    text,
    position=(10, 10),
    font_size=20,
    color=(255, 255, 255),
    font_path=None,
):
    """
    Add text to an image.

    Args:
        image_path: Path to the image file
        text: Text to add
        position: Position of the text (x, y)
        font_size: Size of the font
        color: Color of the text (R, G, B)
        font_path: Path to the font file (optional)

    Returns:
        str: Path to the modified image file
    """
    try:
        # Check if the file exists
        if not os.path.exists(image_path):
            LOGGER.error(f"Image file not found: {image_path}")
            return None

        # Check if the file is a valid image
        try:
            # Open the image
            img = Image.open(image_path)

            # Verify it's a valid image by accessing its properties
            img.verify()
            # Need to reopen after verify
            img = Image.open(image_path)
        except Exception as img_error:
            LOGGER.error(f"Invalid image file {image_path}: {img_error}")
            return None

        # Create a draw object
        draw = ImageDraw.Draw(img)

        # Load a font
        font = None
        if font_path and os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
            except Exception as e:
                LOGGER.error(f"Error loading font {font_path}: {e}")
                font = None

        if font is None:
            # Use default font
            font = ImageFont.load_default()

        # Draw the text
        draw.text(position, text, fill=color, font=font)

        # Save the image
        output_path = f"{os.path.splitext(image_path)[0]}_text{os.path.splitext(image_path)[1]}"
        img.save(output_path)

        LOGGER.info(f"Successfully added text to image: {output_path}")
        return output_path

    except Exception as e:
        LOGGER.error(f"Error adding text to image: {e}")
        return None

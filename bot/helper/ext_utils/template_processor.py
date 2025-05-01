#!/usr/bin/env python3
import gc
import re
from logging import getLogger

from bot.helper.ext_utils.font_utils import (
    FONT_STYLES,
    apply_font_style,
    apply_google_font_style,
    is_google_font,
)

# Legacy implementation is used directly in this file

try:
    from bot.helper.ext_utils.gc_utils import smart_garbage_collection
except ImportError:
    smart_garbage_collection = None

LOGGER = getLogger(__name__)

# Regular expression patterns for template variables with different styling options
# Format: {{{{variable}font1}font2}font3} or {{{variable}font1}font2} or {{variable}font} or {variable}
QUAD_NESTED_TEMPLATE_VAR_PATTERN = r"{{{{([^{}]+)}([^{}]*)}([^{}]*)}([^{}]*)}"
NESTED_TEMPLATE_VAR_PATTERN = r"{{{([^{}]+)}([^{}]*)}([^{}]*)}"
TEMPLATE_VAR_PATTERN = r"{{([^{}]+)}([^{}]*)}|{([^{}]+)}"


async def process_template(template, data_dict):
    """
    Process a template string with advanced formatting options including Google Fonts,
    HTML formatting, Unicode styling, and nested templates.

    Args:
        template (str): The template string with variables in various formats:
                        - {var} - Simple variable
                        - {{var}style} - Variable with styling (Google Font, HTML, Unicode)
                        - {{{var}style1}style2} - Nested styling with two levels
                        - {{{{var}style1}style2}style3} - Nested styling with three levels
                        - Any arbitrary nesting depth with any combination of styles
        data_dict (dict): Dictionary containing values for template variables

    Returns:
        str: The processed template with all variables replaced and formatting applied
    """
    if not template:
        return ""

    # Use the legacy template processor directly
    LOGGER.debug("Using legacy template processor")

    # Legacy template processor for backward compatibility
    # Make a copy of the template to avoid modifying the original
    processed_template = template

    # First, process quadruple nested template variables (four braces)
    # Format: {{{{variable}font1}font2}font3}
    for match in re.finditer(QUAD_NESTED_TEMPLATE_VAR_PATTERN, processed_template):
        var_name = match.group(1).strip()
        style1 = match.group(2).strip() if match.group(2) else None
        style2 = match.group(3).strip() if match.group(3) else None
        style3 = match.group(4).strip() if match.group(4) else None
        original_match = match.group(0)

        if var_name in data_dict:
            value = str(data_dict[var_name])
            LOGGER.debug(
                f"Processing quad nested template: {{{{{{{{var_name}}}}{style1}}}{style2}}}{style3}"
            )
        else:
            # If it's not a template variable, treat it as custom text
            value = var_name
            LOGGER.debug(
                f"Processing custom text in quad nested template: {var_name}"
            )

        # Apply first style (innermost)
        if style1:
            try:
                LOGGER.debug(f"Applying style1: {style1} to {value}")
                # Check if it's a Google Font
                if await is_google_font(style1):
                    value = await apply_google_font_style(value, style1)
                    LOGGER.debug(f"Applied Google Font {style1}, result: {value}")
                # Check if it's an HTML style
                elif style1.lower() in FONT_STYLES:
                    value = await apply_font_style(value, style1)
                    LOGGER.debug(f"Applied HTML style {style1}, result: {value}")
                # Check if it's a single character (emoji/unicode)
                elif (
                    len(style1) == 1 or len(style1) == 2
                ):  # Support for emoji (which can be 2 chars)
                    value = f"{style1}{value}{style1}"
                    LOGGER.debug(f"Applied emoji/unicode {style1}, result: {value}")
                # Special handling for the literal string "style"
                elif style1.lower() == "style":
                    LOGGER.debug(
                        "'style' is a reserved word, not a valid font style. Using code formatting instead."
                    )
                    value = f"<code>{value}</code>"
                else:
                    LOGGER.warning(f"Style1 '{style1}' not recognized")
            except Exception as e:
                LOGGER.error(f"Error applying style1 {style1}: {e}")

            # Apply second style
            if style2:
                try:
                    LOGGER.debug(f"Applying style2: {style2} to {value}")
                    # Check if it's a Google Font
                    if await is_google_font(style2):
                        value = await apply_google_font_style(value, style2)
                        LOGGER.debug(
                            f"Applied Google Font {style2}, result: {value}"
                        )
                    # Check if it's an HTML style
                    elif style2.lower() in FONT_STYLES:
                        value = await apply_font_style(value, style2)
                        LOGGER.debug(f"Applied HTML style {style2}, result: {value}")
                        # Special handling for combined HTML styles
                        if "_" in style2.lower():
                            LOGGER.debug(f"Detected combined HTML style: {style2}")
                    # Check if it's a single character (emoji/unicode)
                    elif (
                        len(style2) == 1 or len(style2) == 2
                    ):  # Support for emoji (which can be 2 chars)
                        value = f"{style2}{value}{style2}"
                        LOGGER.debug(
                            f"Applied emoji/unicode {style2}, result: {value}"
                        )
                    # Special handling for the literal string "style"
                    elif style2.lower() == "style":
                        LOGGER.debug(
                            "'style' is a reserved word, not a valid font style. Using code formatting instead."
                        )
                        value = f"<code>{value}</code>"
                    else:
                        LOGGER.warning(f"Style2 '{style2}' not recognized")
                except Exception as e:
                    LOGGER.error(f"Error applying style2 {style2}: {e}")

            # Apply third style (outermost)
            if style3:
                try:
                    LOGGER.debug(f"Applying style3: {style3} to {value}")
                    # Check if it's a Google Font
                    if await is_google_font(style3):
                        value = await apply_google_font_style(value, style3)
                        LOGGER.debug(
                            f"Applied Google Font {style3}, result: {value}"
                        )
                    # Check if it's an HTML style
                    elif style3.lower() in FONT_STYLES:
                        value = await apply_font_style(value, style3)
                        LOGGER.debug(f"Applied HTML style {style3}, result: {value}")
                        # Special handling for combined HTML styles
                        if "_" in style3.lower():
                            LOGGER.debug(f"Detected combined HTML style: {style3}")
                    # Check if it's a single character (emoji/unicode)
                    elif (
                        len(style3) == 1 or len(style3) == 2
                    ):  # Support for emoji (which can be 2 chars)
                        value = f"{style3}{value}{style3}"
                        LOGGER.debug(
                            f"Applied emoji/unicode {style3}, result: {value}"
                        )
                    # Special handling for the literal string "style"
                    elif style3.lower() == "style":
                        LOGGER.debug(
                            "'style' is a reserved word, not a valid font style. Using code formatting instead."
                        )
                        value = f"<code>{value}</code>"
                    else:
                        LOGGER.warning(f"Style3 '{style3}' not recognized")
                except Exception as e:
                    LOGGER.error(f"Error applying style3 {style3}: {e}")

            # Replace in the template
            LOGGER.debug(f"Replacing {original_match} with {value}")
            processed_template = processed_template.replace(original_match, value)

    # Next, process nested template variables (triple braces)
    # Format: {{{variable}font1}font2}
    for match in re.finditer(NESTED_TEMPLATE_VAR_PATTERN, processed_template):
        var_name = match.group(1).strip()
        inner_style = match.group(2).strip() if match.group(2) else None
        outer_style = match.group(3).strip() if match.group(3) else None
        original_match = match.group(0)

        if var_name in data_dict:
            value = str(data_dict[var_name])
            LOGGER.debug(
                f"Processing nested template: {{{{{var_name}}}{inner_style}}}{outer_style}"
            )
        else:
            # If it's not a template variable, treat it as custom text
            value = var_name
            LOGGER.debug(f"Processing custom text in nested template: {var_name}")

        # Apply inner style first
        if inner_style:
            try:
                LOGGER.debug(f"Applying inner style: {inner_style} to {value}")
                # Check if it's a Google Font
                if await is_google_font(inner_style):
                    value = await apply_google_font_style(value, inner_style)
                    LOGGER.debug(
                        f"Applied Google Font {inner_style}, result: {value}"
                    )
                # Check if it's an HTML style
                elif inner_style.lower() in FONT_STYLES:
                    value = await apply_font_style(value, inner_style)
                    LOGGER.debug(
                        f"Applied HTML style {inner_style}, result: {value}"
                    )
                # Check if it's a single character (emoji/unicode)
                elif (
                    len(inner_style) == 1 or len(inner_style) == 2
                ):  # Support for emoji (which can be 2 chars)
                    value = f"{inner_style}{value}{inner_style}"
                    LOGGER.debug(
                        f"Applied emoji/unicode {inner_style}, result: {value}"
                    )
                # Special handling for the literal string "style"
                elif inner_style.lower() == "style":
                    LOGGER.debug(
                        "'style' is a reserved word, not a valid font style. Using code formatting instead."
                    )
                    value = f"<code>{value}</code>"
                else:
                    LOGGER.warning(f"Inner style '{inner_style}' not recognized")
            except Exception as e:
                LOGGER.error(f"Error applying inner style {inner_style}: {e}")

            # Apply outer style
            if outer_style:
                try:
                    LOGGER.debug(f"Applying outer style: {outer_style} to {value}")
                    # Check if it's a Google Font
                    if await is_google_font(outer_style):
                        value = await apply_google_font_style(value, outer_style)
                        LOGGER.debug(
                            f"Applied Google Font {outer_style}, result: {value}"
                        )
                    # Check if it's an HTML style
                    elif outer_style.lower() in FONT_STYLES:
                        value = await apply_font_style(value, outer_style)
                        LOGGER.debug(
                            f"Applied HTML style {outer_style}, result: {value}"
                        )
                        # Special handling for combined HTML styles to ensure proper nesting
                        if "_" in outer_style.lower():
                            LOGGER.debug(
                                f"Detected combined HTML style: {outer_style}"
                            )
                    # Check if it's a single character (emoji/unicode)
                    elif (
                        len(outer_style) == 1 or len(outer_style) == 2
                    ):  # Support for emoji (which can be 2 chars)
                        value = f"{outer_style}{value}{outer_style}"
                        LOGGER.debug(
                            f"Applied emoji/unicode {outer_style}, result: {value}"
                        )
                    # Special handling for the literal string "style"
                    elif outer_style.lower() == "style":
                        LOGGER.debug(
                            "'style' is a reserved word, not a valid font style. Using code formatting instead."
                        )
                        value = f"<code>{value}</code>"
                    else:
                        LOGGER.warning(f"Outer style '{outer_style}' not recognized")
                except Exception as e:
                    LOGGER.error(f"Error applying outer style {outer_style}: {e}")

            # Replace in the template
            LOGGER.debug(f"Replacing {original_match} with {value}")
            processed_template = processed_template.replace(original_match, value)

    # Function to process regular template variables
    async def replace_match(match):
        # Check which group matched
        if match.group(1) is not None:
            # Format: {{variable}style}
            var_name = match.group(1).strip()
            style_name = match.group(2).strip() if match.group(2) else None
            LOGGER.debug(f"Processing template variable: {{{var_name}}}{style_name}")

            # Get the variable value
            if var_name in data_dict:
                value = str(data_dict[var_name])
                LOGGER.debug(f"Variable {var_name} value: {value}")

                # Apply styling if specified
                if style_name:
                    try:
                        LOGGER.debug(f"Applying style: {style_name} to {value}")
                        # Check if it's a Google Font
                        if await is_google_font(style_name):
                            styled_value = await apply_google_font_style(
                                value, style_name
                            )
                            LOGGER.debug(
                                f"Applied Google Font {style_name}, result: {styled_value}"
                            )
                            return styled_value
                        # Check if it's an HTML style
                        if style_name.lower() in FONT_STYLES:
                            styled_value = await apply_font_style(value, style_name)
                            LOGGER.debug(
                                f"Applied HTML style {style_name}, result: {styled_value}"
                            )
                            return styled_value
                        # Check if it's a single character (emoji/unicode)
                        if (
                            len(style_name) == 1 or len(style_name) == 2
                        ):  # Support for emoji (which can be 2 chars)
                            styled_value = f"{style_name}{value}{style_name}"
                            LOGGER.debug(
                                f"Applied emoji/unicode {style_name}, result: {styled_value}"
                            )
                            return styled_value
                        # Special handling for the literal string "style"
                        if style_name.lower() == "style":
                            LOGGER.debug(
                                "'style' is a reserved word, not a valid font style. Using code formatting instead."
                            )
                            return f"<code>{value}</code>"
                        LOGGER.warning(f"Style '{style_name}' not recognized")
                        return value
                    except Exception as e:
                        LOGGER.error(f"Error applying style {style_name}: {e}")
                        return value
                return value
            # If it's not a template variable, treat it as custom text
            value = var_name
            LOGGER.debug(f"Custom text: {var_name}")

            # Apply styling if specified
            if style_name:
                try:
                    LOGGER.debug(f"Applying style: {style_name} to {value}")
                    # Check if it's a Google Font
                    if await is_google_font(style_name):
                        styled_value = await apply_google_font_style(
                            value, style_name
                        )
                        LOGGER.debug(
                            f"Applied Google Font {style_name}, result: {styled_value}"
                        )
                        return styled_value
                    # Check if it's an HTML style
                    if style_name.lower() in FONT_STYLES:
                        styled_value = await apply_font_style(value, style_name)
                        LOGGER.debug(
                            f"Applied HTML style {style_name}, result: {styled_value}"
                        )
                        # Special handling for combined HTML styles
                        if "_" in style_name.lower():
                            LOGGER.debug(
                                f"Detected combined HTML style: {style_name}"
                            )
                        return styled_value
                    # Check if it's a single character (emoji/unicode)
                    if (
                        len(style_name) == 1 or len(style_name) == 2
                    ):  # Support for emoji (which can be 2 chars)
                        styled_value = f"{style_name}{value}{style_name}"
                        LOGGER.debug(
                            f"Applied emoji/unicode {style_name}, result: {styled_value}"
                        )
                        return styled_value
                    # Special handling for the literal string "style"
                    if style_name.lower() == "style":
                        LOGGER.debug(
                            "'style' is a reserved word, not a valid font style. Using code formatting instead."
                        )
                        return f"<code>{value}</code>"
                    LOGGER.warning(f"Style '{style_name}' not recognized")
                    return f"<code>{value}</code>"
                except Exception as e:
                    LOGGER.error(f"Error applying style {style_name}: {e}")
                    return value
            return value
            LOGGER.debug(f"Variable {var_name} not found in data dictionary")
            return match.group(0)  # Return the original if variable not found
        # Format: {variable}
        var_name = match.group(3).strip()
        LOGGER.debug(f"Processing simple variable: {var_name}")
        if var_name in data_dict:
            value = str(data_dict[var_name])
            LOGGER.debug(f"Variable {var_name} value: {value}")
            return value
        LOGGER.debug(f"Variable {var_name} not found in data dictionary")
        # For simple variables, we don't treat them as custom text
        # to maintain backward compatibility
        return match.group(0)  # Return the original if variable not found

    # Process regular template variables
    result = processed_template
    for match in re.finditer(TEMPLATE_VAR_PATTERN, processed_template):
        replacement = await replace_match(match)
        result = result.replace(match.group(0), replacement)

    # Final processing of HTML tags to ensure they're properly formatted
    processed_result = await process_html_tags(result)

    # Force garbage collection after processing complex templates
    # This can create many temporary strings and objects
    if smart_garbage_collection and len(template) > 1000:  # Only for large templates
        # Use normal mode for template processing
        smart_garbage_collection(aggressive=False)
    elif len(template) > 1000:  # Only for large templates
        # Only collect generation 0 (youngest objects) for better performance
        gc.collect(0)

    return processed_result


async def process_html_tags(text):
    """
    Process HTML tags in the text to ensure they are properly formatted.

    Args:
        text (str): Text that may contain HTML tags

    Returns:
        str: Text with properly formatted HTML tags
    """
    # Check for common HTML tag issues
    if not text:
        return text

    # Log the HTML processing
    LOGGER.debug(f"Processing HTML tags in: {text}")

    # This function can be expanded to handle more complex HTML processing if needed
    # For now, we just validate that tags are properly nested

    # Check for unclosed tags
    open_tags = []
    # List of supported Electrogram HTML tags
    supported_tags = [
        "b",
        "strong",
        "i",
        "em",
        "u",
        "s",
        "del",
        "strike",
        "spoiler",
        "code",
        "pre",
        "blockquote",
        "a",
    ]

    # Check for expandable blockquotes and ensure they have multiple lines
    expandable_blockquote_pattern = (
        r"<blockquote\s+expandable[^>]*>(.*?)</blockquote>"
    )
    for match in re.finditer(expandable_blockquote_pattern, text, re.DOTALL):
        content = match.group(1)
        if "\n" not in content:
            # Add a newline to ensure it works as expandable
            new_content = content + "\n "
            text = text.replace(
                match.group(0), f"<blockquote expandable>{new_content}</blockquote>"
            )
            LOGGER.debug(
                "Added newline to expandable blockquote to ensure it works properly"
            )

    for match in re.finditer(r"<([a-z0-9_-]+)[^>]*>", text, re.IGNORECASE):
        tag = match.group(1).lower()
        if tag not in ["br", "hr", "img"]:
            if tag not in supported_tags:
                LOGGER.warning(f"Unsupported HTML tag: {tag} in: {text}")
                # Consider replacing unsupported tags with supported alternatives
                if tag == "tg-spoiler":
                    text = text.replace(f"<{tag}", "<spoiler").replace(
                        f"</{tag}>", "</spoiler>"
                    )
            open_tags.append(tag)

    for match in re.finditer(r"</([a-z0-9_-]+)>", text, re.IGNORECASE):
        close_tag = match.group(1).lower()
        if open_tags and open_tags[-1] == close_tag:
            open_tags.pop()
        else:
            LOGGER.warning(f"Potentially mismatched HTML tags in: {text}")

    if open_tags:
        LOGGER.warning(f"Unclosed HTML tags: {open_tags} in: {text}")

    # Return the potentially modified text
    # Force garbage collection if the text is very large
    if smart_garbage_collection and len(text) > 10000:  # Only for very large texts
        # Use normal mode for HTML processing
        smart_garbage_collection(aggressive=False)
    elif len(text) > 10000:  # Only for very large texts
        # Only collect generation 0 (youngest objects) for better performance
        gc.collect(0)

    return text

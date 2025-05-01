import json
import urllib.parse
from asyncio import create_task

from httpx import AsyncClient, Timeout

from bot import LOGGER, user_data
from bot.core.config_manager import Config
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_message,
    send_message,
)


async def send_long_message(message, text, time=300):
    """
    Split and send long messages that exceed Telegram's 4096 character limit

    Args:
        message: Message to reply to
        text: Text content to send
        time: Time in seconds after which to auto-delete the messages

    Returns:
        List of sent message objects
    """
    # Maximum length for a single Telegram message
    MAX_LENGTH = 4000  # Using 4000 instead of 4096 to be safe

    # If the message is short enough, send it as is
    if len(text) <= MAX_LENGTH:
        msg = await send_message(message, text)
        create_task(auto_delete_message(msg, time=time))  # noqa: RUF006
        return [msg]

    # Split the message into chunks
    chunks = []
    current_chunk = ""

    # Split by paragraphs first (double newlines)
    paragraphs = text.split("\n\n")

    for paragraph in paragraphs:
        # If adding this paragraph would exceed the limit, start a new chunk
        if len(current_chunk) + len(paragraph) + 2 > MAX_LENGTH:
            # If the current chunk is not empty, add it to chunks
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            # If the paragraph itself is too long, split it by sentences
            if len(paragraph) > MAX_LENGTH:
                sentences = paragraph.replace(". ", ".\n").split("\n")
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 2 > MAX_LENGTH:
                        if current_chunk:
                            chunks.append(current_chunk)
                            current_chunk = ""

                        # If the sentence is still too long, split it by words
                        if len(sentence) > MAX_LENGTH:
                            words = sentence.split(" ")
                            for word in words:
                                if len(current_chunk) + len(word) + 1 > MAX_LENGTH:
                                    chunks.append(current_chunk)
                                    current_chunk = word + " "
                                else:
                                    current_chunk += word + " "
                        else:
                            current_chunk = sentence + "\n\n"
                    else:
                        current_chunk += sentence + "\n\n"
            else:
                current_chunk = paragraph + "\n\n"
        else:
            current_chunk += paragraph + "\n\n"

    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk)

    # Send each chunk as a separate message
    sent_messages = []
    for i, chunk in enumerate(chunks):
        # Add part number if there are multiple chunks
        if len(chunks) > 1:
            prefix = f"<b>Part {i + 1}/{len(chunks)}</b>\n\n"
            chunk = prefix + chunk

        msg = await send_message(message, chunk)
        create_task(auto_delete_message(msg, time=time))  # noqa: RUF006
        sent_messages.append(msg)

    return sent_messages


@new_task
async def ask_ai(_, message):
    """
    Command handler for /ask
    Sends user's question to the configured AI provider and displays the response
    """
    # Check if message is valid
    if not message or not hasattr(message, "from_user") or not message.from_user:
        LOGGER.error("Invalid message object received in ask_ai")
        return

    # Check if message has text
    if not hasattr(message, "text") or not message.text:
        LOGGER.error("Message without text received in ask_ai")
        return

    # Check if Extra Modules are enabled
    if not Config.ENABLE_EXTRA_MODULES:
        error_msg = await send_message(
            message,
            "❌ <b>AI module is currently disabled.</b>\n\nPlease contact the bot owner to enable it.",
        )
        # Auto-delete error message after 5 minutes
        create_task(auto_delete_message(error_msg, message, time=300))  # noqa: RUF006
        return

    user_id = message.from_user.id

    # Get user-specific settings if available
    user_dict = user_data.get(user_id, {})

    # Determine which AI provider to use (user settings take priority)
    ai_provider = user_dict.get(
        "DEFAULT_AI_PROVIDER", Config.DEFAULT_AI_PROVIDER
    ).lower()

    # Check if this is a direct command without arguments (e.g., just "/ask")
    # In this case, we should show the help message
    if (
        not hasattr(message, "text")
        or not message.text
        or message.text.strip() == f"/{message.command[0]}"
        if (hasattr(message, "command") and message.command)
        else False
    ):
        provider_name = ai_provider.capitalize()
        help_msg = await send_message(
            message,
            f"🧠 <b>{provider_name} AI Chatbot</b>\n\n"
            "💓 <b>Command:</b> /ask <i>your question</i>\n\n"
            "👼 <b>Answer:</b> Send me your question to chat with AI.\n\n"
            f"🤖 <b>Current AI Provider:</b> {provider_name}\n\n"
            "⏳ <b>Wait for Answer:</b> On✅",
        )
        # Auto-delete help message after 5 minutes
        create_task(auto_delete_message(help_msg, time=300))  # noqa: RUF006
        # Auto-delete command message after 5 minutes
        create_task(auto_delete_message(message, time=300))  # noqa: RUF006
        return

    # Extract the question from the message
    try:
        # Simple approach: if the message starts with a command (like /ask), extract everything after it
        if hasattr(message, "text") and message.text:
            # Check if the message starts with a command
            if message.text.startswith("/"):
                # Find the first space after the command
                space_index = message.text.find(" ")
                if space_index != -1:
                    # Extract everything after the first space
                    question = message.text[space_index + 1 :].strip()
                else:
                    # No space found, so no question
                    error_msg = await send_message(
                        message,
                        "❌ <b>Error:</b> Could not extract your question. Please use the format: /ask your question here",
                    )
                    # Auto-delete error message after 5 minutes
                    create_task(auto_delete_message(error_msg, time=300))  # noqa: RUF006
                    # Auto-delete command message after 5 minutes
                    create_task(auto_delete_message(message, time=300))  # noqa: RUF006
                    return
            else:
                # Not a command, use the entire message as the question
                question = message.text.strip()
        else:
            # If we can't extract a question, show an error
            error_msg = await send_message(
                message,
                "❌ <b>Error:</b> Could not extract your question. Please use the format: /ask your question here",
            )
            # Auto-delete error message after 5 minutes
            create_task(auto_delete_message(error_msg, time=300))  # noqa: RUF006
            # Auto-delete command message after 5 minutes
            create_task(auto_delete_message(message, time=300))  # noqa: RUF006
            return
    except Exception as e:
        # Handle any exceptions that might occur
        LOGGER.error(f"Error extracting question: {e!s}")
        error_msg = await send_message(
            message,
            "❌ <b>Error:</b> Could not extract your question. Please use the format: /ask your question here",
        )
        # Auto-delete error message after 5 minutes
        create_task(auto_delete_message(error_msg, time=300))  # noqa: RUF006
        # Auto-delete command message after 5 minutes
        create_task(auto_delete_message(message, time=300))  # noqa: RUF006
        return

    # Send a waiting message
    wait_msg = await send_message(message, "⏳ <b>Processing your request...</b>")

    try:
        # Process the request based on the AI provider
        if ai_provider == "mistral":
            # Get Mistral API settings
            api_key = user_dict.get("MISTRAL_API_KEY", Config.MISTRAL_API_KEY)
            api_url = user_dict.get("MISTRAL_API_URL", Config.MISTRAL_API_URL)

            # Check if we have either an API key or URL
            if not api_key and not api_url:
                error_msg = await send_message(
                    message,
                    "❌ <b>Error:</b> No API key or URL configured for Mistral AI. Please set up Mistral AI in settings.",
                )
                # Auto-delete error message after 5 minutes
                create_task(auto_delete_message(error_msg, time=300))  # noqa: RUF006
                # Auto-delete command message after 5 minutes
                create_task(auto_delete_message(message, time=300))  # noqa: RUF006
                await delete_message(wait_msg)
                return

            # Get response from Mistral AI
            response = await get_ai_response(question, api_key, api_url, user_id)
            provider_display = "Mistral AI"

        elif ai_provider == "deepseek":
            # Get DeepSeek API settings
            api_key = user_dict.get("DEEPSEEK_API_KEY", Config.DEEPSEEK_API_KEY)
            api_url = user_dict.get("DEEPSEEK_API_URL", Config.DEEPSEEK_API_URL)

            # Check if we have either an API key or URL
            if not api_key and not api_url:
                error_msg = await send_message(
                    message,
                    "❌ <b>Error:</b> No API key or URL configured for DeepSeek AI. Please set up DeepSeek AI in settings.",
                )
                # Auto-delete error message after 5 minutes
                create_task(auto_delete_message(error_msg, time=300))  # noqa: RUF006
                # Auto-delete command message after 5 minutes
                create_task(auto_delete_message(message, time=300))  # noqa: RUF006
                await delete_message(wait_msg)
                return

            # Get response from DeepSeek AI
            response = await get_deepseek_response(
                question, api_key, api_url, user_id
            )
            provider_display = "DeepSeek AI"

        elif ai_provider == "chatgpt":
            # Get ChatGPT API settings
            api_key = user_dict.get("CHATGPT_API_KEY", Config.CHATGPT_API_KEY)
            api_url = user_dict.get("CHATGPT_API_URL", Config.CHATGPT_API_URL)

            # Check if we have either an API key or URL
            if not api_key and not api_url:
                error_msg = await send_message(
                    message,
                    "❌ <b>Error:</b> No API key or URL configured for ChatGPT. Please set up ChatGPT in settings.",
                )
                # Auto-delete error message after 5 minutes
                create_task(auto_delete_message(error_msg, time=300))  # noqa: RUF006
                # Auto-delete command message after 5 minutes
                create_task(auto_delete_message(message, time=300))  # noqa: RUF006
                await delete_message(wait_msg)
                return

            # Get response from ChatGPT
            response = await get_chatgpt_response(
                question, api_key, api_url, user_id
            )
            provider_display = "ChatGPT"

        elif ai_provider == "gemini":
            # Get Gemini API settings
            api_key = user_dict.get("GEMINI_API_KEY", Config.GEMINI_API_KEY)
            api_url = user_dict.get("GEMINI_API_URL", Config.GEMINI_API_URL)

            # Check if we have either an API key or URL
            if not api_key and not api_url:
                error_msg = await send_message(
                    message,
                    "❌ <b>Error:</b> No API key or URL configured for Gemini AI. Please set up Gemini AI in settings.",
                )
                # Auto-delete error message after 5 minutes
                create_task(auto_delete_message(error_msg, time=300))  # noqa: RUF006
                # Auto-delete command message after 5 minutes
                create_task(auto_delete_message(message, time=300))  # noqa: RUF006
                await delete_message(wait_msg)
                return

            # Get response from Gemini AI
            response = await get_gemini_response(question, api_key, api_url, user_id)
            provider_display = "Gemini AI"

        elif ai_provider == "custom":
            # Get Custom API URL
            api_url = user_dict.get("CUSTOM_AI_API_URL", Config.CUSTOM_AI_API_URL)

            # Check if we have a custom API URL
            if not api_url:
                error_msg = await send_message(
                    message,
                    "❌ <b>Error:</b> No custom API URL configured. Please set up a custom API URL in settings.",
                )
                # Auto-delete error message after 5 minutes
                create_task(auto_delete_message(error_msg, time=300))  # noqa: RUF006
                # Auto-delete command message after 5 minutes
                create_task(auto_delete_message(message, time=300))  # noqa: RUF006
                await delete_message(wait_msg)
                return

            # Get response from Custom API
            response = await get_custom_ai_response(question, api_url, user_id)
            provider_display = "Custom AI"

        else:
            # Default to Mistral if the provider is not recognized
            api_key = user_dict.get("MISTRAL_API_KEY", Config.MISTRAL_API_KEY)
            api_url = user_dict.get("MISTRAL_API_URL", Config.MISTRAL_API_URL)

            # Check if we have either an API key or URL
            if not api_key and not api_url:
                error_msg = await send_message(
                    message,
                    "❌ <b>Error:</b> No API key or URL configured for Mistral AI. Please set up Mistral AI in settings.",
                )
                # Auto-delete error message after 5 minutes
                create_task(auto_delete_message(error_msg, time=300))  # noqa: RUF006
                # Auto-delete command message after 5 minutes
                create_task(auto_delete_message(message, time=300))  # noqa: RUF006
                await delete_message(wait_msg)
                return

            # Get response from Mistral AI
            response = await get_ai_response(question, api_key, api_url, user_id)
            provider_display = "Mistral AI"

        # Format the response
        formatted_response = f"🤖 <b>{provider_display}:</b>\n\n{response}"

        # Send the response using the long message handler to handle message length limits
        # This will automatically handle messages that are too long for Telegram
        await send_long_message(message, formatted_response, time=300)

    except Exception as e:
        LOGGER.error(f"Error in AI response: {e!s}")
        error_msg = await send_message(message, f"❌ <b>Error:</b> {e!s}")
        # Auto-delete error message after 5 minutes
        create_task(auto_delete_message(error_msg, time=300))  # noqa: RUF006

    # Delete the waiting message
    await delete_message(wait_msg)

    # Auto-delete the command message after 5 minutes
    create_task(auto_delete_message(message, time=300))  # noqa: RUF006


async def get_ai_response(question, api_key, api_url, user_id):
    """
    Get a response from the AI using either direct API key or external API URL
    Falls back to the other method if one fails
    """
    # Try with API key first if available
    if api_key:
        try:
            return await get_response_with_api_key(question, api_key)
        except Exception as e:
            LOGGER.warning(f"Failed to get response with API key: {e!s}")
            # If API URL is available, try that as fallback
            if api_url:
                LOGGER.info("Falling back to external API URL")
                return await get_response_with_api_url(question, api_url, user_id)
            raise e

    # If no API key but URL is available
    elif api_url:
        try:
            return await get_response_with_api_url(question, api_url, user_id)
        except Exception as e:
            raise Exception(
                f"Failed to get response from external API: {e!s}"
            ) from e

    # This should never happen due to earlier checks
    raise Exception("No API key or URL configured")


async def get_response_with_api_key(question, api_key):
    """
    Get a response from Mistral AI using the official API
    """
    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    data = {
        "model": "mistral-small-latest",
        "messages": [{"role": "user", "content": question}],
    }

    timeout = Timeout(30.0, connect=10.0)

    async with AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=data)

        if response.status_code != 200:
            raise Exception(
                f"API returned status code {response.status_code}: {response.text}"
            )

        response_data = response.json()
        return response_data["choices"][0]["message"]["content"]


async def get_response_with_api_url(question, api_url, user_id):
    """
    Get a response from Mistral AI using an external API URL
    """
    # Use the more flexible custom AI response function
    return await get_custom_ai_response(question, api_url, user_id)


async def get_deepseek_response(question, api_key, api_url, user_id):
    """
    Get a response from the DeepSeek AI using either direct API key or external API URL
    Falls back to the other method if one fails
    """
    # Try with API key first if available
    if api_key:
        try:
            return await get_deepseek_response_with_api_key(question, api_key)
        except Exception as e:
            LOGGER.warning(f"Failed to get response with API key: {e!s}")
            # If API URL is available, try that as fallback
            if api_url:
                LOGGER.info("Falling back to external API URL")
                return await get_deepseek_response_with_api_url(
                    question, api_url, user_id
                )
            raise e

    # If no API key but URL is available
    elif api_url:
        try:
            return await get_deepseek_response_with_api_url(
                question, api_url, user_id
            )
        except Exception as e:
            raise Exception(
                f"Failed to get response from external API: {e!s}"
            ) from e

    # This should never happen due to earlier checks
    raise Exception("No API key or URL configured")


async def get_deepseek_response_with_api_key(question, api_key):
    """
    Get a response from DeepSeek AI using the official API
    """
    url = "https://api.deepseek.com/v1/chat/completions"  # This is a placeholder URL

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    data = {
        "model": "deepseek-chat",  # This is a placeholder model name
        "messages": [{"role": "user", "content": question}],
    }

    timeout = Timeout(30.0, connect=10.0)

    async with AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=data)

        if response.status_code != 200:
            raise Exception(
                f"API returned status code {response.status_code}: {response.text}"
            )

        response_data = response.json()
        return response_data["choices"][0]["message"]["content"]


async def get_deepseek_response_with_api_url(question, api_url, user_id):
    """
    Get a response from DeepSeek AI using an external API URL
    """
    # Use the more flexible custom AI response function
    return await get_custom_ai_response(question, api_url, user_id)


async def get_chatgpt_response(question, api_key, api_url, user_id):
    """
    Get a response from ChatGPT using either direct API key or external API URL
    Falls back to the other method if one fails
    """
    # Try with API key first if available
    if api_key:
        try:
            return await get_chatgpt_response_with_api_key(question, api_key)
        except Exception as e:
            LOGGER.warning(f"Failed to get response with API key: {e!s}")
            # If API URL is available, try that as fallback
            if api_url:
                LOGGER.info("Falling back to external API URL")
                return await get_chatgpt_response_with_api_url(
                    question, api_url, user_id
                )
            raise e

    # If no API key but URL is available
    elif api_url:
        try:
            return await get_chatgpt_response_with_api_url(
                question, api_url, user_id
            )
        except Exception as e:
            raise Exception(
                f"Failed to get response from external API: {e!s}"
            ) from e

    # This should never happen due to earlier checks
    raise Exception("No API key or URL configured")


async def get_chatgpt_response_with_api_key(question, api_key):
    """
    Get a response from ChatGPT using the official OpenAI API
    """
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": question}],
    }

    timeout = Timeout(30.0, connect=10.0)

    async with AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=data)

        if response.status_code != 200:
            raise Exception(
                f"API returned status code {response.status_code}: {response.text}"
            )

        response_data = response.json()
        return response_data["choices"][0]["message"]["content"]


async def get_chatgpt_response_with_api_url(question, api_url, user_id):
    """
    Get a response from ChatGPT using an external API URL
    """
    # Use the more flexible custom AI response function
    return await get_custom_ai_response(question, api_url, user_id)


async def get_gemini_response(question, api_key, api_url, user_id):
    """
    Get a response from the Gemini AI using either direct API key or external API URL
    Falls back to the other method if one fails
    """
    # Try with API key first if available
    if api_key:
        try:
            return await get_gemini_response_with_api_key(question, api_key)
        except Exception as e:
            LOGGER.warning(f"Failed to get response with API key: {e!s}")
            # If API URL is available, try that as fallback
            if api_url:
                LOGGER.info("Falling back to external API URL")
                return await get_gemini_response_with_api_url(
                    question, api_url, user_id
                )
            raise e

    # If no API key but URL is available
    elif api_url:
        try:
            return await get_gemini_response_with_api_url(question, api_url, user_id)
        except Exception as e:
            raise Exception(
                f"Failed to get response from external API: {e!s}"
            ) from e

    # This should never happen due to earlier checks
    raise Exception("No API key or URL configured")


async def get_gemini_response_with_api_key(question, api_key):
    """
    Get a response from Gemini AI using the official Google AI API
    """
    # Format the URL with the API key
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"

    headers = {
        "Content-Type": "application/json",
    }

    data = {"contents": [{"parts": [{"text": question}]}]}

    timeout = Timeout(30.0, connect=10.0)

    async with AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=data)

        if response.status_code != 200:
            raise Exception(
                f"API returned status code {response.status_code}: {response.text}"
            )

        response_data = response.json()

        # Extract the response text from the Gemini API response format
        try:
            return response_data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected response format: {e}") from e


async def get_gemini_response_with_api_url(question, api_url, user_id):
    """
    Get a response from Gemini AI using an external API URL
    """
    # Use the more flexible custom AI response function
    return await get_custom_ai_response(question, api_url, user_id)


async def get_custom_ai_response(question, api_url, user_id):
    """
    Get a response from a custom AI API URL
    This function is designed to work with various API formats and automatically
    detect the appropriate request method and parameters
    """
    # Ensure the URL doesn't end with a slash if it doesn't have query parameters
    if "?" not in api_url:
        api_url = api_url.rstrip("/")

    # Prepare common data payloads
    json_data = {
        "id": user_id,  # Using user's ID for history/tracking
        "question": question,
    }

    # URL encode the question for GET requests
    encoded_question = urllib.parse.quote(question)
    encoded_user_id = str(user_id)

    timeout = Timeout(30.0, connect=10.0)

    # Detect if the URL already contains placeholders
    has_question_placeholder = any(
        ph in api_url
        for ph in [
            "{question}",
            "{your_question}",
            "{q}",
            "{text}",
            "{your_text}",
            "{site}",
            "{url}",
            "{IMAGE_URL}",
            "{TOOL_NAME}",
        ]
    )
    has_id_placeholder = any(
        ph in api_url for ph in ["{id}", "{your_telegram_id}", "{your_id}"]
    )

    # Replace placeholders if they exist in the URL
    if has_question_placeholder:
        api_url = (
            api_url.replace("{question}", encoded_question)
            .replace("{your_question}", encoded_question)
            .replace("{q}", encoded_question)
            .replace("{text}", encoded_question)
            .replace("{your_text}", encoded_question)
            .replace("{site}", encoded_question)
            .replace("{url}", encoded_question)
            .replace("{IMAGE_URL}", encoded_question)
            .replace("{TOOL_NAME}", "text")  # Default tool is text
        )

    if has_id_placeholder:
        api_url = (
            api_url.replace("{id}", encoded_user_id)
            .replace("{your_telegram_id}", encoded_user_id)
            .replace("{your_id}", encoded_user_id)
        )

    # Prepare different GET URL formats based on the examples provided
    get_url_formats = [
        # Standard format with question parameter
        f"{api_url}{'&' if '?' in api_url else '?'}question={encoded_question}",
        # Format with q parameter (used by many APIs including Truecaller and OCR)
        f"{api_url}{'&' if '?' in api_url else '?'}q={encoded_question}",
        # Format with text parameter
        f"{api_url}{'&' if '?' in api_url else '?'}text={encoded_question}",
        # Format with id and question parameters
        f"{api_url}{'&' if '?' in api_url else '?'}id={user_id}&question={encoded_question}",
        # Format for PHP example with id and question
        f"{api_url}{'&' if '?' in api_url else '?'}id={user_id}question={encoded_question}",
        # Format with query parameter (used by Play Store API and others)
        f"{api_url}{'&' if '?' in api_url else '?'}query={encoded_question}",
        # Format for screenshot and image processing APIs
        f"{api_url}{'&' if '?' in api_url else '?'}url={encoded_question}",
        # Format for image processing APIs with tool parameter
        f"{api_url}{'&' if '?' in api_url else '?'}url={encoded_question}&tool=text",
    ]

    # If URL already has placeholders, use it directly as the first option
    if has_question_placeholder:
        get_url_formats.insert(0, api_url)

    LOGGER.debug(f"Custom AI API URL: {api_url}")
    LOGGER.debug(f"URL has question placeholder: {has_question_placeholder}")
    LOGGER.debug(f"URL has ID placeholder: {has_id_placeholder}")

    async with AsyncClient(timeout=timeout) as client:
        try:
            response = None
            error_messages = []

            # Try POST request first with JSON data (most common for AI APIs)
            try:
                LOGGER.debug(f"Trying POST request to {api_url} with JSON data")
                response = await client.post(api_url, json=json_data)
                if response.status_code == 200:
                    LOGGER.debug("POST request successful")
                else:
                    error_messages.append(
                        f"POST with JSON data failed: {response.status_code}"
                    )
            except Exception as e:
                error_messages.append(f"POST with JSON data error: {e!s}")
                response = None

            # If POST with JSON fails, try POST with form data
            if not response or response.status_code != 200:
                try:
                    LOGGER.debug(f"Trying POST request to {api_url} with form data")
                    form_data = {"question": question, "id": str(user_id)}
                    response = await client.post(api_url, data=form_data)
                    if response.status_code == 200:
                        LOGGER.debug("POST with form data successful")
                    else:
                        error_messages.append(
                            f"POST with form data failed: {response.status_code}"
                        )
                except Exception as e:
                    error_messages.append(f"POST with form data error: {e!s}")
                    response = None

            # If both POST methods fail, try different GET URL formats
            if not response or response.status_code != 200:
                for i, get_url in enumerate(get_url_formats):
                    try:
                        LOGGER.debug(f"Trying GET request to {get_url}")
                        response = await client.get(get_url)
                        if response.status_code == 200:
                            LOGGER.debug(
                                f"GET request successful with format {i + 1}"
                            )
                            break

                        error_messages.append(
                            f"GET format {i + 1} failed: {response.status_code}"
                        )
                        response = None
                    except Exception as e:
                        error_messages.append(f"GET format {i + 1} error: {e!s}")
                        response = None

            # If all requests failed, raise an exception with all error messages
            if not response or response.status_code != 200:
                raise Exception(
                    f"All API request methods failed: {'; '.join(error_messages)}"
                )

            # Try to parse the response
            content_type = response.headers.get("content-type", "")
            LOGGER.debug(f"Response content type: {content_type}")

            # Handle image responses (for APIs that return images)
            if "image" in content_type:
                LOGGER.debug("Detected image response")
                return "[Image response received. Cannot display in text format.]"

            # Try to parse as JSON first
            try:
                response_data = response.json()
                LOGGER.debug(f"Response JSON: {json.dumps(response_data)[:500]}...")

                # Check for common response formats
                # Format 1: {"status": "success", "answer": "..."}
                if response_data.get("status") == "success":
                    for key in [
                        "message",
                        "answer",
                        "content",
                        "response",
                        "result",
                        "text",
                    ]:
                        if key in response_data:
                            return response_data[key]
                    return "Success response received but no content found."

                # Format 2: OpenAI-like {"choices": [{"message": {"content": "..."}}]}
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    try:
                        return response_data["choices"][0]["message"]["content"]
                    except (KeyError, IndexError):
                        pass

                # Format 3: Google Gemini-like {"candidates": [{"content": {"parts": [{"text": "..."}]}}]}
                if (
                    "candidates" in response_data
                    and len(response_data["candidates"]) > 0
                ):
                    try:
                        return response_data["candidates"][0]["content"]["parts"][0][
                            "text"
                        ]
                    except (KeyError, IndexError):
                        pass

                # Format 4: Direct text in the response
                if isinstance(response_data, str):
                    return response_data

                # Format 5: Simple {"response": "..."} or {"answer": "..."} or {"message": "..."}
                for key in [
                    "response",
                    "answer",
                    "message",
                    "content",
                    "text",
                    "result",
                    "data",
                    "output",
                    "generated_text",
                    "completion",
                ]:
                    if key in response_data:
                        if isinstance(response_data[key], str):
                            return response_data[key]

                        if isinstance(response_data[key], dict):
                            # Handle nested structures
                            for nested_key in [
                                "text",
                                "content",
                                "message",
                                "value",
                                "result",
                            ]:
                                if nested_key in response_data[key]:
                                    return response_data[key][nested_key]

                # Format 6: Anthropic-like {"completion": "..."}
                if "completion" in response_data:
                    return response_data["completion"]

                # If we can't find a recognized format, return the raw JSON as string
                return f"Received response: {json.dumps(response_data)}"

            except json.JSONDecodeError:
                # If not JSON, return the raw text (which might be the actual response)
                return response.text

        except Exception as e:
            raise Exception(f"Error communicating with custom API: {e!s}") from e

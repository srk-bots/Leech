import json
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

    user_id = message.from_user.id

    # Get user-specific settings if available
    user_dict = user_data.get(user_id, {})

    # Determine which AI provider to use (user settings take priority)
    ai_provider = user_dict.get(
        "DEFAULT_AI_PROVIDER", Config.DEFAULT_AI_PROVIDER
    ).lower()

    # Check if message.command exists and has text after the command
    if (
        not hasattr(message, "command")
        or message.command is None
        or len(message.command) < 2
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
        # Auto-delete command message
        create_task(auto_delete_message(message, time=0))  # noqa: RUF006
        return

    # Extract the question from the message
    try:
        # Try to extract the question using command parsing first
        if (
            hasattr(message, "command")
            and message.command
            and len(message.command) >= 2
        ):
            question = message.text.split(" ", 1)[1].strip()
        # Fallback to simple text parsing if command parsing fails
        elif hasattr(message, "text") and message.text and " " in message.text:
            # Skip the command part (assuming it starts with /)
            question = message.text.split(" ", 1)[1].strip()
        else:
            # If we can't extract a question, show an error
            error_msg = await send_message(
                message,
                "❌ <b>Error:</b> Could not extract your question. Please use the format: /ask your question here",
            )
            # Auto-delete error message after 5 minutes
            create_task(auto_delete_message(error_msg, time=300))  # noqa: RUF006
            # Auto-delete command message
            create_task(auto_delete_message(message, time=0))  # noqa: RUF006
            return
    except IndexError:
        # Handle the case where splitting the message fails
        error_msg = await send_message(
            message,
            "❌ <b>Error:</b> Could not extract your question. Please use the format: /ask your question here",
        )
        # Auto-delete error message after 5 minutes
        create_task(auto_delete_message(error_msg, time=300))  # noqa: RUF006
        # Auto-delete command message
        create_task(auto_delete_message(message, time=0))  # noqa: RUF006
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
                # Auto-delete command message
                create_task(auto_delete_message(message, time=0))  # noqa: RUF006
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
                # Auto-delete command message
                create_task(auto_delete_message(message, time=0))  # noqa: RUF006
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
                # Auto-delete command message
                create_task(auto_delete_message(message, time=0))  # noqa: RUF006
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
                # Auto-delete command message
                create_task(auto_delete_message(message, time=0))  # noqa: RUF006
                await delete_message(wait_msg)
                return

            # Get response from Gemini AI
            response = await get_gemini_response(question, api_key, api_url, user_id)
            provider_display = "Gemini AI"

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
                # Auto-delete command message
                create_task(auto_delete_message(message, time=0))  # noqa: RUF006
                await delete_message(wait_msg)
                return

            # Get response from Mistral AI
            response = await get_ai_response(question, api_key, api_url, user_id)
            provider_display = "Mistral AI"

        # Format the response
        formatted_response = f"🤖 <b>{provider_display}:</b>\n\n{response}"

        # Send the response
        response_msg = await send_message(message, formatted_response)

        # Auto-delete the response after 5 minutes
        create_task(auto_delete_message(response_msg, time=300))  # noqa: RUF006

    except Exception as e:
        LOGGER.error(f"Error in AI response: {e!s}")
        error_msg = await send_message(message, f"❌ <b>Error:</b> {e!s}")
        # Auto-delete error message after 5 minutes
        create_task(auto_delete_message(error_msg, time=300))  # noqa: RUF006

    # Delete the waiting message
    await delete_message(wait_msg)

    # Auto-delete the command message
    create_task(auto_delete_message(message, time=0))  # noqa: RUF006


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
    # Ensure the URL doesn't end with a slash
    api_url = api_url.rstrip("/")

    data = {
        "id": user_id,  # Using user's ID for history
        "question": question,
    }

    timeout = Timeout(30.0, connect=10.0)

    async with AsyncClient(timeout=timeout) as client:
        response = await client.post(api_url, json=data)

        if response.status_code != 200:
            raise Exception(
                f"API returned status code {response.status_code}: {response.text}"
            )

        try:
            response_data = response.json()

            if response_data.get("status") == "success":
                return response_data.get("answer", "No answer provided")
            raise Exception(
                f"API returned error: {response_data.get('error', 'Unknown error')}"
            )
        except json.JSONDecodeError as e:
            raise Exception("Invalid JSON response from API") from e


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
    # Ensure the URL doesn't end with a slash
    api_url = api_url.rstrip("/")

    # If the URL is the default DeepSeek API URL from the example
    if "deepseek.privates-bots.workers.dev" in api_url:
        # Use the format from the example
        full_url = f"{api_url}/?question={question}"

        timeout = Timeout(30.0, connect=10.0)

        async with AsyncClient(timeout=timeout) as client:
            response = await client.get(full_url)

            if response.status_code != 200:
                raise Exception(
                    f"API returned status code {response.status_code}: {response.text}"
                )

            try:
                response_data = response.json()

                if response_data.get("status") == "success":
                    return response_data.get("message", "No message provided")
                raise Exception(
                    f"API returned error: {response_data.get('error', 'Unknown error')}"
                )
            except json.JSONDecodeError as e:
                raise Exception("Invalid JSON response from API") from e
    else:
        # Use a more standard POST request format for custom endpoints
        data = {
            "id": user_id,  # Using user's ID for history
            "question": question,
        }

        timeout = Timeout(30.0, connect=10.0)

        async with AsyncClient(timeout=timeout) as client:
            response = await client.post(api_url, json=data)

            if response.status_code != 200:
                raise Exception(
                    f"API returned status code {response.status_code}: {response.text}"
                )

            try:
                response_data = response.json()

                if response_data.get("status") == "success":
                    return response_data.get(
                        "message", response_data.get("answer", "No answer provided")
                    )
                raise Exception(
                    f"API returned error: {response_data.get('error', 'Unknown error')}"
                )
            except json.JSONDecodeError as e:
                raise Exception("Invalid JSON response from API") from e


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
    # Ensure the URL doesn't end with a slash
    api_url = api_url.rstrip("/")

    data = {
        "id": user_id,  # Using user's ID for history
        "question": question,
    }

    timeout = Timeout(30.0, connect=10.0)

    async with AsyncClient(timeout=timeout) as client:
        response = await client.post(api_url, json=data)

        if response.status_code != 200:
            raise Exception(
                f"API returned status code {response.status_code}: {response.text}"
            )

        try:
            response_data = response.json()

            if response_data.get("status") == "success":
                return response_data.get(
                    "message", response_data.get("answer", "No answer provided")
                )
            raise Exception(
                f"API returned error: {response_data.get('error', 'Unknown error')}"
            )
        except json.JSONDecodeError as e:
            raise Exception("Invalid JSON response from API") from e


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
    # Ensure the URL doesn't end with a slash
    api_url = api_url.rstrip("/")

    data = {
        "id": user_id,  # Using user's ID for history
        "question": question,
    }

    timeout = Timeout(30.0, connect=10.0)

    async with AsyncClient(timeout=timeout) as client:
        response = await client.post(api_url, json=data)

        if response.status_code != 200:
            raise Exception(
                f"API returned status code {response.status_code}: {response.text}"
            )

        try:
            response_data = response.json()

            if response_data.get("status") == "success":
                return response_data.get(
                    "message", response_data.get("answer", "No answer provided")
                )
            raise Exception(
                f"API returned error: {response_data.get('error', 'Unknown error')}"
            )
        except json.JSONDecodeError as e:
            raise Exception("Invalid JSON response from API") from e

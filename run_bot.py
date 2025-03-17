#!/usr/bin/env python3
"""
Direct entry point script for running the bot.
This script bypasses the module import system and directly imports the main function.
"""

import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s [%(module)s:%(lineno)d]",
    datefmt="%d-%b %I:%M:%S %p",
)
logger = logging.getLogger(__name__)

# Ensure /usr/src/app is in the Python path
if "/usr/src/app" not in sys.path:
    sys.path.insert(0, "/usr/src/app")


def find_module_dir():
    """Find the correct module directory (tghbot or bot)."""
    potential_modules = ["tghbot", "bot"]
    for module in potential_modules:
        if os.path.isdir(module) and os.path.exists(
            os.path.join(module, "__main__.py"),
        ):
            logger.info(f"Found module directory: {module}")
            return module

    logger.error("No valid module directory found!")
    sys.exit(1)


def import_and_run_module(module_dir):
    """Import and run the module directly."""
    try:
        # First check if the module can be imported normally
        logger.info(f"Attempting to import {module_dir}.__main__ module")
        try:
            __import__(f"{module_dir}.__main__", fromlist=["*"])
            # If we got here, the module was imported but we don't need to do anything
            # as its top-level code would have already executed
            logger.info(f"Successfully imported {module_dir}.__main__ module")
            return True
        except ImportError as e:
            logger.warning(f"Standard import failed: {e}, trying spec-based import")

        # Second attempt: load the module via spec
        main_path = os.path.join(os.getcwd(), module_dir, "__main__.py")
        logger.info(f"Loading module from path: {main_path}")

        if not os.path.exists(main_path):
            logger.error(f"File not found: {main_path}")
            return False

        # Read and execute the module content directly
        with open(main_path) as f:
            module_content = f.read()

        # Create a proper module context
        module_globals = {
            "__name__": f"{module_dir}.__main__",
            "__file__": main_path,
            "__package__": module_dir,
        }

        logger.info(f"Executing {module_dir}.__main__.py content in custom context")
        exec(module_content, module_globals)
        logger.info(f"Successfully executed {module_dir}.__main__.py content")
        return True
    except Exception as e:
        logger.exception(f"Failed to import and run module: {e}")
        return False


def run_bot():
    """Run the bot by finding and executing the appropriate module."""
    module_dir = find_module_dir()

    # Create __init__.py files if they don't exist to ensure proper package structure
    for root, dirs, _ in os.walk(module_dir):
        for d in dirs:
            init_file = os.path.join(root, d, "__init__.py")
            if not os.path.exists(init_file):
                logger.info(
                    f"Creating missing __init__.py in {os.path.join(root, d)}",
                )
                with open(init_file, "w") as f:
                    pass  # Create empty file

    # First try: import and execute module directly
    if import_and_run_module(module_dir):
        logger.info(f"Successfully ran {module_dir}.__main__ module")
        return

    # Second try: run main function directly if available
    try:
        logger.info("Trying to directly execute main function...")
        # This approach is tailored to the specific structure observed in tghbot.__main__.py
        # which defines a main() function and runs it with bot_loop.run_until_complete()

        # Import bot_loop from the module
        bot_loop_module = __import__(f"{module_dir}", fromlist=["bot_loop"])
        bot_loop = bot_loop_module.bot_loop

        # Import the main function
        main_module = __import__(f"{module_dir}.__main__", fromlist=["main"])
        main_func = main_module.main

        # Run the main function with the bot_loop
        logger.info("Executing main function via bot_loop.run_until_complete()")
        bot_loop.run_until_complete(main_func())

        # Also run the rest of the code that normally runs after main()
        logger.info("Running post-main initialization code")
        exec(f"from {module_dir}.core.handlers import add_handlers; add_handlers()")
        exec(
            f"from {module_dir}.helper.ext_utils.bot_utils import create_help_buttons; create_help_buttons()",
        )
        exec(
            f"from {module_dir}.helper.listeners.aria2_listener import add_aria2_callbacks; add_aria2_callbacks()",
        )

        # Run the event loop forever as the original code does
        logger.info("Bot started, running event loop forever")
        bot_loop.run_forever()
    except Exception as e:
        logger.exception(f"Failed to run main function directly: {e}")

        # Final try: just execute the file directly in the current process
        logger.info("Attempting to execute file directly as last resort")
        main_file = os.path.join(module_dir, "__main__.py")
        if os.path.exists(main_file):
            with open(main_file) as f:
                logger.info(f"Executing {main_file} content directly")
                exec(f.read())
        else:
            logger.error(f"Could not find {main_file}")
            sys.exit(1)


if __name__ == "__main__":
    try:
        run_bot()
    except Exception as e:
        logger.exception(f"Fatal error running bot: {e}")
        sys.exit(1)

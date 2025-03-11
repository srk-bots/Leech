#!/usr/bin/env python3
"""
Launcher script for tghbot that properly handles relative imports.
This script sets up the correct Python module context to ensure relative imports work correctly.
"""
import os
import sys
import importlib.util
import logging

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def main():
    """Run the bot by properly importing the tghbot package."""
    # Ensure the current directory is in the Python path
    sys.path.insert(0, os.getcwd())
    
    try:
        # Import the module the proper way to handle relative imports
        logger.info("Importing tghbot module...")
        import tghbot.__main__
        logger.info("Successfully imported and executed tghbot.__main__")
    except ImportError as e:
        logger.error(f"Failed to import tghbot module: {e}")
        
        # Try alternative approach by executing __main__.py with proper context
        try:
            logger.info("Trying alternative approach...")
            # Create a spec for the module
            module_spec = importlib.util.spec_from_file_location(
                "tghbot.__main__", os.path.join(os.getcwd(), "tghbot", "__main__.py")
            )
            if not module_spec:
                logger.error("Could not find tghbot.__main__ module")
                return False
                
            # Create a new module based on the spec
            module = importlib.util.module_from_spec(module_spec)
            sys.modules["tghbot.__main__"] = module
            
            # Execute the module
            logger.info("Executing tghbot.__main__ module...")
            module_spec.loader.exec_module(module)
            logger.info("Successfully executed tghbot.__main__ module")
            return True
        except Exception as e:
            logger.error(f"Alternative approach failed: {e}")
            return False
            
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        logger.error("Failed to launch the bot")
        sys.exit(1)
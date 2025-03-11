#!/bin/bash

# Error handling - exit on any error and print the command that failed
set -e
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
trap 'echo "\"${last_command}\" command failed with exit code $?."' EXIT

# Directory structure check - ensure bot is renamed to tghbot
if [ -d "bot" ] && [ ! -d "tghbot" ]; then
    echo "Renaming 'bot' directory to 'tghbot'..."
    mv bot tghbot
    # Also update imports if needed
    find . -type f -name "*.py" -exec sed -i 's/from bot\./from tghbot./g; s/import bot\./import tghbot./g' {} +
fi

# If tghbot doesn't exist but bot exists at the system level, make symlink
if [ ! -d "tghbot" ] && [ -d "/usr/src/app/bot" ]; then
    echo "Creating symlink from 'bot' to 'tghbot'..."
    ln -sf /usr/src/app/bot /usr/src/app/tghbot
fi

# Ensure Python environment is properly set up
export PYTHONPATH="/usr/src/app"
export VIRTUAL_ENV="/usr/src/app/.venv"

# Activate virtual environment explicitly
source $VIRTUAL_ENV/bin/activate || { echo "Failed to activate virtual environment"; exit 1; }

# Debug information
echo "=== ENVIRONMENT DIAGNOSTICS ==="
echo "Current Python path: $PYTHONPATH"
echo "Virtual environment: $VIRTUAL_ENV"
echo "Python version: $(python3 --version)"
echo "Current directory: $(pwd)"
echo "Python executable: $(which python3)"
echo "Directory contents:"
ls -la
echo "Python package list:"
pip list
echo "=== END DIAGNOSTICS ==="

# Backup critical files before running update
echo "Creating backup of critical files..."
mkdir -p /tmp/tghbot_backup/core
if [ -d "tghbot" ] && [ -d "tghbot/core" ]; then
    cp -r tghbot/core /tmp/tghbot_backup/
    if [ -f "run_bot.py" ]; then
        cp run_bot.py /tmp/tghbot_backup/
    fi
fi

# Run the update script with error capture
echo "Running update script..."
if ! python3 update.py 2> update_error.log; then
    echo "Error running update script:"
    cat update_error.log
else
    echo "Update script completed successfully"
fi

# Restore critical files after update
echo "Restoring critical files..."
mkdir -p tghbot/core
if [ -d "/tmp/tghbot_backup/core" ]; then
    cp -r /tmp/tghbot_backup/core/* tghbot/core/
    if [ -f "/tmp/tghbot_backup/run_bot.py" ]; then
        cp /tmp/tghbot_backup/run_bot.py .
    fi
fi

# Make run_bot.py executable if it exists
if [ -f "run_bot.py" ]; then
    chmod +x run_bot.py
    echo "Made run_bot.py executable"
fi

# Start the bot using the dedicated entry script
echo "Starting bot using run_bot.py..."
if [ -f "run_bot.py" ]; then
    if ! python3 run_bot.py 2> bot_error.log; then
        echo "Error running bot with run_bot.py:"
        cat bot_error.log
        echo "Trying alternative methods..."
        
        # Determine module name
        if [ -d "tghbot" ]; then
            MODULE_NAME="tghbot"
        elif [ -d "bot" ]; then
            MODULE_NAME="bot"
            echo "Warning: Using 'bot' module instead of 'tghbot'"
        else
            echo "Error: Neither 'tghbot' nor 'bot' directory found!"
            ls -la
            echo "Keeping container alive for debugging..."
            tail -f /dev/null
            exit 1
        fi
        
        # Create __init__.py files if needed
        find $MODULE_NAME -type d -exec touch {}/__init__.py \;
        echo "Ensured all directories in $MODULE_NAME have __init__.py files"
        
        # Try direct execution method as fallback
        echo "Attempting direct module execution..."
        if [ -f "${MODULE_NAME}/__main__.py" ]; then
            cd "/usr/src/app/${MODULE_NAME}" && python3 __main__.py 2> fallback_error.log || {
                echo "Direct module execution failed:"
                cat fallback_error.log
                
                # Final fallback - try Python module import
                echo "Trying final method - direct import in Python..."
                cd "/usr/src/app" && python3 -c "import sys; sys.path.insert(0, '/usr/src/app'); from ${MODULE_NAME}.__main__ import main; import asyncio; asyncio.run(main())" 2> final_error.log || {
                    echo "All methods failed. Debug information:"
                    cat final_error.log
                    echo "Python version: $(python3 --version)"
                    echo "Current directory:"
                    pwd
                    echo "Directory contents:"
                    ls -la
                    echo "${MODULE_NAME} directory contents:"
                    ls -la ${MODULE_NAME}/
                    echo "Python path:"
                    python3 -c "import sys; print(sys.path)" || echo "Failed to print Python path"
                    echo "Contents of ${MODULE_NAME}/__main__.py:"
                    cat ${MODULE_NAME}/__main__.py
                    echo "Installed packages:"
                    pip list
                    echo "Keeping container alive for debugging..."
                    tail -f /dev/null
                }
            }
        else
            echo "ERROR: ${MODULE_NAME}/__main__.py not found!"
            ls -la ${MODULE_NAME}/
            echo "Keeping container alive for debugging..."
            tail -f /dev/null
        fi
    fi
else
    echo "ERROR: run_bot.py not found! Falling back to launcher script..."
    
    # Ensure launcher.py exists and is executable
    if [ ! -f "launcher.py" ]; then
        echo "Creating launcher.py script for proper module imports..."
        cat > launcher.py << 'EOL'
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
EOL
    fi
    
    chmod +x launcher.py
    
    # Ensure all directories have __init__.py files in tghbot
    find tghbot -type d -exec touch {}/__init__.py \;
    echo "Created __init__.py files in all subdirectories of tghbot"
    
    # Run the launcher script with proper Python path
    echo "Running launcher.py to handle relative imports correctly..."
    export PYTHONPATH="/usr/src/app:${PYTHONPATH}"
    python3 launcher.py 2> launcher_error.log || {
        echo "Launcher script failed:"
        cat launcher_error.log
        echo "Keeping container alive for debugging..."
        tail -f /dev/null
    }
fi

# Disable trap before exit
trap - EXIT
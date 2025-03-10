#!/bin/bash

# Ensure Python environment is properly set up
export PYTHONPATH=/usr/src/app:$PYTHONPATH
export VIRTUAL_ENV=/usr/src/app/.venv

# Activate virtual environment explicitly
source $VIRTUAL_ENV/bin/activate

# Debug information
echo "Current Python path: $PYTHONPATH"
echo "Virtual environment: $VIRTUAL_ENV"
echo "Python version: $(python3 --version)"
echo "Current directory: $(pwd)"
echo "Directory contents: $(ls -la)"

# Run the update script
python3 update.py

# Start the bot with the new module name - with better error handling
echo "Starting bot..."
if ! python3 -m tghbot; then
    echo "Error running tghbot module. Trying alternative method..."
    cd /usr/src/app && python3 -c "from tghbot.__main__ import main; import asyncio; asyncio.run(main())"
fi
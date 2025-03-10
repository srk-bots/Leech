#!/bin/bash

# Add the current directory to PYTHONPATH
export PYTHONPATH=/usr/src/app:$PYTHONPATH

# Run the update script
python3 update.py

# Start the bot with the new module name
python3 -m tghbot
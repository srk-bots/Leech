#!/bin/bash

# Check if bot directory exists but tghbot doesn't
if [ -d "bot" ] && [ ! -d "tghbot" ]; then
    echo "Renaming 'bot' directory to 'tghbot'..."
    mv bot tghbot
    # Create a symlink for backward compatibility
    ln -sf $(pwd)/tghbot $(pwd)/bot
fi

# Find all Python files and update imports with more comprehensive patterns
find . -type f -name "*.py" -exec sed -i -E 's/from bot([^a-zA-Z])/from tghbot\1/g; s/import bot([^a-zA-Z])/import tghbot\1/g; s/ bot\./ tghbot./g; s/^bot\./tghbot./g' {} +

echo "Import statements updated"

# Run git diff to verify changes (if in git repository)
if [ -d .git ]; then
    git diff
fi

# Verify module structure
if [ -d "tghbot" ]; then
    echo "tghbot directory exists"
    if [ -f "tghbot/__main__.py" ]; then
        echo "tghbot/__main__.py exists - module should be importable"
    else
        echo "WARNING: tghbot/__main__.py does not exist!"
    fi
else
    echo "ERROR: tghbot directory does not exist!"
fi
#!/bin/bash

# Find all Python files and update imports
find tghbot -type f -name "*.py" -exec sed -i -E 's/from bot([^a-zA-Z])/from tghbot\1/g; s/import bot([^a-zA-Z])/import tghbot\1/g' {} +

# Run git diff to verify changes (if in git repository)
if [ -d .git ]; then
    git diff
fi
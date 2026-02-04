#!/bin/bash
echo "Cleaning up repository..."

# Ensure the directory exists
mkdir -p nfl_cap_tracker

# Move the runner into the folder
if [ -f run_app.py ]; then
    mv run_app.py nfl_cap_tracker/
fi

# Move the sync script
if [ -f sync.sh ]; then
    mv sync.sh nfl_cap_tracker/
fi

# Remove temporary setup scripts from the repo
git rm --cached setup_git.sh debug_ssh.sh organize.sh revert_structure.sh 2>/dev/null
rm setup_git.sh debug_ssh.sh organize.sh revert_structure.sh 2>/dev/null

# Clean up any DS_Store clutter
find . -name ".DS_Store" -delete

# Commit the changes
git add .
git commit -m "chore: cleanup repository structure and remove temporary scripts"
git push

echo "Cleanup Complete! Everything is now inside 'nfl_cap_tracker/'."

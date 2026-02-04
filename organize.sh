#!/bin/bash
echo "Organizing files..."
mkdir -p nfl_cap_tracker
mv SalaryCap.py requirements.txt nfl_cap_tracker/
# Keep run_app.py and sync.sh at the root
git add .
git commit -m "refactor: move project code into nfl_cap_tracker subdirectory"
git push
echo "Restucturing Complete! Restart the app with 'python3 run_app.py'"

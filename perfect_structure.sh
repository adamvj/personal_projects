#!/bin/bash
echo "Structuring repo: Root should ONLY contain nfl_cap_tracker folder."

# 1. Ensure the directory exists
mkdir -p nfl_cap_tracker

# 2. Files that MUST be inside nfl_cap_tracker
# For each file, if it exists at root, move it (overwrite) inside.
for file in SalaryCap.py requirements.txt run_app.py sync.sh; do
    if [ -f "$file" ]; then
        echo "Moving $file to nfl_cap_tracker/"
        mv "$file" nfl_cap_tracker/
    fi
done

# 3. Add the changes (moves) to git
git add nfl_cap_tracker/

# 4. EXPLICITLY remove these files from the root git index if they exist
# This ensures they don't show up at the top level of GitHub
git rm --cached SalaryCap.py requirements.txt run_app.py sync.sh cleanup_repo.sh setup_git.sh debug_ssh.sh organize.sh revert_structure.sh 2>/dev/null

# 5. Delete the temporary scripts themselves from local root
rm cleanup_repo.sh setup_git.sh debug_ssh.sh organize.sh revert_structure.sh 2>/dev/null

# 6. Commit and Push
git add .
git commit -m "chore: enforce strict folder structure - all code inside nfl_cap_tracker"
git push

echo "Success! Check GitHub now. You should only see the 'nfl_cap_tracker' folder."

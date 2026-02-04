#!/bin/bash
echo "--- Checking .ssh directory ---"
ls -F ~/.ssh/

echo ""
echo "--- Checking ssh config ---"
if [ -f ~/.ssh/config ]; then
    cat ~/.ssh/config
else
    echo "No config file found."
fi

echo ""
echo "--- Attempting to fix agent and add keys ---"
eval "$(ssh-agent -s)"

# Try adding common key types
# We use standard names. If you use a custom name, you'll need to 'ssh-add' it manually.
for key in ~/.ssh/id_rsa ~/.ssh/id_ed25519 ~/.ssh/id_ecdsa; do
    if [ -f "$key" ]; then
        echo "Adding $key..."
        ssh-add "$key"
    fi
done

echo ""
echo "--- Testing GitHub Connection ---"
ssh -T git@github.com

echo ""
echo "--- Attempting Git Fetch again ---"
git fetch origin

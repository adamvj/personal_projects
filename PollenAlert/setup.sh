#!/bin/bash

# Exit on error
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

echo "Setting up Python environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Created virtual environment."
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Make the python script executable
chmod +x pollen_alert.py

# Remove legacy cron jobs if they exist
if crontab -l 2>/dev/null | grep -q "$DIR/pollen_alert.py"; then
    echo "Removing legacy cron jobs..."
    crontab -l 2>/dev/null | grep -v "$DIR/pollen_alert.py" | crontab -
fi

# Setup LaunchAgent
PLIST_PATH="$HOME/Library/LaunchAgents/com.adamvj.pollenalert.plist"

echo "Configuring LaunchAgent for 9:30 AM, 12:00 PM, and 5:00 PM..."

mkdir -p "$HOME/Library/LaunchAgents"

cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.adamvj.pollenalert</string>
    <key>ProgramArguments</key>
    <array>
        <string>$DIR/venv/bin/python</string>
        <string>$DIR/pollen_alert.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$DIR</string>
    <key>StandardOutPath</key>
    <string>/tmp/pollen_cron.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/pollen_cron.log</string>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>9</integer>
            <key>Minute</key>
            <integer>30</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>12</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>17</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>
</dict>
</plist>
EOF

# Unload just in case
launchctl unload "$PLIST_PATH" 2>/dev/null || true
# Load new agent
launchctl load "$PLIST_PATH"

echo "LaunchAgent installed successfully. It will now run even after your Mac wakes from sleep."

echo ""
echo "Setup complete! The pollen alert script will now run automatically."
echo "You can check the manual execution with:"
echo "source venv/bin/activate && python pollen_alert.py"
echo ""
echo "To receive notifications on your phone, download the 'ntfy' app (iOS/Android)"
echo "and subscribe to the topic: adam_pollen_alert_12345"

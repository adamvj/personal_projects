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

# Setup Cron Jobs (Runs every day at 9:30 AM, 12 PM, and 5 PM)
CRON_CMD_1="30 9 * * * cd $DIR && $DIR/venv/bin/python $DIR/pollen_alert.py > $DIR/cron.log 2>&1"
CRON_CMD_2="0 12 * * * cd $DIR && $DIR/venv/bin/python $DIR/pollen_alert.py > $DIR/cron.log 2>&1"
CRON_CMD_3="0 17 * * * cd $DIR && $DIR/venv/bin/python $DIR/pollen_alert.py > $DIR/cron.log 2>&1"

# Check if cron job already exists and remove old ones to avoid duplicates
if crontab -l 2>/dev/null | grep -q "$DIR/pollen_alert.py"; then
    echo "Removing legacy cron jobs..."
    crontab -l 2>/dev/null | grep -v "$DIR/pollen_alert.py" | crontab -
fi

echo "Adding cron jobs to run at 9:30 AM, 12:00 PM, and 5:00 PM daily..."
(crontab -l 2>/dev/null; echo "$CRON_CMD_1"; echo "$CRON_CMD_2"; echo "$CRON_CMD_3") | crontab -
echo "Cron jobs added successfully."

echo ""
echo "Setup complete! The pollen alert script will now run automatically."
echo "You can check the manual execution with:"
echo "source venv/bin/activate && python pollen_alert.py"
echo ""
echo "To receive notifications on your phone, download the 'ntfy' app (iOS/Android)"
echo "and subscribe to the topic: adam_pollen_alert_12345"

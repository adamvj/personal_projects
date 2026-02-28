# News Updates Email Bot

This project pulls the latest Tech, AI, and Trading news from Google News RSS, summarizes it using an AI API, and emails it to you via SMTP.

## Setup Instructions

1. **API Keys**: Copy the contents of `.env.example` into a new file named `.env`. Fill in all the fields:
   - `OPENAI_API_KEY`: Get this from platform.openai.com
   - `SENDER_EMAIL`: The email address sending the messages (e.g. your Gmail).
   - `SENDER_PASSWORD`: Your email password. If using Gmail, you MUST create an **App Password** (Google Account -> Security -> 2-Step Verification -> App Passwords). Regular passwords will not work.
   - `RECEIVER_EMAIL`: Where you want to receive the news (adamvjose@gmail.com).

2. **Run Locally**:
   To test that it works, open your terminal in this directory (`/Users/adamjose/Desktop/Projects/Personal/NewsUpdates`) and run:
   ```bash
   source venv/bin/activate
   python3 main.py
   ```

3. **Automate (Daily Cron Job)**:
   This script is currently configured to run twice a day (at 9:30 AM and 9:00 PM) on your Mac:
   - Open terminal and type `crontab -e` to view or edit the schedule
   - The current schedule is:
     `30 9 * * * cd /Users/adamjose/Desktop/Projects/Personal/NewsUpdates && /Users/adamjose/Desktop/Projects/Personal/NewsUpdates/venv/bin/python main.py >> /Users/adamjose/Desktop/Projects/Personal/NewsUpdates/podcast.log 2>&1`
     `0 21 * * * cd /Users/adamjose/Desktop/Projects/Personal/NewsUpdates && /Users/adamjose/Desktop/Projects/Personal/NewsUpdates/venv/bin/python main.py >> /Users/adamjose/Desktop/Projects/Personal/NewsUpdates/podcast.log 2>&1`
   *(Note: Your Mac needs to be awake at these times for the script to run).*

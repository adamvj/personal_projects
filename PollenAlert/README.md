# Pollen Alert Tool

## Overview
A lightweight background automation script built for macOS that monitors daily pollen levels and pushes real-time notifications to your phone. It intelligently fetches the user's location via IP and queries the free Open-Meteo Air Quality API for hourly pollen forecasts for specific allergens like Grass, Trees (Alder, Birch, Olive), and Weeds (Mugwort, Ragweed). The script evaluates the data against sensitive, customized thresholds and dispatches push notifications via `ntfy.sh` if the levels are considered high.

The tool operates seamlessly in the background, utilizing a virtual environment for dependency management and a cron job schedule running three times daily (9:30 AM, 12:00 PM, and 5:00 PM) to ensure you always know when to take precautions.

## Skills & Concepts Learned
* **API Integration & Data Parsing**: Mastered fetching and interpreting complex JSON data from multiple REST APIs (`ip-api.com` for location, `open-meteo.com` for hourly air quality index data).
* **Push Notification Systems**: Interfaced with `ntfy.sh` to trigger instant, cross-platform mobile push notifications without requiring heavy third-party SDKs. 
* **Task Automation & Scheduling**: Automated Python scripts on Unix-based systems using `crontab` to create reliable background jobs. 
* **Environment Management**: Utilized bash scripting (`setup.sh`) to automate the initialization of Python virtual environments and dependency installation, creating a reproducible setup process.
* **Error Handling & Resilience**: Designed robust exceptions using the `requests` library to handle network issues or bad data gracefully without crashing the scheduling pipeline.

# NFL Positional Cap Tracker

A Streamlit application that provides real-time tracking of NFL team salary cap allocations by position.

## Features
- **Real-Time Data**: Scrapes live active roster data from Spotrac.
- **Dynamic League Overview**: Aggregates data from all 32 teams to show true league-wide positional spending averages.
- **Team Breakdown**: Detailed pie chart and data table for any selected team.
- **Resilient**: Built-in 120s timeouts and auto-retries to handle Spotrac server issues (502 errors).
- **Export**: Download any view as a CSV file.

## Installation

1.  Navigate to the project folder:
    ```bash
    cd nfl_cap_tracker
    ```
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## How to Run

Launch the application with the included runner script:

```bash
python3 run_app.py
```

The app will open in your default web browser (usually at `http://localhost:8501`).

## Updating

If you make changes or want to push updates to GitHub, simply run the sync script:

```bash
./sync.sh
```

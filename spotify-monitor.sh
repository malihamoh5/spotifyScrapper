#!/bin/bash

# Spotify Playlist Scraper Monitor
# Monitors the scraper output and restarts processes as needed

echo "Starting Spotify scraper monitor..."

# Define constants
MIN_SIZE_GB=5000
CHECK_INTERVAL=30  # minutes

echo "Minimum file size: $MIN_SIZE_GB GB"
echo "Check interval: $CHECK_INTERVAL minutes"

# Function to convert size in bytes to gigabytes
bytes_to_gb() {
    echo "$1 / 1024 / 1024 / 1024" | bc -l
}

while true; do
    # Get today's date and format it to match the file naming convention
    today=$(date +%y%m%d)
    file_name="${today}_output.csv"
    
    # Current timestamp for logging
    timestamp=$(date)

    # Check if the file exists
    if [ -f "$file_name" ]; then
        # Get the file size in bytes
        file_size=$(stat -c %s "$file_name")

        # Convert file size to gigabytes
        file_size_gb=$(bytes_to_gb "$file_size")

        # Restart if file is smaller than the configured size
        if (( $(echo "$file_size_gb < $MIN_SIZE_GB" | bc -l) )); then
            echo "$timestamp: File size ($file_size_gb GB) is below threshold ($MIN_SIZE_GB GB)"
            echo "$timestamp: Stopping all PM2 processes..."
            pm2 delete all

            echo "$timestamp: Starting new scraper processes..."
            node start-scrapers.js
            
            echo "$timestamp: Processes restarted. Waiting for $CHECK_INTERVAL minutes..."
        else
            echo "$timestamp: File size ($file_size_gb GB) is sufficient. No restart needed."
        fi
    else
        echo "$timestamp: Output file for today not found. Starting scraper processes..."
        node start-scrapers.js
        echo "$timestamp: Processes started. Waiting for $CHECK_INTERVAL minutes..."
    fi

    # Convert minutes to seconds for sleep
    sleep_duration=$(( CHECK_INTERVAL * 60 ))
    sleep $sleep_duration
done
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
    file_pattern="${today}_output_part_*.csv"
    
    # Current timestamp for logging
    timestamp=$(date)

    # Check if any output files exist for today
    if ls $file_pattern 1> /dev/null 2>&1; then
        # Calculate total size of all output files
        total_size=0
        file_count=0
        
        for file_name in $file_pattern; do
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS
                file_size=$(stat -f %z "$file_name")
            else
                # Linux
                file_size=$(stat -c %s "$file_name")
            fi
            total_size=$((total_size + file_size))
            file_count=$((file_count + 1))
        done

        # Convert total size to gigabytes
        total_size_gb=$(bytes_to_gb "$total_size")

        echo "$timestamp: Found $file_count output files, total size: $total_size_gb GB"

        # Restart if total size is smaller than the configured size
        if (( $(echo "$total_size_gb < $MIN_SIZE_GB" | bc -l) )); then
            echo "$timestamp: Total file size ($total_size_gb GB) is below threshold ($MIN_SIZE_GB GB)"
            echo "$timestamp: Stopping all PM2 processes..."
            pm2 delete all

            echo "$timestamp: Starting new scraper processes..."
            node start-scrapers.js
            
            echo "$timestamp: Processes restarted. Waiting for $CHECK_INTERVAL minutes..."
        else
            echo "$timestamp: Total file size ($total_size_gb GB) is sufficient. No restart needed."
        fi
    else
        echo "$timestamp: No output files found for today. Starting scraper processes..."
        node start-scrapers.js
        echo "$timestamp: Processes started. Waiting for $CHECK_INTERVAL minutes..."
    fi

    # Convert minutes to seconds for sleep
    sleep_duration=$(( CHECK_INTERVAL * 60 ))
    sleep $sleep_duration
done
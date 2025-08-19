#!/bin/bash

# Define the paths to the configuration files
CONFIG_FILE1="./ecosystem.config.js"
# CONFIG_FILE2="./chartmetric-scraper/ecosystem.config.js"

# Function to convert size in bytes to terabytes
bytes_to_tb() {
    echo "$1 / 1024 / 1024 / 1024 / 1024" | bc -l
}

while true; do
    # Get today's date and format it to match the file naming convention
    today=$(date +%y%m%d)
    file_pattern="${today}_output_part_*.csv"

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

        # Convert total size to terabytes
        total_size_tb=$(bytes_to_tb "$total_size")

        echo "Found $file_count output files, total size: $total_size_tb TB"

        # Restart if total size is smaller than 5.0 TB
        if (( $(echo "$total_size_tb < 5.0" | bc -l) )); then
            echo "Total file size ($total_size_tb TB) is below threshold (5.0 TB)"
            echo "Stopping all PM2 processes..."
            pm2 delete all

            echo "Starting new PM2 processes from configuration files..."
            pm2 start "$CONFIG_FILE1"
            # Uncomment the following lines if you want to start a second configuration file in a subdirectory
            # cd chartmetric-scraper
            # pm2 start "ecosystem.config.js"
            # cd ..  # Return to the original directory

            echo "Processes restarted. Waiting for 30 minutes..."
        else
            echo "Total file size ($total_size_tb TB) is sufficient. No restart needed. Waiting for 30 minutes..."
        fi
    else
        echo "No output files found for today. Starting PM2 processes..."
        pm2 start "$CONFIG_FILE1"
        # Uncomment the following lines if you want to start a second configuration file in a subdirectory
        # cd chartmetric-scraper
        # pm2 start "ecosystem.config.js"
        # cd ..  # Return to the original directory
    fi

    sleep 1800  # Sleep for 30 minutes
done
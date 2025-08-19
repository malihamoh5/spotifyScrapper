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
    file_name="${today}_output.csv"

    # Check if the file exists
    if [ -f "$file_name" ]; then
        # Get the file size in bytes
        # file_size=$(stat -c %s "$file_name") FOR UBUNTU
        file_size=$(stat -f %z "$file_name") // FOR MACOS

        # Convert file size to terabytes
        file_size_tb=$(bytes_to_tb "$file_size")

        # Restart if file is smaller than 1.5 TB
        if (( $(echo "$file_size_tb < 5.0" | bc -l) )); then
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
            echo "File size is sufficient. No restart needed. Waiting for 30 minutes..."
        fi
    else
            echo "Starting new PM2 processes from configuration files..."
            pm2 start "$CONFIG_FILE1"
            # Uncomment the following lines if you want to start a second configuration file in a subdirectory
            # cd chartmetric-scraper
            # pm2 start "ecosystem.config.js"
            # cd ..  # Return to the original directory
    fi

    sleep 1800  # Sleep for 30 minutes
done
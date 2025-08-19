#!/bin/bash

# Spotify Scraper System Setup Script
# Sets up the necessary files and directories for the Spotify scraper system

echo "Setting up Spotify Scraper System..."

# Create necessary directories
directories=(
  "playlists"
  "temp_chunks"
  "05_playlists"
)

for dir in "${directories[@]}"; do
  if [ ! -d "$dir" ]; then
    mkdir -p "$dir"
    echo "Created directory: $dir"
  else
    echo "Directory already exists: $dir"
  fi
done

# Make scripts executable
scripts=(
  "spotify-monitor.sh"
  "data-deduplicator.py"
  "data-combiner.py"
)

for script in "${scripts[@]}"; do
  if [ -f "$script" ]; then
    chmod +x "$script"
    echo "Made executable: $script"
  else
    echo "Warning: Script not found: $script"
  fi
done

# Check for Node.js and required packages
if ! command -v node &> /dev/null; then
  echo "Error: Node.js is not installed. Please install Node.js before continuing."
  exit 1
fi

echo "Checking Node.js dependencies..."
npm install

# Check for Python and required packages
if ! command -v python3 &> /dev/null; then
  echo "Error: Python 3 is not installed. Please install Python 3 before continuing."
  exit 1
fi

echo "Checking Python dependencies..."
python3 -m pip install pandas numpy tqdm psutil pyarrow

# Check for PM2
if ! command -v pm2 &> /dev/null; then
  echo "PM2 is not installed. Installing globally..."
  npm install -g pm2
else
  echo "PM2 is already installed."
fi

echo "Setup complete! You can now run the system with:"
echo "  ./spotify-monitor.sh"
echo ""
echo "To manually run components:"
echo "  - Update token: node spotify-token-manager.js"
echo "  - Deduplicate data: ./data-deduplicator.py"
echo "  - Combine files: ./data-combiner.py"
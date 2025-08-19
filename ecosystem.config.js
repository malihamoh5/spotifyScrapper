/**
 * Dynamic PM2 Ecosystem Configuration for Spotify Playlist Scrapers
 * Easily adjust the number of scraper instances by changing NUM_SCRAPERS
 */

const fs = require("fs");
const path = require("path");

// Configure the number of scraper instances to run
// *** Change this value to increase/decrease the number of scrapers ***
const NUM_SCRAPERS = 5;

// Helper function to generate a scraper process
function generateScraperProcess(id) {
  return {
    name: `spotify-scraper-${id}`,
    script: "spotify-scraper.js",
    node_args: "--max-old-space-size=4096",
    env: {
      CSV_FILE_PATH: `../05_playlists/playlists_part_${String(id).padStart(3, '0')}.csv`,
      CHECKPOINT_FILE_NAME: `../05_playlists/checkpoint_${id}.json`
    },
    autorestart: true,
    max_restarts: 10,
    restart_delay: 5000
  };
}

// Ensure playlist files exist
const playlistsDir = path.resolve(__dirname, "../05_playlists");
if (!fs.existsSync(playlistsDir)) {
  fs.mkdirSync(playlistsDir, { recursive: true });
  console.log("Created playlists directory.");
}

// Generate the specified number of scraper processes
const scraperProcesses = [];
for (let i = 1; i <= NUM_SCRAPERS; i++) {
  const process = generateScraperProcess(i);
  
  // Ensure the playlist file exists
  const playlistFile = path.resolve(__dirname, process.env.CSV_FILE_PATH);
  if (!fs.existsSync(playlistFile)) {
    fs.writeFileSync(playlistFile, "https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF", "utf8");
    console.log(`Created playlist file: ${playlistFile}`);
  }
  
  scraperProcesses.push(process);
}

// Export the PM2 configuration
module.exports = {
  apps: scraperProcesses
};
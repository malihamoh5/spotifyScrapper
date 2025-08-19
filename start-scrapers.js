/**
 * Simple Start Scrapers Script
 * Fetches token and launches scrapers with PM2
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log("Starting Spotify scrapers...");

try {
  // First, ensure we have a valid token
  console.log("Fetching Spotify token...");
  execSync("node spotify-token-manager.js", { stdio: "inherit" });
  
  // Create the playlists directory if it doesn't exist
  const playlistsDir = path.resolve(__dirname, "../05_playlists");
  if (!fs.existsSync(playlistsDir)) {
    fs.mkdirSync(playlistsDir, { recursive: true });
    console.log("Created playlists directory.");
  }
  
  // Make sure the ecosystem.config.js file exists
  const ecosystemFile = path.resolve(__dirname, "ecosystem.config.js");
  if (!fs.existsSync(ecosystemFile)) {
    console.error("ecosystem.config.js file not found. Please create it first.");
    process.exit(1);
  }
  
  // Start the scrapers using PM2
  console.log("Starting scraper processes with PM2...");
  execSync("pm2 start ecosystem.config.js", { stdio: "inherit" });
  
  console.log("Scrapers started successfully!");
} catch (error) {
  console.error("Error starting scrapers:", error);
  process.exit(1);
}
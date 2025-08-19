/**
 * Spotify Token Manager
 * Fetches and manages Spotify API tokens
 */

const puppeteer = require("puppeteer");
const fs = require("fs");
const config = require('./config');
const TOKEN_FILE = config.paths.tokenFile;

// Helper function to fetch Spotify token
async function fetchSpotifyToken() {
  console.log("Starting browser to fetch Spotify token...");
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  let tokenLogged = false;
  let spotifyToken = "";

  await page.setRequestInterception(true);
  page.on("request", (interceptedRequest) => {
    const requestHeaders = interceptedRequest.headers();
    if (
      !tokenLogged &&
      requestHeaders.authorization &&
      requestHeaders.authorization.startsWith("Bearer ")
    ) {
      spotifyToken = requestHeaders.authorization;
      tokenLogged = true;
      console.log("Spotify token captured successfully");
      interceptedRequest.abort();
    } else {
      interceptedRequest.continue();
    }
  });

  console.log("Navigating to Spotify playlist page...");
  await page.goto(config.spotify.testPlaylistUrl, {
    waitUntil: "networkidle2",
    timeout: 60000, // 60 seconds timeout
  });

  await browser.close();
  if (!tokenLogged) {
    console.error("Failed to capture Spotify token.");
  }
  return spotifyToken;
}

// Function to write token to file
function writeTokenToFile(token) {
  console.log("Writing token to file...");
  fs.writeFileSync(TOKEN_FILE, JSON.stringify({ token }), "utf8");
  console.log("Token written to file successfully.");
}

// Function to read token from file
function readTokenFromFile() {
  console.log("Reading token from file...");
  if (fs.existsSync(TOKEN_FILE)) {
    const fileContent = fs.readFileSync(TOKEN_FILE, "utf8");
    try {
      const data = JSON.parse(fileContent);
      console.log("Token read successfully");
      return data.token;
    } catch (error) {
      console.error("Error parsing token file:", error);
      return null;
    }
  } else {
    console.error("Token file does not exist.");
  }
  return null;
}

// Main function to fetch and store token
async function main() {
  try {
    console.log("Fetching Spotify token...");
    const token = await fetchSpotifyToken();
    if (token) {
      writeTokenToFile(token);
      console.log("Spotify token fetched and stored.");
    } else {
      console.error("Spotify token was not fetched.");
    }
  } catch (error) {
    console.error("Error fetching Spotify token:", error);
  }
}

// If called directly, fetch the token
if (require.main === module) {
  main();
}

module.exports = { fetchSpotifyToken, writeTokenToFile, readTokenFromFile };
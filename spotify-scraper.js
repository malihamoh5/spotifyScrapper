/**
 * Optimized Spotify Playlist Scraper
 * Fetches track data from Spotify playlists with minimal overhead
 */

const axios = require("axios");
const fs = require("fs");
const { parse } = require("csv-parse");
const { promisify } = require("util");
const { exec } = require("child_process");
const config = require('./config');
// Get configuration
const CONCURRENT_LIMIT = config.scraper.concurrentRequests;
const TOKEN_FILE = config.paths.tokenFile;
const CHECKPOINT_FILE_NAME = process.env.CHECKPOINT_FILE_NAME;
const CSV_FILE_PATH = process.env.CSV_FILE_PATH;

// Global variables
let currentSpotifyToken = null;

// We'll initialize this later
let limit;

const extractPlaylistId = (url) => {
  const parts = url.split("/");
  return parts[parts.length - 1];
};

function readTokenFromFile() {
  if (fs.existsSync(TOKEN_FILE)) {
    const fileContent = fs.readFileSync(TOKEN_FILE, "utf8");
    try {
      const data = JSON.parse(fileContent);
      return data.token;
    } catch (error) {
      return null;
    }
  }
  return null;
}

function refreshToken() {
  return new Promise((resolve, reject) => {
    exec("node spotify-token-manager.js", (error, stdout, stderr) => {
      if (error) {
        reject(error.message);
      } else if (stderr) {
        reject(stderr);
      } else {
        resolve(stdout);
      }
    });
  });
}

async function fetchPlaylistData(playlistId, spotifyToken) {
  const base_url = "https://api-partner.spotify.com/pathfinder/v1/query";
  const operationName = "queryPlaylist";
  const extensions =
    '{"persistedQuery":{"version":1,"sha256Hash":"41f1c628a28715fd037d6cb18726994f73ee1883e23d98128ad432ad2a23d632"}}';
  let offset = 0;
  let playlistData = [];
  let total_count = null;

  while (total_count === null || offset < total_count) {
    const variables = `{"uri":"spotify:playlist:${playlistId}","limit":100,"offset":${offset}}`;
    const full_url = `${base_url}?operationName=${operationName}&variables=${encodeURIComponent(
      variables
    )}&extensions=${encodeURIComponent(extensions)}`;
    try {
      const response = await axios.get(full_url, {
        headers: { Authorization: spotifyToken },
      });

      if (
        response.data &&
        response.data.data &&
        response.data.data.playlistV2 &&
        response.data.data.playlistV2.content
      ) {
        const items = response.data.data.playlistV2.content.items;
        
        items.forEach((item) => {
          const track_info = item.itemV2 ? item.itemV2.data : null;
          if (
            track_info &&
            "name" in track_info &&
            "availableMarkets" in track_info &&
            "playability" in track_info &&
            "playcount" in track_info &&
            "uri" in track_info &&
            "duration" in track_info
          ) {
            const artistNames = track_info.artists.items.map(artist => artist.profile.name).join(";");
            const artistUris = track_info.artists.items.map(artist => artist.uri).join(";");
            playlistData.push({
              Name: track_info.name,
              PlaylistID: playlistId,
              AvailableMarkets: track_info.availableMarkets.items.length,
              Playability: track_info.playability
                ? track_info.playability.playable
                : false,
              Playcount: parseInt(track_info.playcount),
              URI: track_info.uri,
              ArtistNames: artistNames,
              ArtistUris: artistUris,
              Duration: track_info.duration.totalMilliseconds
            });
          }
        });
        
        offset += 30;
        total_count = response.data.data.playlistV2.content.totalCount;
      } else {
        break;
      }
    } catch (error) {
      if (error.response && error.response.status === 401) {
        await refreshToken();
        spotifyToken = readTokenFromFile();
      } else {
        break;
      }
    }
  }
  
  return playlistData;
}

function escapeCsvField(field) {
  if (typeof field === 'string' && field.includes(',')) {
    return `"${field.replace(/"/g, '""')}"`;
  }
  return field;
}

function jsonToCsv(jsonArray, includeHeaders = true) {
  if (jsonArray.length === 0) {
    return "";
  }
  const columns = Object.keys(jsonArray[0]);
  const header = includeHeaders ? columns.join(",") + "\n" : "";
  const rows = jsonArray
    .map((obj) =>
      columns.map((col) => escapeCsvField(obj[col] || "")).join(",")
    )
    .join("\n");
  return header + rows;
}

function chunkArray(array, size) {
  const chunks = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}

function saveProgressToCheckpoint(checkpointFile, progress) {
  fs.writeFileSync(checkpointFile, JSON.stringify(progress), "utf8");
}

function loadProgressFromCheckpoint(checkpointFile) {
  if (fs.existsSync(checkpointFile)) {
    const fileContent = fs.readFileSync(checkpointFile, "utf8");
    if (fileContent.trim().length === 0) {
      return { chunkIndex: 0, playlistIndex: 0 };
    }
    try {
      const checkpoint = JSON.parse(fileContent);
      return checkpoint;
    } catch (error) {
      return { chunkIndex: 0, playlistIndex: 0 };
    }
  }
  return { chunkIndex: 0, playlistIndex: 0 };
}

async function processChunks(
  chunks,
  outputFile,
  spotifyToken,
  limit,
  checkpoint
) {
  const fileExists = fs.existsSync(outputFile);
  
  for (let i = checkpoint.chunkIndex; i < chunks.length; i++) {
    const chunk = chunks[i];
    
    const playlistDataPromises = chunk
      .map((url, index) => {
        if (i === checkpoint.chunkIndex && index < checkpoint.playlistIndex) {
          return null;
        }
        return limit(async () => {
          const playlistId = extractPlaylistId(url);
          const data = await fetchPlaylistData(playlistId, spotifyToken);
          saveProgressToCheckpoint(CHECKPOINT_FILE_NAME, {
            chunkIndex: i,
            playlistIndex: index,
          });
          return data;
        });
      })
      .filter(Boolean); // Filter out null promises

    try {
      const results = await Promise.all(playlistDataPromises);
      const flattenedResults = results.flat();
      
      if (flattenedResults.length > 0) {
        const csvData = jsonToCsv(flattenedResults, !fileExists);
        fs.appendFileSync(outputFile, csvData + "\n", "utf8");
      }
    } catch (error) {
      // Continue with next chunk on error
    }
  }
}

function ensureFileExists(filePath, headers) {
  if (!fs.existsSync(filePath)) {
    fs.writeFileSync(filePath, headers.join(",") + "\n", "utf8");
  }
}

async function main() {
  // Get the current date in YYMMDD format
  const currentDate = new Date().toISOString().slice(2, 10).replace(/-/g, "");
  // Each scraper instance writes to its own file to avoid conflicts
  const scraperId = process.env.SCRAPER_ID || '1';
  const outputFile = `${currentDate}_output_part_${scraperId}.csv`;

  const headers = [
    "Name",
    "PlaylistID",
    "AvailableMarkets",
    "Playability",
    "Playcount",
    "URI",
    "ArtistNames",
    "ArtistUris",
    "Duration"
  ];

  ensureFileExists(outputFile, headers);

  try {
    // Import p-limit dynamically
    const pLimitModule = await import('p-limit');
    limit = pLimitModule.default(CONCURRENT_LIMIT);
    
    currentSpotifyToken = readTokenFromFile();
    if (!currentSpotifyToken) {
      process.exit(1);
    }

    if (!fs.existsSync(CSV_FILE_PATH)) {
      process.exit(1);
    }

    const csvContent = fs.readFileSync(CSV_FILE_PATH, "utf8");
    const records = await promisify(parse)(csvContent, {
      columns: false,
      skip_empty_lines: true,
    });
    const spotifyLinks = records.map((row) => row[0]);
    
    const chunks = chunkArray(spotifyLinks, config.scraper.chunkSize);
    const checkpoint = loadProgressFromCheckpoint(CHECKPOINT_FILE_NAME);

    await processChunks(
      chunks,
      outputFile,
      currentSpotifyToken,
      limit,
      checkpoint
    );
  } catch (err) {
    // Silent error handling
  }
}

main();
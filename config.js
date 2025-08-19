/**
 * Central configuration file for Spotify scraper
 */

module.exports = {
  // File and directory settings
  paths: {
    tokenFile: "spotify_token.json",
    playlistsFolder: "playlists",
    tempDir: "temp_chunks",
  },
  
  // Scraper settings
  scraper: {
    concurrentRequests: 4,
    chunkSize: 7,
    nodeMemoryLimit: 4096, // In MB
    playlistsDirPath: "05_playlists",
    playlistsCheckpoint: "05_playlists/checkpoint",
    // Uncomment and edit to enable second configuration for other scrapers
    // secondaryScraperDir: "chartmetric-scraper"
  },
  
  // Monitor settings
  monitor: {
    fileMinSizeGB: 5000, // Minimum file size in GB before stopping scraping (5 TB)
    checkIntervalMinutes: 30, // How often to check file size
  },
  
  // Data processing settings
  dataProcessing: {
    deduplicationKey: "URI", // Column used for deduplication
    processingChunkSize: 500000, // Rows per chunk during processing
  },
  
  // Spotify API settings
  spotify: {
    testPlaylistUrl: "https://open.spotify.com/playlist/0JTaSx9jkW1saMOc6t0vIk"
  },
  
  // Scraper instances configuration
  scraperInstances: {
    regularScrapers: 10  // Number of scraper instances to run
  }
};
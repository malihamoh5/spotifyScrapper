# Spotify Scraper System - Fixes Applied

## **Problems Identified & Fixed**

### 1. **macOS Compatibility Issues** ✅ FIXED
- **Problem**: Monitoring scripts used Linux-specific `stat -c %s` syntax
- **Fix**: Added OS detection and used appropriate `stat` commands for both macOS and Linux
- **Files Fixed**: `spotify-monitor.sh`, `90_start_scraper.sh`

### 2. **File Path Mismatches** ✅ FIXED
- **Problem**: Ecosystem config tried to create files in `../05_playlists` (parent directory)
- **Fix**: Changed all paths to use `05_playlists` in current directory
- **Files Fixed**: `ecosystem.config.js`, `start-scrapers.js`, `setup.sh`

### 3. **Multiple Scrapers Writing to Same File** ✅ FIXED
- **Problem**: All 5 scraper instances were writing to the same `250118_output.csv` file
- **Fix**: Each scraper now writes to its own file: `250118_output_part_1.csv`, `250118_output_part_2.csv`, etc.
- **Files Fixed**: `spotify-scraper.js`, `ecosystem.config.js`

### 4. **Monitoring Script File Detection** ✅ FIXED
- **Problem**: Monitoring scripts looked for single `250118_output.csv` file
- **Fix**: Updated to detect and sum sizes of all `250118_output_part_*.csv` files
- **Files Fixed**: `spotify-monitor.sh`, `90_start_scraper.sh`

## **How the Fixed System Works**

### **Before (Broken)**:
```
5 scrapers → 1 output file → File corruption → Crashes
```

### **After (Fixed)**:
```
Scraper 1 → 250118_output_part_1.csv
Scraper 2 → 250118_output_part_2.csv  
Scraper 3 → 250118_output_part_3.csv
Scraper 4 → 250118_output_part_4.csv
Scraper 5 → 250118_output_part_5.csv

Monitor → Sums all file sizes → Restarts if below threshold
```

## **Testing the Fixes**

### **Step 1: Clean Setup**
```bash
# Stop any running processes
pm2 delete all

# Clean up old files
rm -f *_output*.csv
rm -rf 05_playlists

# Run setup
chmod +x setup.sh
./setup.sh
```

### **Step 2: Test Token Management**
```bash
node spotify-token-manager.js
# Should create spotify_token.json
```

### **Step 3: Test Single Scraper**
```bash
# Test one scraper instance
SCRAPER_ID=1 CSV_FILE_PATH=05_playlists/playlists_part_001.csv CHECKPOINT_FILE_NAME=05_playlists/checkpoint_1.json node spotify-scraper.js
```

### **Step 4: Test Full System**
```bash
# Start all scrapers
node start-scrapers.js

# Check PM2 status
pm2 status

# Monitor logs
pm2 logs
```

### **Step 5: Test Monitoring**
```bash
# Start monitoring in background
nohup ./spotify-monitor.sh > spotify-monitor.log 2>&1 &

# Check monitoring logs
tail -f spotify-monitor.log
```

## **Expected Behavior After Fixes**

1. **No More Crashes**: Each scraper writes to its own file
2. **Proper Monitoring**: File size detection works on macOS and Linux
3. **Auto-Restart**: System automatically restarts when target size not reached
4. **Data Integrity**: No more file corruption from multiple writers

## **Monitoring Output Example**
```
Mon Aug 18 19:24:07 PKT 2025: Found 5 output files, total size: 2.45 GB
Mon Aug 18 19:24:07 PKT 2025: Total file size (2.45 GB) is below threshold (5.0 GB)
Mon Aug 18 19:24:07 PKT 2025: Stopping all PM2 processes...
Mon Aug 18 19:24:07 PKT 2025: Starting new scraper processes...
```

## **Troubleshooting**

### **If scrapers still crash**:
1. Check PM2 logs: `pm2 logs`
2. Check individual scraper logs: `pm2 logs spotify-scraper-1`
3. Verify token is valid: `cat spotify_token.json`

### **If monitoring doesn't work**:
1. Check file permissions: `ls -la spotify-monitor.sh`
2. Check OS compatibility: `echo $OSTYPE`
3. Test file size detection manually

### **If files aren't created**:
1. Check directory exists: `ls -la 05_playlists/`
2. Check playlist input files: `ls -la 05_playlists/playlists_part_*.csv`
3. Verify environment variables are set correctly

## **Next Steps**

1. **Test the fixes** using the testing steps above
2. **Monitor the system** for 24-48 hours to ensure stability
3. **Adjust thresholds** in `config.js` if needed
4. **Scale up** by increasing `NUM_SCRAPERS` in `ecosystem.config.js`

The system should now be stable and handle large-scale Spotify data collection without crashing! 
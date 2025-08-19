#!/usr/bin/env python3
"""
Data Deduplicator for Spotify track data
Removes duplicate entries from CSV files based on URI
"""

import csv
import sys
import glob
import os
import re
import datetime
import json

# Load configuration
def load_config():
    try:
        with open('config.js', 'r') as f:
            # Extract the content between the module.exports = { and the closing };
            config_text = f.read()
            config_json = re.search(r'module\.exports\s*=\s*(\{.*?\n\}\s*);', config_text, re.DOTALL)
            if config_json:
                # Convert JS object to JSON-like string
                js_obj = config_json.group(1)
                # Replace JS style with JSON style
                js_obj = re.sub(r'(\w+):', r'"\1":', js_obj)
                # Replace single quotes with double quotes
                js_obj = js_obj.replace("'", '"')
                # Remove trailing commas
                js_obj = re.sub(r',\s*(\}|\])', r'\1', js_obj)
                # Parse the JSON
                return json.loads(js_obj)
            else:
                raise ValueError("Could not parse config.js")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        # Default configuration
        return {
            "dataProcessing": {
                "deduplicationKey": "URI"
            }
        }

def deduplicate_csv(input_file, output_file, key_column):
    """
    Deduplicate a CSV file based on a key column
    
    Args:
        input_file: Path to the input CSV file
        output_file: Path to the output CSV file
        key_column: Column name to use for deduplication
    """
    # Increase CSV field size limit to handle large files
    try:
        csv.field_size_limit(sys.maxsize)
    except OverflowError:
        csv.field_size_limit(int(sys.maxsize / 2))
    
    seen_keys = set()
    with open(input_file, mode='r', newline='', encoding='utf-8') as infile, \
         open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        # Read and write header row
        try:
            headers = next(reader)
            writer.writerow(headers)
        except StopIteration:
            print(f"Error: File {input_file} appears to be empty")
            return

        # Find index of key column
        try:
            key_index = headers.index(key_column)
        except ValueError:
            print(f"Error: Column '{key_column}' not found in the CSV header.")
            print(f"Available columns: {', '.join(headers)}")
            return

        # Process data rows
        skipped_rows = 0
        processed_rows = 0
        unique_rows = 0
        
        for row in reader:
            processed_rows += 1
            try:
                key = row[key_index]
                if key and key not in seen_keys:  # Skip empty keys
                    seen_keys.add(key)
                    writer.writerow(row)
                    unique_rows += 1
            except IndexError:
                skipped_rows += 1
                if skipped_rows <= 10:  # Only show first 10 errors
                    print(f"Warning: Row {processed_rows} has insufficient columns")

        # Print statistics
        print(f"Processed {input_file}:")
        print(f"  Total rows processed: {processed_rows}")
        print(f"  Unique rows saved: {unique_rows}")
        print(f"  Duplicate rows: {processed_rows - unique_rows - skipped_rows}")
        print(f"  Skipped rows due to missing data: {skipped_rows}")

def deduplicate_all_files(pattern, key_column):
    """
    Deduplicate all files matching a pattern
    
    Args:
        pattern: Glob pattern to match files
        key_column: Column name to use for deduplication
    """
    # Find files matching the pattern
    files = glob.glob(pattern)
    if not files:
        print(f"No files found matching pattern: {pattern}")
        return
    
    # Get today's date in YYMMDD format
    today_date = datetime.datetime.now().strftime('%y%m%d')
    
    # Sort files by date (extracted from filename)
    try:
        files.sort(key=lambda x: int(re.search(r'(\d{6})_output\.csv', x).group(1)))
    except (AttributeError, ValueError):
        print("Warning: Could not sort files by date. Processing in default order.")
    
    # Print summary of files to process
    print(f"Found {len(files)} files to process:")
    for f in files:
        print(f"  {f}")

    # Process each file
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    for file in files:
        # Uncomment to skip today's file if needed
        # if re.search(rf'{today_date}_output\.csv', file):
        #     print(f"Skipping today's file: {file}")
        #     skipped_count += 1
        #     continue

        # Determine output filename
        file_name, file_extension = os.path.splitext(file)
        output_file = file_name.replace('_output', '') + '_unique' + file_extension
        print(f"\nProcessing file: {file}")

        # Skip if output file already exists
        if os.path.exists(output_file):
            print(f"Unique file already exists: {output_file}, skipping deduplication.")
            if os.path.exists(file):
                os.remove(file)
                print(f"Deleted original file: {file}")
            skipped_count += 1
            continue

        # Process the file
        try:
            deduplicate_csv(file, output_file, key_column)
            print(f"Deduplicated and saved as: {output_file}")
            
            # Delete original file if output was created successfully
            if os.path.exists(output_file):
                os.remove(file)
                print(f"Deleted original file: {file}")
            processed_count += 1
        except Exception as e:
            print(f"Error processing file {file}: {str(e)}")
            error_count += 1

    # Print summary
    print("\nDeduplication summary:")
    print(f"  Files processed successfully: {processed_count}")
    print(f"  Files skipped (already processed): {skipped_count}")
    print(f"  Files with errors: {error_count}")
    print(f"  Total files found: {len(files)}")

if __name__ == "__main__":
    print("Spotify Data Deduplicator")
    print("=========================")
    
    # Load configuration
    config = load_config()
    
    # Get deduplication key from config
    dedup_key = config.get("dataProcessing", {}).get("deduplicationKey", "URI")
    print(f"Using deduplication key: {dedup_key}")
    
    # Check for command-line arguments
    if len(sys.argv) > 1:
        # If pattern is provided as argument
        pattern = sys.argv[1]
        print(f"Using pattern from command line: {pattern}")
        
        # Check if custom key is provided
        if len(sys.argv) > 2:
            dedup_key = sys.argv[2]
            print(f"Using custom deduplication key: {dedup_key}")
    else:
        # Default pattern
        pattern = "*_output.csv"
        print(f"Using default pattern: {pattern}")
    
    # Run deduplication
    deduplicate_all_files(pattern, dedup_key)
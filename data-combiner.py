#!/usr/bin/env python3
"""
Data Combiner for Spotify track data
Combines and processes multiple CSV files with deduplication
"""

import os
import glob
import pandas as pd
import numpy as np
import time
from tqdm import tqdm
import psutil
import gc
import csv
from io import StringIO
import json
import re
import sys

# Load configuration
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
            config = json.loads(js_obj)
        else:
            raise ValueError("Could not parse config.js")
except Exception as e:
    print(f"Error loading configuration: {e}")
    # Default configuration
    config = {
        "dataProcessing": {
            "processingChunkSize": 500000,
            "tempDir": "temp_chunks"
        }
    }

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / 1024 / 1024
    return f"{mem:.2f} MB"

def process_large_csvs(files_list, output_file, chunk_size=None, temp_dir=None):
    """
    Process multiple large CSV files by:
    1. Reading each file in chunks
    2. Sorting by Playcount (descending)
    3. Deduplicating based on URI (keeping highest Playcount)
    
    Args:
        files_list: List of specific CSV files to process or glob pattern
        output_file: Path to the final output file
        chunk_size: Number of rows to process at once
        temp_dir: Directory for temporary files
    """
    # Use configuration values or defaults
    chunk_size = chunk_size or config.get("dataProcessing", {}).get("processingChunkSize", 500000)
    temp_dir = temp_dir or config.get("dataProcessing", {}).get("tempDir", "temp_chunks")
    
    start_time = time.time()
    
    # If input is a glob pattern, expand it
    if isinstance(files_list, str):
        files = glob.glob(files_list)
        print(f"Found {len(files)} files matching pattern: {files_list}")
    else:
        # Filter to make sure files exist
        files = [f for f in files_list if os.path.exists(f)]
        print(f"Processing {len(files)} specified files: {', '.join(files)}")
    
    # Create temp directory if it doesn't exist
    os.makedirs(temp_dir, exist_ok=True)
    
    # Track all temp files created
    temp_files = []
    total_rows_processed = 0
    
    # Step 1: Process each input file in chunks, creating sorted temp files
    for file_num, file_path in enumerate(files, 1):
        file_start_time = time.time()
        file_size_gb = os.path.getsize(file_path) / (1024**3)
        print(f"\nProcessing file {file_num}/{len(files)}: {file_path} ({file_size_gb:.2f} GB)")
        print(f"Memory usage before processing: {get_memory_usage()}")
        
        # Track chunks for this file
        file_chunks = []
        file_rows_processed = 0
        
        # Process file in chunks
        try:
            # First attempt to detect delimiter and quoting format
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as sample:
                    sample_data = sample.read(10000)  # Read a small sample to detect format
                    dialect = csv.Sniffer().sniff(sample_data)
                
                # Read with more robust error handling
                chunk_iter = pd.read_csv(
                    file_path, 
                    chunksize=chunk_size,
                    on_bad_lines='warn',    # Skip bad lines in newer pandas versions
                    dtype=str,              # Read everything as string initially
                    low_memory=False,       # More accurate dtypes detection
                    delimiter=dialect.delimiter,
                    quotechar=dialect.quotechar,
                    escapechar='\\',        # Handle potential escaping
                    encoding='utf-8',
                    encoding_errors='replace'
                )
            except Exception as e:
                print(f"CSV format detection failed: {str(e)}. Using default CSV reader settings.")
                # Fallback to default settings
                chunk_iter = pd.read_csv(
                    file_path, 
                    chunksize=chunk_size,
                    on_bad_lines='warn',
                    dtype=str,
                    low_memory=False,
                    encoding='utf-8',
                    encoding_errors='replace'
                )
            
            total_chunks = None  # We'll estimate this after first chunk
        except Exception as file_error:
            print(f"\nError processing file {file_path}: {str(file_error)}")
            print("Attempting to continue with next file...")
            continue  # Skip to the next file
        
        for i, chunk in enumerate(tqdm(chunk_iter, desc=f"Reading chunks from {os.path.basename(file_path)}", 
                                        total=total_chunks, unit="chunks")):
            # Update total_chunks estimate after first chunk
            if i == 0 and total_chunks is None:
                try:
                    # Estimate total chunks based on file size and first chunk size
                    first_chunk_memory = chunk.memory_usage(deep=True).sum()
                    file_size = os.path.getsize(file_path)
                    estimated_chunks = int(file_size / (first_chunk_memory / chunk.shape[0]) * chunk.shape[0])
                    total_chunks = max(estimated_chunks // chunk_size, i+1)
                    tqdm.write(f"Estimated {total_chunks} chunks in this file")
                except:
                    total_chunks = None  # Continue without estimate if calculation fails
            
            # For each chunk, make sure Playcount is numeric for proper sorting
            # (since we're reading everything as strings initially)
            if 'Playcount' in chunk.columns:
                try:
                    chunk['Playcount'] = pd.to_numeric(chunk['Playcount'], errors='coerce')
                    chunk = chunk.fillna({'Playcount': 0})  # Replace NaN with 0 for invalid conversions
                except Exception as e:
                    print(f"Warning: Error converting Playcount to numeric: {str(e)}")
            
            # Process this chunk
            if len(chunk.columns) > 0:  # Only process if chunk has data
                file_rows_processed += len(chunk)
                
                # Check if the required columns exist
                if 'Playcount' in chunk.columns and 'URI' in chunk.columns:
                    # Sort by Playcount (descending) and deduplicate on URI keeping first occurrence (highest Playcount)
                    chunk = chunk.sort_values('Playcount', ascending=False)
                    chunk = chunk.drop_duplicates(subset=['URI'])
                    
                    # Write sorted & deduplicated chunk to temp file
                    temp_file = os.path.join(temp_dir, f"temp_chunk_{file_num}_{i}.parquet")
                    chunk.to_parquet(temp_file, index=False)
                    file_chunks.append(temp_file)
                else:
                    print(f"Warning: Chunk {i} missing required columns. Available columns: {chunk.columns.tolist()}")
            else:
                print(f"Warning: Empty chunk {i} encountered")
            
            # Clear memory
            del chunk
            gc.collect()
            
            if i % 10 == 0:
                tqdm.write(f"Memory usage: {get_memory_usage()}")
        
        total_rows_processed += file_rows_processed
        temp_files.extend(file_chunks)
        
        print(f"Processed {file_rows_processed:,} rows from file {file_num}")
        print(f"Created {len(file_chunks)} temporary chunk files")
        print(f"Time taken: {time.time() - file_start_time:.2f} seconds")
        print(f"Memory usage after processing: {get_memory_usage()}")
    
    print(f"\nTotal rows processed across all files: {total_rows_processed:,}")
    print(f"Total temporary files created: {len(temp_files)}")
    
    # Step 2: Merge all temp files and perform final deduplication
    print("\nMerging temporary files and performing final deduplication...")
    print(f"Memory usage before merge: {get_memory_usage()}")
    
    # Create a dictionary to track highest Playcount for each URI
    uri_highest_playcount = {}
    uri_row_data = {}
    
    # Process each temp file
    for i, temp_file in enumerate(tqdm(temp_files, desc="Merging temp files")):
        try:
            df = pd.read_parquet(temp_file)
            
            # Iterate through rows (more memory efficient than apply)
            for _, row in df.iterrows():
                uri = row['URI']
                playcount = row['Playcount']
                
                # Keep track of highest Playcount for each URI
                if uri not in uri_highest_playcount or playcount > uri_highest_playcount[uri]:
                    uri_highest_playcount[uri] = playcount
                    uri_row_data[uri] = row.to_dict()
            
            # Clean up
            del df
            gc.collect()
            
            if (i+1) % 10 == 0:
                tqdm.write(f"Processed {i+1}/{len(temp_files)} temp files. Memory: {get_memory_usage()}")
                tqdm.write(f"Unique URIs found so far: {len(uri_highest_playcount):,}")
        except Exception as temp_file_error:
            print(f"Error processing temp file {temp_file}: {str(temp_file_error)}")
    
    print(f"Total unique URIs after deduplication: {len(uri_highest_playcount):,}")
    
    # Convert deduplicated data to DataFrame
    print("Creating final DataFrame...")
    final_df = pd.DataFrame(list(uri_row_data.values()))
    
    # Save final result
    print(f"Saving final deduplicated data to {output_file}...")
    final_df.to_csv(output_file, index=False)
    
    # Cleanup temp files
    print("Cleaning up temporary files...")
    for temp_file in temp_files:
        try:
            os.remove(temp_file)
        except:
            pass
    
    try:
        os.rmdir(temp_dir)
    except:
        print(f"Note: Could not remove temp directory {temp_dir}, it might not be empty")
    
    total_time = time.time() - start_time
    print(f"\nProcessing complete!")
    print(f"Total time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
    print(f"Final file size: {os.path.getsize(output_file) / (1024**3):.2f} GB")
    print(f"Final memory usage: {get_memory_usage()}")
    
    return final_df

if __name__ == "__main__":
    # Get chunk size from config
    chunk_size = config.get("dataProcessing", {}).get("processingChunkSize", 500000)
    temp_dir = config.get("dataProcessing", {}).get("tempDir", "temp_chunks")
    
    if len(sys.argv) > 1:
        # Use command line arguments if provided
        if sys.argv[1] == "--pattern" and len(sys.argv) > 2:
            # Process using pattern
            file_pattern = sys.argv[2]
            output_file = sys.argv[3] if len(sys.argv) > 3 else "combined_deduplicated.csv"
            print(f"Processing files matching pattern: {file_pattern}")
            print(f"Output will be saved to: {output_file}")
            process_large_csvs(file_pattern, output_file, chunk_size, temp_dir)
        elif sys.argv[1] == "--files":
            # Process specific files
            files_to_process = sys.argv[2:-1]
            output_file = sys.argv[-1]
            print(f"Processing specified files: {files_to_process}")
            print(f"Output will be saved to: {output_file}")
            process_large_csvs(files_to_process, output_file, chunk_size, temp_dir)
        else:
            print("Usage:")
            print("  python data-combiner.py --pattern \"*_unique.csv\" [output_file.csv]")
            print("  python data-combiner.py --files file1.csv file2.csv ... output_file.csv")
    else:
        # Default behavior
        file_pattern = "*_unique.csv"
        output_file = "combined_deduplicated.csv"
        print(f"No arguments provided. Using default pattern: {file_pattern}")
        print(f"Output will be saved to: {output_file}")
        process_large_csvs(file_pattern, output_file, chunk_size, temp_dir)
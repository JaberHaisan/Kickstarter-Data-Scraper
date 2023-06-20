import glob
import os
import logging
import csv

PATH = "Output"
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, datefmt='%m/%d/%Y %I:%M:%S %p')

def merge_csv_files(csv_file_paths, merged_csv_path):
    """"Writes multiple csv files to one csv file.
    
    Inputs:
    csv_file_path [iterable] - An iterable containing csv file paths.
    merged_csv_path [str] - Location of csv file to be written to."""
    files = []
    readers = []
    longest_header = []
    
    # Get csv readers and file objects. Also get the longest
    # header.
    for csv_file_path in csv_file_paths:
        f = open(csv_file_path, "r", encoding="utf-8", newline='')
        reader = csv.reader(f)
        readers.append(reader)
        files.append(f)

        header = next(reader)
        if len(header) > len(longest_header):
            longest_header = header
    
    # Write lines.
    with open(merged_csv_path, "w", encoding="utf-8", newline='') as f_obj:
        writer = csv.writer(f_obj)
        writer.writerow(header)
        for reader in readers:
            writer.writerows(reader)

    # Close files.
    for file in files:
        file.close()

if __name__ == "__main__":
    # Find csvs.
    result_csvs = glob.iglob(PATH + "/*/results*.csv")
    missing_csvs = glob.iglob(PATH + "/*/missing*.csv")

    # Merge csvs and write to one csv.
    logging.info("Started merging results csv files...")
    merge_csv_files(result_csvs, os.path.join(PATH, "merged_results.csv"))
    logging.info("Finished merging results csvs files.")

    logging.info("Started merging missing csv files...")
    merge_csv_files(missing_csvs, os.path.join(PATH, "merged_missing.csv"))
    logging.info("Finished merging missing csvs files.")

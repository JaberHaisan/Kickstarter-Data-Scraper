import glob
import os
import logging

import pandas as pd

PATH = "Output"
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, datefmt='%m/%d/%Y %I:%M:%S %p')

# Find csvs.
result_csvs = glob.iglob(PATH + "/*/results*.csv")
missing_csvs = glob.iglob(PATH + "/*/missing*.csv")

# Merge csvs and write to one csv.
logging.info("Started merging results csvs...")
merged_results_df = pd.concat([pd.read_csv(result_csv, low_memory=False) for result_csv in result_csvs])
merged_results_df.to_csv(os.path.join(PATH, "merged_results.csv"), index=False)
logging.info("Fininished merging results csvs.")

logging.info("Started merging missing csvs...")
merged_missing_df = pd.concat([pd.read_csv(missing_csv, low_memory=False) for missing_csv in missing_csvs])
merged_missing_df.to_csv(os.path.join(PATH, "merged_missing.csv"), index=False)
logging.info("Fininished merging missing csvs.")

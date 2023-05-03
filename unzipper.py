import os
import zipfile

def extract_html_files(path, data_folder):
    """Extracts all html files in the zipped folders in path
    to the given data folder (created if it doesn't exist) and
    returns a list of the file paths.

    path [str] - Path to zip files.
    data_folder [str] - Path to folder to store unzipped data."""
    data_folder_path = os.path.join(path, data_folder)

    # # Make data folder if it doesn't exist.
    # os.makedirs(data_folder_path, exist_ok=True)

    # Find all zip files in current path and extract them to data_folder.
    zip_files = []
    for file in os.listdir(path):
        if file.endswith(".zip"):
            zip_files.append(file)

    for zip_file in zip_files:
        with zipfile.ZipFile(os.path.join(path, zip_file), 'r') as zip_ref:
            zip_ref.extractall(data_folder_path)

    # Files to ignore.
    ignore_set = {"community", "faqs", "comments", "updates"}

    # Get paths of all html files in the data folder.
    html_files = []
    for (root,dirs,files) in os.walk(data_folder_path):
        for file in files:
            if file.endswith(".html"):
                # Ignore certain files.
                if file.split("_")[1] not in ignore_set:
                    html_files.append(os.path.join(root, file))
    
    return html_files

if __name__ == "__main__":
    # Path to zip files.
    path = r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Data\art"

    # Folder which will contain unzipped data.
    data_folder = "Unzipped"

    html_files = extract_html_files(path, data_folder)
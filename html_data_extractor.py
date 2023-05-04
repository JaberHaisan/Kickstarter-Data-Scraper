from datetime import datetime
import os
import zipfile
import time
import multiprocessing

from bs4 import BeautifulSoup
import pandas as pd

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

def extract_campaign_data(file_path):
    """"Extracts data from a kickstarter campaign page and returns
    it in a dictionary."""
    with open(file_path, encoding='utf8') as infile:
        soup = BeautifulSoup(infile, "html.parser")

    data = {}

    # Date and time accessed.
    date_time_str = file_path.split("_")[-1]
    date_time_str = date_time_str[:-5] 
    date, time = date_time_str.split("-")

    data["date_accessed"] = date
    data["time_accessed"] = time

    # Creator, Title and Blurb
    meta_elem = soup.select('meta[name="description"]')[0]
    lines = meta_elem["content"].splitlines()
    creator, title = lines[0].split(" is raising funds for ")
    title = title.strip()
    blurb = lines[-1].strip()

    data["title"] = title
    data["creator"] = creator
    data["blurb"] = blurb 
    
    # Url
    url_elem = soup.select('meta[property="og:url"]')
    data["url"] = url_elem[0]["content"]

    # Backers.
    try:
        backers_elem = soup.select('div[class="block type-16 type-24-md medium soft-black"]')
        backers = backers_elem[0].getText()
    # Backers data missing.
    except:
        backers = ""
    finally:
        data["backers"] = backers

    # Project goal.
    try:
        goal_elem = soup.select('span[class="inline-block-sm hide"]')
        goal = goal_elem[0].contents[1].getText()
    # Goal data missing.
    except:
        goal = ""
    finally:
        data["goal"] = goal

    # Pledged amount.
    try:
        pledged_elem = soup.select('span[class="ksr-green-700"]')
        pledged = pledged_elem[0].getText()
    # Pledged amount data missing.
    except IndexError:
        pledged = ""
    finally: 
        data["pledged"] = pledged

    # Campaign end time.
    try:
        end_time_elem = soup.select('p[class="mb3 mb0-lg type-12"]')[0]
        time_str = end_time_elem.getText()[80:]
        dt = datetime.strptime(time_str, "%B %d %Y %I:%M %p %Z %z.")
        endday, endmonth, endyear = dt.day, dt.month, dt.year
    # End time missing.
    except IndexError:
        endday, endmonth, endyear = "", "", ""
    finally:
        data["endday"] = endday
        data["endmonth"] = endmonth
        data["endyear"] = endyear

    # Category and Location.
    try:
        cat_loc_elems = soup.select('span[class="ml1"]')
        cat_loc_data = [cat_loc_elem.getText() for cat_loc_elem in cat_loc_elems]
        category = cat_loc_data[0]
        location = cat_loc_data[-1]
    # Category and location missing.
    except IndexError:
        category = ""
        location = ""
    finally:
        data["category"] = category
        data["location"] = location

    # Number of projects created.
    try:
       project_num_elem = soup.select('a[class="dark-grey-500 keyboard-focusable"]')
       projects_num = project_num_elem[0].getText().split()[0]
    # Project number missing.
    except IndexError:
        projects_num = ""
    finally:
        data["projects_num"] = projects_num

    # Number of comments.
    comments_elem = soup.select('data[itemprop="Project[comments_count]"]')
    data["comments_num"] = comments_elem[0].getText()
    
    # Number of updates.
    updates_elem = soup.select('a[data-content="updates"]')[0]
    data["updates_num"] = updates_elem.contents[1].getText()

    # Number of faq.
    faq_elem = soup.select('a[data-content="faqs"]')[0]
    # Kickstarter does not show 0 if there are no faq so
    # need to check for lack of faq.
    if len(faq_elem.contents) > 1:
        data["faq_num"] = faq_elem.contents[1].getText()
    else:
        data["faq_num"] = 0

    # Description.
    try:
        description_elem = soup.select('div[class="full-description js-full-description responsive-media formatted-lists"]')
        description = description_elem[0].getText().strip()
    # Desciption missing.
    except IndexError:
        description = ""
    finally:
        data["description"] = description

    return data

if __name__ == "__main__":
    # Path to zip files.
    path = r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Data\art"

    # Folder which will contain unzipped data.
    data_folder = "Unzipped"

    html_files = extract_html_files(path, data_folder)

    start = time.time()

    pool = multiprocessing.Pool()
    all_data = pool.map(extract_campaign_data, html_files, chunksize=10)
    pool.close()
    pool.join()

    end = time.time()
    print(f"Took {end-start}s to process {len(html_files)} files.")

    df = pd.DataFrame(all_data)

    df.to_csv('results.csv', index=False)

# # Testing code.
# if __name__ == "__main__":
#     # No faq
#     file_path_1 = r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Data\art\a1\1-1000-supporters-an-art-gallery-and-design-boutiq\1-1000-supporters-an-art-gallery-and-design-boutiq_20190312-010622.html"
    
#     # Has faq. No blurb, creator, backer, goal, date, category, location, projects_num
#     file_path_2 = r"C:/Users/jaber/OneDrive/Desktop/Research_JaberChowdhury/Data/art/a1/100-quirky-characters/100-quirky-characters_20190201-150330.html"
    
#     data_1 = extract_campaign_data(file_path_1)
#     data_2 = extract_campaign_data(file_path_2)

#     data = [data_1, data_2]
#     df = pd.DataFrame(data)

#     df.to_csv('results.csv')

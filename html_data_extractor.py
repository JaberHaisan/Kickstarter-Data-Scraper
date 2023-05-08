import os
import zipfile
import time
import multiprocessing
from datetime import datetime
import re

from bs4 import BeautifulSoup
import pandas as pd

def extract_html_files(path, data_folder):
    """Extracts all files in the zipped folders in path
    to the given data folder (created if it doesn't exist) and
    returns a list of the html file paths.

    Inputs:
    path [str] - Path to zip files.
    data_folder [str] - Path to folder to store unzipped data."""
    data_folder_path = os.path.join(path, data_folder)

    # Make data folder if it doesn't exist.
    os.makedirs(data_folder_path, exist_ok=True)

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

def get_digits(string):
    """Returns only digits from string as a single integer."""
    res = re.findall(r'\d+', string)
    return int("".join(res))

def get_pledge_data(bs4_tag, index):
    """Returns a dict of data from a kickstarter pledge li bs4 tag.
    Dict will contain:
    rd_title: Pledge title
    rd_cost: Pledge cost
    rd_desc: Pledge description 
    rd_delivery_date: Pledge Estimated Delivery. Format YYYY-MM-DD.
    rd_backers: Total number of backers.
    rd_limit: Limit in number of backers of pledge. Empty string if there are no
    limits.

    Inputs:
    bs4_tag [bs4.element.Tag] - A tag of a kickstarter Pledge.
    Index [int] - The index of the current pledge."""
    pledge_data = {}
    i = str(index)

    pledge_data['rd_title_' + i] = bs4_tag.select_one('h3[class="pledge__title"]').getText().strip()
    pledge_data['rd_cost_' + i] = bs4_tag.select_one('span[class="pledge__currency-conversion"] > span').getText()
    pledge_data['rd_desc_' + i] = bs4_tag.select_one('div[class="pledge__reward-description pledge__reward-description--expanded"]').getText().replace('\n', '')[:-4]
    pledge_data['rd_delivery_date_' + i] = bs4_tag.select_one('span[class="pledge__detail-info"] > time')['datetime']

    try:
        rd_backers = get_digits(bs4_tag.select_one('span[class="pledge__backer-count"]').getText())
        rd_limit = ""
    # Reward has a limit so it has a different class value.
    except AttributeError:
        rd_backers = get_digits(bs4_tag.select_one('span[class="block pledge__backer-count"]').getText())
        rd_limit = get_digits(bs4_tag.select_one('span[class="pledge__limit"]').getText().split()[-1])
    finally:
        pledge_data["rd_backers_" + i] = rd_backers
        pledge_data["rd_limit_" + i] = rd_limit

    return pledge_data

def extract_campaign_data(file_path):
    """"Extracts data from a kickstarter campaign page and returns
    it in a dictionary.
    
    Inputs:
    file_path [str] - Path to html file."""
    with open(file_path, encoding='utf8') as infile:
        soup = BeautifulSoup(infile, "lxml")

    data = {}
    # Boolean to toggle for currency conversion.
    conversion_needed = False

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

    # Creator profile url
    creator_profile_elem = soup.select_one('meta[property="kickstarter:creator"]')
    data["creator_profile"] = creator_profile_elem['content']

    # Backers.
    try:
        backers_elem = soup.select('div[class="block type-16 type-24-md medium soft-black"]')
        backers = backers_elem[0].getText()
    # Backers data missing.
    except:
        backers = ""
    finally:
        data["backers"] = backers

    # Get conversion rate of currency if necessary for goal and pledged amounts.
    curr_elems = soup.select('div[class="input__currency-conversion"]')
    # Check if currency conversions are present.
    if len(curr_elems) > 0:
        curr_elem = curr_elems[0]
        back_elem = soup.select('input[name="backing[amount]"]')[0]

        base_curr = get_digits(curr_elem.contents[1].getText())
        other_curr = get_digits(back_elem["value"])
        conversion_rate = base_curr / other_curr
        base_curr_symbol = "".join([char for char in curr_elem.contents[1].getText() if not char.isdigit()])
        conversion_needed = True

        data["conversion_rate"] = conversion_rate
    else:
        data["conversion_rate"] = 1

    # Project goal.
    try:
        goal_elem = soup.select('span[class="inline-block-sm hide"]')
        goal = goal_elem[0].contents[1].getText()
        converted_goal = goal
        if conversion_needed:
            converted_goal = get_digits(converted_goal) * conversion_rate
            converted_goal = base_curr_symbol + str(converted_goal)
    # Goal data missing.
    except:
        goal = ""
        converted_goal = ""
    finally:
        data["goal"] = goal
        data["converted_goal"] = converted_goal

    # Pledged amount.
    try:
        pledged_elem = soup.select('span[class="ksr-green-700"]')
        pledged = pledged_elem[0].getText()
        converted_pledged = pledged
        if conversion_needed:
            converted_pledged = get_digits(converted_pledged) * conversion_rate
            converted_pledged = base_curr_symbol + str(converted_pledged)
    # Pledged amount data missing.
    except IndexError:
        pledged = ""
        converted_pledged = ""
    finally: 
        data["pledged"] = pledged
        data["converted_pledged"] = converted_pledged

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

    # Projects we love (PWL), Category, Location. PWL is 1 if project is 
    # part of PWL and otherwise 0.
    try:
        pwl_cat_loc_elems = soup.select('span[class="ml1"]')
        pwl_cat_loc_data = [pwl_cat_loc_elem.getText() for pwl_cat_loc_elem in pwl_cat_loc_elems]

        # Project is part of Projects we Love.
        if "Project We Love" in pwl_cat_loc_data:
            pwl = 1
            category = pwl_cat_loc_data[1]
            location = pwl_cat_loc_data[2]
        else:
            pwl = 0
            category = pwl_cat_loc_data[0]
            location = pwl_cat_loc_data[1]

    # Category or location missing.
    except IndexError:
        pwl = ""
        category = ""
        location = ""
    finally:
        data["pwl"] = pwl
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

    # Pledges.
    pledge_elems = soup.select('li[class="hover-group js-reward-available pledge--available pledge-selectable-sidebar"]')
    for i, pledge_elem in enumerate(pledge_elems):
        data |= get_pledge_data(pledge_elem, i)

    return data

def test_extract_campaign_data():
    # Testing code.
    file_paths = [
                r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Data\art\a1\1-1000-supporters-an-art-gallery-and-design-boutiq\1-1000-supporters-an-art-gallery-and-design-boutiq_20190312-010622.html",
                #r"C:/Users/jaber/OneDrive/Desktop/Research_JaberChowdhury/Data/art/a1/15-pudgy-budgie-and-friends-enamel-pins/15-pudgy-budgie-and-friends-enamel-pins_20190214-140329.html",
                ]
    data = [extract_campaign_data(file_path) for file_path in file_paths]
    df = pd.DataFrame(data)
    df.to_csv('test.csv', index = False)

if __name__ == "__main__":
    # Path to zip files.
    path = r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Data\art"

    # Folder which will contain unzipped data.
    data_folder = "Unzipped"

    html_files = extract_html_files(path, data_folder)

    # Extract data from html files.
    start = time.time()

    pool = multiprocessing.Pool()
    all_data = pool.map(extract_campaign_data, html_files, chunksize=10)
    pool.close()
    pool.join()

    end = time.time()
    print(f"Took {end-start}s to process {len(html_files)} files.")

    # Create dataframe and export output as csv.
    df = pd.DataFrame(all_data)
    df.to_csv('results.csv', index=False)

    # test_extract_campaign_data()
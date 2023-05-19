import os
import zipfile
import time
import multiprocessing
from datetime import datetime
import re
from collections import defaultdict
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
import pandas as pd
import tqdm

# Set logging.
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
# Toggle to turn off unzipping if already done.
UNZIP = False
# Toggle to turn off live scraping. 
OFFLINE = True

def extract_html_files(path, data_folder, unzip=True):
    """Extracts all files in the zipped folders in path
    to the given data folder (created if it doesn't exist) and
    returns a tuple of lists of the html file paths according to
    their type. If unzip is set to False, it will not unzip the
    folders in path and will just extract html files in
    path/data_folder.

    Inputs:
    path [str] - Path to zip files.
    data_folder [str] - Path to folder to store unzipped data.
    unzip [boolean] - Whether to unzip files at path or not."""
    data_folder_path = os.path.join(path, data_folder)

    if unzip:
        # Make data folder if it doesn't exist.
        os.makedirs(data_folder_path, exist_ok=True)

        logging.info("Unzipping files in path...")
        # Find all zip files in current path and extract them to data_folder.
        zip_files = []
        for file in os.listdir(path):
            if file.endswith(".zip"):
                zip_files.append(file)

        for zip_file in tqdm.tqdm(zip_files):
            with zipfile.ZipFile(os.path.join(path, zip_file), 'r') as zip_ref:
                zip_ref.extractall(data_folder_path)

        # Unzip any files in inside data_folder.
        logging.info("Unzipping nested zips...")
        data_folder_zips = []
        for (root, dirs, files) in os.walk(data_folder_path):
            for file in files:
                if file.endswith(".zip"):
                    data_folder_zips.append(os.path.join(root, file))
        
        # Unzip files inside original directory and delete the zips.
        for zip_file in tqdm.tqdm(data_folder_zips):
            file_dir = os.path.dirname(zip_file)
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(file_dir)
            os.remove(zip_file)

    # Files to ignore.
    ignore_set = {"community", "faqs", "comments"}

    # # Get paths of all html files in the data folder.
    campaign_files = []
    update_files = []
    for (root, dirs, files) in os.walk(data_folder_path):
        for file in files:
            if file.endswith(".html"):
                file_type = file.split("_")[1]

                if file_type == "updates":
                    update_files.append(os.path.join(root, file))
                elif file_type not in ignore_set:
                    campaign_files.append(os.path.join(root, file))
    
    return campaign_files, update_files

def get_str(string):
    """Returns a string without any digits."""
    return "".join([char for char in string if not char.isdigit()]).strip()

def get_digits(string, conv="float"):
    """Returns only digits from string as a single int/float. Default
    is float.
    
    Inputs: 
    string[str] - Any string.
    conv[str] - Enter "float" if you need float. Otherwise will provide integer."""
    if conv == "float":
        res = re.findall(r'[0-9.]+', string)
        return float("".join(res))
    else:
        res = re.findall(r'\d+', string)
        return int("".join(res))

def get_pledge_data(file_path, bs4_tag, index=0):
    """Returns a dict of data from a kickstarter pledge li bs4 tag.
    Dict will contain:
    rd_id: Pledge unique id.
    rd_title: Pledge title
    rd_price: Pledge price
    rd_desc: Pledge description 
    rd_list: A list of rewards from pledge description. Empty string if no list given.
    rd_delivery_date: Pledge Estimated Delivery. Format YYYY-MM-DD.
    rd_shipping_location: Pledge Shipping location. Empty string if no shipping location.
    rd_backers: Total number of backers.
    rd_limit: Limit in number of backers of pledge. Empty string if there are no
    limits. For unavailable pledges, limit = backers because they don't show limits.
    rd_gone: Status of pledge. If it is no longer available has a value of 1 and otherwise 0.

    Inputs:
    bs4_tag [bs4.element.Tag] - A tag of a kickstarter Pledge.
    Index [int] - Optional. The index of the current pledge. Has a default value of 0."""
    pledge_data = {}
    i = str(index)

    pledge_data['rd_id_' + i] = bs4_tag['data-reward-id']
    pledge_data['rd_title_' + i] = bs4_tag.select_one('h3[class="pledge__title"]').getText().strip()
    pledge_data['rd_price_' + i] = get_digits(bs4_tag.select_one('span[class="pledge__currency-conversion"] > span').getText()) 
    pledge_data['rd_desc_' + i] = bs4_tag.select_one('div[class="pledge__reward-description pledge__reward-description--expanded"]').getText().replace('\n', '')[:-4]
    
    # Rewards list. If it does not exist, return empty string.
    rd_list = [elem.getText().replace('\n', '') for elem in bs4_tag.select('li[class="list-disc"]')]
    if len(rd_list) == 0:
        pledge_data['rd_list_' + i] = ""
    else:
        pledge_data['rd_list_' + i] = rd_list
    
    pledge_data['rd_delivery_date_' + i] = bs4_tag.select_one('span[class="pledge__detail-info"] > time')['datetime']

    # Below elem can contain estimated date of delivery and the shipping location (optional).
    pledge_detail_elems = bs4_tag.select('span[class="pledge__detail-info"]')
    # It has the shipping location.
    if len(pledge_detail_elems) > 1:
        pledge_data['rd_shipping_location_' + i] = pledge_detail_elems[1].getText()
    # No shipping location.
    else:
        pledge_data['rd_shipping_location_' + i] = ""

    try:
        rd_backers = get_digits(bs4_tag.select_one('span[class="pledge__backer-count"]').getText())
    # Reward has a limit so it has a different class value.
    except AttributeError:
        rd_backers = get_digits(bs4_tag.select_one('span[class="block pledge__backer-count"]').getText())
    finally:
        pledge_data["rd_backers_" + i] = rd_backers

    rd_limit_elem = bs4_tag.select_one('span[class="pledge__limit"]')
    try:
        rd_limit = get_digits(rd_limit_elem.getText().split()[-1])
    except:
        rd_limit = ""
    pledge_data["rd_limit_" + i] = rd_limit

    # Below tag is there only for pledges which have reached their limit.
    # These pledges don't show the limit so their limit = num of backers 
    rd_gone_elem = bs4_tag.select_one('span[class="pledge__limit pledge__limit--all-gone mr2"]')
    if rd_gone_elem != None:
        pledge_data["rd_limit_" + i] = rd_backers
        pledge_data["rd_gone_" + i] = 1
    else:
        pledge_data["rd_gone_" + i] = 0

    return pledge_data

def get_category_data(cat_str):
    """Returns a tuple of (category, subcategory) from a given cat_str which
    can be either a category or subcategory.
    
    Inputs:
    cat_str = A string which is either a category or subcategory."""
    categories = {'Art': {'Painting', 'Textiles', 'Conceptual Art', 'Video Art', 'Installations', 'Social Practice', 'Sculpture', 'Ceramics', 'Public Art', 'Illustration', 'Digital Art', 'Performance Art', 'Mixed Media'}, 
                'Comics': {'Comic Books', 'Events', 'Graphic Novels', 'Anthologies', 'Webcomics'}, 
                'Crafts': {'Candles', 'Printing', 'Crochet', 'Taxidermy', 'Stationery', 'Pottery', 'Weaving', 'DIY', 'Woodworking', 'Embroidery', 'Glass', 'Quilts', 'Knitting'}, 
                'Dance': {'Spaces', 'Workshops', 'Residencies', 'Performances'}, 
                'Design': {'Interactive Design', 'Product Design', 'Graphic Design', 'Architecture', 'Typography', 'Toys', 'Civic Design'}, 
                'Film & Video': {'Television', 'Thrillers', 'Fantasy', 'Music Videos', 'Romance', 'Narrative Film', 'Action', 'Movie Theaters', 'Horror', 'Festivals', 'Experimental', 'Webseries', 'Documentary', 'Family', 'Drama', 'Science Fiction', 'Comedy', 'Animation', 'Shorts'}, 
                'Food': {'Bacon', 'Cookbooks', "Farmer's Markets", 'Community Gardens', 'Spaces', 'Small Batch', 'Events', 'Drinks', 'Restaurants', 'Vegan', 'Farms', 'Food Trucks'}, 
                'Games': {'Puzzles', 'Live Games', 'Video Games', 'Mobile Games', 'Gaming Hardware', 'Tabletop Games', 'Playing Cards'}, 
                'Journalism': {'Photo', 'Video', '`Print`', 'Audio', 'Web'}, 
                'Music': {'Indie Rock', 'Rock', 'Faith', 'Country & Folk', 'World Music', 'Kids', 'Comedy', 'Classical Music', 'Pop', 'Punk', 'Hip-Hop', 'Electronic Music', 'Jazz', 'Latin', 'R&B', 'Blues', 'Metal', 'Chiptune'}, 
                'Photography': {'People', 'Fine Art', 'Photobooks', 'Nature', 'Animals', 'Places'}, 
                'Publishing': {'Academic', 'Young Adult', "Children's Books", 'Periodicals', 'Calendars', 'Literary Spaces', 'Fiction', 'Radio & Podcasts', 'Literary Journals', 'Comedy', 'Letterpress', 'Art Books', 'Anthologies', 'Zines', 'Poetry', 'Nonfiction', 'Translations'}, 
                'Technology': {'Wearables', 'Makerspaces', '3D Printing', 'Robots', 'Space Exploration', 'Hardware', 'Camera Equipment', 'Apps', 'Sound', 'Flight', 'Fabrication Tools', 'Software', 'DIY Electronics', 'Web', 'Gadgets'}, 
                'Theater': {'Festivals', 'Spaces', 'Experimental', 'Musical', 'Comedy', 'Immersive', 'Plays'}}
    
    category, subcategory = "", ""

    # No way to know subcategory from category.
    if cat_str in categories.keys():
        category = cat_str
    else:
        # Was given a subcategory so find it's category.
        for category_name, subcategories in categories.items():
            if cat_str in subcategories:
                category = category_name
                subcategory = cat_str
                break
    
    return (category, subcategory)

def extract_update_files_data(files):
    """"Takes a list of update files of the same root and returns a tuple of url and startdate."""
    date = ("", "", "")
    for file in files:
        with open(file, encoding='utf8') as infile:
            soup = BeautifulSoup(infile, "lxml")
        
        # Url
        url = soup.select_one('meta[property="og:url"]')["content"]

        # Start date
        date_elem = soup.select_one('time[class="invisible-if-js js-adjust-time"]')

        # First file has the start date so no point in checking the other files
        if date_elem != None:
            dt = datetime.strptime(date_elem.getText(), "%B %d, %Y")
            date = (dt.day, dt.month, dt.year)
            break
    # None of the saved files had the start date so take it from the live page
    # if not offline.
    else:
        if not OFFLINE:
            update_url = url + "/posts"
            driver = webdriver.Chrome()
            driver.get(update_url)
            # Wait at most 10s for required tag to load and otherwise raise a TimeoutException.
            date_selector = 'div[class="type-11 type-14-sm text-uppercase"]'
            try:
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, date_selector))
                )
            finally:
                dt = datetime.strptime(driver.find_element(By.CSS_SELECTOR, date_selector).text, "%B %d, %Y")
                date = (dt.day, dt.month, dt.year)
                driver.quit()

    return (url, date)

def extract_campaign_data(file_path):
    """"Extracts data from a kickstarter campaign page and returns
    it in a dictionary.
    
    Inputs:
    file_path [str] - Path to html file."""
    with open(file_path, encoding='utf8') as infile:
        soup = BeautifulSoup(infile, "lxml")

    data = {}

    # Date and time accessed.
    date_time_str = file_path.split("_")[-1]
    date_time_str = date_time_str[:-5] 
    date, time = date_time_str.split("-")

    data["date_accessed"] = date
    data["time_accessed"] = time

    # Url
    url_elem = soup.select('meta[property="og:url"]')
    data["url"] = url_elem[0]["content"]

    # Project Id and Creator Id.
    creator_id, project_id = data["url"].split("/")[-2:]
    data["project_id"] = project_id
    data["creator_id"] = creator_id

    # Creator, Title and Blurb
    meta_elem = soup.select('meta[name="description"]')[0]
    lines = meta_elem["content"].splitlines()
    creator, title = lines[0].split(" is raising funds for ")
    title = title.strip()
    blurb = lines[-1].strip()

    data["title"] = title
    data["creator"] = creator
    data["blurb"] = blurb 

    # Status of campaign.
    status = ""

    # Status strings (to make any changes to status easier).
    successful = "Successful"
    unsuccessful = "Unsuccessful"
    live = "Live"

    # Only succesful campaigns have the below tag.
    successful_stats_elem = soup.select_one('div[class="NS_campaigns__spotlight_stats"]')
    if successful_stats_elem == None:
        time_left_elem = soup.select_one('span[class="block type-16 type-24-md medium soft-black"]')
        # Unsuccesful campaign
        if time_left_elem == None or time_left_elem.getText() == "0":
            fin_elem = soup.select_one('div[class="normal type-18"]')
            if fin_elem != None: 
                if unsuccessful in fin_elem.getText():
                    status = unsuccessful
                else:
                    print("Check status:", file_path, fin_elem.getText())
                    status = fin_elem.getText()

        # Live campaign
        else:
            status = live
    else:
        status = successful

    data["status"] = status
    
    # Backers.
    backers = ""
    if status != successful:
        backers_selector = 'div[class="block type-16 type-24-md medium soft-black"]'
    else: 
        backers_selector = 'div[class="mb0"] > h3[class="mb0"]'
        
    backers_elem = soup.select_one(backers_selector)
    if backers_elem != None:
        backers = backers_elem.getText().strip()

    data["backers"] = backers

    # Default values.
    original_curr_symbol = converted_curr_symbol = ""
    conversion_rate = 1
    goal = converted_goal = ""
    pledged = converted_pledged = ""

    # Some tags for campaigns at different statuses are distinct for
    # currency symbols, goals and pledges.
    if status == live:
        # Boolean to toggle for currency conversion.
        conversion_needed = False

        # Get conversion rate of currency if necessary for goal and pledged amounts.
        curr_elems = soup.select('div[class="input__currency-conversion"]')
        # Check if currency conversions are present.
        if len(curr_elems) > 0:
            curr_elem = curr_elems[0]
            back_elem = soup.select('input[name="backing[amount]"]')[0]

            converted_curr_amount = get_digits(curr_elem.contents[1].getText())
            original_curr_amount = get_digits(back_elem["value"])
            conversion_rate = converted_curr_amount / original_curr_amount

            # Get symbols for both currencies.
            converted_curr_symbol = get_str(curr_elem.contents[1].getText())
            original_curr_symbol = soup.select_one('span[class="new-form__currency-box__text"]').getText().strip()

            conversion_needed = True
            conversion_rate = conversion_rate

        # No need for conversion.
        else:
            original_curr_symbol = converted_curr_symbol = re.findall("window.current_currency = '(\w+)'", str(soup))[0].strip()

        # Fix symbols to one form if they have known alternate forms.
        fixed_symbols = {"USD": "$", "US$": "$", "Â£": "£", "â‚¬": "€"}
        if original_curr_symbol in fixed_symbols.keys():
            original_curr_symbol = fixed_symbols[original_curr_symbol]
        if converted_curr_symbol in fixed_symbols.keys():
            converted_curr_symbol = fixed_symbols[converted_curr_symbol]

        # Project goal.
        goal_elem = soup.select_one('span[class="inline-block-sm hide"]')
        if goal_elem != None:
            goal = get_digits(goal_elem.contents[1].getText(), "int") 
            if conversion_needed:
                converted_goal = goal * conversion_rate
            else:
                converted_goal = goal

        # Pledged amount.
        pledged_elem = soup.select_one('span[class="ksr-green-700"]')
        if pledged_elem != None:
            pledged = get_digits(pledged_elem.getText()) 
            if conversion_needed:
                converted_pledged = pledged * conversion_rate
            else:
                converted_pledged = pledged         

    elif status in {successful, unsuccessful}:
        if status == successful:
            completed_goal_selector = 'div[class="type-12 medium navy-500"] > span[class="money"]'
            completed_pledge_selector = 'h3[class="mb0"] > span[class="money"]'
        elif status == unsuccessful:
            completed_goal_selector = 'span[class="inline-block-sm hide"] > span[class="money"]'
            completed_pledge_selector = 'span[class="soft-black"]'

        # No way to get conversion rate in a completed project.
        completed_goal_elem = soup.select_one(completed_goal_selector)
        completed_pledge_elem = soup.select_one(completed_pledge_selector)
        if completed_goal_elem != None:
            original_curr_symbol = converted_curr_symbol = get_str(completed_goal_elem.getText())
            goal = converted_goal = get_digits(completed_goal_elem.getText())

        if completed_pledge_elem != None:
            pledged = converted_pledged = get_digits(completed_pledge_elem.getText())

    data["original_curr_symbol"] = original_curr_symbol
    data["converted_curr_symbol"] = converted_curr_symbol   
    data["conversion_rate"] = conversion_rate
    data["goal"] = goal
    data["converted_goal"] = converted_goal
    data["pledged"] = pledged
    data["converted_pledged"] = converted_pledged

    # Campaign start time. Will be extracted from updates files
    # so just leave space for it to be added later.
    data["startday"] = ""
    data["startmonth"] = ""
    data["startyear"] = ""

    # Campaign end time.
    endday, endmonth, endyear = "", "", ""

    if status == live:
        end_time_elem = soup.select_one('p[class="mb3 mb0-lg type-12"]')
        if end_time_elem != None:
            time_str = end_time_elem.getText()[80:]
            dt = datetime.strptime(time_str, "%B %d %Y %I:%M %p %Z %z.")
            endday, endmonth, endyear = dt.day, dt.month, dt.year

    elif status == successful:
        end_time_elem = soup.select('time[data-format="ll"]')
        if len(end_time_elem) >= 2:
            time_str = end_time_elem[1].getText()
            dt = datetime.strptime(time_str, "%b %d, %Y")
            endday, endmonth, endyear = dt.day, dt.month, dt.year

    elif status == unsuccessful:
        end_time_elem = soup.select_one('div[class="type-14 pt1"]')
        if end_time_elem != None:
            time_str = end_time_elem.getText()[46:]
            dt = datetime.strptime(time_str, "%a, %B %d %Y %I:%M %p %Z %z")
            endday, endmonth, endyear = dt.day, dt.month, dt.year

    data["endday"] = endday
    data["endmonth"] = endmonth
    data["endyear"] = endyear

    # Number of images and photos.
    photos, videos = 0, 0
    # Get number of photos and videos in highlight.
    highlight_elem = soup.select_one('div[class="grid-row grid-row mb5-lg mb0-md order-0-md order-2-lg"]')
    if highlight_elem != None:
        photos += len(highlight_elem.select("img"))
        videos += len(highlight_elem.select("video"))
    # Get number of photos and videos in description.
    description_container_elem = soup.select_one('div[class="col col-8 description-container"]')
    if description_container_elem != None:
        photos += len(description_container_elem.select("img"))
        videos += len(description_container_elem.select("video"))
    data["num_photos"] = photos
    data["num_videos"] = videos

    # Make 100 (make100), Projects we love (pwl), Category, Location. make100/pwl is 1 if project is 
    # part of it and otherwise 0.
    try:
        spc_cat_loc_elems = soup.select('span[class="ml1"]')
        spc_cat_loc_data = [pwl_cat_loc_elem.getText() for pwl_cat_loc_elem in spc_cat_loc_elems]

        special = {"Project We Love", "Make 100"}
        # Project is part of Projects we Love or Make 100.
        if spc_cat_loc_data[0] in special:
            cat_str = spc_cat_loc_data[1]
            location = spc_cat_loc_data[2]
            if spc_cat_loc_data[0] == "Project We Love":
                pwl = 1
                make100 = 0
            elif spc_cat_loc_data[0] == "Make 100":
                pwl = 0
                make100 = 1
        else:
            cat_str = spc_cat_loc_data[0]
            location = spc_cat_loc_data[1]
            pwl = 0
            make100 = 0

        category, subcategory = get_category_data(cat_str)

    # Category or location missing.
    except IndexError:
        pwl = ""    
        make100 = ""
        category = ""
        subcategory = ""
        location = ""
    finally:
        data["pwl"] = pwl
        data["make100"] = make100
        data["category"] = category
        data["subcategory"] = subcategory
        data["location"] = location

    # Try alternate tags for successful campaigns if category/location
    # is missing.
    cat_loc_elems = soup.select('a[class="grey-dark mr3 nowrap type-12"]')
    if len(cat_loc_elems) != 0:
        data["location"] = cat_loc_elems[0].getText().strip()
        data["category"], data["subcategory"] = get_category_data(cat_loc_elems[1].getText().strip())

    # Number of projects created.
    try:
        project_num_elem = soup.select('a[class="dark-grey-500 keyboard-focusable"]')
        # Try other possible tag for project num if necessary.
        if len(project_num_elem) == 0:
            project_num_elem = soup.select('span[class="dark-grey-500"]')   

        projects_num = project_num_elem[0].getText().split()[0]
        if projects_num == "First":
            projects_num = "1"
    # Project number missing.
    except IndexError:
        projects_num = ""
    finally:
        data["num_projects"] = projects_num

    # Number of comments.
    comments_elem = soup.select('data[itemprop="Project[comments_count]"]')
    data["num_comments"] = comments_elem[0].getText()
    
    # Number of updates.
    updates_elem = soup.select('a[data-content="updates"]')[0]
    data["num_updates"] = updates_elem.contents[1].getText()

    # Number of faq.
    faq_elem = soup.select('a[data-content="faqs"]')[0]
    # Kickstarter does not show 0 if there is no faq.
    if len(faq_elem.contents) > 1:
        data["num_faq"] = faq_elem.contents[1].getText()
    else:
        data["num_faq"] = 0

    # Description.
    description_elem = soup.select_one('div[class="full-description js-full-description responsive-media formatted-lists"]')
    if description_elem != None:
        description = description_elem.getText().strip()
    else:
        description = ""
    data["description"] = description
    
    # Risks.
    risk_elem = soup.select_one('div[class="mb3 mb10-sm mb3 js-risks"]')
    if risk_elem != None:
        risk = risk_elem.getText().strip()
        # Remove first line "Risks and challenges" and last line "Learn about accountability on Kickstarter"
        # because they are the same for all projects.
        risk = "".join(risk.splitlines(keepends=True)[1:-1])
    else:
        risk = ""
    data["risk"] = risk

    # Pledges. rd_gone is 0 for available pledges and 1 for complete pledges. 
    all_pledge_elems = []
    all_pledge_elems.extend([pledge_elem for pledge_elem in soup.select('li[class="hover-group js-reward-available pledge--available pledge-selectable-sidebar"]')])
    all_pledge_elems.extend([pledge_elem for pledge_elem in soup.select('li[class="hover-group pledge--all-gone pledge-selectable-sidebar"]')])
    all_pledge_elems.extend([pledge_elem for pledge_elem in soup.select('li[class="hover-group pledge--inactive pledge-selectable-sidebar"]')])

    data["num_rewards"] = len(all_pledge_elems)

    for i, pledge_elem in enumerate(all_pledge_elems):
        data |= get_pledge_data(file_path, pledge_elem, i)

    return data

def test_extract_campaign_data():
    # Testing code.
    file_paths = [
                # r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Data\art\a1\1-1000-supporters-an-art-gallery-and-design-boutiq\1-1000-supporters-an-art-gallery-and-design-boutiq_20190312-010622.html", # Nothing special
                # r"C:/Users/jaber/OneDrive/Desktop/Research_JaberChowdhury/Data/art/a1/2269-can-a-poster-change-the-future/2269-can-a-poster-change-the-future_20190509-000703.html", # Has pledge lists.
                # r"C:/Users/jaber/OneDrive/Desktop/Research_JaberChowdhury/Data/art/a1/10years-100paintings-art-book-by-agustin-iglesias/10years-100paintings-art-book-by-agustin-iglesias_20190424-135918.html", # Has currency issue
                r"C:/Users/jaber/OneDrive/Desktop/Research_JaberChowdhury/Data/art/a1/15-pudgy-budgie-and-friends-enamel-pins/15-pudgy-budgie-and-friends-enamel-pins_20190310-220712.html", # Unsuccesful campaign
                # r"C:/Users/jaber/OneDrive/Desktop/Research_JaberChowdhury/Data/art/a1/1-dollar-1-drawing-0/1-dollar-1-drawing-0_20190707-222902.html", # Successful campaign
                ]
    data = [extract_campaign_data(file_path) for file_path in file_paths]
    df = pd.DataFrame(data)
    df.to_csv('test.csv', index = False)

if __name__ == "__main__":
    # Toggle from true/false or 1/0 if testing or not testing.
    testing = 0

    if not testing:
        # Path to zip files.
        path = r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Data\art"

        # Folder which will contain unzipped data.
        data_folder = "Unzipped"

        campaign_files, update_files = extract_html_files(path, data_folder, UNZIP)

        # Extract data from html files.

        # Process update files.
        logging.info("Processing update files...")
        roots = defaultdict(list)
        for file_path in  update_files:
            roots[os.path.dirname(file_path)].append(file_path)

        pool = multiprocessing.Pool()
        update_data = pool.map(extract_update_files_data, roots.values())
        update_data = dict(update_data)

        # Process campaign files.
        logging.info("Processing campaign files...")
        campaign_data = list(tqdm.tqdm(pool.imap(extract_campaign_data, campaign_files, chunksize=100), total=len(campaign_files)))
        pool.close()
        pool.join()

        # Merge campaign and update data.
        all_data = []
        for campaign_datum in campaign_data:
            url = campaign_datum["url"]
            campaign_datum["startday"], campaign_datum["startmonth"], campaign_datum["startyear"] = update_data.get(url, ("", "", ""))
            all_data.append(campaign_datum)

        # Create dataframe and export output as csv.
        df = pd.DataFrame(all_data)
        df.to_csv('results.csv', index=False)

    else:
        test_extract_campaign_data()
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
    """Returns only digits from string as a single float."""
    res = re.findall(r'[0-9.]', string)
    return float("".join(res))

def get_pledge_data(bs4_tag, index=0):
    """Returns a dict of data from a kickstarter pledge li bs4 tag.
    Dict will contain:
    rd_title: Pledge title
    rd_cost: Pledge cost
    rd_desc: Pledge description 
    rd_list: A list of rewards from pledge description. Empty string if no list given.
    rd_delivery_date: Pledge Estimated Delivery. Format YYYY-MM-DD.
    rd_shipping_location: Pledge Shipping location. Empty string if no shipping location.
    rd_backers: Total number of backers.
    rd_limit: Limit in number of backers of pledge. Empty string if there are no
    limits.

    Inputs:
    bs4_tag [bs4.element.Tag] - A tag of a kickstarter Pledge.
    Index [int] - Optional. The index of the current pledge. Has a default value of 0."""
    pledge_data = {}
    i = str(index)

    pledge_data['rd_title_' + i] = bs4_tag.select_one('h3[class="pledge__title"]').getText().strip()
    pledge_data['rd_cost_' + i] = get_digits(bs4_tag.select_one('span[class="pledge__currency-conversion"] > span').getText()) 
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

    try:
        rd_limit = get_digits(bs4_tag.select_one('span[class="pledge__limit"]').getText().split()[-1])
    except AttributeError:
        rd_limit = ""
    finally:
        pledge_data["rd_limit_" + i] = rd_limit

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
                'Journalism': {'Photo', 'Video', 'Print', 'Audio', 'Web'}, 
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

        converted_curr_amount = get_digits(curr_elem.contents[1].getText())
        original_curr_amount = get_digits(back_elem["value"])
        conversion_rate = converted_curr_amount / original_curr_amount

        # Get symbols for both currencies.
        converted_curr_symbol = "".join([char for char in curr_elem.contents[1].getText() if not char.isdigit()]).strip()
        original_curr_symbol = soup.select_one('span[class="new-form__currency-box__text"]').getText().strip()

        conversion_needed = True
        data["conversion_rate"] = conversion_rate

    # No need for conversion.
    else:
        data["conversion_rate"] = 1
        original_curr_symbol = converted_curr_symbol = re.findall("window.current_currency = '(\w+)'", str(soup))[0].strip()

    # Change symbols if they have known alternate forms.
    usd_other_set = {"USD", "US$"}
    if original_curr_symbol in usd_other_set:
        original_curr_symbol = "$"
    if converted_curr_symbol in usd_other_set:
        converted_curr_symbol = "$"

    data["original_curr"] = original_curr_symbol
    data["converted_curr"] = converted_curr_symbol

    # Project goal.
    try:
        goal_elem = soup.select('span[class="inline-block-sm hide"]')
        goal = get_digits(goal_elem[0].contents[1].getText()) 
        converted_goal = goal
        if conversion_needed:
            converted_goal = converted_goal * conversion_rate
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
        pledged = get_digits(pledged_elem[0].getText()) 
        converted_pledged = pledged
        if conversion_needed:
            converted_pledged = converted_pledged * conversion_rate
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

    # Number of projects created.
    try:
       project_num_elem = soup.select('a[class="dark-grey-500 keyboard-focusable"]')
       projects_num = project_num_elem[0].getText().split()[0]
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
    # Kickstarter does not show 0 if there are no faq so
    # need to check for lack of faq.
    if len(faq_elem.contents) > 1:
        data["num_faq"] = faq_elem.contents[1].getText()
    else:
        data["num_faq"] = 0

    # Description.
    try:
        description_elem = soup.select('div[class="full-description js-full-description responsive-media formatted-lists"]')
        description = description_elem[0].getText().strip()
    # Desciption missing.
    except IndexError:
        description = ""
    finally:
        data["description"] = description

    # Risks.
    try:
        risk_elem = soup.select('div[class="mb3 mb10-sm mb3 js-risks"]')
        risk = risk_elem[0].getText().strip()
        # Remove first line "Risks and challenges" and last line "Learn about accountability on Kickstarter"
        # because they are the same for all projects.
        risk = "".join(risk.splitlines(keepends=True)[1:-1])
    # Risk missing.
    except IndexError:
        risk = ""
    finally:
        data["risk"] = risk

    # Pledges. rd_gone is 0 because pledge is avaialable. 
    pledge_elems = soup.select('li[class="hover-group js-reward-available pledge--available pledge-selectable-sidebar"]')
    i = 0
    for i, pledge_elem in enumerate(pledge_elems, i):
        data |= get_pledge_data(pledge_elem, i)
        data |= {"rd_gone_" + str(i): 0}

    # Complete Pledges. Continues from i + 1. rd_gone is 1 because pledge is unavaialable. 
    complete_pledge_elems = soup.select('li[class="hover-group pledge--all-gone pledge-selectable-sidebar"]')
    for j, complete_pledge_elem in enumerate(complete_pledge_elems, i + 1):
        data |= get_pledge_data(complete_pledge_elem, j)
        data |= {"rd_gone_" + str(j): 1}

    return data

def test_extract_campaign_data():
    # Testing code.
    file_paths = [
                # r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Data\art\a1\1-1000-supporters-an-art-gallery-and-design-boutiq\1-1000-supporters-an-art-gallery-and-design-boutiq_20190312-010622.html", # Nothing special
                # r"C:/Users/jaber/OneDrive/Desktop/Research_JaberChowdhury/Data/art/a1/15-pudgy-budgie-and-friends-enamel-pins/15-pudgy-budgie-and-friends-enamel-pins_20190214-140329.html", # Requires currency conversion
                # r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Data\art\a1\9th-annual-prhbtn-street-art-festival\9th-annual-prhbtn-street-art-festival_20190827-163448.html", # Has completed pledge
                r"C:/Users/jaber/OneDrive/Desktop/Research_JaberChowdhury/Data/art/a1/2269-can-a-poster-change-the-future/2269-can-a-poster-change-the-future_20190509-000703.html", # Has pledge lists.
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

    else:
        test_extract_campaign_data()
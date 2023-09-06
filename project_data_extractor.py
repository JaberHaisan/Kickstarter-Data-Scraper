import multiprocessing
from datetime import datetime
import re
import logging
import time
import json
import winsound
import random

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup
import pandas as pd

# Settings.

# Path to data. Make sure to use raw strings or escape "\".
DATA_PATH = r"F:\Kickstarter Zips\Unzipped"
# Set logging.
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, datefmt='%m/%d/%Y %I:%M:%S %p')
# Set what value to enter in case of missing data. Default is ""
MISSING = ""
# Chromedriver path
CHROMEDRIVER_PATH = r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Kickstarter-Data-Scraper\chromedriver.exe"

# Script.

def main():
    campaign_data = []
    update_data = {}
    pool = multiprocessing.Pool()

    pool.close()
    pool.join()

    logging.info("Writing data to file...")

    output_folder = "Output"

def test_extract_campaign_data():
    # Testing code.
    file_paths = ["https://www.kickstarter.com/projects/petersand/manylabs-sensors-for-students"]
    data = [extract_campaign_data(file_path) for file_path in file_paths]
    df = pd.DataFrame(data)
    df.to_csv('test.csv', index = False)

def get_str(string, extra):
    """Returns a string without any digits.
    
    Inputs:
    string [str] - Any string.
    extra [set] - Extra set of characters to exclude."""
    return "".join([char for char in string if not (char.isdigit() or char in extra)]).strip()

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

def get_pledge_data(bs4_tag, index=0):
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

    pledge_data['rd_id_' + i] = bs4_tag['id']
    pledge_data['rd_title_' + i] = bs4_tag.select_one('[class="support-700 semibold type-18 m0 mr1 text-wrap-balance break-word"]').getText().strip()
    
    # pledge_data['rd_price_' + i] = get_digits(bs4_tag.select_one('span[class="pledge__currency-conversion"] > span').getText())

    pledge_data['rd_desc_' + i] = bs4_tag.select_one('[class="type-14 lh20px mb0 support-700 text-prewrap"]').getText()
    
    # Rewards list. If it does not exist, return empty string.
    # rd_list = [elem.getText().replace('\n', '') for elem in bs4_tag.select('li[class="list-disc"]')]
    # if len(rd_list) == 0:
    #     pledge_data['rd_list_' + i] = MISSING
    # else:
    #     pledge_data['rd_list_' + i] = rd_list
    
    pledge_data['rd_delivery_date_' + i] = bs4_tag.select_one('time[datetime]')['datetime']

    # Below elem can contain estimated date of delivery and the shipping location (optional).
    # pledge_detail_elems = bs4_tag.select('span[class="pledge__detail-info"]')
    # # It has the shipping location.
    # if len(pledge_detail_elems) > 1:
    #     pledge_data['rd_shipping_location_' + i] = pledge_detail_elems[1].getText()
    # # No shipping location.
    # else:
    #     pledge_data['rd_shipping_location_' + i] = MISSING

    # try:
    #     rd_backers = get_digits(bs4_tag.select_one('span[class="pledge__backer-count"]').getText())
    # # Reward has a limit so it has a different class value.
    # except AttributeError:
    #     rd_backers = get_digits(bs4_tag.select_one('span[class="block pledge__backer-count"]').getText())
    # finally:
    #     pledge_data["rd_backers_" + i] = rd_backers

    # rd_limit_elem = bs4_tag.select_one('span[class="pledge__limit"]')
    # try:
    #     rd_limit = get_digits(rd_limit_elem.getText().split()[-1])
    # except:
    #     rd_limit = MISSING
    # pledge_data["rd_limit_" + i] = rd_limit

    # # Below tag is there only for pledges which have reached their limit.
    # # These pledges don't show the limit so their limit = num of backers 
    # rd_gone_elem = bs4_tag.select_one('span[class="pledge__limit pledge__limit--all-gone mr2"]')
    # if rd_gone_elem != None:
    #     pledge_data["rd_limit_" + i] = rd_backers
    #     pledge_data["rd_gone_" + i] = 1
    # else:
    #     pledge_data["rd_gone_" + i] = 0

    return pledge_data

def get_category_data(cat_str):
    """Returns a tuple of (category, subcategory) from a given cat_str which
    can be either a category or subcategory.
    
    Inputs:
    cat_str = A string which is either a category or subcategory."""
    categories = {'Art': {'Ceramics', 'Conceptual Art', 'Digital Art', 'Illustration', 'Installations', 'Mixed Media', 'Painting', 'Performance Art', 'Public Art', 'Sculpture', 'Social Practice', 'Textiles', 'Video Art'}, 
                'Comics': {'Anthologies', 'Comic Books', 'Events', 'Graphic Novels', 'Webcomics'}, 
                'Crafts': {'Candles', 'Crochet', 'DIY', 'Embroidery', 'Glass', 'Knitting', 'Pottery', 'Printing', 'Quilts', 'Stationery', 'Taxidermy', 'Weaving', 'Woodworking'}, 
                'Dance': {'Performances', 'Residencies', 'Spaces', 'Workshops'}, 
                'Design': {'Architecture', 'Civic Design', 'Graphic Design', 'Interactive Design', 'Product Design', 'Toys', 'Typography'}, 
                'Fashion': {'Accessories', 'Apparel', 'Childrenswear', 'Couture', 'Footwear', 'Jewelry', 'Pet Fashion', 'Ready-to-wear'}, 
                'Film & Video': {'Action', 'Animation', 'Comedy', 'Documentary', 'Drama', 'Experimental', 'Family', 'Fantasy', 'Festivals', 'Horror', 'Movie Theaters', 'Music Videos', 'Narrative Film', 'Romance', 'Science Fiction', 'Shorts', 'Television', 'Thrillers', 'Webseries'}, 
                'Food': {'Bacon', 'Community Gardens', 'Cookbooks', 'Drinks', 'Events', "Farmer's Markets", 'Farms', 'Food Trucks', 'Restaurants', 'Small Batch', 'Spaces', 'Vegan'}, 
                'Games': {'Gaming Hardware', 'Live Games', 'Mobile Games', 'Playing Cards', 'Puzzles', 'Tabletop Games', 'Video Games'}, 
                'Journalism': {'Audio', 'Photo', 'Print', 'Video', 'Web'}, 
                'Music': {'Blues', 'Chiptune', 'Classical Music', 'Comedy', 'Country & Folk', 'Electronic Music', 'Faith', 'Hip-Hop', 'Indie Rock', 'Jazz', 'Kids', 'Latin', 'Metal', 'Pop', 'Punk', 'R&B', 'Rock', 'World Music'}, 
                'Photography': {'Animals', 'Fine Art', 'Nature', 'People', 'Photobooks', 'Places'}, 
                'Publishing': {'Academic', 'Anthologies', 'Art Books', 'Calendars', "Children's Books", 'Comedy', 'Fiction', 'Letterpress', 'Literary Journals', 'Literary Spaces', 'Nonfiction', 'Periodicals', 'Poetry', 'Radio & Podcasts', 'Translations', 'Young Adult', 'Zines'}, 
                'Technology': {'3D Printing', 'Apps', 'Camera Equipment', 'DIY Electronics', 'Fabrication Tools', 'Flight', 'Gadgets', 'Hardware', 'Makerspaces', 'Robots', 'Software', 'Sound', 'Space Exploration', 'Wearables', 'Web'}, 
                'Theater': {'Comedy', 'Experimental', 'Festivals', 'Immersive', 'Musical', 'Plays', 'Spaces'}}
    
    category, subcategory = cat_str, MISSING

    # No way to know subcategory from category.
    if cat_str not in categories.keys():
        # Might be given a subcategory so try finding it's category.
        for category_name, subcategories in categories.items():
            if cat_str in subcategories:
                category = category_name
                subcategory = cat_str
                break
    
    return (category, subcategory)

def get_live_soup(link, given_driver=None):
    """Returns a bs4 soup object of the given link. Returns None if it is a deleted kickstarter account.
    
    link [str] - A link to a website.
    scroll [bool] - True if you want selenium to keep scrolling down till loading no longer happens.
    False by default.
    given_driver [selenium webdriver] - A webdriver. None by default."""
    if given_driver == None:
        driver = uc.Chrome(driver_executable_path=CHROMEDRIVER_PATH)
    else:
        driver = given_driver
    driver.get(link)

    soup = BeautifulSoup(driver.page_source, "lxml")

    # If there is a capcha, Beep and sleep.
    capcha_elem = soup.select_one('div[id="px-captcha"]')
    if capcha_elem != None:
        winsound.Beep(440, 1000)        
        time.sleep(30)
    
    # If it is a deleted account or there is a 404 error, return.
    deleted_elem = soup.select_one('div[class="center"]')
    non_existent_elem = soup.select_one('a[href="/?ref=404-ksr10"]')
    if deleted_elem != None or non_existent_elem != None:
        driver.quit()
        return

    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "lxml")

    if given_driver == None:
        driver.quit()

    return soup

def extract_campaign_data(path):
    """Extracts data from a kickstarter campaign page and returns
    it in a dictionary. 
    
    Inputs:
    path [str] - Path to html file.
    is_link [boolean] - True if path is a link and False otherwise. False by default."""
    data = {"url": path}
    
    driver = uc.Chrome(driver_executable_path=CHROMEDRIVER_PATH)
    campaign_soup = get_live_soup(path, given_driver=driver)
    reward_soup = get_live_soup(path + "/rewards", given_driver=driver)
    driver.quit()

    # Prepare str for getting date and time. 
    path = datetime.now().strftime('_%Y%m%d-%H%M%S.html')

    data = {}

    # Date and time accessed.
    date_time_str = path.split("_")[-1]
    date_time_str = date_time_str[:-5] 
    date, time = date_time_str.split("-")

    data["date_accessed"] = date
    data["time_accessed"] = time

    # Url. If missing, do not continue.
    try:
        url_elem = campaign_soup.select_one('meta[property="og:url"]')
        data["url"] = url_elem["content"]
    except:
        return data

    # Project Id and Creator Id.
    creator_id, project_id = data["url"].split("/")[-2:]
    data["project_id"] = project_id
    data["creator_id"] = creator_id

    # Creator, Title and Blurb
    meta_elem = campaign_soup.select_one('meta[name="description"]')
    lines = meta_elem["content"].splitlines()
    creator, title = lines[0].split(" is raising funds for ")
    title = title.strip().replace(" on Kickstarter!", "")
    blurb = lines[-1].strip()

    data["title"] = title
    data["creator"] = creator
    data["blurb"] = blurb 

    # data-initial attribute has a lot of the required data elements
    # so check if it exists.
    project_data_elem = campaign_soup.select_one('div[data-initial]')
    project_data = None
    if project_data_elem != None:
        project_data = json.loads(project_data_elem['data-initial']).get('project', None)  

    # Creator verified identity.
    verified_identity = MISSING
    if project_data:
        verified_identity = project_data['verifiedIdentity']
    data['verified_identity'] = verified_identity  

    # Status of campaign.
    status = MISSING


    # Status strings. prj.db
    successful = "Successful"
    failed = "Failed"
    canceled = "Canceled"
    suspended = "Suspended"
    live = "Live"

    data["status"] = status

    # Backers. prj.db
    backers = MISSING

    data["backers"] = backers

    # Collaborators. Empty list if no collaborators and
    # empty string if it was not possible to extract.
    collaborators = []
    if project_data:
        collab_list = project_data['collaborators']['edges']
        for collab in collab_list:
            collaborators.append((collab['node']['name'], collab['node']['url'], collab['title']))
    else:
        collaborators = ""
    data["collaborators"] = collaborators

    # Default values. prj.db
    original_curr_symbol = converted_curr_symbol = MISSING
    conversion_rate = 0
    goal = converted_goal = MISSING
    pledged = converted_pledged = MISSING

    data["original_curr_symbol"] = original_curr_symbol
    data["converted_curr_symbol"] = converted_curr_symbol   
    data["conversion_rate"] = conversion_rate
    data["goal"] = goal
    data["converted_goal"] = converted_goal
    data["pledged"] = pledged
    data["converted_pledged"] = converted_pledged

    # Campaign start time. Will be extracted from updates files
    # so just leave space for it to be added later. prj.db
    data["startday"] = MISSING
    data["startmonth"] = MISSING
    data["startyear"] = MISSING

    # Number of images and photos.
    photos, videos = 0, 0
    # Get number of photos and videos in highlight.
    highlight_elem = campaign_soup.select_one('div[class="grid-row grid-row mb5-lg mb0-md order-0-md order-2-lg"]')
    if highlight_elem != None:
        photos += len(highlight_elem.select("img"))
        # Check either possible tag for video in highlight.
        videos += len(highlight_elem.select('svg[class="svg-icon__icon--play icon-20 fill-white"]')) or len(highlight_elem.select("video"))
    # Get number of photos and videos in description.
    description_container_elem = campaign_soup.select_one('div[class="col col-8 description-container"]')
    if description_container_elem != None:
        photos += len(description_container_elem.select("img"))

        videos += len(description_container_elem.select("video"))
        videos += len(description_container_elem.select('div[class="template oembed"]'))
        
    data["num_photos"] = photos
    data["num_videos"] = videos

    # Make 100 (make100), Projects we love (pwl), Category, Location. make100/pwl is 1 if project is 
    # part of it and otherwise 0. prj.db
    pwl = MISSING    
    make100 = MISSING
    category = MISSING
    subcategory = MISSING
    location = MISSING

    data["pwl"] = pwl
    data["make100"] = make100
    data["category"] = category
    data["subcategory"] = subcategory
    data["location"] = location

    # Number of projects created.
    num_projects = MISSING
    if project_data and project_data['creator']:
            if 'createdProjects' in project_data['creator']:
                num_projects = project_data['creator']['createdProjects']['totalCount']
            else:
                num_projects = project_data['creator']['launchedProjects']['totalCount']

    data["num_projects"] = num_projects

    # Number of projects backed.
    num_backed = MISSING
    if project_data and project_data['creator']:
        if 'backedProjects' in project_data['creator']:
            if project_data['creator']['backedProjects'] != None:
                num_backed = project_data['creator']['backedProjects']['totalCount']
        else:
            num_backed = project_data['creator']['backingsCount']

    data["num_backed"] = num_backed 

    # Number of comments.
    comments_elem = campaign_soup.select_one('data[itemprop="Project[comments_count]"]')
    data["num_comments"] = comments_elem.getText()
    
    # Number of updates.
    updates_elem = campaign_soup.select_one('a[data-content="updates"] > span[class="count"]')
    data["num_updates"] = updates_elem.getText()

    # Number of faq.
    faq_elem = campaign_soup.select_one('a[data-content="faqs"]')
    # Kickstarter does not show 0 if there is no faq.
    if len(faq_elem.contents) > 1:
        data["num_faq"] = faq_elem.contents[1].getText()
    else:
        data["num_faq"] = 0

    # Description.
    description_elem = campaign_soup.select_one('div[class="full-description js-full-description responsive-media formatted-lists"]')
    if description_elem != None:
        description = description_elem.getText().strip()
    else:
        description = MISSING
    data["description"] = description
    
    # Risks.
    risk_elem = campaign_soup.select_one('div[class="mb3 mb10-sm mb3 js-risks"]')
    if risk_elem != None:
        risk = risk_elem.getText().strip()
        # Remove first line "Risks and challenges" and last line "Learn about accountability on Kickstarter"
        # because they are the same for all projects.
        risk = "".join(risk.splitlines(keepends=True)[1:-1])
    else:
        risk = MISSING
    data["risk"] = risk

    # Pledges. rd_gone is 0 for available pledges and 1 for complete pledges. 
    all_pledge_elems = []
    all_pledge_elems.extend([pledge_elem for pledge_elem in reward_soup.select('article[data-test-id]')])

    data["num_rewards"] = len(all_pledge_elems)

    for i, pledge_elem in enumerate(all_pledge_elems):
        data |= get_pledge_data(pledge_elem, i)

    return data

if __name__ == "__main__":
    # main()
    test_extract_campaign_data()
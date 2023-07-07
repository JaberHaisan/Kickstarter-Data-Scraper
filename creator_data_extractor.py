import re
import time
from datetime import datetime
import json
import random
import logging
import os
import winsound

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup

# Location of creator_ids.json
CREATOR_FILE_PATH = r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Kickstarter-Data-Scraper\Output\creator_ids_0.json"
# Output folder.
OUTPUT_PATH = "Creator Output"
# Chromedriver path
CHROMEDRIVER_PATH = r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Kickstarter-Data-Scraper\chromedriver.exe"
# Set logging.
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, datefmt='%m/%d/%Y %I:%M:%S %p')

# Get deleted creators.
deleted_creators = []
if os.path.exists("deleted_creators.json"):
    with open(f"deleted_creators.json", "r") as f_obj:
        deleted_creators = json.load(f_obj)   

def main():
    # https://www.kickstarter.com/profile/dicedungeons/ # Lots of loading comments.
    # https://www.kickstarter.com/profile/shiftcam # Backed projects are public.
    # https://www.kickstarter.com/profile/mybirdbuddy/ # Multiple websites in about.

    with open(CREATOR_FILE_PATH, "r") as f_obj:
        creator_ids = json.load(f_obj)
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    later = {"thirdwayind", "dwarvenforge", "peak-design", "350683997", "152730994", "geniusgames"}

    # Get already extracted creators and remove them from creator_ids.
    extracted_creators = set(os.path.splitext(file)[0] for file in os.listdir(OUTPUT_PATH))
    
    skip = extracted_creators | later | set(deleted_creators)
    creator_ids = [creator_id for creator_id in creator_ids if creator_id not in skip]

    for i, creator_id in enumerate(creator_ids, 1):
        extract_write(creator_id)
        
        with open("deleted_creators.json", "w") as f_obj:
            json.dump(deleted_creators, f_obj)

        # Stop scraping for a period of time to not be blocked as a bot.
        if len(creator_ids) > 1 and i % 10 == 0:
            logging.info("Sleeping...\n")

            if i % 100 == 0:
                time.sleep(10 * 60)

            elif i % 10 == 0:
                time.sleep(30)

def get_digits(string, conv="float"):
    """Returns only digits from string as a single int/float. Default
    is float. Returns empty string if no digit found.

    Inputs: 
    string[str] - Any string.
    conv[str] - Enter "float" if you need float. Otherwise will provide integer."""
    if conv == "float":
        res = re.findall(r'[0-9.]+', string)
        if res == "":
            return ""
        return float("".join(res))
    else:
        res = re.findall(r'\d+', string)
        if res == "":
            return ""
        return int("".join(res))
    
def get_live_soup(link, scroll=False, given_driver=None):
    """Returns a bs4 soup object of the given link. Returns None if it is a deleted kickstarter account.
    
    link [str] - A link to a website.
    scroll [bool] - True if you want selenium to keep scrolling down till loading no longer happens.
    False by default.
    given_driver [selenium webdriver] - A webdriver. None by default."""
    if given_driver == None:
        driver = uc.Chrome(executable_path=CHROMEDRIVER_PATH)
    else:
        driver = given_driver
    driver.get(link)

    soup = BeautifulSoup(driver.page_source, "lxml")

    # If there is a capcha, Beep and wait for a minute for user to finish it.
    capcha_elem = soup.select_one('div[id="px-captcha"]')
    if capcha_elem != None:
        winsound.Beep(440, 1000)        
        time.sleep(45)
    
    # If it is a deleted account or there is a 404 error, return.
    deleted_elem = soup.select_one('div[class="center"]')
    non_existent_elem = soup.select_one('a[href="/?ref=404-ksr10"]')
    if deleted_elem != None or non_existent_elem != None:
        driver.quit()
        return
    
    if not scroll:
        time.sleep(1)
    else:
        scroll_num = 1
        while True:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait to scroll. Notify if unusually high number of scrolls (which may mean that
            # there is a 403 error).
            if scroll_num % 60 == 0:
                winsound.Beep(440, 1000)

            if scroll_num % 30 == 0:
                time.sleep(30)
            else:
                time.sleep(random.uniform(1, 2))

            scroll_num += 1

            # Stop scrolling if no longer loading.
            try:
                elem = driver.find_element(By.CSS_SELECTOR, 'li[data-last_page="true"]')
            except:
                continue
            else:
                break

    if given_driver == None:
        driver.quit()

    soup = BeautifulSoup(driver.page_source, "lxml")
    return soup

def extract_elem_text(soup, selector):
    """Returns resulting text of using given selector in soup.
    If there was no text, returns empty string. 
    
    Inputs:
    soup[bs4.BeautifulSoup] - A soup.
    selector[str] - A css selector."""
    elem = soup.select_one(selector)
    if elem == None:
        return ""
    else:
        return elem.getText()

def parse_data_project(data_project):
    """Parses a kickstarter data project dictionary and returns a dictionary of
    required keys.
    
    data-project [dict]- A kickstarter data project dict."""
    result = {}

    result['name'] = data_project['name']
    result['url'] = data_project['urls']['web']['project']
    result['creator_id'] = data_project['creator']['id']
    result['blurb'] = data_project['blurb']

    # Convert currencies to USD.
    result['currency'] = 'USD'
    result['goal'] = data_project['goal'] * data_project['static_usd_rate']
    result['pledged'] = data_project['usd_pledged']

    result['backers'] = data_project['backers_count']
    result['state'] = data_project['state'].title()
    result['pwl'] = int(data_project['staff_pick'])
    result['location'] = data_project.get('location', {}).get('short_name', "")

    if 'parent_name' in data_project['category']:
        result['subcategory'] = data_project['category']['name']
        result['category'] = data_project['category']['parent_name']
    else:
        result['subcategory'] = ""
        result['category'] = data_project['category']['name']

    result['created_date'] = datetime.fromtimestamp(data_project['created_at']).strftime('%Y-%m-%d')
    result['launched_date'] = datetime.fromtimestamp(data_project['launched_at']).strftime('%Y-%m-%d')
    result['deadline_date'] = datetime.fromtimestamp(data_project['deadline']).strftime('%Y-%m-%d')

    return result

def extract_creator_data(path, is_link=True):
    """Returns a dictionary of the data for the creator. If passed a file, it should be of
    a format like 'Dice Dungeons — About.html'. Returns None in case of a deleted account."""
    data = {}

    if is_link:
        driver = uc.Chrome(executable_path=CHROMEDRIVER_PATH)
        # Extract data from available pages.
        about_soup = get_live_soup(path + "/about", given_driver=driver)

        if about_soup == None:
            return 
        
        # There may be multiple pages for created projects.
        created_soup = get_live_soup(path + "/created", given_driver=driver)
        created_soups = [created_soup]
        while True:
            next_elem = created_soup.select_one('a[rel="next"]')

            # No further pages.
            if next_elem == None:
                break   
            
            created_soup = get_live_soup("https://www.kickstarter.com/" + next_elem['href'], given_driver=driver)
            created_soups.append(created_soup)

        # Do not try to scrap pages if they are not public.
        if about_soup.select_one('a[class="nav--subnav__item__link nav--subnav__item__link--gray js-comments-link"]') != None:
            comment_soup = get_live_soup(path + "/comments", True, driver)
        else:
            comment_soup = None

        # Number of projects backed.
        backed = extract_elem_text(about_soup, 'span[class="backed"]')
        backed = get_digits(backed, "int")

        if about_soup.select_one('a[class="nav--subnav__item__link nav--subnav__item__link--gray js-backed-link"]') != None and backed != 0:
            backed_soup = get_live_soup(path, True, driver)
        else:
            backed_soup = None
        
        driver.quit()
    else:
        with open(path + " — About.html", encoding='utf8', errors="backslashreplace") as infile:
            about_soup = BeautifulSoup(infile, "lxml")
        with open(path + " — Comments.html", encoding='utf8', errors="backslashreplace") as infile:
            comment_soup = BeautifulSoup(infile, "lxml")
        with open(path + " — Created.html", encoding='utf8', errors="backslashreplace") as infile:
            created_soup = BeautifulSoup(infile, "lxml")
        if about_soup.select_one('a[class="nav--subnav__item__link nav--subnav__item__link--gray js-backed-link"]') != None:
            with open(path + " — Backed.html", encoding='utf8', errors="backslashreplace") as infile:
                backed_soup = BeautifulSoup(infile, "lxml")
        else:
            backed_soup = None                  

    # Creator id.
    url_elem = about_soup.select_one('meta[property="og:url"]')
    data["url"] = url_elem["content"]

    # Project Id and Creator Id.
    data["creator_id"] = data["url"].split("/")[-1]

    # Join date.
    join_day, join_month, join_year = "", "", ""
    join_date_elem = about_soup.select_one('span[class="joined"] > time')
    if join_date_elem != None:
        join_date = datetime.strptime(join_date_elem['datetime'], '%Y-%m-%dT%H:%M:%S%z')
        join_day, join_month, join_year = join_date.day, join_date.month, join_date.year
        
    data['join_day'], data['join_month'], data['join_year'] = join_day, join_month, join_year

    # Location.
    data['location'] = extract_elem_text(about_soup, 'span[class="location"] > a')

    # Biography.
    data['biography'] = extract_elem_text(about_soup, 'div[class="grid-col-12 grid-col-8-sm grid-col-6-md"]').strip()

    data['num_backed'] = backed

    # Number of created projects.
    data['num_created'] = extract_elem_text(about_soup, 'a[class="nav--subnav__item__link nav--subnav__item__link--gray js-created-link"] > span').strip()

    # Websites.
    websites = [elem['href'] for elem in about_soup.select('ul[class="menu-submenu mb6"] > li > a')]
    data['num_websites'] = len(websites)
    data['has_facebook'] = any("facebook" in website for website in websites)
    data['has_twitter'] = any("twitter" in website for website in websites)
    data['has_instagram'] = any("instagram" in website for website in websites)
    data['websites'] = websites

    # Comments.
    comments = []
    if comment_soup != None:
        comment_elems = comment_soup.select('li[class="flex flex-wrap page"] > ol > li')
        for comment_elem in comment_elems:
            comment_str = comment_elem.select_one('p[class="body"]').getText()
            link = "https://www.kickstarter.com" + comment_elem.select_one('a[class="read-more"]')['href']
            date = comment_elem.select_one('a[class="read-more"] > time').getText()
            comments.append((comment_str, date, link))

    data['comments_hidden'] = int(comment_soup == None)
    data['num_comments'] = len(comments)
    data['comments'] = comments

    # Created projects.
    created_data_projects = []
    for created_soup in created_soups:
        created_project_elem = created_soup.select_one('div[data-projects]')
        created_data_projects.extend(json.loads(created_project_elem['data-projects']))

    created_projects = []
    for created_data_project in created_data_projects:
        created_projects.append(parse_data_project(created_data_project))
    data['created_projects'] = created_projects

    # Backed projects.
    backed_projects = []
    if backed_soup != None:
        backed_data_projects = [json.loads(elem['data-project']) for elem in backed_soup.select('div[data-project]')]
        for backed_data_project in backed_data_projects:
            backed_projects.append(parse_data_project(backed_data_project))   
    data['backed_projects'] = backed_projects

    return data

def extract_write(creator_id):
    """Takes a creator_id, extracts data from pages and writes
    the data as a json file to output_path"""
    logging.info(f"Started extracting {creator_id} data...")
    creator_datum = extract_creator_data(r"https://www.kickstarter.com/profile/" + creator_id)

    # Update deleted_creators.json in case of a deleted creator.
    if creator_datum == None:
        deleted_creators.append(creator_id)

    # Write data to file.
    logging.info(f"Writing {creator_id} data to file...")
    with open(os.path.join(OUTPUT_PATH, f"{creator_id}.json"), "w") as f_obj:
        json.dump(creator_datum, f_obj)

if __name__ == "__main__":
    main()

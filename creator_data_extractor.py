import re
import time
from datetime import datetime
import json

from selenium import webdriver
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup
import pandas as pd

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
    
def get_live_soup(link, scroll=False):
    """Returns a bs4 soup object of the given link.
    
    link [str] - A link to a website.
    scroll [bool] - True if you want selenium to keep scrolling down till loading no longer happens.
    False by default"""
    driver = webdriver.Chrome()
    driver.get(link)

    if not scroll:
        time.sleep(1)
    else:
        while True:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait to scroll. Break if no longer loading.
            time.sleep(5)
            try:
                elem = driver.find_element(By.CSS_SELECTOR, 'img[alt="Loading icon"]')
            except:
                break

    soup = BeautifulSoup(driver.page_source, "lxml")
    driver.quit()

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

def extract_creator_data(path, is_link=True):
    """Returns a dictionary of the data for the creator."""
    data = {}

    if is_link:
        # Extract data from about page.
        about_soup = get_live_soup(path + "/about")
        comment_soup = get_live_soup(path + "/comments", True)
    else:
        with open(path, encoding='utf8', errors="backslashreplace") as infile:
            about_soup = BeautifulSoup(infile, "lxml")        

    # Number of projects backed.
    backed = extract_elem_text(about_soup, 'span[class="backed"]')
    data['num_backed'] = get_digits(backed, "int")
    
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

    # Number of created projects.
    data['num_created'] = extract_elem_text(about_soup, 'a[class="nav--subnav__item__link nav--subnav__item__link--gray js-created-link"] > span').strip()

    # Websites.
    data['websites'] = [elem['href'] for elem in about_soup.select('ul[class="menu-submenu mb6"] > li > a')]

    # Comments.
    comments = []
    comment_elems = comment_soup.select('li[class="flex flex-wrap page"] > ol > li')
    for comment_elem in comment_elems:
        comment_str = comment_elem.select_one('p[class="body"]').getText()
        link = "https://www.kickstarter.com" + comment_elem.select_one('a[class="read-more"]')['href']
        date = comment_elem.select_one('a[class="read-more"] > time').getText()
        comments.append((comment_str, date, link))

    data['num_comments'] = len(comments)
    data['comments'] = comments

    return data

def parse_data_project(data_project):
    """Parses a kickstarter data project dictionary and returns a dictionary of
    required keys.
    
    data-project [dict]- A kickstarter data project dict."""
    result = {}

    result['name'] = data_project['name']
    result['url'] = data_project['urls']['web']['project']
    result['creator_id'] = data_project['creator']['id']
    result['blurb'] = data_project['blurb']
    result['currency'] = data_project['currency']
    result['goal'] = data_project['goal']
    result['pledged'] = data_project['pledged']
    result['backers'] = data_project['backers_count']
    result['state'] = data_project['state'].title()
    result['pwl'] = int(data_project['staff_pick'])
    result['location'] = data_project['location']['short_name']

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

if __name__ == "__main__":
    # https://www.kickstarter.com/profile/dicedungeons/comments # Lots of loading comments.
    # https://www.kickstarter.com/profile/shiftcam # Backed projects are public.
    # https://www.kickstarter.com/profile/mybirdbuddy/about # Multiple websites in about.

    # data = extract_creator_data(r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Kickstarter-Data-Scraper\Test\Creator\Soul Mama London — About.html", False)
    # df = pd.DataFrame([data])
    # df.to_csv('creator_test.csv', index = False)
    path = r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Kickstarter-Data-Scraper\Test\Creator\Dice Dungeons — Created.html"

    with open(path, encoding='utf8', errors="backslashreplace") as infile:
        created_soup = BeautifulSoup(infile, "lxml")

    data_project = created_soup.select_one('div[data-projects]')['data-projects']
    d = json.loads(data_project)[0]
    parse_data_project(d)
     


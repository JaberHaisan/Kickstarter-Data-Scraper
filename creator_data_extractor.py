import re
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup
import pandas as pd

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

def extract_creator_data(creator_url):
    """Returns a dictionary of the data for the creator."""
    data = {}

    # Extract data from about page.
    about_soup = get_live_soup(creator_url + "/about")

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

    return data

if __name__ == "__main__":
    # https://www.kickstarter.com/profile/dicedungeons/comments # Lots of loading comments.
    # https://www.kickstarter.com/profile/manbomb # Backed projects are public.
    # https://www.kickstarter.com/profile/mybirdbuddy/about # Multiple websites in about.
    
    # path = r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Kickstarter-Data-Scraper\Test\Creator\Soul Mama London — About.html"
    # with open(path, encoding='utf8', errors="backslashreplace") as infile:
    #     soup = BeautifulSoup(infile, "lxml")
    data = extract_creator_data("https://www.kickstarter.com/profile/soulmama")
    df = pd.DataFrame(data)
    df.to_csv('creator_test.csv', index = False)


import re
import time
from datetime import datetime

from selenium import webdriver
from bs4 import BeautifulSoup

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
    
def get_live_soup(link):
    """Returns a bs4 soup object of the given link.
    
    link [str] - A link to a website."""
    driver = webdriver.Chrome()
    driver.get(link)
    time.sleep(1)
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

if __name__ == "__main__":
    path = r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Kickstarter-Data-Scraper\Test\Creator\Soul Mama London — About.html"
    with open(path, encoding='utf8', errors="backslashreplace") as infile:
        soup = BeautifulSoup(infile, "lxml")

    data = {}
    
    # Number of projects backed.
    backed = extract_elem_text(soup, 'span[class="backed"]')
    data['backed'] = get_digits(backed, "int")
    
    # Join date.
    join_day, join_month, join_year = "", "", ""
    join_date_elem = soup.select_one('span[class="joined"] > time')
    if join_date_elem != None:
        join_date = datetime.strptime(join_date_elem['datetime'], '%Y-%m-%dT%H:%M:%S%z')
        join_day, join_month, join_year = join_date.day, join_date.month, join_date.year
    data['join_day'], data['join_month'], data['join_year'] = join_day, join_month, join_year

    # Location.
    data['location'] = extract_elem_text(soup, 'span[class="location"] > a')

    # Biography.
    data['biography'] = extract_elem_text(soup, 'div[class="grid-col-12 grid-col-8-sm grid-col-6-md"]').strip()

    print(data)

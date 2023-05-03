import csv
from datetime import datetime

from bs4 import BeautifulSoup

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
    description_elem = soup.select('div[class="full-description js-full-description responsive-media formatted-lists"]')
    description = description_elem[0].getText().strip()
    data["description"] = description

    return data

if __name__ == "__main__":
    # No faq
    file_path_1 = r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Data\art\a1\1-1000-supporters-an-art-gallery-and-design-boutiq\1-1000-supporters-an-art-gallery-and-design-boutiq_20190312-010622.html"
    
    # Has faq. No blurb, creator, backer, goal, date, category, location, projects_num
    file_path_2 = r"C:/Users/jaber/OneDrive/Desktop/Research_JaberChowdhury/Data/art/a1/100-quirky-characters/100-quirky-characters_20190201-150330.html"
    
    data_1 = extract_campaign_data(file_path_1)
    data_2 = extract_campaign_data(file_path_2)

    # Write results to a csv file.
    with open('results.csv', 'w') as f: 
        w = csv.DictWriter(f, data_1.keys())
        w.writeheader()
        w.writerows([data_1, data_2])
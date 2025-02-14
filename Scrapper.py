from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
import time  
import re
import os
import urllib.parse

# ✅ Retrieve MongoDB credentials from GitHub Secrets
username = urllib.parse.quote_plus(os.getenv("MONGO_USER", ""))
password = urllib.parse.quote_plus(os.getenv("MONGO_PASS", ""))

# ✅ Connect to MongoDB Atlas
client = MongoClient(f"mongodb+srv://{username}:{password}@hackathondb.hwg5w.mongodb.net/?retryWrites=true&w=majority&appName=hackathondb")
db = client["hackathonDB"]
collection = db["events"]

# ✅ Clear existing data to avoid duplication
collection.delete_many({})
print("Database cleared before inserting new data.")

# ✅ Configure Chrome for GitHub Actions (Headless Mode)
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode (no GUI)
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# ✅ Set up Chrome WebDriver service
service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)

# ✅ Open Devpost hackathon page
url = "https://devpost.com/hackathons"
driver.get(url)

# ✅ Wait for page to load
WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "hackathon-tile")))

# ✅ Scroll dynamically until at least 50 or 100 hackathons are loaded
TARGET_COUNT = 100  # Change to 50 if needed
MAX_SCROLLS = 30  # Prevent infinite scrolling
prev_count = 0
scroll_attempts = 0

while len(driver.find_elements(By.CLASS_NAME, "hackathon-tile")) < TARGET_COUNT and scroll_attempts < MAX_SCROLLS:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)  # Wait for new content to load
    
    current_count = len(driver.find_elements(By.CLASS_NAME, "hackathon-tile"))
    print(f"Scroll {scroll_attempts + 1}: Found {current_count} hackathons")
    
    if current_count == prev_count:  # No new hackathons loaded
        break
    
    prev_count = current_count
    scroll_attempts += 1

print(f"Final Total Hackathons Found: {len(driver.find_elements(By.CLASS_NAME, 'hackathon-tile'))}")

# ✅ Extract Hackathon Data
scraped_events = []
events = driver.find_elements(By.CLASS_NAME, "hackathon-tile")[:TARGET_COUNT]

for event in events:
    try:
        driver.execute_script("arguments[0].scrollIntoView();", event)
        time.sleep(1)

        name = event.find_element(By.CSS_SELECTOR, "h3.mb-4").text
        date_text = event.find_element(By.CLASS_NAME, "submission-period").text  

        # ✅ Extract start_date and end_date
        date_match = re.search(r"(\w+ \d{1,2})(?:, (\d{4}))? - (\w+ \d{1,2}, \d{4})", date_text)
        if date_match:
            start_date, start_year, end_date = date_match.groups()
            if not start_year:
                start_date += f", {end_date.split()[-1]}"
        else:
            start_date, end_date = date_text, "Not available"

        # ✅ Extract mode & location
        location_info = event.find_element(By.CLASS_NAME, "info").text
        mode = "Online" if "online" in location_info.lower() else "Offline"
        location = "None" if mode == "Online" else location_info

        # ✅ Extract prize amount (if available)
        try:
            prize = event.find_element(By.CLASS_NAME, "prize-amount").text
        except:
            prize = "Not mentioned"

        # ✅ Extract apply link
        apply_link = event.find_element(By.TAG_NAME, "a").get_attribute("href")

        hackathon_data = {
            "name": name,
            "start_date": start_date,
            "end_date": end_date,
            "mode": mode,
            "location": location,
            "prize_money": prize,
            "apply_link": apply_link
        }

        scraped_events.append(hackathon_data)

    except Exception as e:
        print(f"Skipping one event due to error: {e}")

# ✅ Insert into MongoDB
if scraped_events:
    collection.insert_many(scraped_events)
    print(f"{len(scraped_events)} hackathons stored in MongoDB successfully!")

# ✅ Close browser
driver.quit()

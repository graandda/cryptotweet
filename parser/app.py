import csv
import json
import os
from datetime import datetime, timedelta
import time

from bs4 import BeautifulSoup

import redis
from selenium.webdriver import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver

redis_client = redis.Redis(port=6379, db=0)  # out docker


# redis_client = redis.StrictRedis(host='redis', port=6379, db=0) # in docker


def callback(message):
    print(message)


class TwitterWorker:
    capabilities = DesiredCapabilities.CHROME
    # capabilities["loggingPrefs"] = {"performance": "ALL"}  # chromedriver < ~75
    capabilities["goog:loggingPrefs"] = {"performance": "ALL"}  # chromedriver 75+

    def __init__(self):
        self.URL = "https://twitter.com/login/"
        self.ACCOUNT_DATA = {}
        self.WORKER_CODE = self.pick_account()
        self.SESSION_DATA_PATH = f"session_{self.WORKER_CODE}"
        self.options = Options()
        self.load_options()
        self.driver = webdriver.Chrome(options=self.options)
        self.currency = self.pick_currency()

    def pick_account(self) -> int:
        """
        check free account credentials and pick them
        if credentials is free, make sign with account info in redis
        :return:
        """
        with open("account_data.json", "r") as f:
            accounts = json.load(f)

        for account in accounts.keys():
            if not redis_client.exists(f"instance:{int(account)}"):
                redis_client.hset(f"instance:{int(account)}", "currency", f"")
                self.ACCOUNT_DATA = accounts[f"{int(account)}"]
                return int(account)

    def pick_currency(self) -> dict:
        """
        pick free currency for parsing
        :return:
        """
        with open("currency_query_data.json", "r") as f:
            currencies_data = json.load(f)
        for currency in currencies_data.keys():
            if not redis_client.exists(f"currency:{currency}"):
                redis_client.hset(
                    f"instance:{self.WORKER_CODE}", "currency", f"{currency}"
                )
                return currencies_data[currency]

    def load_options(self) -> None:
        """
        Load options into driver
        :return:
        """
        self.options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        )
        self.options.add_argument("--user-data-dir=" + self.SESSION_DATA_PATH)
        ##self.options.add_argument('--headless') docker
        self.options.add_argument("--no-sandbox")
        ##self.options.add_argument('--disable-dev-shm-usage') docker

    def login(self) -> str:
        wait = WebDriverWait(self.driver, 50)
        # find username field
        wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[autocomplete="username"]'))
        ).send_keys(self.ACCOUNT_DATA["MAIL"])
        # find next button
        wait.until(
            EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Next")]'))
        ).click()
        time.sleep(5)

        # if login expired in first time
        try:
            wait.until(EC.element_to_be_clickable((By.TAG_NAME, "input"))).send_keys(
                self.ACCOUNT_DATA["LOGIN"]
            )
            wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//span[contains(text(), "Next")]')
                )
            ).click()
        except Exception:
            wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, '[autocomplete="current-password"]')
                )
            ).send_keys(self.ACCOUNT_DATA["PASSWORD"])
            wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//span[contains(text(), "Log in")]')
                )
            ).click()
        finally:
            # find password field and login
            wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, '[autocomplete="current-password"]')
                )
            ).send_keys(self.ACCOUNT_DATA["PASSWORD"])
            wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//span[contains(text(), "Log in")]')
                )
            ).click()
        return "200: Making login..."

    def start_twitter_session(self) -> str:
        # create instance of Chrome webdriver
        try:
            self.driver.get(self.URL)

            self.driver.implicitly_wait(10)
            if self.driver.current_url != "https://twitter.com/home":
                try:
                    self.login()
                    print("Login is succeeded!")
                    return 200
                except Exception as ex:
                    print(f"Smth wrong, when i try to login! \n Exeption: {ex}")
                    raise ex
        except Exception as ex:
            raise ex
        return "200: Starting session..."

    def make_search(self) -> str:
        """
        find all yesterday posts
        """
        lang = "en"
        since = (datetime.now() - timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )  # get yesterday date
        url = f"https://twitter.com/search?f=top&q={'%20'.join(word for word in self.currency['query_words'])}%20%20min_faves%3A{self.currency['min_faves']}%20lang%3A{lang}%20since%3A{since}&src=typed_query"
        self.driver.get(url)
        return "200: Making search..."

    def do_scroll(self) -> None:
        scrols_to_all_new_posts = 6
        for i in range(scrols_to_all_new_posts + 1):
            body = self.driver.find_element("tag name", "body")
            body.send_keys(Keys.PAGE_DOWN)
            # Wait for a while to let the content load
            time.sleep(2)

    def do_parse(self) -> str:
        self.do_scroll()
        time.sleep(3)
        parse_all_posts_on_page(self.driver.page_source)

        return "200: Parssing done!"

    def delete_session(self):
        redis_client.delete(f"instance:{self.WORKER_CODE}")


def parse_all_posts_on_page(page_source):
    # Parse the page source with BeautifulSoup
    soup = BeautifulSoup(page_source, "html.parser")

    # Find the div element with the specified data-testid
    elements = soup.find_all("div", {"data-testid": "cellInnerDiv"})
    count = 0
    for element in elements:

        if element:
            count += 1
            print(f"{count}.{element.text}")
            load_post_to_csv(element.text)
        else:
            print("Element not found")
        pass


# TODO: Make load into scv more efficient
def load_post_to_csv(content):
    csv_filename = "output.csv"
    header = ["Author", "Content", "Replies", "Reposts", "Likes", "Views"]
    file_path = "" + csv_filename

    if os.path.exists(file_path):
        with open(csv_filename, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=header)
            writer.writerow({"Content": content})
    else:
        with open(csv_filename, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=header)
            writer.writeheader()
            writer.writerow({"Content": content})


if __name__ == "__main__":
    pubsub = redis_client.pubsub()
    pubsub.subscribe("parser_tasks")

    try:
        driver = TwitterWorker()
    except Exception as Ex:
        driver.delete_session()
        raise Ex
    for message in pubsub.listen():
        print(message)
        if message["type"] == "message":
            if message["data"].decode() == "login_to_twitter":
                try:
                    callback(driver.start_twitter_session())
                    print(
                        f"pick account number: {driver.WORKER_CODE} n/ with currency key: {driver.currency}"
                    )
                except Exception as ex:
                    driver.delete_session()
                    callback(ex)

            if message["data"].decode() == "make_search":
                try:
                    callback(driver.make_search())
                except Exception as ex:
                    driver.delete_session()
                    callback(ex)

            if message["data"].decode() == "make_parse":
                try:
                    callback(driver.do_parse())
                except Exception as ex:
                    driver.delete_session()
                    callback(ex)

        driver.delete_session()

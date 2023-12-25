import json
import time

import redis
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver


redis_client = redis.Redis(port=6379, db=0)  # docker
# redis_client = redis.StrictRedis(host='redis', port=6379, db=0) # docker


def callback(message):
    print(message)


class TwitterWorker:
    URL = "https://twitter.com/login/"
    capabilities = DesiredCapabilities.CHROME
    # capabilities["loggingPrefs"] = {"performance": "ALL"}  # chromedriver < ~75
    capabilities["goog:loggingPrefs"] = {"performance": "ALL"}  # chromedriver 75+

    def __init__(self):
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

    def load_options(self):
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

    def login(self):
        wait = WebDriverWait(self.driver, 200)
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
        return 200

    def start_twitter_session(self):
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

    def make_q(self):
        # btc bitcoin  min_faves:97 lang:en since:2023-01-01
        url = "https://twitter.com/search?f=top&q=btc%20bitcoin%20%20min_faves%3A97%20lang%3Aen%20since%3A2023-01-01&src=typed_query"


if __name__ == "__main__":
    pubsub = redis_client.pubsub()
    pubsub.subscribe("parser_tasks")
    driver = TwitterWorker()

    for message in pubsub.listen():
        print(message)
        if message["type"] == "message":
            if message["data"].decode() == "login_to_twitter":
                try:
                    callback(driver.start_twitter_session())
                except Exception as ex:
                    callback(ex)

            if message["data"].decode() == "make_search":
                try:
                    callback(driver.start_twitter_session())
                except Exception as ex:
                    callback(ex)

            if message["data"].decode() == "make_parse":
                try:
                    callback(driver.start_twitter_session())
                except Exception as ex:
                    callback(ex)

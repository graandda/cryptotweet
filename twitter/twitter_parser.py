# TODO: Make authorization
import json
import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from selenium import webdriver
import logging
from red import conn


class TwitterWorker():
    ACCOUNT_DATA = {}
    URL = "https://twitter.com/login/"
    capabilities = DesiredCapabilities.CHROME
    # capabilities["loggingPrefs"] = {"performance": "ALL"}  # chromedriver < ~75
    capabilities["goog:loggingPrefs"] = {"performance": "ALL"}  # chromedriver 75+

    def __init__(self):
        self.WORKER_CODE = self.pick_account()
        self.SESSION_DATA_PATH = f"./twitter/session_{self.WORKER_CODE}"
        self.options = Options()
        self.load_options()
        self.driver = webdriver.Chrome(options=self.options)
        self.write_session()

    def pick_account(self):
        """
        check what account credentials free and pick them
        :return:
        """

        with open("./twitter/account_data.json", "r") as f:
            accounts = json.load(f)

        for account in accounts.keys():
            if not conn.exists(f"instance:{int(account)}"):
                self.ACCOUNT_DATA = accounts[f"{int(account)}"]
                return int(account)

    def load_options(self):
        """
        Load options into driver
        :return:
        """
        self.options.add_argument("start-maximized")
        # self.options.
        # add_argument('--headless')  # Run in headless mode without opening a browser window
        self.options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
        self.options.add_argument("--user-data-dir=" + self.SESSION_DATA_PATH)

    def login(self):
        wait = WebDriverWait(self.driver, 200)
        # find username field
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[autocomplete="username"]'))).send_keys(
            self.ACCOUNT_DATA["MAIL"])
        # find next button
        wait.until(EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Next")]'))).click()
        time.sleep(5)

        # if login expired in first time
        try:
            wait.until(EC.element_to_be_clickable((By.TAG_NAME, 'input'))).send_keys(
                self.ACCOUNT_DATA["LOGIN"])
            wait.until(EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Next")]'))).click()
        except Exception:
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[autocomplete="current-password"]'))).send_keys(
                self.ACCOUNT_DATA["PASSWORD"])
            wait.until(EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Log in")]'))).click()

        # find password field and login
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[autocomplete="current-password"]'))).send_keys(
            self.ACCOUNT_DATA["PASSWORD"])
        wait.until(EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Log in")]'))).click()
        time.sleep(100)

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

    # def write_session(self):
    #     url = self.driver.command_executor._url
    #     session_id = self.driver.session_id
    #     f = open(f"./twitter/sessioninfo_{self.WORKER_CODE}.txt", "w")
    #     f.write(f"{url}\n")
    #     f.write(f"{session_id}")
    #     f.close()
    #     print('Wrote webdriver session details')
    #
    # def attach_to_session(self):
    #     f = open(f"./twitter/sessioninfo_{self.WORKER_CODE}.txt", "r")
    #     lines = f.readlines()
    #     url = lines[0]
    #     session_id = lines[1]
    #     session_id.strip()
    #     self.driver.session_id = session_id
    #     # Replace the patched function with original function
    #     return self

    def write_session(self):
        url = self.driver.command_executor._url
        session_id = self.driver.session_id

        # Store essential information in a dictionary
        session_info = {'url': url, 'session_id': session_id}

        # Serialize the dictionary to JSON
        serialized_info = json.dumps(session_info)

        # Store the serialized information in Redis or any other storage
        # For demonstration, assuming 'redis_conn' is a Redis connection
        conn.set(f"session_info:{self.WORKER_CODE}", serialized_info)

    def attach_to_session(self):
        # Retrieve the stored information from Redis
        stored_info = conn.get(f"session_info:{self.WORKER_CODE}")

        # Deserialize the information from JSON
        session_info = json.loads(stored_info)

        # Ensure 'options' is not None, provide a default ChromeOptions instance if needed
        self.driver.session_id = session_info['session_id']

        return self

    def do_smth(self):
        self.driver.get("https://google.com")



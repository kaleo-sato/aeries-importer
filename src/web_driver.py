from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import sys

from aeries_utils import AeriesData


def get_aeries_cookie() -> str:
    # Set up Chrome options to connect to the existing Chrome session
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Get the Aeries cookie
    driver.get('https://aeries.musd.org')
    s_cookie = driver.get_cookie('s')['value']

    try:
        AeriesData(periods=[], s_cookie=s_cookie).probe()
    except AttributeError:
        driver.quit()
        sys.exit(
            'Aeries cookie is invalid. Please check if you are logged in to Aeries in your Chrome session.',
        )
    else:
        # Close the WebDriver instance (not the actual Chrome window)
        driver.quit()

    return s_cookie

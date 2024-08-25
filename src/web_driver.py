from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def get_aeries_cookie():
    # Set up Chrome options to connect to the existing Chrome session
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222/")

    # Initialize the WebDriver instance to connect to the existing Chrome session
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Get the Aeries cookie
    driver.get('https://aeries.musd.org')
    s_cookie = driver.get_cookie('s')['value']

    # Close the WebDriver instance (not the actual Chrome window)
    driver.quit()

    return s_cookie

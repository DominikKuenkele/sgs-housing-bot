from selenium.webdriver import Firefox, FirefoxOptions


def get_webdriver(headless=True) -> Firefox:
    firefox_options = FirefoxOptions()
    firefox_options.headless = headless

    driver = Firefox(options=firefox_options)
    driver.implicitly_wait(5)

    return driver

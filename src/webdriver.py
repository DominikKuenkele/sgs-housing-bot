from selenium.webdriver import Firefox, FirefoxOptions


def get_webdriver(headless=True) -> Firefox:
    options = FirefoxOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")

    driver = Firefox(options=options)

    return driver

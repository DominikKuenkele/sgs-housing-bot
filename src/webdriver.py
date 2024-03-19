import tempfile

from selenium.webdriver import Firefox, FirefoxOptions


DOWNLOAD_PATH = tempfile.gettempdir()


def get_webdriver(headless=True) -> Firefox:
    firefox_options = FirefoxOptions()
    firefox_options.headless = headless

    # download folder
    firefox_options.set_preference("browser.download.folderList", 2)
    firefox_options.set_preference(
        "browser.download.manager.showWhenStarting", False)
    firefox_options.set_preference("browser.download.dir", DOWNLOAD_PATH)
    firefox_options.set_preference(
        "browser.helperApps.neverAsk.saveToDisk", "application/x-gzip")

    driver = Firefox(options=firefox_options)
    driver.implicitly_wait(5)

    return driver

import logging
import sqlite3

from sgs import SGS
from webdriver import get_webdriver

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class MissingEnvironmentVariable(Exception):
    pass


if __name__ == "__main__":
    try:
        webdriver = get_webdriver(headless=True)

        db_connection = sqlite3.connect("database.db")
        log.info("opening SGS website...")
        appartments = SGS(webdriver).get_appartments()
        for app in appartments:
            print(app.id, app.address, app.location, app.size, app.area, app.free_from)
        log.info("storing appartments...")
    except:
        log.error("Failed.", exc_info=True)
    finally:
        webdriver.quit()
        webdriver.quit()

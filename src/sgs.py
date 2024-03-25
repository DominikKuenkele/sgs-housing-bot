import logging
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class SGSApartment:
    def __init__(self, apartment_element: WebElement) -> None:
        self.id = apartment_element.find_element(By.TAG_NAME, "mat-card").get_property(
            "id"
        )
        self.address = apartment_element.find_element(By.CLASS_NAME, "address").text
        self.location = apartment_element.find_element(By.CLASS_NAME, "location").text
        self.size = apartment_element.find_element(By.CLASS_NAME, "size").text.split(
            "\n"
        )[0]
        self.area = float(
            apartment_element.find_element(By.CLASS_NAME, "area").text.split("\n")[0]
        )
        self.rent = int(
            apartment_element.find_element(By.CLASS_NAME, "rent").text.split("\n")[0]
        )
        self.free_from = datetime.strptime(
            apartment_element.find_element(By.CLASS_NAME, "free-from").text.split("\n")[
                0
            ],
            "%Y-%m-%d",
        )
        self.url = f"https://minasidor.sgs.se/market/residential/{self.id}"


class SGS:
    URL = "https://minasidor.sgs.se/market/residential?pageSize=100"

    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

    def get_apartments(self) -> list[SGSApartment]:
        self.driver.get(self.URL)

        wait = WebDriverWait(self.driver, 15)
        wait.until(expected_conditions.title_is("Mina Sidor"))

        log.info("Opened website")

        apartments = [
            SGSApartment(apartment)
            for apartment in self.driver.find_elements(
                By.CSS_SELECTOR, "taiga-market-objects-list > div"
            )
        ]
        log.info("Found %s apartments.", len(apartments))

        return apartments

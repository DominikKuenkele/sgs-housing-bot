from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait


class Appartment:
    def __init__(self, appartment_element: WebElement) -> None:
        self.id = appartment_element.find_element(By.TAG_NAME, "mat-card").get_property(
            "id"
        )
        self.address = appartment_element.find_element(By.CLASS_NAME, "address").text
        self.location = appartment_element.find_element(By.CLASS_NAME, "location").text
        self.size = appartment_element.find_element(By.CLASS_NAME, "size").text.split(
            "\n"
        )[0]
        self.area = appartment_element.find_element(By.CLASS_NAME, "area").text.split(
            "\n"
        )[0]
        self.rent = appartment_element.find_element(By.CLASS_NAME, "rent").text.split(
            "\n"
        )[0]
        self.free_from = appartment_element.find_element(
            By.CLASS_NAME, "free-from"
        ).text.split("\n")[0]


class SGS:
    URL = "https://minasidor.sgs.se/market/residential?pageSize=100"

    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

    def get_appartments(self) -> list[Appartment]:
        self.driver.get(self.URL)

        wait = WebDriverWait(self.driver, 15)
        wait.until(expected_conditions.title_is("Mina Sidor"))

        appartments = [
            Appartment(appartment)
            for appartment in self.driver.find_elements(
                By.CSS_SELECTOR, "taiga-market-objects-list > div"
            )
        ]
        return appartments

import csv
import logging
import sys
from dataclasses import dataclass, fields, astuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

BASE_URL = "https://webscraper.io/"
# LAPTOP_URL = urljoin(BASE_URL, "test-sites/e-commerce/static/computers/laptops")
HOME_URL = urljoin(BASE_URL, "test-sites/e-commerce/more/")


@dataclass
class Product:
    title: str
    description: str
    price: float
    rating: int
    num_of_reviews: int
    additional_info: dict

PRODUCT_FIELDS = [field.name for field in fields(Product)]

_driver: WebDriver | None = None

def get_driver() -> WebDriver:
    return _driver


def set_driver(new_driver: WebDriver) -> None:
    global _driver
    _driver = new_driver


logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)8s: %(message)s]",
    handlers=[
        logging.FileHandler("parser.log"),
        logging.StreamHandler(sys.stdout)
    ]
)


def parse_hdd_block_proces(product_soup: BeautifulSoup) -> dict[str, float]:
    detail_url = urljoin(BASE_URL, product_soup.select_one(".title")["href"])
    driver = get_driver()
    driver.get(detail_url)
    swatches = driver.find_element(By.CLASS_NAME, "swatches")
    buttons = swatches.find_elements(By.TAG_NAME, "button")

    prices = {}

    for button in buttons:
        if not button.get_property("disabled"):
            button.click()
            prices[button.get_property("value")] = float(driver.find_element(
                By.CLASS_NAME, "price"
            ).text.replace("$", ""))

    return prices


def parse_single_product(product_soup: BeautifulSoup) -> Product:
    hdd_prices = parse_hdd_block_proces(product_soup)
    return Product(
        title=product_soup.select_one(".title")["title"],
        description=product_soup.select_one(".description").text,
        price=float(product_soup.select_one(".price").text.replace("$", "")),
        rating=int(product_soup.select_one("p[data-rating]")["data-rating"]),
        num_of_reviews=int(
            product_soup.select_one(".ratings > p.review-count").text.split()[0]
        ),
        additional_info={"hdd_prices": hdd_prices}
    )


def get_num_pages(page_soup: BeautifulSoup) -> int:
    pagination = page_soup.select_one(".pagination")

    if pagination is None:
        return 1

    return int(pagination.select("li")[-2].text)


def get_single_page_products(page_soup: BeautifulSoup) -> [Product]:
    products = page_soup.select(".thumbnail")

    return [parse_single_product(product_soup) for product_soup in products]


def get_laptop_products() -> list[Product]:
    page = requests.get(HOME_URL).content
    first_page_soup = BeautifulSoup(page, "html.parser")

    num_pages = get_num_pages(first_page_soup)

    all_products = get_single_page_products(first_page_soup)

    for page_num in range(2, num_pages + 1):
        page = requests.get(HOME_URL, {"page": page_num}).content
        soup = BeautifulSoup(page, "html.parser")
        all_products.extend(get_single_page_products(soup))
        break

    return all_products


def write_to_file(products: list[Product], name_of_file: str) -> None:
    with open(name_of_file, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(PRODUCT_FIELDS)
        writer.writerows([astuple(product) for product in products])


def get_all_products() -> None:
    with webdriver.Chrome() as new_diver:
        set_driver(new_diver)
        home_products = get_laptop_products()
        write_to_file(home_products, "home.csv")


if __name__ == "__main__":
    get_all_products()

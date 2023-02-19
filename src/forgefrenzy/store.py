import re
import json
import time

import requests
import selenium
from bs4 import BeautifulSoup

from forgefrenzy.exceptions import WebResourceError
from forgefrenzy.blueplate.logger import log


class WebResource:
    base_url = "https://example.com"
    request_cooldown = 2
    last_request = time.time() - request_cooldown

    def __init__(self):
        raise RuntimeError("This class is not intended to be instantiated")

    @classmethod
    def get(cls, page=""):
        url = f"{cls.base_url}/{page}"
        delay = max((cls.last_request + cls.request_cooldown) - time.time(), 0.5)
        log.debug(f"Waiting {delay}s to avoid blacklisting")
        time.sleep(delay)
        cls.last_request = time.time()

        log.debug(f"requests.get({url})")

        try:
            return requests.get(url)
        except Exception as e:
            raise WebResourceError(f"Failed to GET {url}") from e

    @classmethod
    def json(cls, page=""):
        try:
            return cls.get(page).json()
        except Exception as e:
            raise WebResourceError(f"Failed to get JSON from {page}") from e

    @classmethod
    def soup(cls, page=""):
        try:
            return BeautifulSoup(cls.get(page).text, "html.parser")
        except Exception as e:
            raise WebResourceError(f"Failed to get BeautifulSoup from {page}") from e


class Webstore(WebResource):
    base_url = "https://dwarvenforge.com"
    product_url = "/products/{handle}.js"
    inventory_url = "/collections/all-products?page={page_number}"
    inventory_url_regex = "href=['\"]/collections/all-products/products/([^'\"]+)['\"]"
    inventory_count_regex = "([0-9]+) products"

    product_count = None
    product_handles = None
    products = []

    @classmethod
    def get_product_count(cls):
        response = cls.get(cls.inventory_url.format(page_number=1))
        product_count = re.search(cls.inventory_count_regex, response.text).group(1)
        return int(product_count)

    @classmethod
    def get_product_handles(cls, page_number=None):
        if page_number is not None:
            response = cls.get(cls.inventory_url.format(page_number=page_number))
            products_from_page = re.findall(cls.inventory_url_regex, response.text)
            return products_from_page

        product_count = cls.get_product_count()
        page_number = 0
        page_products = True
        all_products = []

        log.info(f"Refreshing product list, website reports {product_count} products")

        while page_products:
            page_number += 1
            page_products = cls.get_product_handles(page_number)
            all_products += page_products

            log.debug(f"Page {page_number}: {len(page_products)} products")

        log.info(f"Processed {page_number} pages of products: {len(all_products)} products")

        return all_products

    @classmethod
    def get_product(cls, handle):
        return Webstore.json(cls.product_url.format(handle=handle))

    @classmethod
    def refresh(cls):
        products = []
        for handle in cls.get_product_handles():
            products.append(cls.get_product(handle))

        return products


class Catalog(WebResource):
    base_url = "https://pieces.dwarvenforge.com"
    request_cooldown = 0.5
    set_url_regex = f"href=['\"]{base_url}/item/1/([^'\"]+)['\"]"
    piece_url_regex = f"href=['\"]{base_url}/item/2/([^'\"]+)['\"]"

    @classmethod
    def get_data(cls):
        soup = cls.soup()
        data = soup.find(id="app").attrs["data-page"]

        try:
            as_json = json.loads(data)
        except Exception as e:
            raise CatalogResourceError(f"Failed to get JSON from Catalog inline page data") from e

        return as_json

    @classmethod
    def get_pieces_in_set(cls, sku):
        response = cls.get(f"item/1/{sku}")
        pieces_from_page = re.findall(cls.piece_url_regex, response.text)
        return pieces_from_page

    @classmethod
    def get_sets_with_piece(cls, sku):
        response = cls.get(f"item/2/{sku}")
        sets_from_page = re.findall(cls.set_url_regex, response.text)
        return sets_from_page

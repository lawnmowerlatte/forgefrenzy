""" Command line access using Blueplate Special
>>> m = Main("")
>>> isinstance(m, Main)
True
"""
import json

from forgefrenzy.blueplate.special import Special
from forgefrenzy.blueplate.version import version
import forgefrenzy.blueplate.logger

from forgefrenzy import *

log = forgefrenzy.blueplate.logger.log


class Main(Special):
    """forgefrenzy: A collection of tools to nurture your addiction to Dwarven Forge
    >>> isinstance(script, Main)
    True
    >>> isinstance(script, Special)
    True
    >>> issubclass(script.__class__, Special)
    True
    """

    def fn(self):
        pieces = Pieces()
        sets = Sets()
        partlists = PartLists()
        products = Products()
        stock = Stock()

        wishlist = [
            "5-LEDA-U",
            "4-CORB-U",
            "4-MODW-P",
            "BRV-U",
            "6-A136-U",
            "SID-U"
        ]

        wtb = [products.filter(Product.sku == sku).one() for sku in wishlist]

        log.alert(f"Scanning {len(wtb)} products")
        while True:
            for item in wtb:
                previous = item.quantity
                item.refresh(True)

                if item.quantity > previous:
                    log.alert(f"{item.name} increased stock from {previous} to {item.quantity}")

                if item.quantity < previous:
                    log.alert(f"{item.name} sold {previous-item.quantity}")

                if previous > 0 and item.quantity < 5:
                    log.alert(f"{item.name} very low stock: {item.quantity}")

                if previous > 0 and item.quantity == 0:
                    log.alert(f"{item.name} is now out of stock")

        breakpoint()

        with open("/Users/andrew/Dropbox/Home/Code/bin/history.json", "r") as f:
            history = json.load(f)

        count = 0
        import datetime

        for index, slice in enumerate(history):
            log.info(f"Processing slice {index}/{len(history)}")

            timestamp = datetime.datetime.fromisoformat(slice.pop("time"))
            for handle, quantity in slice.items():
                try:
                    sku = products.primary(handle).sku
                    Point(sku, quantity, timestamp)
                    count += 1
                except Exception as e:
                    log.exception(
                        f"Failed to create record for:\n    handle={handle}\nquantity={quantity}\ntime={timestamp}"
                    )

        # pieces.refresh()
        # sets.refresh()
        # partlists.refresh()
        # products.refresh()

        # product = Products.all()[100]
        # set = product.set
        # breakpoint()

    def test(self, mock_test=False):
        """Run local tests and tests on other mods
        >>> script.test(True)
        Called doctest.testmod(
            <module '...__main__' from '.../__main__.py'>,
        ...
        Called doctest.testmod(
            <module '...blueplate.special' from '.../blueplate/special.py'>,
        ...
        Called doctest.testmod(
            <module '....blueplate.logger' from '.../blueplate/logger.py'>,
        ...
        """
        from .blueplate import logger, special

        super().test(mock_test)
        response = special.Special().test(mock_test)
        special.test_module(logger, mock_test=mock_test)


if __name__ == "__main__":
    script = Main()
    script.main()

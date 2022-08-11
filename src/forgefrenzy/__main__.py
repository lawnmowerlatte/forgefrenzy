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

        # pieces.refresh()
        # sets.refresh()
        # partlists.refresh()
        # products.refresh()

        breakpoint()

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

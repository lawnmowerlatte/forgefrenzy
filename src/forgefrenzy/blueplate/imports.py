import logging

log = logging.getLogger()

try:
    import minimock

    mock = minimock.mock
except:
    log.warning("Unable to import minimock")


try:
    import doctest
except:
    log.warning("Unable to import doctest")

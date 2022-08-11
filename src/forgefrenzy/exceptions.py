class DatabaseAccessError(Exception):
    pass


class DatabaseEntrySpecificationError(Exception):
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return f"{self.__class__.__name__}: {self.message}"


class DatabaseEntryMissingColumnError(Exception):
    def __init__(self, cls, column):
        self.cls = cls
        self.column = column

    def __repr__(self):
        return f"{self.__class__.__name__}: Class {self.cls.__name__} perform this operation. This functionality requires a database with column '{self.column}'"


class InvalidTagValueError(Exception):
    def __init__(self, tag):
        self.tag = tag

    def __repr__(self):
        return f"{self.__class__.__name__}: The tag value: '{self.tag}' could not be processed."


class WebResourceError(Exception):
    pass


class CatalogResourceError(WebResourceError):
    pass

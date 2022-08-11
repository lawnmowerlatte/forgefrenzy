from pathlib import Path
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError

from forgefrenzy.exceptions import *
from forgefrenzy.blueplate.logger import log

logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

EntryORM = declarative_base()


class DFDB:
    def __init__(self, volatile=False, echo=False):
        root = Path(__file__).parent
        database = root / "df.sqlite"

        if volatile:
            log.warning("Starting database in volatile memory")
            self.db = "sqlite:///:memory:"
        else:
            self.db = f"sqlite:///{database}"

        self.engine = create_engine(self.db, echo=echo)

        self.Session = sessionmaker(bind=self.engine)

    def __str__(self):
        return f"DFDB at <{self.db}>"

    def generate_table(self, table_class):
        table_class.metadata.create_all(self.engine)

    @property
    def session(self):
        # return self.Session.begin()
        return DatabaseSession(self)


dfdb = DFDB()


class DatabaseSession:
    """Simple wrapper around existing session context manager"""

    def __init__(self, db):
        self.debug = False
        self.session = db.Session()

    def __enter__(self):
        if self.debug:
            log.info(f"Entering session {self.session}")
        return self.session.__enter__()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.debug:
            log.info(f"Exiting session {self.session}")

        return self.session.__exit__(exc_type, exc_value, exc_traceback)


class DatabaseEntry:
    db = dfdb
    __table__ = None
    __primary__ = None
    tagstring = None

    def __init__(self, **kwargs):
        log.debug(f"Initializing object from values")
        if isinstance(self, EntryORM):
            EntryORM.__init__(self, **kwargs)

        log.debug(f"Created {self} -> {self.db}")

    def __repr__(self):
        return f"{self.__class__.__name__} <{self.primary}>"

    def __str__(self):
        return f"{self.__class__.__name__} <{self.primary}>"

    @property
    def primary(self):
        """
        Returns the value of the primary key for this object
        """
        return self.__getattribute__(self.__primary__)

    @property
    def session(self):
        """Returns a database session"""
        return DatabaseSession(self.db)

    @property
    def as_dict(self):
        """Returns the object/entry as a dictionary"""
        self.sanitize_tags()
        d = {}

        for column in self.__table__.columns:
            d[column.name] = getattr(self, column.name)

        return d

    @property
    def entry(self):
        """Returns the database entry for this object based on the primary key"""
        with self.session as session:
            entry = session.query(self.__class__).filter(self.primary_attribute() == self.primary)

        return entry

    @property
    def exists(self):
        """Returns True/False if the object exists in the database"""
        with self.session as session:
            count = (
                session.query(self.__class__)
                .filter(self.primary_attribute() == self.primary)
                .count()
            )

        return count != 0

    def sanitize_tags(self):
        if self.tagstring is None:
            log.debug(f"This object does not have tags: {self}")
            return

        if isinstance(self.tagstring, str):
            # If it starts as a string, split it into a list so we can sanitize tags individually
            self.tagstring = self.tagstring.split(",")

        if isinstance(self.tagstring, list):
            # Strip whitespace from each tag and join it back into a list
            self.tagstring = [tag.strip() for tag in self.tagstring]
            self.tagstring = ",".join(self.tagstring)

        if isinstance(self.tagstring, str):
            # Lowercase the entire string
            self.tagstring = self.tagstring.lower()
        else:
            # If we don't end up with a string, something went very wrong
            raise InvalidTagValueError(self.tagstring)

    @property
    def tags(self):
        breakpoint()
        self.sanitize_tags()
        return self.tagstring.split(",")

    @tags.setter
    def tags(self, value):
        breakpoint()
        self.tagstring = value
        self.sanitize_tags()

    def save(self):
        """Save or update the object to the database"""
        log.info(f"Saving {self}")
        self.sanitize_tags()

        try:
            with self.session as session:
                if self.exists:
                    log.debug(f"Updating: {self}")
                    entry = session.query(self.__class__).filter(
                        self.primary_attribute() == self.primary
                    )
                    entry.update(self.as_dict, synchronize_session=False)
                    session.commit()
                else:
                    log.info(f"New record: {self}")
                    session.add(self)
                    session.commit()
        except OperationalError as e:
            log.exception(f"Unable to save object {self}")
            raise DatabaseAccessError(f"Unable to save object {self} to {self.db}")

    @classmethod
    def primary_attribute(cls):
        """Stores the attribute reference for the primary key (useful for queries)"""
        return cls.__getattribute__(cls, cls.__primary__)

    @classmethod
    def get_key(cls, value):
        """Returns the database entry based on the given primary key"""

        with cls.db.session as session:
            return session.query(cls).get(value)


class DatabaseTable:
    db = dfdb
    orm = DatabaseEntry

    def __init__(self):
        log.debug(f"Created {self} -> {self.db}")

        # Generate tables for the entry class
        if issubclass(self.orm, EntryORM):
            self.db.generate_table(self.orm)

    def __str__(self):
        return f"{self.__class__.__name__}[{self.orm.__name__}]"

    def __repr__(self):
        return f"{self.__class__.__name__}[{self.orm.__name__}]"

    @classmethod
    def session(cls):
        return DatabaseSession(cls.db).session

    @classmethod
    def query(cls):
        """Return a query for this table with an open session"""
        return cls.session().query(cls.orm)

    @classmethod
    def primary(cls, value):
        """Returns the database entry based on the given primary key"""
        return cls.query().get(value)

    @classmethod
    def all(cls):
        """Returns a list of all objects"""
        return cls.query().all()

    @classmethod
    def keys(cls):
        """Returns a list of all primary keys"""
        return [entry.primary for entry in cls.all()]

    @classmethod
    def keyed(cls):
        """Returns a dictionary of all objects, keyed on the primary key"""
        return {entry.primary: entry for entry in cls.all()}

    @classmethod
    def filter(cls, *args, **kwargs):
        """Filter the table and return the results on an open session"""
        return cls.query().filter(*args, **kwargs)

    @classmethod
    def tagged(cls, *tag_list):
        """
        Filter the table using tags. Each entry in tag list is a string containing one or more
        tags. Tags may be comma separated and may be negated by prepending a dash. Entries must
        match at one or more of the tag lists specified.
        """
        if cls.orm.tagstring is None:
            raise DatabaseEntryMissingColumnError(cls.orm, "tagstring")

        matches = set()
        entries = cls.query()

        for tags in tag_list:
            if isinstance(tag, str):
                tags = tags.split(",")

            for tag in tags:
                if tag[0] == "-":
                    tag = tag[1:]
                    entries = entries.filter(not cls.orm.tagstring.contains(tag))
                else:
                    entries = entries.filter(cls.orm.tagstring.contains(tag))

            matches.add(entries)
            entries = cls.query()

        return matches

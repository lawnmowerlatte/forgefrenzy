import json
from datetime import datetime, timedelta
from pprint import pprint, pformat

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from forgefrenzy.db import DatabaseTable, DatabaseEntry, EntryORM
from forgefrenzy.store import Catalog, Webstore

from forgefrenzy.blueplate.logger import log


class Product(DatabaseEntry, EntryORM):
    __tablename__ = "product"
    __primary__ = "handle"

    default_dataset = "main"
    dataset = Column(String, default=default_dataset)
    handle = Column(String, primary_key=True)
    type = Column(String)
    tagstring = Column(String)
    sku = Column(String)
    name = Column(String)
    price = Column(Integer)
    available = Column(Boolean)
    quantity = Column(Integer)
    weight = Column(Integer)
    updated = Column(DateTime, server_default=func.now())

    def refresh(self, force=False):
        """Pull the latest data from the webstore and update the object"""
        if force or self.refreshable:
            webstore_data = Webstore.get_product(self.handle)
            as_dict = Product.from_webstore_to_dict(webstore_data)

            for key, value in as_dict.items():
                setattr(self, key, value)

            self.updated = datetime.now()
            self.save()

            point = Point(self.sku, self.quantity, self.updated)

    def save(self):
        if self.updated is None:
            self.updated = datetime.now()

        super().save()

    @property
    def set(self):
        sku = self.sku
        if sku.endswith("-U") or sku.endswith("-P"):
            sku = sku[:-2]

        return Sets.primary(sku)

    @property
    def partlists(self):
        return [part for part in self.set.partlist]

    @property
    def pieces(self):
        pieces = [part.piece for part in self.partlists]
        return Pieces.filter_many(Piece.sku, pieces)

    @property
    def refreshable(self):
        try:
            return self.next_update <= datetime.now()
        except:
            return True

    @property
    def next_update(self):
        if self.updated is None:
            # If the product has never updated, return 0 to force update
            return 0

        refresh_frequency = 60 * 24 * 7

        if self.type.lower() in ["dwarvenite", "resin"]:
            refresh_frequency = 60 * 24

            if self.available and self.quantity > 0:
                if self.quantity < 10:
                    refresh_frequency = 1
                elif self.quantity < 25:
                    refresh_frequency = 5
                elif self.quantity < 50:
                    refresh_frequency = 10
                elif self.quantity < 100:
                    refresh_frequency = 30
                elif self.quantity < 200:
                    refresh_frequency = 60

        return self.updated + timedelta(minutes=refresh_frequency)

    @classmethod
    def from_webstore_to_dict(cls, webstore_data):
        """
        Takes the JSON blob returned by the webstore and converts it into a dictionary matching
        the structure of the ORM object
        """
        as_dict = {}
        as_dict["handle"] = webstore_data["handle"]
        as_dict["type"] = webstore_data["type"]
        as_dict["tagstring"] = webstore_data["tags"]

        if len(webstore_data.get("variants", [])) == 0:
            log.warning(
                "No variant information is available for '{self.title}', creating entry with partial data"
            )
            as_dict["sku"] = webstore_data.get("sku")
            as_dict["name"] = webstore_data.get("title")
            as_dict["price"] = webstore_data.get("price")
            as_dict["available"] = webstore_data.get("available")
        else:
            if len(webstore_data["variants"]) > 1:
                log.warning(
                    "More than one variant is available for '{self.title}', creating entry with first variant"
                )

            variant = webstore_data["variants"][0]

            as_dict["sku"] = variant.get("sku")
            as_dict["name"] = variant.get("name")
            as_dict["price"] = variant.get("price")
            as_dict["available"] = variant.get("available")
            as_dict["quantity"] = variant.get("inventory_quantity")
            as_dict["weight"] = variant.get("weight")

        return as_dict

    @classmethod
    def from_webstore(cls, webstore_data):
        return cls(**cls.from_webstore_to_dict(webstore_data))

    @classmethod
    def from_handle(cls, handle):
        return Product.from_webstore(Webstore.get_product(handle))


class Products(DatabaseTable):
    orm = Product

    def refresh(self, force=False):
        handles = self.refresh_handles(force)
        products = self.refresh_products(handles, force)
        return products

    def refresh_handles(self, force=False):
        if force:
            return Webstore.get_product_handles()

    def refresh_products(self, handles, force=False):
        """
        Refresh the product information for the given handles.
        If the handle does not exist in the database, data will be fetched from the webstore and added to the database.
        If force is enabled, all entries in the database will be refreshed.
        If neither, the object will determine whether it is ready to be refreshed based on the refreshable attribute.
        :param handles:
        :type handles:
        :param force:
        :type force:
        :return:
        :rtype:
        """
        handles = handles or self.keys()
        products = []

        for handle in handles:
            log.debug(f"Checking if refreshable: {handle}")
            product = self.primary(handle)

            if product is None:
                log.debug(f"No record for {handle}, creating a new record")
                # Product is new
                product = Product.from_handle(handle)
                product.save()
                products.append(product)
            elif force or product.refreshable:
                if force:
                    log.info(f"Forcing refresh of product: {product}")
                else:
                    log.debug(f"Refreshing product {product} due to timer")

                product.refresh(force)
                products.append(product)
            else:
                log.info(f"Skipping product because it is not eligible for a refresh: {product}")

        return products

    def painted(self):
        return self.tagged("painted")

    def unpainted(self):
        return self.tagged("unpainted")


class Set(DatabaseEntry, EntryORM):
    __tablename__ = "set"
    __primary__ = "sku"
    default_dataset = "main"
    dataset = Column(String, default=default_dataset)
    sku = Column(String, primary_key=True)
    name = Column(String)
    img = Column(String)
    tagstring = Column(String)

    @property
    def partlists(self):
        return PartLists.filter(PartList.set == self.sku).all()

    @property
    def products(self):
        return Products.filter(Product.sku.startswith(self.sku)).all()

    @property
    def pieces(self):
        pieces = [part.piece for part in self.partlists]
        return Pieces.filter_many(Piece.sku, pieces)


class Sets(DatabaseTable):
    orm = Set
    remap = {
        "sku": "value",
        "name": "text",
        "img": "img",
        "tagstring": "tag",
    }

    def refresh(self):
        """
        Contacts the catalog to pull down the latest sets list.
        Injests them into Set objects and saves them to the database.
        Returns the list of Set objects for convenience.
        """
        catalog_data = Catalog.get_data()
        log.debug(f"Found {len(json.dumps(catalog_data))} bytes in catalog data")
        entries = catalog_data["props"]["data_hints"]
        log.debug(f"Found {len(entries)} total entries in catalog data")
        set_entries = [entry for entry in entries if "set_sku" not in entry.keys()]
        log.debug(f"Found {len(set_entries)} set entries in catalog data")

        sets = []
        for set_entry in set_entries:
            remapped = {k: set_entry[v] for k, v in self.remap.items()}
            new_set = Set(**remapped)
            sets.append(new_set)
            new_set.save()

        return sets


class PartList(DatabaseEntry, EntryORM):
    __tablename__ = "partlist"
    __primary__ = "id"
    default_dataset = "main"
    id = Column(Integer, primary_key=True)
    set = Column(String, ForeignKey("set.sku"))
    piece = Column(String, ForeignKey("pieces.sku"))
    quantity = Column(Integer)

    def __repr__(self):
        return f"{self.__class__.__name__} <{self.quantity} {self.piece} in {self.set}>"

    def __str__(self):
        return f"{self.__class__.__name__} <{self.quantity} {self.piece} in {self.set}>"


class PartLists(DatabaseTable):
    orm = PartList
    remap = {
        "set": {"set": "value", "piece": "piece_sku", "quantity": "piece_quantity"},
        "piece": {"piece": "value", "set": "set_sku", "quantity": "piece_quantity"},
    }

    def refresh(self):
        """
        Contacts the catalog to pull down the latest sets list.
        Reads the quantity of pieces
        Returns the list of PartList objects for convenience.
        """
        catalog_data = Catalog.get_data()
        log.debug(f"Found {len(json.dumps(catalog_data))} bytes in catalog data")
        entries = catalog_data["props"]["data_hints"]
        log.debug(f"Found {len(entries)} total entries in catalog data")
        set_entries = [entry for entry in entries if "set_sku" not in entry.keys()]
        log.debug(f"Found {len(set_entries)} set entries in catalog data")
        piece_entries = [entry for entry in entries if "piece_sku" not in entry.keys()]
        log.debug(f"Found {len(piece_entries)} piece entries in catalog data")

        partlists = []
        for piece in piece_entries:
            remapped = {k: piece[v] for k, v in self.remap["piece"].items()}
            new_partlist = PartList(**remapped)
            partlists.append(new_partlist)
            new_partlist.save()

        return partlists


class Piece(DatabaseEntry, EntryORM):
    __tablename__ = "pieces"
    __primary__ = "sku"
    default_dataset = "main"
    dataset = Column(String, default=default_dataset)
    sku = Column(String, primary_key=True)
    name = Column(String)
    img = Column(String)
    tagstring = Column(String)

    @property
    def partlist(self):
        return PartLists.filter(PartList.piece == self.sku).all()

    @property
    def sets(self):
        sets = [part.set for part in self.partlist]
        return Sets.filter_many(Set.sku, sets)

    @property
    def products(self):
        products = []
        for set in self.sets:
            products.extend(set.products)

        return products


class Pieces(DatabaseTable):
    orm = Piece
    remap = {
        "sku": "value",
        "name": "text",
        "img": "img",
        "tagstring": "piece_tag",
    }

    def refresh(self):
        """
        Contacts the catalog to pull down the latest pieces list.
        Injests them into Piece objects and saves them to the database.
        Returns the list of Piece objects for convenience.
        """
        catalog_data = Catalog.get_data()
        log.debug(f"Found {len(json.dumps(catalog_data))} bytes in catalog data")
        entries = catalog_data["props"]["data_hints"]
        log.debug(f"Found {len(entries)} total entries in catalog data")
        piece_entries = [entry for entry in entries if "piece_sku" not in entry.keys()]
        log.debug(f"Found {len(piece_entries)} piece entries in catalog data")

        pieces = []
        for piece in piece_entries:
            remapped = {k: piece[v] for k, v in self.remap.items()}
            new_piece = Piece(**remapped)
            pieces.append(new_piece)
            new_piece.save()

        return pieces


class Point(DatabaseEntry, EntryORM):
    """An individual data point corresponding to an amount of inventory at a given time"""

    __tablename__ = "stock"
    __primary__ = "id"

    default_dataset = "main"
    dataset = Column(String, default=default_dataset)
    id = Column(Integer, primary_key=True)
    sku = Column(String)
    quantity = Column(Integer)
    timestamp = Column(DateTime, server_default=func.now())
    redundant = Column(Boolean)

    def __init__(self, sku, quantity, timestamp=None):
        self.sku = sku
        self.quantity = quantity
        self.timestamp = timestamp or datetime.now()
        self.redundant = False

        self.save()

    def __str__(self):
        return f"{self.__class__.__name__} <{self.sku}@{self.timestamp}>"


class Stock(DatabaseTable):
    orm = Point

    @classmethod
    def series(cls, *args, **kwargs):
        products = Products.filter(*args, **kwargs)
        skus = [product.sku for product in products]
        series = [Series(sku) for sku in skus]
        return series


class Series(DatabaseTable):
    orm = Point

    def __init__(self, sku):
        self.sku = sku

        super().__init__()

    def query(self):
        """Override the class method with an object specific one that filters the table by the object's SKU"""
        return (
            self.session()
            .query(self.orm)
            .filter(Point.sku == self.sku)
            .order_by(Point.timestamp.asc())
        )

    def all(self):
        return Series.all(self)

    @property
    def history(self):
        return self.all()

    def clean(self):
        points = self.history
        current = None

        for index, point in enumerate(points):
            # Try to find the next data point
            try:
                next = points[index + 1]
            except IndexError:
                # If we are on the last item, it's automatically important
                log.warning(f"{point} at index {index} is the last item")
                continue

            if current is None or point.quantity != current:
                # If the quantity changed, set the new reference point
                log.info(f"{point} is different from the preceding series")
                current = point.quantity

            elif point.quantity != next.quantity:
                # If the quantity didn't change, but it's the last in the series, keep it
                log.info(f"{point} is the last in the series")

            else:
                # If the quantity hasn't changed and it isn't the last in the series, mark it as redudnant
                log.info(f"{point} is a mid-series value, marking as redundant")
                point.redundant = True
                point.save()

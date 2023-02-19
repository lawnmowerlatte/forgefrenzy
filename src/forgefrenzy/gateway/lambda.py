import json

from sqlalchemy import inspect
import aws_lambda_wsgi
from flask import Flask, Response

from forgefrenzy import *
from forgefrenzy.db import dfdb, DatabaseEntry

app = Flask(__name__)
admin = Flask("admin")


@app.route("/ff/", methods=["GET"])
def root():
    data = {"ok": True}
    return successful_response(data)


@app.route("/ff/version", methods=["GET"])
def version():
    data = {
        "version": forgefrenzy_version,
    }
    return successful_response(data)


@app.route("/ff/db", methods=["GET"])
def db():
    inspector = inspect(dfdb.engine)

    data = {
        "database": dfdb.db,
        "dialect": dfdb.engine.dialect.__class__.__name__,
        "schemas": {
            schema: inspector.get_table_names(schema=schema)
            for schema in inspector.get_schema_names()
        },
    }
    return successful_response(data)


@app.route("/ff/product/<handle>", methods=["GET"])
def get_product(handle):
    data = Products.primary(handle).as_dict
    return successful_response(data)


@app.route("/ff/stock", methods=["GET"])
def get_stock():
    data = {value.handle: value.quantity for value in Products.all()}
    return successful_response(data)


@app.route("/ff/partlist", methods=["GET"])
def get_partlist():
    data = [pl.as_dict for pl in PartLists.all()]
    return successful_response(data)


@app.route("/ff/set/<sku>", methods=["GET"])
def get_set(sku):
    data = Sets.primary(sku).as_dict
    return successful_response(data)


@app.route("/ff/set/<sku>/pieces", methods=["GET"])
def get_pieces_in_set(sku):
    data = [piece.as_dict for piece in Sets.primary(sku).pieces]
    return successful_response(data)


@app.route("/ff/set/<sku>/products", methods=["GET"])
def get_products_of_set(sku):
    data = [product.as_dict for product in Sets.primary(sku).products]
    return successful_response(data)


@app.route("/ff/piece/<sku>", methods=["GET"])
def get_piece(sku):
    data = Pieces.primary(sku).as_dict
    return successful_response(data)


@app.route("/ff/piece/<sku>/products", methods=["GET"])
def get_products_with_piece(sku):
    data = Pieces.primary(sku)
    return successful_response(data)


@app.route("/ff/piece/<sku>/sets", methods=["GET"])
def get_sets_with_piece(sku):
    data = Pieces.primary(sku).sets
    return successful_response(data)


def sanitize_data(data_to_sanitize):
    if isinstance(data_to_sanitize, list):
        return [sanitize_data(item) for item in data_to_sanitize]
    if isinstance(data_to_sanitize, dict):
        return {key: sanitize_data(value) for key, value in data_to_sanitize.items()}
    if (
        isinstance(data_to_sanitize, str)
        or isinstance(data_to_sanitize, int)
        or isinstance(data_to_sanitize, float)
        or isinstance(data_to_sanitize, bool)
    ):
        return data_to_sanitize
    if issubclass(data_to_sanitize.__class__, DatabaseEntry):
        return sanitize_data(data_to_sanitize.as_dict)

    return str(data_to_sanitize)


def successful_response(data):
    data = sanitize_data(data)

    try:
        data_as_json = (json.dumps(data, indent=4, sort_keys=True),)
    except json.JSONDecodeError as e:
        return Response(
            {
                "raw": data,
                "message": "The data could not be converted to JSON",
                "exception": str(e),
                "class": e.__class__.__name__,
                "traceback": e.__traceback__,
            },
            206,
            {"Content-Type": "application/json"},
        )

    return Response(data_as_json, 200, {"Content-Type": "application/json"})


def handler(event, context):
    """Processes output and exceptions and generates a valid API response"""
    try:
        response = aws_lambda_wsgi.response(app, event, context)
        print(response)
        return response
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "message": "The handler raised an exception",
                    "exception": str(e),
                    "class": e.__class__.__name__,
                    "traceback": e.__traceback__,
                }
            ),
        }


def admin(event, context):
    """Processes output and exceptions and generates a valid API response"""
    try:
        response = aws_lambda_wsgi.response(admin, event, context)
        print(response)
        return response
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "message": "The handler raised an exception",
                    "exception": str(e),
                    "class": e.__class__.__name__,
                    "traceback": e.__traceback__,
                }
            ),
        }


if __name__ == "__main__":
    app.run(debug=True, port=8000)
    # admin.run(debug=True, port=8000)

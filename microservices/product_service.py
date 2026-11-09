import os
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

if __package__:
    from .database import connect_database
    from .service_discovery import register_service
else:
    from database import connect_database
    from service_discovery import register_service

app = Flask(__name__)
CORS(app)

DATABASE_PATH = Path(os.environ.get(
    "PRODUCTS_DATABASE", Path(__file__).resolve().with_name("products.db")
))
SERVICE_PORT = int(os.environ.get("PRODUCTS_PORT", "5032"))
SERVICE_URL = os.environ.get(
    "PRODUCTS_SERVICE_URL", f"http://127.0.0.1:{SERVICE_PORT}"
).rstrip("/")

INITIAL_PRODUCTS = [
    (1, "Laptop", 999.99, 10),
    (2, "Mouse", 29.99, 50),
    (3, "Keyboard", 79.99, 30)
]


def initialize_database():
    with connect_database(DATABASE_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL
            )
        """)
        connection.executemany(
            """INSERT OR IGNORE INTO products (id, name, price, stock)
               VALUES (?, ?, ?, ?)""",
            INITIAL_PRODUCTS
        )


def get_product_object(product_id):
    with connect_database(DATABASE_PATH) as connection:
        product = connection.execute(
            "SELECT id, name, price, stock FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()
    return dict(product) if product is not None else None


@app.route('/health', methods=['GET'])
def get_health():
    return jsonify({"status": "All good"}), 200


@app.route('/', methods=['GET'])
def get_products():
    with connect_database(DATABASE_PATH) as connection:
        products = connection.execute(
            "SELECT id, name, price, stock FROM products ORDER BY id"
        ).fetchall()
    return jsonify([dict(product) for product in products]), 200


@app.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = get_product_object(product_id)
    if product is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product), 200


@app.route('/<int:product_id>/stock', methods=['PUT'])
def update_product_stock(product_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid data"}), 400

    stock = data.get('stock')
    if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
        return jsonify({"error": "Stock must be a non-negative integer"}), 400

    with connect_database(DATABASE_PATH) as connection:
        cursor = connection.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (stock, product_id)
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "Product not found"}), 404
        product = connection.execute(
            "SELECT id, name, price, stock FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

    return jsonify(dict(product)), 200


if __name__ == '__main__':
    initialize_database()
    register_service("products", SERVICE_URL)
    app.run(host="0.0.0.0", port=SERVICE_PORT, debug=True, use_reloader=False)

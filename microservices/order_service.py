from datetime import datetime
import os
from pathlib import Path

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

if __package__:
    from .database import connect_database
    from .service_discovery import discover_service_url, register_service
else:
    from database import connect_database
    from service_discovery import discover_service_url, register_service

app = Flask(__name__)
CORS(app)

DATABASE_PATH = Path(os.environ.get(
    "ORDERS_DATABASE", Path(__file__).resolve().with_name("orders.db")
))
SERVICE_PORT = int(os.environ.get("ORDERS_PORT", "5033"))
SERVICE_URL = os.environ.get(
    "ORDERS_SERVICE_URL", f"http://127.0.0.1:{SERVICE_PORT}"
).rstrip("/")


def initialize_database():
    with connect_database(DATABASE_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                total REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


@app.route('/health', methods=['GET'])
def get_health():
    return jsonify({"status": "All good"}), 200

@app.route('/', methods=['POST'])
@app.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    user_id = data.get("user_id")
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)
    if not _is_positive_integer(user_id):
        return jsonify({"error": "user_id must be a positive integer"}), 400
    if not _is_positive_integer(product_id):
        return jsonify({"error": "product_id must be a positive integer"}), 400
    if not _is_positive_integer(quantity):
        return jsonify({"error": "quantity must be a positive integer"}), 400

    try:
        if get_user_object(user_id) is None:
            return jsonify({"error": "User not found"}), 404

        product = get_product_object(product_id)
        if product is None:
            return jsonify({"error": "Product not found"}), 404

        stock = product.get("stock")
        price = product.get("price")
        if (
            isinstance(stock, bool)
            or not isinstance(stock, int)
            or isinstance(price, bool)
            or not isinstance(price, (int, float))
        ):
            return jsonify({"error": "Product service returned invalid product data"}), 502

        if stock < quantity:
            return jsonify({"error": "Insufficient stock"}), 400

        updated_product = update_stock(product_id, stock - quantity)
        if updated_product is None:
            return jsonify({"error": "Product not found"}), 404
        order_data = {
            "user_id": user_id,
            "product_id": product_id,
            "quantity": quantity,
            "total": price * quantity,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        with connect_database(DATABASE_PATH) as connection:
            cursor = connection.execute(
                """INSERT INTO orders
                   (user_id, product_id, quantity, total, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    order_data["user_id"],
                    order_data["product_id"],
                    order_data["quantity"],
                    order_data["total"],
                    order_data["status"],
                    order_data["created_at"]
                )
            )
            order_data["id"] = cursor.lastrowid
    except requests.exceptions.Timeout:
        return jsonify({"error": "A dependent service timed out"}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "A dependent service is unavailable"}), 503
    except (requests.exceptions.RequestException, ValueError):
        return jsonify({"error": "A dependent service returned an invalid response"}), 502

    return jsonify(order_data), 201

@app.route('/<int:order_id>', methods=['GET'])
@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    with connect_database(DATABASE_PATH) as connection:
        order = connection.execute(
            """SELECT id, user_id, product_id, quantity, total, status, created_at
               FROM orders WHERE id = ?""",
            (order_id,)
        ).fetchone()
    if order is None:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(dict(order)), 200

def _is_positive_integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0

def _get_service_object(url):
    response = requests.get(url, timeout=5)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError("Service response must be a JSON object")
    return result

def get_user_object(user_id):
    base_url = discover_service_url("users")
    return _get_service_object(f"{base_url}/users/{user_id}")

def get_product_object(product_id):
    base_url = discover_service_url("products")
    return _get_service_object(f"{base_url}/{product_id}")

def update_stock(product_id, stock):
    base_url = discover_service_url("products")
    response = requests.put(
        f"{base_url}/{product_id}/stock",
        json={"stock": stock},
        timeout=5
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError("Service response must be a JSON object")
    return result

if __name__ == '__main__':
    initialize_database()
    register_service("orders", SERVICE_URL)
    app.run(host="0.0.0.0", port=SERVICE_PORT, debug=True, use_reloader=False)

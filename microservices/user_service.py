import os
from pathlib import Path
from typing import Any

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
    "USERS_DATABASE", Path(__file__).resolve().with_name("users.db")
))
SERVICE_PORT = int(os.environ.get("USERS_PORT", "5031"))
SERVICE_URL = os.environ.get(
    "USERS_SERVICE_URL", f"http://127.0.0.1:{SERVICE_PORT}"
).rstrip("/")


def initialize_database():
    with connect_database(DATABASE_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL
            )
        """)
        connection.executemany(
            "INSERT OR IGNORE INTO users (id, name, email) VALUES (?, ?, ?)",
            [
                (1, "Alice", "alice@example.com"),
                (2, "Bob", "bob@example.com")
            ]
        )


def get_user_object(user_id: int) -> Any:
    with connect_database(DATABASE_PATH) as connection:
        user = connection.execute(
            "SELECT id, name, email FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
    return dict(user) if user is not None else None


@app.route('/health', methods=['GET'])
def get_health():
    return jsonify({"status": "All good"}), 200


@app.route('/users', methods=['GET'])
@app.route('/', methods=['GET'])
def get_users():
    with connect_database(DATABASE_PATH) as connection:
        users = connection.execute(
            "SELECT id, name, email FROM users ORDER BY id"
        ).fetchall()
    return jsonify([dict(user) for user in users]), 200


@app.route('/users', methods=['POST'])
@app.route('/', methods=['POST'])
def create_user():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    name = data.get("name")
    email = data.get("email")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "Name is required"}), 400
    if not isinstance(email, str) or not email.strip():
        return jsonify({"error": "Email is required"}), 400

    with connect_database(DATABASE_PATH) as connection:
        cursor = connection.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            (name.strip(), email.strip())
        )
        user = {
            "id": cursor.lastrowid,
            "name": name.strip(),
            "email": email.strip()
        }
    return jsonify(user), 201


@app.route('/users/<int:user_id>', methods=['GET'])
@app.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = get_user_object(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user), 200


if __name__ == '__main__':
    initialize_database()
    register_service("users", SERVICE_URL)
    app.run(host="0.0.0.0", port=SERVICE_PORT, debug=True, use_reloader=False)

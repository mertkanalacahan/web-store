from flask import Flask, jsonify, request

app = Flask(__name__)
services = {}


@app.route('/health', methods=['GET'])
def get_health():
    return jsonify({"status": "healthy", "service": "service-registry"}), 200


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    name = data.get("name")
    url = data.get("url")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "Service name is required"}), 400
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return jsonify({"error": "A valid HTTP service URL is required"}), 400

    services[name.strip()] = url.rstrip("/")
    return jsonify({"status": "registered"}), 201


@app.route('/discover/<service_name>', methods=['GET'])
def discover(service_name):
    url = services.get(service_name)
    if url is None:
        return jsonify({"error": "Service not found"}), 404
    return jsonify({"url": url}), 200


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5100, debug=True, use_reloader=False)

# api_gateway.py
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
import requests

if __package__:
    from .service_discovery import discover_service_url
else:
    from service_discovery import discover_service_url

app = Flask(__name__)

SERVICE_NAMES = ('users', 'products', 'orders')
STATIC_DIRECTORY = Path(__file__).resolve().parent / "static"

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the gateway itself"""
    return jsonify({"status": "healthy", "service": "api-gateway"}), 200

@app.route('/<service>/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def gateway(service, path):
    """
    Main gateway routing function.
    Routes requests to the appropriate microservice based on the service name.
    """
    # Check if the service exists
    if service not in SERVICE_NAMES:
        return jsonify({
            "error": "Service not found",
            "available_services": list(SERVICE_NAMES)
        }), 404
    
    try:
        service_url = discover_service_url(service)
    except requests.exceptions.Timeout:
        return jsonify({"error": "Service registry timeout"}), 504
    except requests.exceptions.RequestException:
        return jsonify({"error": "Service registry unavailable"}), 503
    except ValueError:
        return jsonify({"error": "Service registry returned an invalid URL"}), 502

    target_url = f"{service_url}/{path}"
    
    # Prepare request data
    headers = {key: value for key, value in request.headers if key != 'Host'}
    params = request.args
    json_data = request.get_json(silent=True)
    
    # Add request tracing header (useful for debugging)
    if 'X-Request-ID' not in headers:
        import uuid
        headers['X-Request-ID'] = str(uuid.uuid4())
    
    try:
        # Forward the request to the appropriate service
        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=params,
            json=json_data,
            timeout=10  # 10 second timeout
        )
        
        # Return the response from the service
        return response.content, response.status_code, dict(response.headers)
    
    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Service timeout",
            "service": service,
            "message": f"{service} service did not respond in time"
        }), 504
    
    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "Service unavailable",
            "service": service,
            "message": f"Cannot connect to {service} service at {service_url}"
        }), 503
    
    except Exception as e:
        return jsonify({
            "error": "Gateway error",
            "message": str(e)
        }), 500

@app.route('/<service>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def gateway_root(service):
    """
    Handle requests to service root (e.g., /users, /products, /orders)
    """
    return gateway(service, '')

@app.route('/status', methods=['GET'])
def status():
    """
    Check the health status of all registered services
    """
    service_status = {}
    
    for service_name in SERVICE_NAMES:
        try:
            service_url = discover_service_url(service_name)
            response = requests.get(f"{service_url}/health", timeout=2)
            service_status[service_name] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "url": service_url,
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
        except requests.exceptions.Timeout as e:
            service_status[service_name] = {
                "status": "unavailable",
                "error": str(e)
            }
        except requests.exceptions.RequestException as e:
            service_status[service_name] = {
                "status": "unavailable",
                "error": str(e)
            }
        except ValueError as e:
            service_status[service_name] = {
                "status": "unavailable",
                "error": str(e)
            }
    
    all_healthy = all(s["status"] == "healthy" for s in service_status.values())
    
    return jsonify({
        "gateway": "healthy",
        "services": service_status,
        "overall_status": "healthy" if all_healthy else "degraded"
    }), 200 if all_healthy else 503
    
# Serve the dashboard page
@app.route('/')
def dashboard():
    return send_from_directory(STATIC_DIRECTORY, 'index.html')

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Not found",
        "message": "The requested endpoint does not exist",
        "available_services": list(SERVICE_NAMES)
    }), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "error": "Internal server error",
        "message": str(e)
    }), 500

if __name__ == '__main__':
    print("=" * 50)
    print("API Gateway starting...")
    print(f"Gateway URL: http://127.0.0.1:5030")
    print("=" * 50)
    print("Registered services:")
    for service in SERVICE_NAMES:
        print(f"  /{service}/* -> service discovered from registry")
    print("=" * 50)
    print("Additional endpoints:")
    print("  GET /health  - Gateway health check")
    print("  GET /status  - All services status")
    print("=" * 50)
    
    app.run(port=5030, debug=True)
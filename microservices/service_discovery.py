import os

import requests

SERVICE_REGISTRY_URL = os.environ.get(
    "SERVICE_REGISTRY_URL", "http://127.0.0.1:5100"
).rstrip("/")


def register_service(name, url):
    response = requests.post(
        f"{SERVICE_REGISTRY_URL}/register",
        json={"name": name, "url": url},
        timeout=5
    )
    response.raise_for_status()


def discover_service_url(name):
    response = requests.get(
        f"{SERVICE_REGISTRY_URL}/discover/{name}",
        timeout=5
    )
    response.raise_for_status()
    data = response.json()
    url = data.get("url") if isinstance(data, dict) else None
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise ValueError(f"Registry returned an invalid URL for service '{name}'")
    return url.rstrip("/")

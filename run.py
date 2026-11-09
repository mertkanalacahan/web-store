import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import venv


ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
SERVICES = (
    ("service registry", "microservices.service_registry", "http://127.0.0.1:5100/health"),
    ("user service", "microservices.user_service", "http://127.0.0.1:5031/health"),
    ("product service", "microservices.product_service", "http://127.0.0.1:5032/health"),
    ("order service", "microservices.order_service", "http://127.0.0.1:5033/health"),
    ("API gateway", "microservices.api_gateway", "http://127.0.0.1:5030/health"),
)
STARTUP_TIMEOUT_SECONDS = 20


def venv_python():
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def wait_for_service(process, name, health_url):
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        exit_code = process.poll()
        if exit_code is not None:
            raise RuntimeError(f"{name} exited during startup (exit code {exit_code}).")

        try:
            with urllib.request.urlopen(health_url, timeout=1) as response:
                if response.status == 200:
                    print(f"{name} is ready: {health_url}", flush=True)
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.25)

    raise RuntimeError(f"{name} did not become healthy within {STARTUP_TIMEOUT_SECONDS} seconds.")


def stop_services(processes):
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()

    for process in reversed(processes):
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main():
    python = venv_python()
    processes = []
    return_code = 0

    try:
        if not python.is_file():
            print("Creating virtual environment...", flush=True)
            venv.EnvBuilder(with_pip=True).create(VENV_DIR)

        print("Checking dependencies...", flush=True)
        subprocess.run(
            [str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(REQUIREMENTS)],
            cwd=ROOT,
            check=True,
        )

        environment = os.environ.copy()
        environment["PYTHONUNBUFFERED"] = "1"

        for name, module, health_url in SERVICES:
            print(f"Starting {name}...", flush=True)
            process = subprocess.Popen(
                [str(python), "-m", module],
                cwd=ROOT,
                env=environment,
            )
            processes.append(process)
            wait_for_service(process, name, health_url)

        app_url = "http://127.0.0.1:5030"
        print(f"\nWeb store is running at {app_url}", flush=True)
        print("Press Ctrl+C to stop all services.", flush=True)

        while True:
            for process, (name, _, _) in zip(processes, SERVICES):
                exit_code = process.poll()
                if exit_code is not None:
                    raise RuntimeError(f"{name} stopped unexpectedly (exit code {exit_code}).")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping services...", flush=True)
    except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
        print(f"\nUnable to run the web store: {error}", file=sys.stderr, flush=True)
        return_code = 1
    finally:
        stop_services(processes)

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())

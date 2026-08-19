"""Local dev runner: starts FastAPI (port 8000) and Streamlit (port 10000 by
default, or $PORT) and keeps them alive. The Docker image uses supervisord
instead, which auto-restarts crashed services."""
import os
import subprocess
import sys
import time
import urllib.request

BACKEND_PORT = 8000


def _wait_for_backend(timeout: int = 60) -> None:
    url = f"http://localhost:{BACKEND_PORT}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    print(f"Backend healthy on port {BACKEND_PORT}.")
                    return
        except Exception:
            pass
        time.sleep(1)
    print(f"Warning: backend did not become healthy within {timeout}s. Continuing anyway.")


def start_services() -> None:
    frontend_port = os.getenv("PORT", "10000")

    print(f"Starting FastAPI backend on port {BACKEND_PORT}...")
    backend_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(BACKEND_PORT),
        ]
    )

    _wait_for_backend()

    print(f"Starting Streamlit frontend on port {frontend_port}...")
    frontend_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.port",
            frontend_port,
            "--server.address",
            "0.0.0.0",
        ]
    )

    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("Shutting down services...")
        backend_process.terminate()
        frontend_process.terminate()


if __name__ == "__main__":
    start_services()
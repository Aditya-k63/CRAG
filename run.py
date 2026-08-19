"""Local dev runner: serves the FastAPI backend, which also hosts the chat UI."""
import os
import sys
import threading
import webbrowser

import uvicorn

DEFAULT_PORT = 8000


def _open_browser(port: int) -> None:
    url = f"http://localhost:{port}"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()


def main() -> None:
    port = int(os.getenv("PORT", str(DEFAULT_PORT)))
    _open_browser(port)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
    )


if __name__ == "__main__":
    sys.exit(main())
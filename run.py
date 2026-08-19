"""Local dev runner: serves the FastAPI backend, which also hosts the chat UI."""
import os
import sys

import uvicorn

DEFAULT_PORT = 8000


def main() -> None:
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", str(DEFAULT_PORT))),
    )


if __name__ == "__main__":
    sys.exit(main())

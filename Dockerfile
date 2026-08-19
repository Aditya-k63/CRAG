FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Backend serves the chat UI and the API (Render exposes $PORT, default 8000)
EXPOSE 8000

CMD ["/bin/sh", "start.sh"]
FROM python:3.11-slim

WORKDIR /app

# Install system essentials for source compilation
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose Render's default routing web port
EXPOSE 10000

CMD ["python", "run.py"]
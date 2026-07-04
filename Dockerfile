# Slim Python base keeps the image small; no compile step is needed.
FROM python:3.12-slim

WORKDIR /app

# Install deps first so this layer caches across code-only changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webkong.py bot.py ./

# The optional health server listens here; only needed if the host healthchecks.
EXPOSE 3000

CMD ["python", "bot.py"]

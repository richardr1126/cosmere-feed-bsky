FROM python:3.12.8-slim-bookworm

WORKDIR /usr/src/app/

# Copy package files and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code except .dockerignore files
COPY . .

EXPOSE 8000

# Runs when the container is started
CMD ["gunicorn", "web.app:app", "--bind", "0.0.0.0:8000", "--workers", "1"]

FROM python:3.12.8-slim-bookworm

WORKDIR /usr/src/app/

# Copy the rest of the application code
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Runs when the container is started
CMD ["python", "start_stream.py"]

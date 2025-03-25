FROM python:3.12.8-slim-bookworm

WORKDIR /usr/src/app/

# Install pip requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Runs when the container is started
CMD ["python", "start_stream.py"]

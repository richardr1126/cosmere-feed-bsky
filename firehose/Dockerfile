FROM python:3.12.8-slim-bookworm

# create a volume for the sqlite database, so that it persists between container restarts
# need persistent storage attached to server
VOLUME /var/data/
WORKDIR /usr/src/app/

# Copy the rest of the application code
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Runs when the container is started
CMD ["python", "start_stream.py"]

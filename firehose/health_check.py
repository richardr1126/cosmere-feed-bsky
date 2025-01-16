# health_check.py
from data_stream import is_healthy
from utils.logger import logger

if __name__ == "__main__":
    if is_healthy():
        exit(0)  # Healthy
    else:
        logger.error("Health check failed")
        exit(1)  # Unhealthy
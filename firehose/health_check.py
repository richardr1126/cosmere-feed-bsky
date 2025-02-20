# health_check.py
from utils.logger import logger
from datetime import datetime, timedelta, timezone
from database import db, SubscriptionState

def is_healthy():
    state = None
    with db.connection_context():
        with db.atomic():
            state = SubscriptionState.get_or_none()

    if not state or not state.last_indexed_at:
        return False
    
    # Check if the firehose last log is within the last 15 minutes
    # If it is, the health check is considered healthy
    return (datetime.now(timezone.utc) - state.last_indexed_at) < timedelta(minutes=15)

if __name__ == "__main__":
    if is_healthy():
        exit(0)  # Healthy
    else:
        logger.error("Health check failed")
        exit(1)  # Unhealthy
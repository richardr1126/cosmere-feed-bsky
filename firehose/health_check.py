# health_check.py
from utils.logger import logger
from datetime import datetime, timedelta, timezone
from database import db, SubscriptionState

def is_healthy():
    with db.connection_context():
        state = SubscriptionState.get_or_none()
        if not state or not state.last_indexed_at:
            return False
        return (datetime.now(timezone.utc) - state.last_indexed_at) < timedelta(minutes=5)

if __name__ == "__main__":
    if is_healthy():
        exit(0)  # Healthy
    else:
        logger.error("Health check failed")
        exit(1)  # Unhealthy
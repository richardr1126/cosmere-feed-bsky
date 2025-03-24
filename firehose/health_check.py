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
    
    # Both timestamps should be naive for comparison since PostgreSQL stores naive UTC
    current_time = datetime.utcnow()
    last_indexed = state.last_indexed_at
    
    time_difference = current_time - last_indexed
    logger.info(f"Current time (UTC): {current_time}")
    logger.info(f"Last indexed (UTC): {last_indexed}")
    logger.info(f"Time difference: {time_difference}")
    
    return time_difference < timedelta(minutes=15)

if __name__ == "__main__":
    if is_healthy():
        exit(0)  # Healthy
    else:
        logger.error("Health check failed")
        exit(1)  # Unhealthy
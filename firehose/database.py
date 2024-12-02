from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
import shutil
import signal
import sys

from utils.logger import logger  # Ensure this is correctly implemented
from utils.config import DEV_MODE, HANDLE, PASSWORD  # Ensure these are set in your config
import peewee
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from atproto import Client, IdResolver, SessionEvent, Session, exceptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
file = '/var/data/new_cosmere_feed.db' if not DEV_MODE else 'new_cosmere_feed.db'
db = peewee.SqliteDatabase(file, timeout=30, pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 128,
    'busy_timeout': 30000
})

# Database Models
class BaseModel(peewee.Model):
    class Meta:
        database = db

class Post(BaseModel):
    uri = peewee.CharField(index=True)
    cid = peewee.CharField()
    reply_parent = peewee.CharField(null=True, default=None)
    reply_root = peewee.CharField(null=True, default=None)
    indexed_at = peewee.DateTimeField(default=datetime.now(timezone.utc), index=True)
    author = peewee.CharField(null=True, default=None, index=True)
    interactions = peewee.BigIntegerField(default=0, index=True)

class SubscriptionState(BaseModel):
    service = peewee.CharField(unique=True)
    cursor = peewee.BigIntegerField()

class SessionState(BaseModel):
    service = peewee.CharField(unique=True)
    session_string = peewee.TextField(null=True)

# SQLite database management functions
def backup_database():
    try:
        db.close()
        backup_file = file.replace('.db', '_backup.db')
        shutil.copy(file, backup_file)
        logger.info(f"Database backup created at {backup_file}.")
        db.connect()
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")

def clear_old_posts(clear_days: int):
    try:
        cutoff_date = datetime.now() - timedelta(days=clear_days)
        query = Post.delete().where(Post.indexed_at < cutoff_date)
        num_deleted = query.execute()
        logger.info(f"Deleted {num_deleted} posts older than {cutoff_date}.")
    except peewee.PeeweeException as e:
        logger.error(f"An error occurred while deleting old posts: {e}")

def vacuum_database():
    try:
        db.execute_sql('VACUUM;')
        logger.info("Database vacuumed to reclaim space.")
    except peewee.PeeweeException as e:
        logger.error(f"An error occurred during vacuuming: {e}")

def cleanup_db(clear_days: int = 3):
    backup_database()
    clear_old_posts(clear_days)
    vacuum_database()

# Hydration Function with Rate Limit and Expired Token Handling
def hydrate_posts_with_interactions(client: Client, batch_size: int = 25):
    try:
        # Retrieve all post URIs from the database
        posts = Post.select(Post.uri, Post.interactions)
        uris = [post.uri for post in posts]

        if not uris:
            logger.info("No posts found in the database to hydrate.")
            return

        # Process URIs in batches
        for i in range(0, len(uris), batch_size):
            batch_uris = uris[i:i + batch_size]
            try:
                # Fetch posts from the API
                fetched_posts = client.get_posts(uris=batch_uris)
                fetched_posts = fetched_posts['posts']

                for fetched_post in fetched_posts:
                    uri = fetched_post.uri
                    if not uri:
                        continue

                    # Extract interaction counts
                    like_count = fetched_post.like_count
                    reply_count = fetched_post.reply_count
                    repost_count = fetched_post.repost_count
                    indexed_at = fetched_post.indexed_at
                    #logger.info(f"Fetched post {fetched_post.author}")

                    # check indexed_at type
                    #logger.info(f"indexed_at type: {type(indexed_at)}")

                    try:
                        indexed_at = datetime.fromisoformat(indexed_at)
                    except Exception as e:
                        raise e

                    #logger.info(f"indexed_at type after: {type(indexed_at)}")

                    # Calculate time difference in hours
                    time_diff = datetime.now(timezone.utc) - indexed_at
                    time_diff_hours = time_diff.total_seconds() / 3600

                    # Calculate "What's Hot" score
                    # Formula: hot_score = interactions / ( (age_in_hours + 2) ** 1.5 )
                    # Adding 2 to avoid division by zero and to give a slight boost to newer posts
                    interactions_score = like_count + (reply_count * 2) + (repost_count * 3)
                    hot_score = interactions_score / ((time_diff_hours + 2) ** 1.5)
                    hot_score *= 100

                    # Update the Post record if the hot_score has changed
                    with db.atomic():
                        rows_updated = (
                            Post.update(interactions=hot_score)
                            .where(
                                (Post.uri == uri) &
                                (Post.interactions != hot_score)
                            )
                            .execute()
                        )
                        # Optional hydration below

                        #update indexed_at once
                        #Post.update(indexed_at=indexed_at).where(Post.uri == uri).execute()
                        #logger.info(f"indexed_at updated for post {uri} to {indexed_at}")

                        # delete posts from exluded dids if they were accidentally added in the db
                        # handles_to_exclude = ['flintds.bsky.social']
                        # if fetched_post.author.handle in handles_to_exclude:
                        #     Post.delete().where(Post.uri == uri).execute()
                        #     logger.info(f"Deleted post {uri} from excluded DID: {fetched_post.author}")

                    if rows_updated:
                        logger.info(f"Hydrated post {uri} with hot_score: {int(hot_score)}.")
                    else:
                        logger.info(f"No update needed for post {uri}; interactions unchanged.")

            except exceptions.AtProtocolError as api_err:
                if hasattr(api_err, 'response'):
                    status_code = api_err.response.status_code
                    if status_code == 429:
                        # Rate limited during hydration
                        reset_timestamp = api_err.response.headers.get('RateLimit-Reset')
                        if reset_timestamp:
                            reset_time = datetime.fromtimestamp(int(reset_timestamp.total_seconds()), timezone.utc)
                        else:
                            reset_time = datetime.now(timezone.utc) + timedelta(seconds=60)  # Default to 60 seconds
                        logger.warning(f"Rate limit exceeded during hydration. Next attempt at {reset_time} UTC.")
                        reschedule_hydration(reset_time, scheduler)
                        return  # Exit to prevent further API calls
                    elif status_code == 400:
                        # Handle other specific status codes if necessary
                        logger.error(f"Hydration failed with status 400. Content: {api_err.response.content}")
                        # Optionally, implement additional error handling here
                else:
                    logger.error(f"API error while fetching posts without response: {api_err}")
            except Exception as e:
                logger.error(f"Unexpected error while hydrating posts: {e}")

    except Exception as e:
        logger.error(f"Error in hydration process: {e}")

# Rescheduling Functions
def reschedule_hydration(reset_time: datetime, scheduler: BackgroundScheduler):
    # Pause the interval hydrate_posts job to prevent further attempts
    try:
        scheduler.pause_job('hydrate_posts_interval')
        logger.info("Paused the interval hydrate_posts job due to rate limiting.")
    except JobLookupError:
        logger.info("No interval hydrate_posts job to pause.")

    # Schedule a one-time hydrate_posts job at reset_time
    try:
        scheduler.remove_job('hydrate_posts_once')
    except JobLookupError:
        pass  # No existing one-time job to remove

    # Initialize a new client instance for the scheduled job
    client = init_client()

    scheduler.add_job(
        hydrate_posts_with_interactions,
        trigger=DateTrigger(run_date=reset_time),
        args=[client],
        id='hydrate_posts_once',
        max_instances=1,
        replace_existing=True
    )
    logger.info(f"One-time hydrate_posts job scheduled to run at {reset_time} UTC.")

# Scheduler Initialization
def start_scheduler(client: Client, schedule_hydration: bool = False) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.start()
    logger.info("BackgroundScheduler instance created and started.")

    # Schedule cleanup_db to run daily at 8 AM UTC
    scheduler.add_job(
        cleanup_db,
        trigger='cron',
        hour=8,
        args=[3],
        id='cleanup_db',
        max_instances=1,
        replace_existing=True
    )
    logger.info("Scheduled daily cleanup_db job at 8 AM UTC.")

    if schedule_hydration:
        # Schedule hydrate_posts_with_interactions to run every 15 minutes
        scheduler.add_job(
            hydrate_posts_with_interactions,
            trigger=IntervalTrigger(minutes=20),
            args=[client],
            id='hydrate_posts_interval',
            max_instances=1,
            coalesce=True,  # If job is missed, run it immediately
            replace_existing=True
        )
        logger.info("Scheduled interval hydrate_posts_with_interactions job every 15 minutes.")

    # Add listener for job events
    scheduler.add_listener(lambda event: hydration_job_listener(event, scheduler), EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    logger.info("Added hydration_job_listener to the scheduler.")

    return scheduler

# Job Listener
def hydration_job_listener(event, scheduler: BackgroundScheduler):
    """
    Listener to detect when the one-time hydrate_posts job completes
    and take appropriate actions.
    """
    if event.job_id == 'hydrate_posts_once':
        if event.exception:
            logger.error("One-time hydrate_posts job failed.")
        else:
            logger.info("One-time hydrate_posts job completed successfully.")
            try:
                scheduler.resume_job('hydrate_posts_interval')
                logger.info("Resumed the interval hydrate_posts job after one-time hydration.")
            except JobLookupError:
                logger.error("Interval hydrate_posts job not found to resume.")

# Bsky Client Session Management Functions
def get_session() -> Optional[str]:
    try:
        session_entry = SessionState.get(SessionState.service == 'atproto')
        return session_entry.session_string
    except peewee.DoesNotExist:
        return None
    except peewee.PeeweeException as e:
        logger.error(f"Error retrieving session from database: {e}")
        return None

def save_session(session_string: str) -> None:
    try:
        session_entry, created = SessionState.get_or_create(service='atproto')
        session_entry.session_string = session_string
        session_entry.save()
        if created:
            logger.info("New session entry created in the database.")
        else:
            logger.info("Session entry updated in the database.")
    except peewee.PeeweeException as e:
        logger.error(f"Error saving session to database: {e}")

def on_session_change(event: SessionEvent, session: Session) -> None:
    if event in (SessionEvent.CREATE, SessionEvent.REFRESH, SessionEvent.IMPORT):
        logger.info(f"Session changed and saved: {event}")
        save_session(session.export())

def init_client() -> Client:
    client = Client()

    # Register the session change handler
    client.on_session_change(on_session_change)

    # Attempt to load existing session from the database
    session_string = get_session()
    if session_string:
        try:
            client.login(session_string=session_string)
            logger.info("Reused existing session from the database.")
        except exceptions.AtProtocolError as e:
            logger.error(f"Failed to login with existing session: {e}")
            logger.info("Attempting to create a new session.")
            client.login(HANDLE, PASSWORD)
    else:
        logger.info("No existing session found in the database. Creating a new session.")
        client.login(HANDLE, PASSWORD)

    return client

# Scheduler Shutdown Function
def shutdown_scheduler(scheduler: BackgroundScheduler):
    try:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shutdown successfully.")
    except Exception as e:
        logger.error(f"Error during scheduler shutdown: {e}")

    try:
        if not db.is_closed():
            db.close()
            logger.info("Database connection closed.")
    except peewee.PeeweeException as e:
        logger.error(f"Error closing database: {e}")

# Main section
# Initialize Database
if db.is_closed():
    db.connect()
    db.create_tables([Post, SubscriptionState, SessionState])
    logger.info("Database connected and tables created.")

# Initialize Client
client = init_client()

# Start Scheduler
scheduler = start_scheduler(client, schedule_hydration=True)
for job in scheduler.get_jobs():
    job.modify(next_run_time=datetime.now())  # Trigger all jobs immediately
from atproto import Client, SessionEvent, Session, exceptions
from datetime import datetime, timedelta, timezone
from typing import Optional
import peewee
import time
import sys
import os
import argparse

from utils.logger import logger
from utils.config import HANDLE, PASSWORD
from database import db, Post, SessionState

# Main Function
def main():
    parser = argparse.ArgumentParser(description='Run scheduler tasks as one-time jobs')
    parser.add_argument('--job', choices=['hydrate', 'cleanup'], required=True,
                       help='Job type to run: hydrate (hydrate posts) or cleanup (database cleanup)')
    parser.add_argument('--clear-days', type=int, default=3,
                       help='Days to keep posts for cleanup job (default: 3)')
    
    args = parser.parse_args()
    
    # Also check environment variable for job type (useful for K8s CronJob)
    job_type = args.job or os.getenv('SCHEDULER_JOB_TYPE', 'hydrate')
    clear_days = args.clear_days if args.clear_days != 3 else int(os.getenv('SCHEDULER_CLEAR_DAYS', '3'))
    
    logger.info(f"Starting scheduler job: {job_type}")
    
    try:
        if job_type == 'hydrate':
            # Initialize Client for hydration
            client = init_client()
            hydrate_posts_with_interactions(client)
            logger.info("Hydration job completed successfully")
        elif job_type == 'cleanup':
            cleanup_db(clear_days)
            logger.info(f"Cleanup job completed successfully (cleared {clear_days} days)")
        else:
            logger.error(f"Unknown job type: {job_type}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Job failed with error: {e}")
        sys.exit(1)
    finally:
        # Ensure database connection is closed
        if not db.is_closed():
            db.close()
            logger.info("Database connection closed.")

# Postgres database management functions
def clear_old_posts(clear_days: int):
    try:
        with db.connection_context():
            logger.info("Database connection opened for cleanup.")
            cutoff_date = datetime.now() - timedelta(days=clear_days)
            query = Post.delete().where(Post.indexed_at < cutoff_date)

            with db.atomic():
                num_deleted = query.execute()

            logger.info(f"Deleted {num_deleted} posts older than {cutoff_date}.")
    except peewee.PeeweeException as e:
        logger.error(f"An error occurred while deleting old posts: {e}")
    finally:
        if not db.is_closed():
            db.close()
            logger.info("Database connection closed after cleanup by force.")
        else:
            logger.info("Database connection closed after cleanup.")

def vacuum_database():
    try:
        with db.connection_context():
            logger.info("Database connection opened for vacuum.")
            db.execute_sql('VACUUM FULL;')
            logger.info("Vacuum operation completed.")
    except peewee.PeeweeException as e:
        logger.error(f"An error occurred while vacuuming the database: {e}")
    finally:
        if not db.is_closed():
            db.close()
            logger.info("Database connection closed after vacuum by force.")
        else:
            logger.info("Database connection closed after vacuum.")

def cleanup_db(clear_days: int = 3):
    clear_old_posts(clear_days)
    vacuum_database()

# Hydration Function with Rate Limit and Expired Token Handling
def hydrate_posts_with_interactions(client: Client, batch_size: int = 25):
    try:
        with db.connection_context():
            logger.info("Hydration Database connection opened.")
            # get posts with uri and interactions from the last 7 days
            posts = Post.select(Post.uri, Post.interactions).where(Post.indexed_at > (datetime.now() - timedelta(days=4)))
            uris = [post.uri for post in posts]

            if not uris:
                logger.info("No posts found in the database to hydrate.")
                return

            # list to collect
            posts_to_update = []

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
                        indexed_at_str = fetched_post.indexed_at
                        
                        # Extract text content from the post record
                        text_content = None
                        if hasattr(fetched_post, 'record') and hasattr(fetched_post.record, 'text'):
                            text_content = fetched_post.record.text

                        # Convert indexed_at to datetime object
                        try:
                            indexed_at = datetime.fromisoformat(indexed_at_str)
                            if indexed_at.tzinfo is None:
                                # Assume UTC if timezone is not provided
                                indexed_at = indexed_at.replace(tzinfo=timezone.utc)
                            else:
                                indexed_at = indexed_at.astimezone(timezone.utc)
                        except Exception as e:
                            logger.error(f"Error parsing indexed_at for post {uri}: {e}")
                            continue

                        # Calculate time difference in hours
                        time_diff = datetime.now(timezone.utc) - indexed_at
                        time_diff_hours = time_diff.total_seconds() / 3600

                        # Calculate "What's Hot" score
                        # Formula: hot_score = interactions / ( (age_in_hours + 2) ** 1.5 )
                        # Adding 2 to avoid division by zero and to give a slight boost to newer posts
                        interactions_score = like_count + (reply_count * 2) + (repost_count * 3)
                        hot_score = interactions_score / ((time_diff_hours + 2) ** 1.5)
                        
                        # Round the hot_score to an integer
                        hot_score *= 100  # Scaling the score
                        hot_score = int(hot_score)

                        # Fetch the current post from the database
                        current_post = Post.get_or_none(Post.uri == uri)
                        if current_post:
                            needs_update = False
                            
                            # Check if interactions need updating
                            if current_post.interactions != hot_score:
                                current_post.interactions = hot_score
                                needs_update = True
                            
                            # Check if text content needs updating (if it's currently null or different)
                            if text_content and (current_post.text is None or current_post.text != text_content):
                                current_post.text = text_content
                                needs_update = True
                            
                            if needs_update:
                                posts_to_update.append(current_post)
                        
                    # pause the loop for 3 seconds
                    #time.sleep(3)

                except exceptions.AtProtocolError as api_err:
                    if api_err.response:
                        status_code = api_err.response.status_code
                        if status_code == 429:
                            # Rate limited during hydration
                            reset_timestamp = api_err.response.headers.get('RateLimit-Reset')
                            if reset_timestamp:
                                reset_time = datetime.fromtimestamp(int(reset_timestamp), timezone.utc)
                            else:
                                reset_time = datetime.now(timezone.utc) + timedelta(seconds=60)  # Default to 60 seconds
                            logger.warning(f"Rate limit exceeded during hydration. Will retry in next scheduled run.")
                            raise api_err  # Re-raise to fail the job so it can be retried
                        elif status_code == 400:
                            # Handle other specific status codes if necessary
                            logger.error(f"Hydration failed with status 400. Content: {api_err.response.content}")
                            # Optionally, implement additional error handling here
                    else:
                        logger.error(f"API error while fetching posts without response: {api_err}")
                except Exception as e:
                    logger.error(f"Unexpected error while hydrating posts: {e}")

            if posts_to_update:
                try:
                    with db.atomic():
                        updated = Post.bulk_update(posts_to_update, fields=['interactions', 'text'])
                    logger.info(f"Hydrated {updated} posts with updated hot_scores and text content.")
                except Exception as e:
                    logger.error(f"Failed to bulk update posts: {e}")
            else:
                logger.info("No posts needed updating based on the latest interactions.")

    except Exception as e:
        logger.error(f"Error in hydration process: {e}")
        raise e  # Re-raise to fail the job

    finally:
        if not db.is_closed():
            db.close()
            logger.info("Hydration Database connection closed by force.")
        else :
            logger.info("Hydration Database connection closed.")

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

if __name__ == '__main__':
    main()
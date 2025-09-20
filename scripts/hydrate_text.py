#!/usr/bin/env python3
"""
Script to hydrate posts with null text from the Bluesky API.
This script finds all posts in the database that have null text and fetches
their actual text content from the Bluesky API.
"""

import sys
import os
import argparse
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables from .env file
load_dotenv()

# Suppress httpx debug logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Add the necessary paths to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'scheduler'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'firehose'))

from atproto import Client, SessionEvent, Session, exceptions
import peewee

# Import database models and utilities
from scheduler.database import db, Post, SessionState
from scheduler.utils.logger import logger

# Get configuration from environment variables
HANDLE = os.environ.get('HANDLE')
PASSWORD = os.environ.get('PASSWORD')

if not HANDLE:
    raise RuntimeError('You should set "HANDLE" environment variable first.')
if not PASSWORD:
    raise RuntimeError('You should set "PASSWORD" environment variable first.')

class TextHydrator:
    def __init__(self):
        self.client = None
        
    def init_client(self) -> Client:
        """Initialize and authenticate the AT Protocol client."""
        client = Client()
        
        # Register the session change handler
        client.on_session_change(self.on_session_change)
        
        # Attempt to load existing session from the database
        session_string = self.get_session()
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
    
    def get_session(self) -> Optional[str]:
        """Retrieve stored session from database."""
        try:
            session_entry = SessionState.get(SessionState.service == 'atproto')
            return session_entry.session_string
        except peewee.DoesNotExist:
            return None
        except peewee.PeeweeException as e:
            logger.error(f"Error retrieving session from database: {e}")
            return None
    
    def save_session(self, session_string: str) -> None:
        """Save session to database."""
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
    
    def on_session_change(self, event: SessionEvent, session: Session) -> None:
        """Handle session change events."""
        if event in (SessionEvent.CREATE, SessionEvent.REFRESH, SessionEvent.IMPORT):
            logger.info(f"Session changed and saved: {event}")
            self.save_session(session.export())
    
    def get_posts_with_null_text(self, limit: Optional[int] = None) -> List[Post]:
        """Get all posts from database that have null text."""
        try:
            with db.connection_context():
                query = Post.select().where(Post.text.is_null())
                if limit:
                    query = query.limit(limit)
                posts = list(query)
                logger.info(f"Found {len(posts)} posts with null text")
                return posts
        except peewee.PeeweeException as e:
            logger.error(f"Error querying posts with null text: {e}")
            return []
    
    def hydrate_posts_text(self, posts: List[Post], batch_size: int = 25) -> None:
        """Hydrate posts with text content from the API."""
        if not posts:
            logger.info("No posts to hydrate.")
            return
        
        uris = [post.uri for post in posts]
        posts_to_update = []
        total_batches = (len(uris) + batch_size - 1) // batch_size
        
        logger.info(f"Processing {len(uris)} posts in {total_batches} batches of {batch_size}")
        
        with tqdm(total=len(uris), desc="Hydrating posts", unit="post") as pbar:
            for batch_num, i in enumerate(range(0, len(uris), batch_size), 1):
                batch_uris = uris[i:i + batch_size]
                pbar.set_description(f"Batch {batch_num}/{total_batches}")
            
                try:
                    # Fetch posts from the API
                    response = self.client.get_posts(uris=batch_uris)
                    fetched_posts = response.posts if hasattr(response, 'posts') else []
                    
                    batch_updated = 0
                    for fetched_post in fetched_posts:
                        uri = fetched_post.uri
                        if not uri:
                            continue
                        
                        # Extract text content
                        text_content = None
                        if hasattr(fetched_post, 'record') and hasattr(fetched_post.record, 'text'):
                            text_content = fetched_post.record.text
                        
                        if text_content:
                            # Find the corresponding post in our list
                            for post in posts:
                                if post.uri == uri:
                                    post.text = text_content
                                    posts_to_update.append(post)
                                    batch_updated += 1
                                    break
                    
                    # Update progress bar
                    pbar.update(len(batch_uris))
                    pbar.set_postfix({"updated": len(posts_to_update)})
                    
                    # Add a small delay between batches to be respectful to the API
                    if batch_num < total_batches:  # Don't sleep after the last batch
                        time.sleep(1)
                    
                except exceptions.AtProtocolError as api_err:
                    if api_err.response:
                        status_code = api_err.response.status_code
                        if status_code == 429:
                            # Rate limited
                            reset_timestamp = api_err.response.headers.get('RateLimit-Reset')
                            if reset_timestamp:
                                reset_time = datetime.fromtimestamp(int(reset_timestamp), timezone.utc)
                                wait_seconds = (reset_time - datetime.now(timezone.utc)).total_seconds()
                                pbar.set_description(f"Rate limited, waiting {wait_seconds:.0f}s")
                                time.sleep(max(wait_seconds, 60))  # Wait at least 60 seconds
                            else:
                                pbar.set_description("Rate limited, waiting 60s")
                                time.sleep(60)
                            continue  # Retry this batch
                        elif status_code == 400:
                            logger.error(f"API error 400 for batch {batch_num}: {api_err.response.content}")
                            pbar.update(len(batch_uris))  # Still update progress
                            continue  # Skip this batch
                        else:
                            logger.error(f"API error {status_code} for batch {batch_num}: {api_err}")
                            pbar.update(len(batch_uris))  # Still update progress
                            continue  # Skip this batch
                    else:
                        logger.error(f"API error without response for batch {batch_num}: {api_err}")
                        pbar.update(len(batch_uris))  # Still update progress
                        continue  # Skip this batch
                except Exception as e:
                    logger.error(f"Unexpected error processing batch {batch_num}: {e}")
                    pbar.update(len(batch_uris))  # Still update progress
                    continue  # Skip this batch
        
        # Bulk update posts with text
        if posts_to_update:
            try:
                with db.connection_context():
                    with db.atomic():
                        updated_count = Post.bulk_update(posts_to_update, fields=['text'])
                    logger.info(f"Successfully updated {updated_count} posts with text content")
            except Exception as e:
                logger.error(f"Failed to bulk update posts: {e}")
        else:
            logger.info("No posts were updated with text content")
    
    def run(self, limit: Optional[int] = None, batch_size: int = 25) -> None:
        """Main execution method."""
        try:
            # Initialize the client
            self.client = self.init_client()
            
            # Get posts with null text
            posts = self.get_posts_with_null_text(limit)
            
            if not posts:
                logger.info("No posts with null text found in the database.")
                return
            
            # Hydrate posts with text
            self.hydrate_posts_text(posts, batch_size)
            
        except Exception as e:
            logger.error(f"Error during text hydration: {e}")
            raise
        finally:
            # Ensure database connection is closed
            if not db.is_closed():
                db.close()
                logger.info("Database connection closed.")

def main():
    """Command line interface."""
    parser = argparse.ArgumentParser(
        description='Hydrate posts with null text from the Bluesky API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        python hydrate_text.py                    # Hydrate all posts with null text
        python hydrate_text.py --limit 100       # Hydrate only 100 posts
        python hydrate_text.py --batch-size 10   # Use smaller batch size
        """
    )
    
    parser.add_argument(
        '--limit', 
        type=int, 
        help='Limit the number of posts to process (default: process all)'
    )
    
    parser.add_argument(
        '--batch-size', 
        type=int, 
        default=25,
        help='Number of posts to process in each API batch (default: 25)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE: No changes will be made to the database")
        try:
            with db.connection_context():
                count = Post.select().where(Post.text.is_null()).count()
                if args.limit and count > args.limit:
                    count = args.limit
                logger.info(f"Would process {count} posts with null text")
        except Exception as e:
            logger.error(f"Error during dry run: {e}")
            sys.exit(1)
        return
    
    logger.info("Starting text hydration process...")
    logger.info(f"Batch size: {args.batch_size}")
    if args.limit:
        logger.info(f"Limit: {args.limit} posts")
    else:
        logger.info("Limit: No limit (processing all posts)")
    
    try:
        hydrator = TextHydrator()
        hydrator.run(limit=args.limit, batch_size=args.batch_size)
        logger.info("Text hydration completed successfully")
    except Exception as e:
        logger.error(f"Text hydration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
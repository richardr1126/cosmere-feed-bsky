from datetime import datetime, timedelta, timezone
from typing import Optional
import json

from firehose.utils import config
from web.database_ro import Post
from firehose.utils.logger import logger

uri = config.TRENDING_URI
CURSOR_EOF = 'eof'

TRENDING_THRESHOLD = 24  # Hours
INTERACTIONS_THRESHOLD = 30  # Minimum hot score for trending posts

def decode_cursor(cursor: str) -> int:
    try:
        return int(cursor)
    except ValueError:
        return 0

def handler(cursor: Optional[str], limit: int) -> dict:
    if not isinstance(limit, int):
        limit = int(limit)

    # Return EOF immediately if we received EOF cursor
    if cursor == CURSOR_EOF:
        return {
            'cursor': CURSOR_EOF,
            'feed': []
        }

    try:
        # Define time threshold for trending posts
        now = datetime.now(timezone.utc)
        trending_threshold = now - timedelta(hours=TRENDING_THRESHOLD)

        # Get current offset from cursor
        offset = decode_cursor(cursor) if cursor and cursor != CURSOR_EOF else 0

        # Fetch trending posts using offset-based pagination
        trending_posts_query = (
            Post.select()
            .where(
                (Post.indexed_at > trending_threshold) &
                (Post.interactions >= INTERACTIONS_THRESHOLD)
            )
            .order_by(Post.interactions.desc(), Post.indexed_at.desc(), Post.cid.desc())
        )

        # Check if we have any posts before pagination
        total_posts = trending_posts_query.count()
        
        # If offset is beyond total posts, return EOF
        if offset >= total_posts:
            return {
                'cursor': CURSOR_EOF,
                'feed': []
            }

        # Apply offset and limit
        trending_posts = list(trending_posts_query.offset(offset).limit(limit + 1))
        has_more = len(trending_posts) > limit
        trending_posts = trending_posts[:limit]

        # If no posts were found, return EOF
        if not trending_posts:
            return {
                'cursor': CURSOR_EOF,
                'feed': []
            }

        logger.info(f"Fetched {len(trending_posts)} trending posts with >={INTERACTIONS_THRESHOLD} interactions starting at offset {offset}")

        # Build the feed
        feed = [{'post': post.uri} for post in trending_posts]

        # Set next cursor
        new_cursor = str(offset + len(trending_posts)) if has_more else CURSOR_EOF
        logger.info(f"Next cursor set to: {new_cursor}")

        return {
            'cursor': new_cursor,
            'feed': feed
        }

    except Exception as e:
        logger.error(f"An unexpected error occurred in handler: {e}", exc_info=True)
        return {
            'cursor': CURSOR_EOF,
            'feed': [],
            'error': 'An unexpected error occurred.'
        }

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
import json

from firehose.utils import config
from web.database_ro import Post
from firehose.utils.logger import logger

uri = config.CHRONOLOGICAL_TRENDING_URI
CURSOR_EOF = 'eof'

DID_TO_PRIORITIZE = 'did:plc:wihwdzwkb6nd3wb565kujg2f'
TRENDING_THRESHOLD = 24  # Hours
INTERACTIONS_THRESHOLD = 30  # Minimum hot score for trending posts

def encode_cursor(cursors: Dict[str, Optional[str]]) -> str:
    return json.dumps(cursors)

def decode_cursor(cursor: str) -> Dict[str, Optional[str]]:
    return json.loads(cursor)

def adjust_limit(limit: int) -> int:
    # Validate and adjust 'limit' to the closest multiple of 5
    if limit <= 0:
        logger.error(f"Invalid limit value: {limit}. Must be positive.")
        return {
            'cursor': CURSOR_EOF,
            'feed': [],
            'error': 'Limit must be a positive integer.'
        }
    
    # Adjust limit to the closest multiple of 5
    if limit % 5 != 0:
        limit = (limit // 5 + 1) * 5
        logger.debug(f"Adjusted limit to the closest multiple of 5: {limit}")

    return limit

def handler(cursor: Optional[str], limit: int) -> dict:
    if not isinstance(limit, int):
        limit = int(limit)

    # Adjust limit to the closest multiple of 5
    limit = adjust_limit(limit) if limit != 1 else 1

    try:
        # Define time thresholds
        now = datetime.now(timezone.utc)
        my_posts_threshold = now - timedelta(hours=12)
        trending_threshold = now - timedelta(hours=TRENDING_THRESHOLD)

        # Define interleaving pattern
        pattern = [
            ('my_posts', 1),
            ('main_posts', 3),
            ('trending_posts', 1)
        ]

        # Calculate total number of pattern repeats needed
        total_patterns = limit // 5  if limit != 1 else 1

        # Initialize cursors for each post type
        if cursor and cursor != CURSOR_EOF:
            try:
                cursors = decode_cursor(cursor)
                my_cursor = cursors.get('my_posts')
                main_cursor = cursors.get('main_posts')
                trending_posts_offset = int(cursors.get('trending_posts_offset', 0))
            except (ValueError, json.JSONDecodeError) as e:
                logger.error(f"Malformed cursor: {cursor}. Error: {e}")
                return {
                    'cursor': CURSOR_EOF,
                    'feed': [],
                    'error': 'Malformed cursor.'
                }
        else:
            cursors = {}
            my_cursor = None
            main_cursor = None
            trending_posts_offset = 0  # Start at the beginning

        # Helper function to build cursor conditions for my_posts and main_posts
        def build_cursor_condition(cursor_value: Optional[str]):
            if cursor_value:
                try:
                    indexed_at, cid = cursor_value.split('::')
                    indexed_at = datetime.fromtimestamp(float(indexed_at)/1000, timezone.utc)
                    return (
                        ((Post.indexed_at == indexed_at) & (Post.cid < cid)) |
                        (Post.indexed_at < indexed_at)
                    )
                except ValueError as e:
                    logger.error(f"Malformed cursor segment: {cursor_value}. Error: {e}")
                    return None
            return None

        # Fetch trending_posts using offset-based pagination
        trending_posts_query = (
            Post.select()
            .where(
                (Post.indexed_at > trending_threshold) &
                (Post.interactions >= INTERACTIONS_THRESHOLD)
            )
            .order_by(Post.interactions.desc(), Post.indexed_at.desc(), Post.cid.desc())
        )

        # Apply offset for trending_posts
        trending_posts = list(trending_posts_query.offset(trending_posts_offset).limit(limit))
        #logger.info(f"Fetched {len(trending_posts)} trending posts with >={INTERACTIONS_THRESHOLD} interactions starting at offset {trending_posts_offset}")

        trending_cids = [post.cid for post in trending_posts]

        # Fetch main_posts excluding trending_posts
        main_posts_query = (
            Post.select()
            .where(Post.author != DID_TO_PRIORITIZE)
            .order_by(Post.indexed_at.desc(), Post.cid.desc())
        )

        main_cursor_condition = build_cursor_condition(main_cursor)
        if main_cursor_condition:
            main_posts_query = main_posts_query.where(main_cursor_condition)

        if trending_cids:
            main_posts_query = main_posts_query.where(Post.cid.not_in(trending_cids))

        if limit == 1:
            main_posts_query = main_posts_query.limit(1)
            return {
                'cursor': CURSOR_EOF,
                'feed': [{'post': main_posts_query[0].uri}]
            }

        main_posts = list(main_posts_query.limit(limit))  # Fetch up to 'limit' main posts
        #logger.debug(f"Fetched {len(main_posts)} main posts excluding trending posts")

        # Fetch my_posts excluding trending_posts
        my_posts_query = (
            Post.select()
            .where(
                (Post.author == DID_TO_PRIORITIZE) &
                (Post.indexed_at > my_posts_threshold)
            )
            .order_by(Post.indexed_at.desc(), Post.cid.desc())
        )

        my_cursor_condition = build_cursor_condition(my_cursor)
        if my_cursor_condition:
            my_posts_query = my_posts_query.where(my_cursor_condition)

        if trending_cids:
            my_posts_query = my_posts_query.where(Post.cid.not_in(trending_cids))

        my_posts = list(my_posts_query.limit(limit))  # Fetch up to 'limit' my posts
        #logger.debug(f"Fetched {len(my_posts)} my posts excluding trending posts")

        # Initialize iterators
        my_posts_iter = iter(my_posts)
        main_posts_iter = iter(main_posts)
        trending_posts_iter = iter(trending_posts)

        combined_posts = []
        seen_cids = set()

        # Track the last fetched post per category
        last_fetched = {
            'my_posts': None,
            'main_posts': None,
            'trending_posts': None
        }

        trending_count = 0

        # Single loop to interleave posts based on the defined pattern
        for _ in range(total_patterns):
            for category, count in pattern:
                for _ in range(count):
                    try:
                        if limit == 10: # Limit 10 when reuests come from following feed
                            category = 'trending_posts'

                        if category == 'my_posts':
                            post = next(my_posts_iter)
                        elif category == 'main_posts':
                            post = next(main_posts_iter)
                        elif category == 'trending_posts':
                            post = next(trending_posts_iter)
                        else:
                            continue  # Unknown category

                        if post.cid not in seen_cids:
                            combined_posts.append(post)
                            seen_cids.add(post.cid)
                            last_fetched[category] = post

                            if category == 'trending_posts': # Track the number of trending_posts fetched
                                #logger.info(f"Added trending post | {post.interactions} | {post.indexed_at}")
                                trending_count += 1

                            if len(combined_posts) >= limit:
                                break
                    except StopIteration:
                        logger.debug(f"No more {category} to add")
                        continue

                if len(combined_posts) >= limit:
                    break
            if len(combined_posts) >= limit:
                break

        # If combined_posts is still less than limit, fill the remaining with main_posts
        while len(combined_posts) < limit:
            try:
                post = next(main_posts_iter)
                if post.cid not in seen_cids:
                    combined_posts.append(post)
                    seen_cids.add(post.cid)
                    last_fetched['main_posts'] = post
            except StopIteration:
                logger.debug("No more main_posts to add during final filling")
                break

        #logger.debug(f"Combined posts count after interleaving: {len(combined_posts)}")

        # Trim the list to the desired limit
        combined_posts = combined_posts[:limit]

        # Remove duplicates by cid while preserving order (additional safeguard)
        unique_posts = []
        seen_cids_final = set()
        for post in combined_posts:
            if post.cid not in seen_cids_final:
                unique_posts.append(post)
                seen_cids_final.add(post.cid)
            if len(unique_posts) >= limit:
                break

        logger.info(f"Total unique posts in feed after deduplication: {len(unique_posts)}")
        logger.info(f"Total trending posts in served: {trending_count}")

        # Build the feed
        feed = [{'post': post.uri} for post in unique_posts]

        new_cursors = {}
        for category, post in last_fetched.items():
            if category in ['my_posts', 'main_posts'] and post:
                # Corrected multiplication by using timestamp()
                timestamp = datetime.fromisoformat(str(post.indexed_at)).timestamp()*1000
                new_cursors[category] = f'{timestamp}::{post.cid}'
            elif category == 'trending_posts' and post:
                # Update the offset based on the number of trending_posts fetched
                new_cursors['trending_posts_offset'] = trending_posts_offset + trending_count
        
        # Encode the new cursor
        if new_cursors:
            new_cursor = encode_cursor(new_cursors)
        else:
            new_cursor = CURSOR_EOF

        # Determine if more posts exist for each category
        def has_more_posts(query, needed):
            return query.limit(needed).count() > 0

        more_trending = len(trending_posts) == limit  # If fetched 'limit' trending_posts, assume more exist
        more_main = has_more_posts(main_posts_query, 1)
        more_my = has_more_posts(my_posts_query, 1)

        if not (more_trending or more_main or more_my):
            new_cursor = CURSOR_EOF

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

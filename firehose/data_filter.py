from datetime import datetime, timezone
import re
from collections import defaultdict
from atproto import models, Client, IdResolver
from utils.logger import logger
from database import db, Post, init_client
import json
from pathlib import Path

handle_resolver = IdResolver().handle
did_resolver = IdResolver().did

FILTER_FILE = Path('filter_config.json')

def load_filters():
    """Load filters from JSON file or return defaults if file doesn't exist"""
    if FILTER_FILE.exists():
        with open(FILTER_FILE, 'r') as f:
            return json.load(f)

filters = load_filters()
HANDLES = filters['HANDLES']
EXCLUDE_HANDLES = filters['EXCLUDE_HANDLES']
PHRASES = filters['PHRASES']
INCLUSIVE_MULTI_TOKENS = filters['INCLUSIVE_MULTI_TOKENS']
TOKENS = filters['TOKENS']
EXCLUDE_TOKENS = filters['EXCLUDE_TOKENS']

dids_to_include = [handle_resolver.resolve(handle) for handle in HANDLES]
dids_to_exclude = [handle_resolver.resolve(handle) for handle in EXCLUDE_HANDLES]

def compile_pattern(items, word_boundary=True, plural=True):
    escaped = [re.escape(item) for item in items]
    if plural:
        # Add optional 's' at the end
        escaped = [f"{item}s?" for item in escaped]
    pattern = "|".join(escaped)
    if word_boundary:
        # Use raw string for word boundaries
        pattern = r'\b(?:' + pattern + r')\b'
    return pattern

# Compile single-word include tokens into one pattern
INCLUDE_TOKENS_PATTERN = compile_pattern(TOKENS)
INCLUDE_TOKENS_REGEX = re.compile(INCLUDE_TOKENS_PATTERN, re.IGNORECASE)

# Compile single-word exclude tokens into one pattern
EXCLUDE_TOKENS_PATTERN = compile_pattern(EXCLUDE_TOKENS)
EXCLUDE_TOKENS_REGEX = re.compile(EXCLUDE_TOKENS_PATTERN, re.IGNORECASE)

# Compile phrases into one pattern
PHRASES_PATTERN = compile_pattern(PHRASES)
PHRASES_REGEX = re.compile(PHRASES_PATTERN, re.IGNORECASE)

# Compile tokens with spaces using positive lookaheads
def compile_multi_word_lookahead(tokens):
    patterns = []
    for token in tokens:
        words = token.split()
        # Use formatted raw strings within lookaheads
        lookaheads = ''.join([fr'(?=.*\b{re.escape(word)}\b)' for word in words])
        patterns.append(lookaheads)
    # Combine all multi-word token lookaheads into one pattern with alternation
    combined_pattern = '|'.join(patterns)
    return re.compile(combined_pattern, re.IGNORECASE)

# Compile include tokens with spaces using positive lookaheads
INCLUSIVE_MULTI_WORD_PATTERN = compile_multi_word_lookahead(INCLUSIVE_MULTI_TOKENS)

def matches_filters(text):
    # Use case-insensitive matching; no need to lowercase the text
    # Check exclude patterns first
    if EXCLUDE_TOKENS_REGEX.search(text):
        return False

    # Check include patterns
    if PHRASES_REGEX.search(text):
        return True
    if INCLUSIVE_MULTI_WORD_PATTERN.search(text):
        return True
    if INCLUDE_TOKENS_REGEX.search(text):
        return True

    return False


def operations_callback(ops: defaultdict) -> None:
    created_posts = ops[models.ids.AppBskyFeedPost]['created']
    deleted_posts = ops[models.ids.AppBskyFeedPost]['deleted']

    posts_to_create = []
    for post in created_posts:
        record = post['record']
        did = post['author']
        now = datetime.now(timezone.utc)

        if did in dids_to_exclude:
            logger.info(f'Skipping post from excluded DID: {did}')
            continue
        
        if did in dids_to_include:
            logger.info(f'Processing post from included DID: {did}')
        
            posts_to_create.append({
                'uri': post['uri'],
                'cid': post['cid'],
                'reply_parent': record.reply.parent.uri if record.reply else None,
                'reply_root': record.reply.root.uri if record.reply else None,
                'author': did,
                'interactions': 0,
                'indexed_at': now,
            })

            continue

        
        if matches_filters(record.text):
            reply_root = post['record'].reply.root.uri if post['record'].reply else None
            reply_parent = post['record'].reply.parent.uri if post['record'].reply else None

            #logger.info(f'Processing matched post: {record.text}')
            logger.info(f'Processing matched post from {did_resolver.resolve(did).also_known_as[0]}')

            posts_to_create.append({
                'uri': post['uri'],
                'cid': post['cid'],
                'reply_parent': reply_parent,
                'reply_root': reply_root,
                'author': did,
                'interactions': 0,
                'indexed_at': now,
            })

    if deleted_posts:
        post_uris_to_delete = [post['uri'] for post in deleted_posts]
        if post_uris_to_delete:
            # Assuming Post.delete() returns a query builder that needs to be executed
            deleted_count = 0
            with db.atomic():
                deleted_count = Post.delete().where(Post.uri.in_(post_uris_to_delete)).execute()
            if deleted_count>0: logger.info(f'Deleted: {deleted_count}')

    if posts_to_create:
        with db.atomic():
            for post_dict in posts_to_create:
                Post.create(**post_dict)
        logger.info(f'Added: {len(posts_to_create)}')

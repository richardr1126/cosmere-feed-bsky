from collections import defaultdict
from datetime import datetime, timezone
from time import time

from atproto import (
    AtUri,
    CAR,
    firehose_models,
    FirehoseSubscribeReposClient,
    models,
    parse_subscribe_repos_message,
)
from atproto.exceptions import FirehoseError

from database import db, Post, SubscriptionState, SessionState, Requests
from utils.logger import logger

# Define the types of records we're interested in and their corresponding namespace IDs
_INTERESTED_RECORDS = {
    models.AppBskyFeedPost: models.ids.AppBskyFeedPost,
}

def _get_ops_by_type(commit: models.ComAtprotoSyncSubscribeRepos.Commit) -> defaultdict:
    """Memory-optimized version of operation processing"""
    operations_by_type = defaultdict(lambda: {'created': [], 'deleted': []})
    
    # Process CAR blocks in chunks to reduce memory usage
    car = CAR.from_bytes(commit.blocks)
    
    for op in commit.ops:
        # Early return for updates we don't care about
        if op.action == 'update':
            continue
            
        uri = AtUri.from_str(f'at://{commit.repo}/{op.path}')
        
        # Handle deletions immediately - they're lightweight
        if op.action == 'delete':
            operations_by_type[uri.collection]['deleted'].append({'uri': str(uri)})
            continue

        # For creates, only process if we have a valid CID and it's a record type we care about
        if op.action == 'create' and op.cid and uri.collection in _INTERESTED_RECORDS.values():
            record_raw_data = car.blocks.get(op.cid)
            if not record_raw_data:
                continue

            try:
                # Only parse records we're interested in
                record = models.get_or_create(record_raw_data, strict=False)
                create_info = {'uri': str(uri), 'cid': str(op.cid), 'author': commit.repo}
                operations_by_type[uri.collection]['created'].append({'record': record, **create_info})
            except Exception as e:
                logger.error(f"Failed to parse record: {e}")
                continue

    # Clear references to help garbage collection
    del car
    return operations_by_type


def run(name, operations_callback, stream_stop_event=None):
    """
    Starts the firehose client and processes incoming messages.

    Args:
        name: The name of the service/subscription.
        operations_callback: A callback function to handle the operations extracted from messages.
        stream_stop_event: An optional threading.Event to signal when to stop the stream.
    """
    # Initialize Database
    if db.is_closed():
        db.connect()
        db.create_tables([Post, SubscriptionState, SessionState, Requests])
        logger.info("Database connected and tables created.")

    while stream_stop_event is None or not stream_stop_event.is_set():
        try:
            # Start the main run loop
            _run(name, operations_callback, stream_stop_event)
        except FirehoseError as e:
            logger.error(f"Firehose error: {e}")
            # Implement a backoff or retry mechanism here
            continue
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            break
        finally:
            logger.info("You should not see this ...")


def _run(name, operations_callback, stream_stop_event=None):
    """
    Connects to the firehose, sets up the message handler, and starts streaming messages.

    Args:
        name: The name of the service/subscription.
        operations_callback: A callback function to handle the operations extracted from messages.
        stream_stop_event: An optional threading.Event to signal when to stop the stream.
    """
    # Add performance monitoring variables
    last_seq = 0
    last_time = time()
    processed_count = 0

    # Retrieve the last known cursor position from the database
    state = SubscriptionState.get_or_none(SubscriptionState.service == name)

    # Initialize parameters with the cursor if available
    params = None
    if state:
        params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=state.cursor)
    else:
        # If no state exists, create an initial subscription state with cursor 0
        SubscriptionState.create(service=name, cursor=0)

    # Initialize the firehose client
    client = FirehoseSubscribeReposClient(params)

    def on_message_handler(message: firehose_models.MessageFrame) -> None:
        nonlocal last_seq, last_time, processed_count, stream_stop_event, client
        """
        Handles incoming messages from the firehose.

        Args:
            message: The message frame received from the firehose.
        """
        # Check if a stop event has been set; if so, stop the client
        if stream_stop_event and stream_stop_event.is_set():
            logger.info("Stopping firehose...")
            client.stop()
            return

        try:
            # Parse the message into a commit object
            commit = parse_subscribe_repos_message(message)
        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            return

        # Only process commit messages
        if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
            #logger.warning(f"Received non-commit message: {commit}")
            return
        
        if not commit.blocks:
            # Skip if there are no blocks to process
            return

        # Update the cursor every ~20,000 events
        if commit.seq % 20000 == 0:
            current_time = time()
            elapsed = current_time - last_time
            rate = 20000 / elapsed if elapsed > 0 else 0
            
            logger.info(f'Cursor|{commit.seq}|{rate:.2f} events/s|{elapsed:.2f}s elapsed')
            
            last_time = current_time

            # Update the client's parameters with the new cursor
            client.update_params(models.ComAtprotoSyncSubscribeRepos.Params(cursor=commit.seq))
            # Persist the new cursor in the database with the last indexed timestamp
            SubscriptionState.update(
                cursor=commit.seq,
                last_indexed_at=datetime.now(timezone.utc),
            ).where(SubscriptionState.service == name).execute()
                

        # Extract operations from the commit
        operations = _get_ops_by_type(commit)
        # Pass the operations to the callback function
        operations_callback(operations)

    # Start the client with the message handler
    client.start(on_message_handler)

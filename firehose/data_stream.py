from collections import defaultdict

from atproto import (
    AtUri,
    CAR,
    firehose_models,
    FirehoseSubscribeReposClient,
    models,
    parse_subscribe_repos_message,
)
from atproto.exceptions import FirehoseError

from database import SubscriptionState, db
from utils.logger import logger

# Define the types of records we're interested in and their corresponding namespace IDs
_INTERESTED_RECORDS = {
    models.AppBskyFeedPost: models.ids.AppBskyFeedPost,
}


def _get_ops_by_type(commit: models.ComAtprotoSyncSubscribeRepos.Commit) -> defaultdict:
    """
    Processes a commit message and extracts operations of interest, grouping them by record type.

    Args:
        commit: The commit message containing the operations.

    Returns:
        A defaultdict where each key is a record namespace ID, and the value is a dictionary with
        'created' and 'deleted' lists of operations.
    """
    # Initialize a defaultdict to store operations grouped by record type
    operations_by_type = defaultdict(lambda: {'created': [], 'deleted': []})

    # Parse the CAR (Content Addressable aRchive) from the commit blocks
    car = CAR.from_bytes(commit.blocks)

    # Iterate over the operations in the commit
    for op in commit.ops:
        if op.action == 'update':
            # Currently not interested in 'update' actions
            continue

        # Construct the URI for the operation
        uri = AtUri.from_str(f'at://{commit.repo}/{op.path}')

        if op.action == 'create':
            if not op.cid:
                # Skip if no CID is present
                continue

            # Prepare information about the creation operation
            create_info = {'uri': str(uri), 'cid': str(op.cid), 'author': commit.repo}

            # Retrieve the raw data of the record from the CAR blocks using the CID
            record_raw_data = car.blocks.get(op.cid)
            if not record_raw_data:
                # Skip if the record data is not found
                continue

            try:
                # Parse the raw data into a record object
                record = models.get_or_create(record_raw_data, strict=False)
            except Exception as e:
                logger.error(f"Failed to parse record: {e}")
                continue

            # Check if the record is of an interested type
            for record_type, record_nsid in _INTERESTED_RECORDS.items():
                if uri.collection == record_nsid and models.is_record_type(record, record_type):
                    # Add the record to the list of created operations for its type
                    operations_by_type[record_nsid]['created'].append({'record': record, **create_info})
                    break  # Found the record type, no need to check further

        elif op.action == 'delete':
            # Add the URI to the list of deleted operations for its type
            operations_by_type[uri.collection]['deleted'].append({'uri': str(uri)})

    return operations_by_type


def run(name, operations_callback, stream_stop_event=None):
    """
    Starts the firehose client and processes incoming messages.

    Args:
        name: The name of the service/subscription.
        operations_callback: A callback function to handle the operations extracted from messages.
        stream_stop_event: An optional threading.Event to signal when to stop the stream.
    """
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


def _run(name, operations_callback, stream_stop_event=None):
    """
    Connects to the firehose, sets up the message handler, and starts streaming messages.

    Args:
        name: The name of the service/subscription.
        operations_callback: A callback function to handle the operations extracted from messages.
        stream_stop_event: An optional threading.Event to signal when to stop the stream.
    """
    # Retrieve the last known cursor position from the database
    state = SubscriptionState.get_or_none(SubscriptionState.service == name)

    # Initialize parameters with the cursor if available
    params = None
    if state:
        params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=state.cursor)
    else:
        # If no state exists, create an initial subscription state with cursor 0
        SubscriptionState.create(service=name, cursor=0)

    # Initialize the firehose client w/o a cursor for now
    client = FirehoseSubscribeReposClient(params)

    def on_message_handler(message: firehose_models.MessageFrame) -> None:
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

        # Update the cursor every ~10,000 events
        if commit.seq % 10000 == 0:
            logger.info(f'Cursor -> {commit.seq}')
            # Update the client's parameters with the new cursor
            client.update_params(models.ComAtprotoSyncSubscribeRepos.Params(cursor=commit.seq))
            # Persist the new cursor in the database
            with db.atomic():
                SubscriptionState.update(cursor=commit.seq).where(SubscriptionState.service == name).execute()


        if not commit.blocks:
            # Skip if there are no blocks to process
            return

        # Extract operations from the commit
        operations = _get_ops_by_type(commit)
        # Pass the operations to the callback function
        operations_callback(operations)

    # Start the client with the message handler
    client.start(on_message_handler)

import sys
import threading
import signal

from utils import config
from utils.logger import logger
import data_stream as data_stream
from data_filter import operations_callback

def main():
    stream_stop_event = threading.Event()

    def handle_termination(signum, frame):
        logger.info(f'Received termination signal {signum}. Stopping firehose stream...')
        stream_stop_event.set()
        sys.exit(0)

    for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]:
        signal.signal(sig, handle_termination)

    while not stream_stop_event.is_set():
        try:
            data_stream.run(config.SERVICE_DID, operations_callback, stream_stop_event)
        except Exception as e:
            logger.error(f"An exception occurred in the firehose: {e}")
            logger.info("Restarting the firehose stream...")

if __name__ == '__main__':
    main()


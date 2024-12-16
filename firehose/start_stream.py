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

    signal.signal(signal.SIGINT, handle_termination)

    
    data_stream.run(config.SERVICE_DID, operations_callback, stream_stop_event)
    logger.info("firehose has exited")


if __name__ == '__main__':
    main()


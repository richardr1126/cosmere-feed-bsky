import sys
import signal

from utils import config
from utils.logger import logger
import data_stream as data_stream
from data_filter import operations_callback

class StopEvent:
    def __init__(self):
        self._stopped = False
    
    def set(self):
        self._stopped = True
    
    def is_set(self):
        return self._stopped

def main():
    stop_event = StopEvent()

    def handle_termination(signum, frame):
        logger.info(f'Received termination signal {signum}. Stopping firehose stream...')
        stop_event.set()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_termination)
    
    data_stream.run(config.SERVICE_DID, operations_callback, stop_event)
    logger.info("firehose has exited")


if __name__ == '__main__':
    main()


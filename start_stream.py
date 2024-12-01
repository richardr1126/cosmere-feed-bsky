import sys
import threading
import signal

from utils import config
import firehose.data_stream as data_stream
from firehose.data_filter import operations_callback

def main():
    stream_stop_event = threading.Event()

    def sigint_handler(*_):
        print('Stopping data stream...')
        stream_stop_event.set()
        sys.exit(0)

    signal.signal(signal.SIGINT, sigint_handler)

    data_stream.run(config.SERVICE_DID, operations_callback, stream_stop_event)

if __name__ == '__main__':
    main()

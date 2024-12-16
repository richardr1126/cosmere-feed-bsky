import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s |%(levelname)s| %(message)s',
  datefmt='%H:%M:%S'
)

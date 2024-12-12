import os

SERVICE_DID = os.environ.get('SERVICE_DID', None)
HOSTNAME = os.environ.get('HOSTNAME', None)
HANDLE = os.environ.get('HANDLE', None)
PASSWORD = os.environ.get('PASSWORD', None)

if HOSTNAME is None:
    raise RuntimeError('You should set "HOSTNAME" environment variable first.')

if SERVICE_DID is None:
    SERVICE_DID = f'did:web:{HOSTNAME}'


CHRONOLOGICAL_TRENDING_URI = os.environ.get('CHRONOLOGICAL_TRENDING_URI')
if CHRONOLOGICAL_TRENDING_URI is None:
    raise RuntimeError('Publish your feed first (run publish_feed.py) to obtain Feed URI. '
                       'Set this URI to "CHRONOLOGICAL_TRENDING_URI" environment variable.')

import os

SERVICE_DID = os.environ.get('SERVICE_DID', None)
HOSTNAME = os.environ.get('HOSTNAME', None)
HANDLE = os.environ.get('HANDLE', None)
PASSWORD = os.environ.get('PASSWORD', None)
POSTGRES_USER = os.environ.get('POSTGRES_USER', None)
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', None)
POSTGRES_DB = os.environ.get('POSTGRES_DB', None)
POSTGRES_HOST = os.environ.get('POSTGRES_HOST', None)
POSTGRES_PORT = os.environ.get('POSTGRES_PORT', None)

if POSTGRES_USER is None:
    raise RuntimeError('You should set "POSTGRES_USER" environment variable first.')
if POSTGRES_PASSWORD is None:
    raise RuntimeError('You should set "POSTGRES_PASSWORD" environment variable first.')
if POSTGRES_DB is None:
    raise RuntimeError('You should set "POSTGRES_DB" environment variable first.')
if POSTGRES_HOST is None:
    raise RuntimeError('You should set "POSTGRES_HOST" environment variable first.')
if POSTGRES_PORT is None:
    raise RuntimeError('You should set "POSTGRES_PORT" environment variable first.')

if HOSTNAME is None:
    raise RuntimeError('You should set "HOSTNAME" environment variable first.')

if SERVICE_DID is None:
    SERVICE_DID = f'did:web:{HOSTNAME}'


CHRONOLOGICAL_TRENDING_URI = os.environ.get('CHRONOLOGICAL_TRENDING_URI')
if CHRONOLOGICAL_TRENDING_URI is None:
    raise RuntimeError('Publish your feed first (run publish_feed.py) to obtain Feed URI. '
                       'Set this URI to "CHRONOLOGICAL_TRENDING_URI" environment variable.')

# logger.info(f'HANDLE: {HANDLE}')
# logger.info(f'PASSWORD: {PASSWORD}')
if HANDLE is None:
    raise RuntimeError('You should set "HANDLE" environment variable first.')

if PASSWORD is None:
    raise RuntimeError('You should set "PASSWORD" environment variable first.')

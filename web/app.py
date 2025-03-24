from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS
from firehose.utils import config
from firehose.utils.logger import logger
from web.algos import algos
from web.auth import AuthorizationError, validate_auth
from web.database_ro import Requests

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return '', 302, {'Location': 'https://bsky.app/profile/did:plc:wihwdzwkb6nd3wb565kujg2f/feed/cosmere'}

@app.route('/.well-known/did.json', methods=['GET'])
def did_json():
    if not config.SERVICE_DID.endswith(config.HOSTNAME):
        return '', 404

    return jsonify({
        '@context': ['https://www.w3.org/ns/did/v1'],
        'id': config.SERVICE_DID,
        'service': [
            {
                'id': '#bsky_fg',
                'type': 'BskyFeedGenerator',
                'serviceEndpoint': f'https://{config.HOSTNAME}'
            }
        ]
    })

@app.route('/xrpc/app.bsky.feed.describeFeedGenerator', methods=['GET'])
def describe_feed_generator():
    feeds = [{'uri': uri} for uri in algos.keys()]
    response = {
        'encoding': 'application/json',
        'body': {
            'did': config.SERVICE_DID,
            'feeds': feeds
        }
    }
    return jsonify(response)

@app.route('/xrpc/app.bsky.feed.getFeedSkeleton', methods=['GET'])
def get_feed_skeleton():
    # Add timeout handling
    if request.environ.get('wsgi.multithread'):
        request.environ['wsgi.input'].set_timeout(10)  # 10 second timeout
        
    feed = request.args.get('feed', default=None, type=str)
    algo = algos.get(feed)
    if not algo:
        return 'Unsupported algorithm', 400

    try:
        cursor = request.args.get('cursor', default=None, type=str)
        limit = request.args.get('limit', default=20, type=int)
        body = algo(cursor, limit)

        # Log the did of the requester in the database on first request
        if limit > 10 and cursor is None:
            try:
                requester_did = validate_auth(request)
                logger.info(f'Authorized user: {requester_did}')
                # Store the did in the database
                Requests.create(indexed_at=datetime.now(timezone.utc), did=requester_did)
            except AuthorizationError:
                logger.debug('Unauthorized user')
    except ValueError:
        return 'Malformed cursor', 400

    return jsonify(body)

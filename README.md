## Cosmere related ATProto Feed Generator powered by [The AT Protocol SDK for Python](https://github.com/MarshalX/atproto)

> Feed Generators are services that provide custom algorithms to users through the AT Protocol.

Official overview (read it first): https://github.com/bluesky-social/feed-generator#overview

### Getting Started

This simple server uses SQLite to store and query data. Data is cleaned and deleted after 3 days using `apscheduler` python package. It also hydrates the posts in the DB with an interaction score defined in `hydrate_posts_with_interactions()`. The interaction score is used in `algos/chrono_trending.py` to interleave trending posts into the chronological feed. The database code is in `firehose/database.py`.

### Setup

Install Python 3.7+, optionally create virtual environment.

Install dependencies:
```shell
pip install -r requirements.txt
```

Copy `.env.example` as `.env`. Fill the variables.

> **Note**
> To get value for "CHRONO_TRENDING_URI" you should publish the feed first. 

### Cloning my Cosmere Feed

If you want to clone to create your own feed, you will need to do a few things:
1. Install dependecies, fill in `example.env` and rename it to `.env`. Then, update top variables in `publish_feed.py`.
1. Change data filter tokens, phrases, account handles, and multi-tokens in `firehose/data_filter.py`.
2. Change database file name is `firehose/database.py` and `web/database_ro.py`. DB file auto-created if not exists.
3. Publish your feed (instructions below).

This server uses a did:web identifier. However, you're free to switch this out for did:plc if you like - you may want to if you expect this Feed Generator to be long-standing and possibly migrating domains.

### Publishing your feed

To publish your feed, go to the script at `publish_feed.py` and change the variables from my cosmere feed. To publish your feed generator, simply run `python publish_feed.py`. To update your feed's display data (name, avatar, description, etc.), just update the relevant variables and re-run the script.

After successfully running the script, you should be able to see your feed from within the app, as well as share it by embedding a link in a post (similar to a quote post).

### Running the Server

WSGI compatibility:
- uses `gunicorn` as the WSGI server for `/web/app.py` (web server)
- firehose is a seperate process done in `/firehose` and started with `start_stream.py` (firhose process)

Run server using `honcho`:
```shell
honcho start
```

Endpoints:
- /.well-known/did.json
- /xrpc/app.bsky.feed.describeFeedGenerator
- /xrpc/app.bsky.feed.getFeedSkeleton

### License

MIT

from datetime import datetime, timedelta, timezone
from utils.logger import logger
from utils.config import DEV_MODE
import peewee

file = 'file:/var/data/new_cosmere_feed.db?mode=ro' if not DEV_MODE else 'file:./new_cosmere_feed.db?mode=ro'

# Configure the read-only SQLite database connection using URI
db = peewee.SqliteDatabase(
    file,
    uri=True,
    timeout=30,
    pragmas={
        'journal_mode': 'wal',
        'cache_size': -1024 * 128,
        'busy_timeout': 30000
    }
)

class BaseModel(peewee.Model):
    class Meta:
        database = db


class Post(BaseModel):
    uri = peewee.CharField(index=True)
    cid = peewee.CharField()
    reply_parent = peewee.CharField(null=True, default=None)
    reply_root = peewee.CharField(null=True, default=None)
    indexed_at = peewee.DateTimeField(default=datetime.now(timezone.utc), index=True)
    author = peewee.CharField(null=True, default=None, index=True)
    interactions = peewee.BigIntegerField(default=0, index=True)


class SubscriptionState(BaseModel):
    service = peewee.CharField(unique=True)
    cursor = peewee.BigIntegerField()

class SessionState(BaseModel):
    service = peewee.CharField(unique=True)
    session_string = peewee.TextField(null=True)

if db.is_closed():
    try:
        db.connect()
        logger.info("Read-only database connection established.")
    except peewee.OperationalError as e:
        logger.error(f"Failed to connect to the database in read-only mode: {e}")

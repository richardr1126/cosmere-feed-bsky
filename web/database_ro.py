from datetime import datetime, timedelta, timezone
from utils.logger import logger
from firehose.utils.config import POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
import peewee

db = peewee.PostgresqlDatabase(POSTGRES_DB, user=POSTGRES_USER, password=POSTGRES_PASSWORD, host='postgres', port=5432)

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

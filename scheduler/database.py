from datetime import datetime, timedelta, timezone
from utils.config import POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, POSTGRES_HOST, POSTGRES_PORT
import peewee

# Database setup
db = peewee.PostgresqlDatabase(POSTGRES_DB, user=POSTGRES_USER, password=POSTGRES_PASSWORD, host=POSTGRES_HOST, port=POSTGRES_PORT)

# Database Models
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
    text = peewee.TextField(null=True, default=None)

class SubscriptionState(BaseModel):
    service = peewee.CharField(unique=True)
    cursor = peewee.BigIntegerField()
    last_indexed_at = peewee.DateTimeField(null=True, default=None)

class SessionState(BaseModel):
    service = peewee.CharField(unique=True)
    session_string = peewee.TextField(null=True)

# table for storing dids
class Requests(BaseModel):
    indexed_at = peewee.DateTimeField(default=datetime.now(timezone.utc), index=True)
    did = peewee.CharField(null=True, default=None, index=True)
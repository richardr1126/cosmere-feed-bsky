from datetime import datetime, timezone
import peewee
from firehose.database import Post as OldPost

# Old Postgres connection
old_db = peewee.PostgresqlDatabase(
    "cosmerefeed",
    user="admin-richard",
    password="xxx",
    host="192.168.0.11",  # If using docker-compose
    port=5432,
)

# New YugabyteDB connection
new_db = peewee.PostgresqlDatabase(
    "cosmerefeed",
    user="cosmerefeed",  # From yugabyte-values.yaml
    password="xxx",
    host="localhost",
    port=5433,  # YugabyteDB default port
)


# Define the same Post model for the new DB
class NewPost(peewee.Model):
    uri = peewee.CharField(index=True)
    cid = peewee.CharField()
    reply_parent = peewee.CharField(null=True, default=None)
    reply_root = peewee.CharField(null=True, default=None)
    indexed_at = peewee.DateTimeField(default=datetime.now(timezone.utc), index=True)
    author = peewee.CharField(null=True, default=None, index=True)
    interactions = peewee.BigIntegerField(default=0, index=True)

    class Meta:
        database = new_db


def migrate_data():
    # Create tables in new DB
    new_db.connect()
    new_db.create_tables([NewPost])

    # Connect to old DB
    old_db.connect()

    # Migrate in batches
    batch_size = 1000
    last_id = 0

    while True:
        posts = (
            OldPost.select()
            .where(OldPost.id > last_id)
            .order_by(OldPost.id)
            .limit(batch_size)
        )

        if not posts:
            break

        with new_db.atomic():
            for post in posts:
                NewPost.create(
                    uri=post.uri,
                    cid=post.cid,
                    reply_parent=post.reply_parent,
                    reply_root=post.reply_root,
                    indexed_at=post.indexed_at,
                    author=post.author,
                    interactions=post.interactions,
                )
                last_id = post.id

        print(f"Migrated batch up to ID {last_id}")


if __name__ == "__main__":
    migrate_data()

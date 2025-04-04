import peewee
from datetime import datetime, timezone
import random
import string
import time
import argparse
import concurrent.futures
from typing import List
import sys

# Database connection
db = peewee.PostgresqlDatabase(
    "cosmerefeed",
    user="cosmerefeed",
    password="xxxxx",
    host="192.168.0.72",
    port=5433,
)

class Post(peewee.Model):
    uri = peewee.CharField(index=True)
    cid = peewee.CharField()
    reply_parent = peewee.CharField(null=True, default=None)
    reply_root = peewee.CharField(null=True, default=None)
    indexed_at = peewee.DateTimeField(default=datetime.now(timezone.utc), index=True)
    author = peewee.CharField(null=True, default=None, index=True)
    interactions = peewee.BigIntegerField(default=0, index=True)

    class Meta:
        database = db
        db_table = "post"

def generate_random_string(length: int) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_test_post() -> dict:
    return {
        'uri': f"at://test.{generate_random_string(10)}/post/{generate_random_string(8)}",
        'cid': generate_random_string(32),
        'reply_parent': f"at://test.{generate_random_string(10)}/post/{generate_random_string(8)}" if random.random() > 0.7 else None,
        'reply_root': f"at://test.{generate_random_string(10)}/post/{generate_random_string(8)}" if random.random() > 0.7 else None,
        'indexed_at': datetime.now(timezone.utc),
        'author': f"test.{generate_random_string(8)}.bsky.social",
        'interactions': random.randint(0, 1000)
    }

def insert_batch(posts: List[dict]) -> float:
    start_time = time.time()
    with db.atomic():
        Post.insert_many(posts).execute()
    return time.time() - start_time

def cleanup_test_data():
    print("Cleaning up test data...")
    start_time = time.time()
    Post.delete().where(Post.uri.contains('at://test.')).execute()
    elapsed = time.time() - start_time
    print(f"Cleanup completed in {elapsed:.2f} seconds")
    #Vacuum the database to reclaim space
    db.execute_sql("VACUUM;")
    print("Database vacuumed.")

def run_stress_test(total_posts: int, batch_size: int, concurrent_batches: int):
    print(f"Starting stress test with {total_posts} posts...")
    print(f"Batch size: {batch_size}, Concurrent batches: {concurrent_batches}")
    
    total_batches = total_posts // batch_size
    times = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_batches) as executor:
        for batch_num in range(total_batches):
            test_posts = [generate_test_post() for _ in range(batch_size)]
            future = executor.submit(insert_batch, test_posts)
            times.append(future.result())
            
            if (batch_num + 1) % 10 == 0:
                print(f"Processed {(batch_num + 1) * batch_size} posts...")
    
    avg_time = sum(times) / len(times)
    print(f"\nTest completed!")
    print(f"Total time: {sum(times):.2f} seconds")
    print(f"Average batch insert time: {avg_time:.2f} seconds")
    print(f"Posts per second: {total_posts / sum(times):.2f}")

def main():
    parser = argparse.ArgumentParser(description='Database Stress Test Tool')
    parser.add_argument('--clean', action='store_true', help='Clean up test data')
    parser.add_argument('--total-posts', type=int, default=10000, help='Total number of posts to insert')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of posts per batch')
    parser.add_argument('--concurrent-batches', type=int, default=4, help='Number of concurrent batch insertions')
    
    args = parser.parse_args()
    
    try:
        db.connect()
        
        if args.clean:
            cleanup_test_data()
        else:
            run_stress_test(args.total_posts, args.batch_size, args.concurrent_batches)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()

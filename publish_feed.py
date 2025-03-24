#!/usr/bin/env python3
# YOU MUST INSTALL ATPROTO SDK
# pip3 install atproto

from atproto import Client, models
import os

# Load .env file from local directory
from dotenv import load_dotenv
load_dotenv()

# YOUR bluesky handle
# Ex: user.bsky.social
HANDLE: str = os.getenv('HANDLE')

# Ex: abcd-1234-efgh-5678
PASSWORD: str = os.getenv('PASSWORD')

# Ex: feed.bsky.dev
HOSTNAME: str = os.getenv('HOSTNAME')
print(HOSTNAME)

# A short name for the record that will show in urls
# Lowercase with no spaces.
# Ex: whats-hot
RECORD_NAME: str = 'cosmere'

# A display name for your feed
# Ex: What's Hot
DISPLAY_NAME: str = 'Cosmere'

# (Optional) A description of your feed
# Ex: Top trending content from the whole network
DESCRIPTION: str = "Realtime gateway into discussion being had about the Cosmere by Brandon Sanderson. #Stormlight #Mistborn\n\nCosmere feed is a mix of chronological and trending cosmere posts. Be careful for spoilers!\n\nKeywords + Code @ https://github.com/richardr1126/cosmere-feed-bsky?tab=readme-ov-file#filters"

# (Optional) The path to an image to be used as your feed's avatar
# Ex: ./path/to/avatar.jpeg
AVATAR_PATH: str = './cosmere.jpg'

# (Optional). Only use this if you want a service did different from did:web
SERVICE_DID: str = ''


# -------------------------------------
# NO NEED TO TOUCH ANYTHING BELOW HERE
# -------------------------------------


def main():
    client = Client()
    client.login(HANDLE, PASSWORD)

    feed_did = SERVICE_DID
    if not feed_did:
        feed_did = f'did:web:{HOSTNAME}'

    avatar_blob = None
    if AVATAR_PATH:
        with open(AVATAR_PATH, 'rb') as f:
            avatar_data = f.read()
            avatar_blob = client.upload_blob(avatar_data).blob

    response = client.com.atproto.repo.put_record(models.ComAtprotoRepoPutRecord.Data(
        repo=client.me.did,
        collection=models.ids.AppBskyFeedGenerator,
        rkey=RECORD_NAME,
        record=models.AppBskyFeedGenerator.Record(
            did=feed_did,
            display_name=DISPLAY_NAME,
            description=DESCRIPTION,
            avatar=avatar_blob,
            created_at=client.get_current_time_iso(),
        )
    ))

    print('Successfully published!')
    print('Feed URI (put in "WHATS_ALF_URI" env var):', response.uri)


if __name__ == '__main__':
    main()

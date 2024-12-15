# Cosmere ATProto Feed Generator PostgreSQL Server

![Docker](https://img.shields.io/docker/image-size/richardr1126/cosmere-feed-bsky/latest)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/Python-3.7%2B-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3.2-blue.svg)
![Gunicorn](https://img.shields.io/badge/Gunicorn-20.1.0-blue.svg)

## Overview

**Cosmere ATProto Feed Generator** is a tailored feed service for fans of Brandon Sanderson's Cosmere universe, built using the [AT Protocol SDK for Python](https://github.com/MarshalX/atproto). It filters and combines trending and chronological posts related to the Cosmere, delivering a curated content stream to users.

> This project builds upon the original [Python feed generator](https://github.com/MarshalX/bluesky-feed-generator) by [@MarshalX](https://github.com/MarshalX).

## Features

- Custom filtering using regexp:
   - **Tokens:** individual keywords, e.g., `mistborn` will match post with text `i love mistborn era 2` it also allows for pluralization, e.g., `mistborns` will match
- It integrates trending posts by calculating interaction scores and maintains the database by cleaning outdated entries with `apscheduler`
- Deployment is streamlined with Docker Compose to run the `web`, `firehose`, and `postgres` services
- Uses Docker compose to run the `web`, `firehose`, and `postgres` services
> **Note:** Posts are only kept for 30 days, and trending posts are calculated based on interactions within the last 24 hours

## Filters

The feed generator uses the following filters to curate content:

- **Tokens:** `allomancy`, `bondsmith`, `cosmere`, `dalinar`, `dawnshard`, `dragonsteel`, `dustbringer`, `edgedancer`, `elantris`, `elsecaller`, `stormblessed`, `thaidakar`, `kholin`, `lightweaver`, `mistborn`, `oathbringer`, `sanderlanche`, `sazed`, `shadesmar`, `skybreaker`, `spren`, `stoneward`, `stormlight`, `surgebinding`, `truthwatcher`, `warbreaker`, `willshaper`, `windrunner`, `roshar`, `scadrial`, `taldain`, `voidbringer`, `shardblade`, `shardplate`, `shardbearer`, `feruchemy`, `hemalurgy`, `lerasium`, `atium`, `mistcloak`, `kandra`, `koloss`, `skaa`, `highstorm`, `parshendi`, `urithiru`, `honorblade`, `surgebinder`, `dawnshard`, `worldhopper`, `perpendicularity`, `adonalsium`, `chasmfiend`, `worldbringer`, `allomancer`, `highspren`, `elantrian`, `inkspren`, `honorspren`, `cultivationspren`, `peakspren`, `ashspren`, `luckspren`, `windspren`, `lifespren`, `towerlight`, `voidlight`, `brandosando`, `numuhukumakiaki'ialunamor`, `dsnx24`, `dsnx2024`, `dragonsteelnexus`, `dragonsteelnexus2024`

- **Inclusive Multi-Tokens:** `brandon sanderson`, `yumi sanderson`, `vin elend`, `yumi painter`, `shallan adolin`, `kaladin syl`, `kaladin adolin`, `kaladin shallan`, `navani kholin`, `shallan pattern`, `shallan veil`, `shallan radiant`, `vin kelsier`, `kelsier survivor`, `wax wayne marasi`, `steris marasi`, `cryptic spren`, `steris wax`, `szeth nightblood`, `shades threnody`, `threnody hell`

- **Phrases:** `17th shard`, `bands of mourning`, `brandon sanderson`, `cognitive realm`, `rhythm of war`, `shadows of self`, `sixth of the dusk`, `shadows for silence`, `shadows of silence`, `ember dark`, `emperor's soul`, `isles of the ember dark`, `stormlight archive`, `sunlit man`, `alloy of law`, `hero of ages`, `lost metal`, `way of kings`, `well of ascension`, `tress of the emerald sea`, `wind and truth`, `words of radiance`, `yumi and the nightmare painter`, `shattered planes`, `knight radiant`, `knights radiant`, `journey before destination`, `life before death, strength before weakness`, `dragon steel nexus`

- **Handles to Include:** `stormlightmemes.bsky.social`, `brotherwisegames.bsky.social`

## Making your own Feed

1. **Update files:**
   - Update `publish_feed.py` with your feed details. **(REQUIRED)**
   - Modify feed post inclusion filters in `firehose/filter_config.py`. **(OPTIONAL)**
   - Update environment variables. **(REQUIRED)**

      ```shell
      cp example.env .env
      ```

2. **Publish Your Feed:** Follow the [Publishing Your Feed](#publishing-your-feed) instructions below.

## Publishing Your Feed

Edit publish_feed.py with your feed details and run:

```shell
python publish_feed.py
```

After successful publication, your feed will appear in the Bluesky app. Obtain the CHRONOLOGICAL_TRENDING_URI for the .env file from the output.

## Installation with Docker Compose

2. Edit .env with your settings:
```env
HOSTNAME=feed.yourdomain.com
HANDLE=your-handle.bsky.social
PASSWORD=your-password
CHRONOLOGICAL_TRENDING_URI=at://did:plc:abcde...
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-db-password
POSTGRES_DB=feed
```
> Note: Obtain CHRONOLOGICAL_TRENDING_URI by running publish_feed.py first.

3. Start the services:
```shell
docker compose up --build --remove-orphans
```

This will start:
- PostgreSQL database with attached volume for database persistence
- Firehose data stream python process
- Feed generator Web server with Gunicorn (4 workers)

## Endpoints

The server provides the following endpoints:

- **Well-Known DID Document:** `GET /.well-known/did.json`
- **Feed Generator Description:** `GET /xrpc/app.bsky.feed.describeFeedGenerator`
- **Feed Skeleton:** `GET /xrpc/app.bsky.feed.getFeedSkeleton`

## License

This project is licensed under the MIT License.

## Acknowledgements

Special thanks to [@MarshalX](https://github.com/MarshalX) for the foundational work on the AT Protocol SDK for Python, [Bluesky Social](https://atproto.com/) for the AT Protocol, and Brandon Sanderson for creating the inspiring Cosmere universe.

## Banned Content
- **Handles to Exclude:** `flintds.bsky.social`
- **Exclude Tokens:** `trump`, `sylvana`, `sylvanna`, `alleria`, `uriele`, `mormon`
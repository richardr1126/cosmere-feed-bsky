# Cosmere ATProto Feed Generator Flask Server

![Docker](https://img.shields.io/docker/image-size/richardr1126/cosmere-feed-bsky/latest)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/Python-3.7%2B-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3.2-blue.svg)
![Gunicorn](https://img.shields.io/badge/Gunicorn-20.1.0-blue.svg)

## Overview

**Cosmere ATProto Feed Generator** is a tailored feed service for fans of Brandon Sanderson's Cosmere universe, built using the [AT Protocol SDK for Python](https://github.com/MarshalX/atproto). It filters and combines trending and chronological posts related to the Cosmere, delivering a curated content stream to users.

> This project builds upon the original [Python feed generator](https://github.com/MarshalX/bluesky-feed-generator) by [@MarshalX](https://github.com/MarshalX).

## Features

- The generator offers custom filtering using SQLite and regular expressions to identify Cosmere-related content.
- It integrates trending posts by calculating interaction scores and maintains the database by cleaning outdated entries with `apscheduler`.
- Deployment is streamlined with `gunicorn` and managed using `honcho` (see Procfile) to run `web` seperatly from `firehose` data stream.
- Will run on **0.5 CPU**, **0.5 GB RAM**.
> **Note:** Posts are only kept for 3 days, and trending posts are calculated based on interactions within the last 24 hours.

## Filters

The feed generator uses the following filters to curate content:

- **Tokens:** `allomancy`, `bondsmith`, `cosmere`, `dalinar`, `dawnshard`, `dragonsteel`, `dustbringer`, `edgedancer`, `elantris`, `elsecaller`, `stormblessed`, `thaidakar`, `kholin`, `lightweaver`, `mistborn`, `oathbringer`, `sanderlanche`, `sazed`, `shadesmar`, `skybreaker`, `spren`, `stoneward`, `stormlight`, `surgebinding`, `truthwatcher`, `warbreaker`, `willshaper`, `windrunner`, `roshar`, `scadrial`, `taldain`, `voidbringer`, `shardblade`, `shardplate`, `shardbearer`, `feruchemy`, `hemalurgy`, `lerasium`, `atium`, `mistcloak`, `kandra`, `koloss`, `skaa`, `highstorm`, `parshendi`, `urithiru`, `honorblade`, `surgebinder`, `dawnshard`, `worldhopper`, `perpendicularity`, `adonalsium`, `chasmfiend`, `worldbringer`, `allomancer`, `highspren`, `elantrian`, `inkspren`, `honorspren`, `cultivationspren`, `peakspren`, `ashspren`, `luckspren`, `windspren`, `lifespren`, `towerlight`, `voidlight`, `brandosando`, `numuhukumakiaki'ialunamor`, `dsnx24`, `dsnx2024`, `dragonsteelnexus`, `dragonsteelnexus2024`

- **Inclusive Multi-Tokens:** `brandon sanderson`, `yumi sanderson`, `vin elend`, `yumi painter`, `shallan adolin`, `kaladin syl`, `kaladin adolin`, `kaladin shallan`, `navani kholin`, `shallan pattern`, `shallan veil`, `shallan radiant`, `vin kelsier`, `kelsier survivor`, `wax wayne marasi`, `steris marasi`, `cryptic spren`, `steris wax`, `szeth nightblood`, `shades threnody`, `threnody hell`

- **Phrases:** `17th shard`, `bands of mourning`, `brandon sanderson`, `cognitive realm`, `rhythm of war`, `shadows of self`, `sixth of the dusk`, `shadows for silence`, `shadows of silence`, `ember dark`, `emperor's soul`, `isles of the ember dark`, `stormlight archive`, `sunlit man`, `alloy of law`, `hero of ages`, `lost metal`, `way of kings`, `well of ascension`, `tress of the emerald sea`, `wind and truth`, `words of radiance`, `yumi and the nightmare painter`, `shattered planes`, `knight radiant`, `knights radiant`, `journey before destination`, `life before death, strength before weakness`, `dragon steel nexus`

- **Handles to Include:** `stormlightmemes.bsky.social`, `brotherwisegames.bsky.social`

## Features

The generator offers custom filtering using SQLite and regular expressions to identify Cosmere-related content. It integrates trending posts by calculating interaction scores and maintains the database by cleaning outdated entries with `apscheduler`. Deployment is streamlined with `gunicorn` and managed using `honcho`.

## Making your own Feed

1. **Update files:**
   - Update `publish_feed.py` with your feed details. **(REQUIRED)**
   - Modify filters in `firehose/data_filter.py`. **(OPTIONAL)**
   - Change database names/routes in `firehose/database.py` and `web/database_ro.py`. **(REQUIRED (unless using Docker))**
   > **Note:** Currently `/var/data/` is used for database storage in a Docker volume. Change this to a different path if needed.

2. **Publish Your Feed:** Follow the [Publishing Your Feed](#publishing-your-feed) instructions below.

## Easiest installation (Docker)

Configure the environment variables by copying and editing the example file:

```shell
cp example.env .env
```

Open `.env` in your preferred text editor and fill in the necessary variables.  
> **Note:** To obtain `CHRONO_TRENDING_URI`, publish the feed first using `publish_feed.py`.

Using docker-compose:
```shell
docker compose up --build --remove-orphans
```

Build and run Docker image:
```shell
docker build --rm -t myfeed .
docker run --rm -it --env-file .env -p 8000:8000 -v feeddata:/var/data/ myfeed
```


### Manual Installation

Ensure you have **Python 3.7+** and **Conda** installed. [Download Miniconda](https://docs.conda.io/en/latest/miniconda.html) if you haven't already.

### Prerequisites

Clone the repository and navigate to its directory:

```shell
git clone https://github.com/yourusername/cosmere-feed-generator.git
cd cosmere-feed-generator
```

Create and activate a Conda environment:

```shell
conda create --name cosmere-feed
conda activate cosmere-feed
```

Install the required dependencies:

```shell
pip install -r requirements.txt
```

## Publishing Your Feed

Edit the `publish_feed.py` script with your specific information such as `HANDLE`, `PASSWORD`, `HOSTNAME`, `RECORD_NAME`, `DISPLAY_NAME`, `DESCRIPTION`, and `AVATAR_PATH`. Run the script to publish your feed:

```shell
python publish_feed.py
```

To update your feed's display data, modify the relevant variables and rerun the script. After successful publication, access your feed via the Bluesky app and share the provided link as needed.

## Running the Server

The server operates two main processes: the web server and the firehose data stream. Use `honcho` to manage these processes as defined in the `Procfile`:

Manually run the server:
```shell
honcho start
```

This command will initiate both the `gunicorn` web server and the `start_stream.py` firehose process.

## Endpoints

The server provides the following endpoints:

- **Well-Known DID Document:** `GET /.well-known/did.json`
- **Feed Generator Description:** `GET /xrpc/app.bsky.feed.describeFeedGenerator`
- **Feed Skeleton:** `GET /xrpc/app.bsky.feed.getFeedSkeleton`

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgements

Special thanks to [@MarshalX](https://github.com/MarshalX) for the foundational work on the AT Protocol SDK for Python, [Bluesky Social](https://atproto.com/) for the AT Protocol, and Brandon Sanderson for creating the inspiring Cosmere universe.

## Banned Content
- **Handles to Exclude:** `flintds.bsky.social`

- **Exclude Tokens:** `trump`, `sylvana`, `sylvanna`, `alleria`, `uriele`, `mormon`
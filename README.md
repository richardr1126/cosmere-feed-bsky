# 🌟 Cosmere ATProto Feed Generator 🌎

<div align="center">

[![ATProtocol](https://img.shields.io/badge/ATProtocol-0066FF?style=for-the-badge&logo=atproto&logoColor=white)](#-)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](#-)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](#-)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](#-)
[![Gunicorn](https://img.shields.io/badge/Gunicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white)](#-)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](#-)

</div>

---

## 📖 Overview 

A specialized feed service for Brandon Sanderson's Cosmere universe fans, powered by the [AT Protocol SDK for Python](https://github.com/MarshalX/atproto). This service intelligently filters and combines trending and chronological posts to deliver a curated Cosmere content stream.

> 💫 Built upon the original [Python feed generator](https://github.com/MarshalX/bluesky-feed-generator) by [@MarshalX](https://github.com/MarshalX).

---

## ✨ Features

### Core Capabilities

- 🔍 **Smart Filtering** with advanced regexp:
  - ⚡ Individual keywords (with automatic plural forms)
  - 🔄 Multi-word tokens (order-independent matching)
  - 📝 Exact phrase matching
  - 👤 Specific handle inclusion

- 🐘 **PostgreSQL Database**
  - 🐳 Docker containerization
  - 💾 Persistent data storage

- 📈 **Trending Posts Integration**
  - ⚖️ Interaction score calculation
  - 🧹 Automated database cleanup via `apscheduler`

- 🐳 **Docker Compose Deployment**
  - 🔄 Orchestrates `web`, `firehose`, and `postgres` services

> ⚠️ **Note:** Posts are retained for 30 days, with trending calculations based on 24-hour interaction windows

---

## 🎯 Filters

### 🔤 Tokens
- `allomancy`, `bondsmith`, `cosmere`, `dalinar`, `dawnshard`, `dragonsteel`, `dustbringer`, `edgedancer`, `elantris`, `elsecaller`, `stormblessed`, `thaidakar`, `kholin`, `lightweaver`, `mistborn`, `oathbringer`, `sanderlanche`, `sazed`, `shadesmar`, `skybreaker`, `spren`, `stoneward`, `stormlight`, `surgebinding`, `truthwatcher`, `warbreaker`, `willshaper`, `windrunner`, `roshar`, `scadrial`, `taldain`, `voidbringer`, `shardblade`, `shardplate`, `shardbearer`, `feruchemy`, `hemalurgy`, `lerasium`, `atium`, `mistcloak`, `kandra`, `koloss`, `skaa`, `highstorm`, `parshendi`, `urithiru`, `honorblade`, `surgebinder`, `dawnshard`, `worldhopper`, `perpendicularity`, `adonalsium`, `chasmfiend`, `worldbringer`, `allomancer`, `highspren`, `elantrian`, `inkspren`, `honorspren`, `cultivationspren`, `peakspren`, `ashspren`, `luckspren`, `windspren`, `lifespren`, `towerlight`, `voidlight`, `brandosando`, `numuhukumakiaki'ialunamor`, `dsnx24`, `dsnx2024`, `dragonsteelnexus`, `dragonsteelnexus2024`

### 🔗 Inclusive Multi-Tokens
- `brandon sanderson`, `yumi sanderson`, `vin elend`, `yumi painter`, `shallan adolin`, `kaladin syl`, `kaladin adolin`, `kaladin shallan`, `navani kholin`, `shallan pattern`, `shallan veil`, `shallan radiant`, `vin kelsier`, `kelsier survivor`, `wax wayne marasi`, `steris marasi`, `cryptic spren`, `steris wax`, `szeth nightblood`, `shades threnody`, `threnody hell`

### 📝 Phrases
- `17th shard`, `bands of mourning`, `brandon sanderson`, `cognitive realm`, `rhythm of war`, `shadows of self`, `sixth of the dusk`, `shadows for silence`, `shadows of silence`, `ember dark`, `emperor's soul`, `isles of the ember dark`, `stormlight archive`, `sunlit man`, `alloy of law`, `hero of ages`, `lost metal`, `way of kings`, `well of ascension`, `tress of the emerald sea`, `wind and truth`, `words of radiance`, `yumi and the nightmare painter`, `shattered planes`, `knight radiant`, `knights radiant`, `journey before destination`, `life before death, strength before weakness`, `dragon steel nexus`

### 👥 Handles to Include
- `stormlightmemes.bsky.social`, `brotherwisegames.bsky.social`

---

## 🛠️ Making your own Feed

### 📋 Step 1: Initial Setup

<details open>
<summary><h4>🔧 Clone & Configure</h4></summary>

1. Clone the repository
   ```shell
   git clone [repository-url]
   cd [repository-name]
   ```

2. Create and configure environment variables
   ```shell
   cp example.env .env
   ```
   Edit `.env` with your settings:
   ```env
   HOSTNAME=feed.yourdomain.com          # Your feed domain
   HANDLE=your-handle.bsky.social        # Your Bluesky handle
   PASSWORD=your-password                # Your Bluesky password
   CHRONOLOGICAL_TRENDING_URI=           # Leave empty for now
   POSTGRES_USER=postgres                # Postgres user to create
   POSTGRES_PASSWORD=your-db-password    # Postgres password to create and use
   POSTGRES_DB=feed                      # Postgres db name to create and use
   ```

</details>

### 🛠️ Step 2: Configure Your Feed

<details open>
<summary><h4>⚙️ Edit Feed Details</h4></summary>

1. Edit `publish_feed.py` with your feed details:
   - `RECORD_NAME`: Short name for the feed identifier (lowercase, no spaces)
   - `DISPLAY_NAME`: User-facing feed name
   - `DESCRIPTION`: Feed description
   - `AVATAR_PATH`: Path to feed avatar image (optional)

2. Modify filters in `firehose/filter_config.json` (optional):
   - `HANDLES`: Accounts to always include
   - `EXCLUDE_HANDLES`: Accounts to always exclude
   - `PHRASES`: Exact phrases to match
   - `INCLUSIVE_MULTI_TOKENS`: Multi-word matches (any order)
   - `TOKENS`: Single words to match
   - `EXCLUDE_TOKENS`: Words to exclude

</details>

### 🚀 Step 3: Publish Your Feed

<details open>
<summary><h4>📤 Install & Run</h4></summary>

1. Install the ATProto SDK:
   ```shell
   pip install atproto
   ```

2. Run the publisher:
   ```shell
   python publish_feed.py
   ```

3. Copy the output Feed URI into your `.env` file as `CHRONOLOGICAL_TRENDING_URI`

</details>

### 🐳 Step 4: Deploy with Docker

<details open>
<summary><h4>🔥 Build & Start Services</h4></summary>

1. Ensure Docker and Docker Compose are installed

2. Build and start services:
   ```shell
   docker compose up --build
   ```

   This launches:
   - PostgreSQL database (with persistence)
   - Firehose data stream processor
   - Feed generator web server (4 Gunicorn workers)

3. Your feed should now be accessible at:
   ```
   https://bsky.app/profile/[your-handle]/feed/[record-name]
   ```

</details>

---

## 📡 Endpoints

The server provides the following endpoints:

- 🔑 **Well-Known DID Document:** `GET /.well-known/did.json`
- 📝 **Feed Generator Description:** `GET /xrpc/app.bsky.feed.describeFeedGenerator`
- 🔄 **Feed Skeleton:** `GET /xrpc/app.bsky.feed.getFeedSkeleton`

---

## 📜 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgements

Special thanks to:
- [@MarshalX](https://github.com/MarshalX) for the foundational work on the AT Protocol SDK for Python
- [Bluesky Social](https://atproto.com/) for the AT Protocol
- Brandon Sanderson for creating the inspiring Cosmere universe

---

## 🚫 Banned Content

### Exclusion Rules
- 🚫 **Handles to Exclude:** `flintds.bsky.social`
- ⛔ **Exclude Tokens:** `trump`, `sylvana`, `sylvanna`, `alleria`, `uriele`, `mormon`
# 🌟 Cosmere ATProto Feed Generator 🌎

<div align="center">

[![ATProtocol](https://img.shields.io/badge/ATProtocol-0066FF?style=for-the-badge&logo=atproto&logoColor=white)](#-)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](#-)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](#-)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](#-)
[![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?style=for-the-badge&logo=kubernetes&logoColor=white)](#-)

</div>

## 📖 Overview 

A specialized feed service for Brandon Sanderson's Cosmere universe fans, running on Kubernetes and powered by YugabyteDB. This service intelligently filters and combines trending and chronological posts to deliver a curated Cosmere content stream.

## 🏗️ Architecture

The application consists of several microservices deployed on a Kubernetes cluster:

- 🌐 **Web API Service** - Flask application serving the ATProto feed endpoints
- 🔥 **Firehose Service** - Processes the Bluesky firehose stream
- ⏰ **Scheduler Service** - Handles periodic tasks and database maintenance
- 📊 **YugabyteDB** - Distributed PostgreSQL-compatible database

### Infrastructure

- 🚀 Hosted on Rackspace Private Cloud (Spot)
- 🔒 SSL/TLS termination with cert-manager and Let's Encrypt
- 🌍 DNS management with external-dns and Cloudflare
- 🔄 Load balancing with NGINX ingress controller

## 🎯 Filters

### Keywords and Phrases
The feed uses a comprehensive set of filters to capture Cosmere-related content:

<details>
<summary>View Filter Categories</summary>

### 🔤 Tokens
- `allomancy`, `bondsmith`, `cosmere`, `dalinar`, `dawnshard`, `dragonsteel`, `dustbringer`, `edgedancer`, `elantris`, `elsecaller`, `stormblessed`, `thaidakar`, `kholin`, `lightweaver`, `mistborn`, `oathbringer`, `sanderlanche`, `sazed`, `shadesmar`, `skybreaker`, `spren`, `stoneward`, `stormlight`, `surgebinding`, `truthwatcher`, `warbreaker`, `willshaper`, `windrunner`, `roshar`, `scadrial`, `taldain`, `voidbringer`, `shardblade`, `shardplate`, `shardbearer`, `feruchemy`, `hemalurgy`, `lerasium`, `atium`, `mistcloak`, `kandra`, `koloss`, `skaa`, `highstorm`, `parshendi`, `urithiru`, `honorblade`, `surgebinder`, `dawnshard`, `worldhopper`, `perpendicularity`, `adonalsium`, `chasmfiend`, `worldbringer`, `allomancer`, `highspren`, `elantrian`, `inkspren`, `honorspren`, `cultivationspren`, `peakspren`, `ashspren`, `luckspren`, `windspren`, `lifespren`, `towerlight`, `voidlight`, `brandosando`, `numuhukumakiaki'ialunamor`, `dsnx24`, `dsnx2024`, `dragonsteelnexus`, `dragonsteelnexus2024`

### 🔗 Inclusive Multi-Tokens
- `brandon sanderson`, `yumi sanderson`, `vin elend`, `yumi painter`, `shallan adolin`, `kaladin syl`, `kaladin adolin`, `kaladin shallan`, `navani kholin`, `shallan pattern`, `shallan veil`, `shallan radiant`, `vin kelsier`, `kelsier survivor`, `wax wayne marasi`, `steris marasi`, `cryptic spren`, `steris wax`, `szeth nightblood`, `shades threnody`, `threnody hell`

### 📝 Phrases
- `17th shard`, `bands of mourning`, `brandon sanderson`, `cognitive realm`, `rhythm of war`, `shadows of self`, `sixth of the dusk`, `shadows for silence`, `shadows of silence`, `ember dark`, `emperor's soul`, `isles of the ember dark`, `stormlight archive`, `sunlit man`, `alloy of law`, `hero of ages`, `lost metal`, `way of kings`, `well of ascension`, `tress of the emerald sea`, `wind and truth`, `words of radiance`, `yumi and the nightmare painter`, `shattered planes`, `knight radiant`, `knights radiant`, `journey before destination`, `life before death, strength before weakness`, `dragon steel nexus`

### 👥 Handles to Include
- `stormlightmemes.bsky.social`, `brotherwisegames.bsky.social`

</details>

```mermaid
graph TD
    subgraph "Rackspace Spot Cloud"
        subgraph "Kubernetes Cluster"
            ingress[NGINX Ingress Controller]
            cert[cert-manager]
            dns[external-dns]
            
            subgraph "Application Services"
                api[Web API Service<br/>Flask - 3 replicas]
                firehose[Firehose Service]
                scheduler[Scheduler Service]
            end
            
            yugadb[(YugabyteDB<br/>Distributed Database)]
        end
    end
    
    internet((Internet)) -->|HTTPS| cf[Cloudflare DNS]
    cf -->|SSL/TLS| ingress
    ingress --> api
    
    bsky[Bluesky Network] -->|Firehose Stream| firehose
    firehose -->|Store Posts| yugadb
    scheduler -->|Maintenance| yugadb
    api -->|Read/Write| yugadb
```

---

## 🛠️ Infrastructure Setup

### Prerequisites
- Kubernetes cluster on Rackspace Spot
- `kubectl` configured with cluster access
- Helm v3 installed
- Docker for building images

### Environment Configuration
Create a `.env` file:
```env
HOSTNAME=cosmere.richardr.dev
HANDLE=your-handle.bsky.social
PASSWORD=your-password
CHRONOLOGICAL_TRENDING_URI=at://...
POSTGRES_USER=cosmerefeed
POSTGRES_PASSWORD=your-password
POSTGRES_DB=feed
POSTGRES_HOST=yugabyte-client.yugabyte.svc.cluster.local
POSTGRES_PORT=5433
GITHUB_PAT=your-github-pat
CLOUDFLARE_API_TOKEN=your-cloudflare-token
```

### Cloud Deployment

1. **Initialize Cluster Components**
```bash
cd k8s/helm/
./setup.sh --clear    # Only if you need to reset the cluster
./setup.sh --build    # Build and push all container images
```

2. **Verify Deployment**
```bash
./check_cluster.sh
```

This will display the status of:
- cert-manager pods
- YugabyteDB cluster
- Application pods
- Service endpoints

3. **Individual Component Updates**
```bash
# Update specific components
./setup.sh --build-web
./setup.sh --build-firehose
./setup.sh --build-scheduler
```

### Local Raspberry Pi Deployment

#### Prerequisites
- Raspberry Pi 5 (recommended 4GB+ RAM)
- Ubuntu Server or Raspberry Pi OS
- `k3sup` installed on your local machine
- `kubectl` installed on your local machine

#### K3s Cluster Setup

1. **Install K3s Server Node**
```bash
k3sup install \  
--ip 192.168.0.18 \
--tls-san 192.168.0.40 \
--cluster \
--k3s-extra-args '--disable servicelb traefik' \
--local-path ~/.kube/config \
--user richard-roberson
```
> Note you might need to manually remove all traefik deployments, pods, and services. This is due to the fact that k3sup will install traefik by default.

2. **Configure Virtual IP with kube-vip**

SSH into the K3s server node and setup kube-vip:
```bash
# Create manifests directory
sudo mkdir -p /var/lib/rancher/k3s/server/manifests/

# Download and apply RBAC configuration
sudo curl https://kube-vip.io/manifests/rbac.yaml | sudo tee /var/lib/rancher/k3s/server/manifests/kube-vip.yaml > /dev/null
echo -e "\n---" | sudo tee -a /var/lib/rancher/k3s/server/manifests/kube-vip.yaml

# Configure and deploy kube-vip
export VIP=192.168.0.40
export INTERFACE=eth0
KVVERSION=$(curl -sL https://api.github.com/repos/kube-vip/kube-vip/releases | jq -r ".[0].name")

alias kube-vip="sudo ctr image pull ghcr.io/kube-vip/kube-vip:$KVVERSION; sudo ctr run --rm --net-host ghcr.io/kube-vip/kube-vip:$KVVERSION vip /kube-vip"

kube-vip manifest daemonset \
  --interface $INTERFACE \
  --address $VIP \
  --inCluster \
  --taint \
  --controlplane \
  --services \
  --arp \
  --leaderElection | sudo tee -a /var/lib/rancher/k3s/server/manifests/kube-vip.yaml
```

3. **Setup kube-vip Cloud Provider**
```bash
# Deploy the cloud controller
kubectl apply -f https://raw.githubusercontent.com/kube-vip/kube-vip-cloud-provider/main/manifest/kube-vip-cloud-controller.yaml

# Configure IP range for services
kubectl create configmap -n kube-system kubevip --from-literal range-global=192.168.0.69-192.168.0.79
```

The local deployment will use:
- Virtual IP (kube-vip): 192.168.0.40 for the control plane
- Service IP Range: 192.168.0.69-192.168.0.79
- Cloudflare Tunnel for secure external access

## 📡 Service Endpoints

The feed is accessible at:
- 🌐 Public endpoint: `https://cosmere.richardr.dev`
- 🔑 ATProto endpoints:
  - `/.well-known/did.json`
  - `/xrpc/app.bsky.feed.describeFeedGenerator`
  - `/xrpc/app.bsky.feed.getFeedSkeleton`

## 📈 Monitoring

- Health checks are configured for all services
- Liveness and readiness probes ensure service availability
- Database metrics available through YugabyteDB dashboard

## 🚀 Scaling

- Web API horizontally scales with 3 replicas
- YugabyteDB runs with 3 master and 3 tserver nodes
- Firehose and scheduler are single-instance services

## 📜 License

This project is licensed under the MIT License.

---

<div align="center">
💫 Powering Cosmere discussions on Bluesky
</div>
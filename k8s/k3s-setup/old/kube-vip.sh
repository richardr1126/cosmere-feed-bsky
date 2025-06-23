# SSH into the K3s server node and run the following commands:
sudo mkdir -p /var/lib/rancher/k3s/server/manifests/

sudo curl https://kube-vip.io/manifests/rbac.yaml | sudo tee /var/lib/rancher/k3s/server/manifests/kube-vip.yaml > /dev/null
echo -e "\n---" | sudo tee -a /var/lib/rancher/k3s/server/manifests/kube-vip.yaml

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

# Edit and add the following to the env of the kube-vip.yaml file:
# - name: enableUPNP
#   value: "true"

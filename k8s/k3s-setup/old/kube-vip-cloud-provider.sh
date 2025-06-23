# Run from kubectl anywhere
kubectl apply -f https://raw.githubusercontent.com/kube-vip/kube-vip-cloud-provider/main/manifest/kube-vip-cloud-controller.yaml
kubectl create configmap -n kube-system kubevip --from-literal range-global=192.168.0.69-192.168.0.79

kubectl annotate service traefik -n kube-system kube-vip.io/forwardUPNP="true"
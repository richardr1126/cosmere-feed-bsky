# Run from kubectl anywhere
kubectl apply -f https://raw.githubusercontent.com/kube-vip/kube-vip-cloud-provider/main/manifest/kube-vip-cloud-controller.yaml
kubectl create configmap -n kube-system kubevip --from-literal range-global=192.168.0.69-192.168.0.79

kubectl delete crd aiservices.hub.traefik.io \
  apiaccesses.hub.traefik.io \
  apicatalogitems.hub.traefik.io \
  ingressrouteudps.traefik.io \
  accesscontrolpolicies.hub.traefik.io \
  apibundles.hub.traefik.io \
  apiplans.hub.traefik.io \
  apiportals.hub.traefik.io \
  apiratelimits.hub.traefik.io \
  apis.hub.traefik.io \
  apiversions.hub.traefik.io \
  ingressroutes.traefik.io \
  middlewares.traefik.io \
  managedsubscriptions.hub.traefik.io \
  middlewaretcps.traefik.io \
  ingressroutetcps.traefik.io \
  tlsoptions.traefik.io \
  tlsstores.traefik.io \
  serverstransports.traefik.io \
  serverstransporttcps.traefik.io \
  traefikservices.traefik.io --ignore-not-found 
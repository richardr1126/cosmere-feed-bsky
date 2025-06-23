k3sup install --ip 192.168.0.18 \
  --tls-san 192.168.0.40 \
  --cluster \
  --k3s-extra-args '--disable servicelb' \
  --local-path ~/.kube/raspberry-pi-kubeconfig.yaml \
  --user richard-roberson
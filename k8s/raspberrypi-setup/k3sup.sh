k3sup install \  
--ip 192.168.0.18 \
--tls-san 192.168.0.40 \
--cluster \
--k3s-extra-args '--disable servicelb traefik' \
--local-path ~/.kube/config \
--user richard-roberson
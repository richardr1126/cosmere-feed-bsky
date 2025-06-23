# Use ssh-copy-id to copy the public key to the node
# ssh-copy-id richard-roberson@192.168.0.30

# Add below to sudo visudo on node
# # For k3sup
# richard-roberson ALL=(ALL) NOPASSWD: ALL

k3sup join --ip 192.168.0.30 \
  --server-ip 192.168.0.18 \
  --server \
  --k3s-channel latest \
  --user richard-roberson
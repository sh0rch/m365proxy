#!/bin/bash

set -e

IMAGE="sh0rch/m365proxy:latest"
CONFIG_DIR="$PWD/config"
QUEUE_DIR="$PWD/queue"
M365_PROXY_CONFIG_FILE="/config/config.json"

mkdir -p "$CONFIG_DIR" "$QUEUE_DIR"

echo "[INFO] Pulling latest Docker image..."
docker pull $IMAGE

echo "[INFO] Running interactive configuration..."
docker run --rm -it -v "$CONFIG_DIR:/config" $IMAGE -config $M365_PROXY_CONFIG_FILE configure || true

echo "[INFO] Running Microsoft 365 login..."
docker run --rm -it -v "$CONFIG_DIR:/config" $IMAGE -config $M365_PROXY_CONFIG_FILE login || true

echo "[INFO] Removing previous container if exists..."
docker rm -f m365proxy 2>/dev/null || true

echo "[INFO] Starting m365proxy container..."
CID=$(docker run -d --name m365proxy \
  -v "$CONFIG_DIR:/config" \
  -v "$QUEUE_DIR:/app/queue" \
  -e "M365_PROXY_CONFIG_FILE=$M365_PROXY_CONFIG_FILE" \
  -p 10025:10025 -p 10110:10110 -p 10465:10465 -p 10995:10995 \
  $IMAGE)

sleep 2
STATUS=$(docker inspect -f '{{.State.Status}}' "$CID")

if [ "$STATUS" = "running" ]; then
  echo "[DONE] m365proxy is now running in the background (container ID: $CID)."
else
  echo "[ERROR] m365proxy failed to start. Check logs with:"
  echo "  docker logs $CID"
  exit 1
fi

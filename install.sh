#!/bin/bash

set -e

IMAGE="sh0rch/m365proxy:latest"
CONFIG_DIR="$PWD/config"
QUEUE_DIR="$PWD/queue"

mkdir -p "$CONFIG_DIR" "$QUEUE_DIR"

if [ ! -f "$CONFIG_DIR/config.json" ]; then
  echo "[INFO] Creating empty config.json..."
  echo "{}" > "$CONFIG_DIR/config.json"
fi

echo "[INFO] Pulling latest Docker image..."
docker pull $IMAGE

echo "[INFO] Running interactive configuration..."
docker run --rm -it -v "$CONFIG_DIR:/config" $IMAGE -config /config/config.json configure || true

echo "[INFO] Running Microsoft 365 login..."
docker run --rm -it -v "$CONFIG_DIR:/config" $IMAGE -config /config/config.json login || true

echo "[INFO] Starting m365proxy container..."
docker run -d --name m365proxy \
  -v "$CONFIG_DIR:/config" \
  -v "$QUEUE_DIR:/app/queue" \
  -p 10025:10025 -p 10110:10110 -p 10465:10465 -p 10995:10995 \
  $IMAGE

echo "[DONE] m365proxy is now running in the background."

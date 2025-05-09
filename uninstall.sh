#!/bin/bash

set -e

CONTAINER_NAME="m365proxy"
IMAGE="sh0rch/m365proxy:mini"

echo "[INFO] Stopping container..."
docker stop "$CONTAINER_NAME" || true

echo "[INFO] Removing container..."
docker rm "$CONTAINER_NAME" || true

echo "[INFO] Removing image..."
docker rmi "$IMAGE" || true

echo "[INFO] Done. Configuration and mail queue directories were not removed."
echo "To fully clean up, delete the following directories manually:"
echo "  $(pwd)/config"
echo "  $(pwd)/queue"
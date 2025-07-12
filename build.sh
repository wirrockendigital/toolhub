#!/bin/bash
# build.sh - Build and push multi-architecture Docker image for Toolhub

# Create or select a buildx builder
docker buildx create --use --name toolhub-builder 2>/dev/null || true

# Build for amd64 and arm64, tag and push to GHCR
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/wirrockendigital/toolhub:latest \
  --push \
  .
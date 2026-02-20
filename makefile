# Makefile für toolhub

GHCR_REPO=ghcr.io/wirrockendigital/toolhub
IMAGE_TAG=latest
LOCAL_PLATFORM?=linux/amd64
PLATFORMS?=linux/amd64,linux/arm64

.PHONY: build push run clean wol-test

build:
	docker buildx build --platform=$(LOCAL_PLATFORM) \
		-t $(GHCR_REPO):$(IMAGE_TAG) \
		--load .

push:
	docker buildx build --platform=$(PLATFORMS) \
		-t $(GHCR_REPO):$(IMAGE_TAG) \
		--push .

run:
	docker run -it --rm $(GHCR_REPO):$(IMAGE_TAG) /bin/bash

clean:
	docker rmi $(GHCR_REPO):$(IMAGE_TAG) || true

wol-test:
	./tools/wol-cli/test-wol.sh

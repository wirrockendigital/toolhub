# Makefile für toolhub

GHCR_REPO=ghcr.io/wirrockendigital/toolhub
IMAGE_TAG=latest
PLATFORM=linux/amd64

.PHONY: build push run clean

build:
	docker buildx build --platform=$(PLATFORM) \
		-t $(GHCR_REPO):$(IMAGE_TAG) \
		--load .

push:s
	docker buildx build --platform=$(PLATFORM) \
		-t $(GHCR_REPO):$(IMAGE_TAG) \
		--push .

run:
	docker run -it --rm $(GHCR_REPO):$(IMAGE_TAG) /bin/bash

clean:
	docker rmi $(GHCR_REPO):$(IMAGE_TAG) || true
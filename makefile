# Makefile für toolhub

IMAGE_NAME=toolhub
IMAGE_TAG=latest
GHCR_REPO=ghcr.io/wirrockendigital/$(IMAGE_NAME)
PLATFORM=linux/amd64

.PHONY: build tag push run clean

build:
	docker build --platform=$(PLATFORM) -t $(IMAGE_NAME):$(IMAGE_TAG) .

tag:
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(GHCR_REPO):$(IMAGE_TAG)

push:
	docker push $(GHCR_REPO):$(IMAGE_TAG)

run:
	docker run -it --rm $(IMAGE_NAME):$(IMAGE_TAG) /bin/bash

clean:
	docker rmi $(IMAGE_NAME):$(IMAGE_TAG) $(GHCR_REPO):$(IMAGE_TAG) || true
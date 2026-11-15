# ==============================================================================
# Podman deployment Makefile for the SEAD Authority Service
#
# Run targets from this directory. The runtime directory is ~/container for the
# deployment user: it holds this bundle, the .env file, the mounted config/
# directory, and the writable logs/ directory. Image build and publication
# targets are in Makefile.dev and are not copied to the deployment user.
# ==============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

BUNDLE_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
DEPLOY_DIR ?= $(HOME)/container
ENV_TEMPLATE ?= $(BUNDLE_DIR).env.example
CONFIG_SOURCE_DIR ?= $(BUNDLE_DIR)../../config
CONFIG_FILES := config.yml entities.yml prompts.yml identity_policy.yml
SYNC_CONFIG ?= false
COMPOSE_FILE := podman-compose.yml
COMPOSE := podman-compose -f $(COMPOSE_FILE)
SERVICE_NAME := sead-authority-service
SERVICE_UNIT := service/$(SERVICE_NAME).service
SERVICE_DIR := $(HOME)/.config/systemd/user
RUNTIME_FILES := podman-compose.yml Makefile .env.example $(SERVICE_UNIT)
IMAGE_REF := ghcr.io/humlab-sead/sead_authority_service

# Runtime values come from the deployment .env when present.
ENV_FILE := $(DEPLOY_DIR)/.env
SEAD_AUTHORITY_PORT := $(shell sed -n 's/^SEAD_AUTHORITY_PORT=\(.*\)/\1/p' $(ENV_FILE) 2>/dev/null | tail -1)
IMAGE_TAG := $(shell sed -n 's/^SEAD_AUTHORITY_IMAGE_TAG=\(.*\)/\1/p' $(ENV_FILE) 2>/dev/null | tail -1)

.PHONY: help
help:
	@echo "SEAD Authority Service - rootless Podman deployment"
	@echo ""
	@echo "  make setup             Create runtime dirs and .env; preserve existing config by default"
	@echo "  make setup SYNC_CONFIG=true  Replace the four mounted config files from CONFIG_SOURCE_DIR"
	@echo "  make pull              Pull the image tag named by .env"
	@echo "  make up                Start the service"
	@echo "  make down              Stop the service"
	@echo "  make restart           Restart the service"
	@echo "  make logs              Follow service logs"
	@echo "  make status            Show container status"
	@echo "  make healthcheck       Check /is_alive on the host port"
	@echo "  make config            Render the resolved compose configuration"
	@echo "  make service-install   Install the systemd user unit"
	@echo "  make service-enable    Enable and start the user unit at boot (enables linger)"

# ---------------------------------------------------------------------------
# First-time setup
# ---------------------------------------------------------------------------

.PHONY: setup
setup:
	@mkdir -p "$(DEPLOY_DIR)/logs" "$(DEPLOY_DIR)/config"
	@for f in $(RUNTIME_FILES); do \
		mkdir -p "$(DEPLOY_DIR)/$$(dirname "$$f")"; \
		if ! cmp -s "$(BUNDLE_DIR)$$f" "$(DEPLOY_DIR)/$$f" 2>/dev/null; then \
			cp "$(BUNDLE_DIR)$$f" "$(DEPLOY_DIR)/$$f"; \
		fi; \
	done
	@if [ ! -f "$(ENV_FILE)" ]; then \
		cp "$(ENV_TEMPLATE)" "$(ENV_FILE)"; \
		chmod 600 "$(ENV_FILE)"; \
		echo "Created $(ENV_FILE) from the example. Edit it before starting."; \
	else \
		echo "Keeping existing $(ENV_FILE)."; \
	fi
	@for f in $(CONFIG_FILES); do \
		if [ ! -f "$(CONFIG_SOURCE_DIR)/$$f" ]; then \
			echo "Missing configuration source: $(CONFIG_SOURCE_DIR)/$$f" >&2; \
			exit 1; \
		fi; \
	done; \
	has_config=false; \
	for f in $(CONFIG_FILES); do \
		if [ -e "$(DEPLOY_DIR)/config/$$f" ]; then has_config=true; fi; \
	done; \
	if [ "$$has_config" = false ]; then \
		cp $(foreach f,$(CONFIG_FILES),"$(CONFIG_SOURCE_DIR)/$(f)") "$(DEPLOY_DIR)/config/"; \
		echo "Initialized $(DEPLOY_DIR)/config from $(CONFIG_SOURCE_DIR)."; \
	else \
		drifted=""; \
		for f in $(CONFIG_FILES); do \
			source_file="$(CONFIG_SOURCE_DIR)/$$f"; \
			target_file="$(DEPLOY_DIR)/config/$$f"; \
			if [ ! -f "$$target_file" ] || ! cmp -s "$$source_file" "$$target_file"; then \
				drifted="$$drifted $$f"; \
				if [ "$(SYNC_CONFIG)" = "true" ]; then \
					cp "$$source_file" "$$target_file"; \
					echo "Synchronized configuration: $$f"; \
				elif [ ! -f "$$target_file" ]; then \
					echo "WARNING: configuration file is missing and was preserved: $$target_file"; \
				else \
					echo "WARNING: configuration drift detected and preserved: $$target_file"; \
				fi; \
			else \
				echo "Configuration matches source: $$f"; \
			fi; \
		done; \
		if [ -n "$$drifted" ] && [ "$(SYNC_CONFIG)" != "true" ]; then \
			echo "         Review differences; rerun with SYNC_CONFIG=true to replace these files:$$drifted"; \
		fi; \
	fi
	@echo "Deployment directory $(DEPLOY_DIR) is ready."

# ---------------------------------------------------------------------------
# Pull the published image
# ---------------------------------------------------------------------------

.PHONY: pull
pull:
	podman pull $(IMAGE_REF):$(if $(IMAGE_TAG),$(IMAGE_TAG),latest)

# ---------------------------------------------------------------------------
# Lifecycle (run the compose project from the deployment directory)
# ---------------------------------------------------------------------------

.PHONY: up
up:
	@cd $(DEPLOY_DIR) && $(COMPOSE) up -d

.PHONY: down
down:
	@cd $(DEPLOY_DIR) && $(COMPOSE) down

.PHONY: restart
restart:
	@cd $(DEPLOY_DIR) && $(COMPOSE) down && $(COMPOSE) up -d

.PHONY: logs
logs:
	@cd $(DEPLOY_DIR) && $(COMPOSE) logs -f sead-authority-service

.PHONY: status
status:
	@cd $(DEPLOY_DIR) && $(COMPOSE) ps

.PHONY: config
config:
	@cd $(DEPLOY_DIR) && $(COMPOSE) config

.PHONY: healthcheck
healthcheck:
	curl -fsS http://localhost:$(if $(SEAD_AUTHORITY_PORT),$(SEAD_AUTHORITY_PORT),8024)/is_alive
	@echo "Health check completed."

# ---------------------------------------------------------------------------
# Systemd user service (boot startup; requires loginctl enable-linger)
# ---------------------------------------------------------------------------

.PHONY: service-install
service-install:
	mkdir -p $(SERVICE_DIR)
	cp $(BUNDLE_DIR)$(SERVICE_UNIT) $(SERVICE_DIR)/
	systemctl --user daemon-reload
	@echo "Installed $(SERVICE_NAME).service. Run 'make service-enable' to start it at boot."

.PHONY: service-enable
service-enable:
	loginctl enable-linger $$USER
	systemctl --user enable --now $(SERVICE_NAME).service
	@echo "Enabled $(SERVICE_NAME).service with lingering. Check: systemctl --user status $(SERVICE_NAME)"

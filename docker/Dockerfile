# Optimized Multi-stage Dockerfile for SEAD Authority Service
# Implements performance optimizations from CI_CD_PERFORMANCE_ANALYSIS.md
#
# Key Optimizations:
# 1. Dependencies installed BEFORE code copy (better layer caching)
# 2. Regular install instead of editable (-e) install
# 3. BuildKit cache mounts for pip
# 4. Optional: uv for faster package installation
# 5. Supports both local build and GitHub clone
#
# Usage:
#   Local build:  docker build -f docker/Dockerfile -t sead-authority-service .
#   From GitHub:  docker build -f docker/Dockerfile --build-arg FROM_GITHUB=true --build-arg GIT_TAG=v1.0.0 -t sead-authority-service .
#   With uv:      docker build -f docker/Dockerfile --build-arg USE_UV=true -t sead-authority-service .

# Stage 1: Builder
FROM python:3.13-slim as builder

# Build arguments
ARG USE_UV=false
ARG FROM_GITHUB=false
ARG GIT_TAG=main
ARG GIT_REPO=https://github.com/humlab-sead/sead_authority_service.git

# Set working directory
WORKDIR /build

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv if requested (much faster than pip)
RUN if [ "$USE_UV" = "true" ]; then \
        pip install --no-cache-dir uv; \
    fi

# ✅ Get source code based on FROM_GITHUB setting
# If FROM_GITHUB=true: clone from repository
# If FROM_GITHUB=false: copy from local context
RUN if [ "$FROM_GITHUB" = "true" ]; then \
        echo "Building from GitHub: ${GIT_REPO}@${GIT_TAG}" && \
        git clone --depth 1 --branch ${GIT_TAG} ${GIT_REPO} . && \
        rm -rf .git; \
    else \
        echo "Building from local context"; \
    fi

# Copy files from local context (only effective when FROM_GITHUB=false)
# When FROM_GITHUB=true, these files already exist from git clone
# ✅ OPTIMIZATION: Copy dependency files first for better caching
COPY --chown=root:root pyproject.toml README.md ./

# ✅ OPTIMIZATION: Install dependencies with cache mount
# BuildKit cache mount persists pip cache across builds
# ✅ OPTIMIZATION: Use regular install (not editable -e)
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "$USE_UV" = "true" ]; then \
        uv pip install --system --no-cache .; \
    else \
        pip install --no-cache-dir --upgrade pip && \
        pip install --no-cache-dir .; \
    fi

# ✅ OPTIMIZATION: Copy application code AFTER dependencies
# Only effective when FROM_GITHUB=false; files already exist when FROM_GITHUB=true
COPY --chown=root:root src ./src
COPY --chown=root:root main.py ./

# Stage 2: Runtime
FROM python:3.13-slim

# Build arguments for runtime configuration
ARG APP_PORT=8000

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOME=/app \
    APP_PORT=${APP_PORT}

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR ${APP_HOME}

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /build/src ./src
COPY --from=builder /build/main.py ./

# Create directories for logs and data
RUN mkdir -p logs data && \
    chown -R appuser:appuser ${APP_HOME}

# Switch to non-root user
USER appuser

# Expose port
EXPOSE ${APP_PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${APP_PORT}/is_alive || exit 1

# Default command - can be overridden in docker-compose
CMD uvicorn main:app --host 0.0.0.0 --port ${APP_PORT}

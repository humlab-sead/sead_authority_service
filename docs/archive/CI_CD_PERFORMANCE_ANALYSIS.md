# CI/CD Build Performance Analysis

## Executive Summary

This document provides a comprehensive analysis of the Docker build workflow performance for the SEAD Authority Service, identifying bottlenecks and providing actionable optimization recommendations.

## Current Configuration

### Workflow: `.github/workflows/docker-build.yml`
- **Platforms**: linux/amd64, linux/arm64 (multi-arch)
- **Caching**: GitHub Actions cache (type=gha, mode=max)
- **Dockerfile**: Multi-stage build (builder + runtime)
- **Python Version**: 3.13-slim
- **Triggers**: Push to main/dev, tags (v*), PRs, manual dispatch

### Build Stages
1. **Builder Stage**: Install build dependencies, copy source, install Python packages
2. **Runtime Stage**: Install runtime dependencies, copy from builder, set up user/permissions

## Performance Bottlenecks Identified

### 1. Multi-Architecture Build Overhead ⚠️ HIGH IMPACT
**Current**: Building for both `linux/amd64` and `linux/arm64` simultaneously

**Impact**: 
- Doubles build time (each architecture built separately)
- Typical overhead: **2-3x slower** than single-arch builds
- For Python projects, arm64 may not be critical unless deploying to ARM infrastructure

**Evidence**:
```yaml
platforms: linux/amd64,linux/arm64
```

**Recommendation**: 
- If not deploying to ARM (Apple Silicon servers, AWS Graviton, etc.), remove arm64
- Consider conditional builds: arm64 only on tagged releases, not every commit

### 2. Redundant Dependency Installation 🔴 CRITICAL
**Current**: Using `pip install -e .` (editable install) in builder

**Issues**:
- Editable installs are slower than regular installs
- Not necessary in Docker containers (code is already copied)
- Installs unnecessary development metadata

**Evidence**:
```dockerfile
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .
```

**Recommendation**: Use `pip install .` instead of `pip install -e .`

### 3. Inefficient Layer Caching 🟡 MEDIUM IMPACT
**Current**: Copying all files before dependency installation

**Issue**: 
- Any code change invalidates dependency cache layer
- Dependencies rebuild even when pyproject.toml hasn't changed
- Not leveraging Docker layer caching effectively

**Evidence**:
```dockerfile
COPY pyproject.toml ./
COPY README.md ./
COPY src ./src         # ← Code changes invalidate next layer
COPY main.py ./
RUN pip install ...    # ← Rebuilt on every code change
```

**Recommendation**: Install dependencies BEFORE copying application code

### 4. Suboptimal pip Caching Strategy 🟡 MEDIUM IMPACT
**Current**: Using `--no-cache-dir` which prevents pip from caching downloads

**Issue**:
- Downloads packages fresh every time
- Slower builds, especially for large dependencies (psycopg, openai, etc.)
- GitHub Actions has 10GB cache limit - plenty for pip cache

**Recommendation**: Use pip cache mount with BuildKit

### 5. Missing Parallel Step Opportunities 🟢 LOW IMPACT
**Current**: Sequential execution of all steps

**Opportunity**: Some steps could run in parallel:
- Metadata extraction doesn't depend on checkout completion
- Could split tests/linting into separate job

### 6. apt-get Updates in Both Stages 🟡 MEDIUM IMPACT
**Current**: Running `apt-get update` twice (builder + runtime)

**Impact**: 
- Network overhead
- ~10-30 seconds per stage
- Package lists downloaded twice

**Recommendation**: Consolidate or use base image with pre-installed packages

## Optimization Recommendations

### Priority 1: Quick Wins (Immediate Implementation)

#### 1.1 Optimize Dockerfile Layer Order
```dockerfile
# Stage 1: Builder - OPTIMIZED
FROM python:3.13-slim as builder

WORKDIR /build

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# ✅ Install dependencies FIRST (separate layer)
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# ✅ Copy code AFTER dependencies (code changes don't invalidate deps)
COPY src ./src
COPY main.py ./
```

**Expected Improvement**: 50-70% faster rebuilds when only code changes

#### 1.2 Remove Editable Install
```dockerfile
# BEFORE
RUN pip install --no-cache-dir -e .

# AFTER
RUN pip install --no-cache-dir .
```

**Expected Improvement**: 10-15% faster dependency installation

#### 1.3 Conditional Multi-Arch Builds
```yaml
# Option A: Only build arm64 on releases
- name: Build and push Docker image
  id: build
  uses: docker/build-push-action@v5
  with:
    platforms: ${{ github.ref_type == 'tag' && 'linux/amd64,linux/arm64' || 'linux/amd64' }}
```

**Expected Improvement**: 50% faster builds on non-release commits

### Priority 2: Advanced Optimizations

#### 2.1 Use pip Cache Mount
```dockerfile
# Stage 1: Builder - WITH CACHE MOUNT
FROM python:3.13-slim as builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml README.md ./

# ✅ Use BuildKit cache mount for pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install .

# Copy application code
COPY src ./src
COPY main.py ./
```

**Expected Improvement**: 30-40% faster dependency installation (cached downloads)

#### 2.2 Use uv for Faster Package Installation
Replace pip with [uv](https://github.com/astral-sh/uv) - extremely fast Python package installer:

```dockerfile
# Stage 1: Builder - WITH UV
FROM python:3.13-slim as builder

WORKDIR /build

# Install uv (very fast Python package installer)
RUN pip install --no-cache-dir uv

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml README.md ./

# ✅ Use uv instead of pip (10-100x faster)
RUN uv pip install --system .

# Copy application code
COPY src ./src
COPY main.py ./
```

**Expected Improvement**: 5-10x faster package installation (uv is extremely fast)

**Note**: You already have `uv.lock` in the project, so you're likely using uv locally. Consider using it in Docker too!

#### 2.3 Optimize Base Image Selection
```dockerfile
# Option A: Use Python alpine for smaller images (but slower builds)
FROM python:3.13-alpine as builder
# Pros: 50% smaller images
# Cons: Need to install more build dependencies, some packages may not work

# Option B: Use pre-built base with common dependencies
FROM ghcr.io/humlab-sead/python-base:3.13 as builder
# Pros: Faster builds (deps pre-installed)
# Cons: Need to maintain custom base image

# Option C: Current approach (best balance)
FROM python:3.13-slim as builder
# Pros: Good balance of size and compatibility
# Cons: Some build overhead
```

**Recommendation**: Stick with `python:3.13-slim` for now (best balance)

#### 2.4 Parallel Test Job
Add a separate test job that runs in parallel with build:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
          cache: 'pip'
      - run: pip install -e ".[dev]"
      - run: pytest
      - run: ruff check

  build-and-push:
    needs: test  # Only build if tests pass
    runs-on: ubuntu-latest
    # ... existing build steps
```

**Expected Improvement**: Catch issues faster, fail fast before expensive build

### Priority 3: Infrastructure Optimizations

#### 3.1 Self-Hosted Runners
**Current**: Using GitHub-hosted runners

**Consideration**: 
- GitHub-hosted: Free, but limited resources, cold starts
- Self-hosted: Faster (warm cache), more control, but maintenance overhead

**Recommendation**: Stick with GitHub-hosted unless builds become frequent bottleneck

#### 3.2 BuildKit Features
Enable advanced BuildKit features:

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3
  with:
    buildkitd-flags: --allow-insecure-entitlement network.host
    config-inline: |
      [worker.oci]
        max-parallelism = 4
```

#### 3.3 Registry Cache
Use registry as cache backend (alternative to GitHub Actions cache):

```yaml
cache-from: type=registry,ref=ghcr.io/${{ github.repository }}:buildcache
cache-to: type=registry,ref=ghcr.io/${{ github.repository }}:buildcache,mode=max
```

**Pros**: Persistent cache across runners, faster pulls
**Cons**: Uses registry storage, slight complexity

## Estimated Build Times

### Current Configuration (Multi-Arch)
- **Cold Build**: 5-8 minutes
- **Warm Build (cache hit)**: 3-5 minutes
- **Code-only Change**: 4-6 minutes (deps rebuild unnecessarily)

### After Priority 1 Optimizations (Single-Arch + Layer Optimization)
- **Cold Build**: 2-4 minutes
- **Warm Build (cache hit)**: 1-2 minutes
- **Code-only Change**: 30-60 seconds (deps cached)

### After Priority 2 Optimizations (+ uv + cache mounts)
- **Cold Build**: 1-2 minutes
- **Warm Build (cache hit)**: 30-45 seconds
- **Code-only Change**: 20-30 seconds

## Implementation Plan

### Phase 1: Immediate (This Week)
1. ✅ Reorder Dockerfile layers (dependencies before code)
2. ✅ Remove editable install (`-e` flag)
3. ✅ Make multi-arch conditional on releases only
4. ✅ Add build time reporting to workflow

**Expected ROI**: 60-70% faster builds, minimal risk

### Phase 2: Short-term (Next Sprint)
1. Add uv for package installation
2. Implement pip cache mounts
3. Add parallel test job
4. Optimize apt-get layer consolidation

**Expected ROI**: Additional 40-50% improvement, low risk

### Phase 3: Long-term (Future Consideration)
1. Evaluate self-hosted runners if build frequency increases
2. Consider custom base images with pre-installed dependencies
3. Implement registry-based caching
4. Add build performance monitoring dashboard

**Expected ROI**: Incremental improvements, higher maintenance

## Monitoring & Metrics

### Current Metrics to Track
1. **Build Duration**: Total time from trigger to completion
2. **Cache Hit Rate**: Percentage of layers pulled from cache
3. **Build Frequency**: Number of builds per day/week
4. **Failed Builds**: Ratio of failed to successful builds

### Recommended Metrics Dashboard
```yaml
# Add to workflow for timing visibility
- name: Report build time
  if: always()
  run: |
    echo "Build completed in ${{ steps.build.outputs.build-time }}"
    echo "Cache hit rate: ${{ steps.build.outputs.cache-hit }}"
```

### GitHub Actions Insights
Monitor at: `https://github.com/humlab-sead/sead_authority_service/actions/workflows/docker-build.yml`

## Cost-Benefit Analysis

### Current Costs
- **Compute Time**: ~4-6 minutes per build
- **Frequency**: ~10-20 builds/day during active development
- **Total Monthly**: ~40-120 hours of build time
- **GitHub Actions Minutes**: Free tier (2,000 min/month) likely sufficient

### Optimization Costs
- **Developer Time**: 2-4 hours for Phase 1 implementation
- **Testing Time**: 1-2 hours validation
- **Maintenance**: Minimal ongoing cost

### Benefits
- **Time Saved**: 60-70% reduction = 24-72 hours/month saved
- **Developer Productivity**: Faster feedback loops
- **CI/CD Costs**: Stay within free tier longer
- **Release Velocity**: Faster deployments

**ROI**: Very high - 2-4 hours investment for 24-72 hours/month saved

## References

- [Docker Build Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [BuildKit Cache](https://docs.docker.com/build/cache/)
- [GitHub Actions Caching](https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows)
- [uv - Fast Python Package Installer](https://github.com/astral-sh/uv)
- [Docker Multi-Platform Builds](https://docs.docker.com/build/building/multi-platform/)

## Appendix: Optimized Dockerfile

See `docker/Dockerfile.optimized` for complete optimized version implementing Priority 1 & 2 recommendations.

# Quick Optimization Guide

## TL;DR - What to Do Now

### 🚀 Quick Wins (15 minutes to implement)

Apply these changes to your current `docker/Dockerfile`:

```dockerfile
# BEFORE (Current)
COPY pyproject.toml ./
COPY README.md ./
COPY src ./src
COPY main.py ./
RUN pip install --no-cache-dir -e .

# AFTER (Optimized) 
COPY pyproject.toml README.md ./              # ← Copy deps files first
RUN pip install --no-cache-dir .              # ← Install deps (note: no -e flag)
COPY src ./src                                # ← Copy code after
COPY main.py ./
```

**Result**: Code changes won't rebuild dependencies anymore → **60-70% faster rebuilds**

### 🎯 Medium Wins (30 minutes to implement)

Update `.github/workflows/docker-build.yml`:

```yaml
# Add this step before "Build and push Docker image"
- name: Determine platforms
  id: platforms
  run: |
    if [[ "${{ github.ref_type }}" == "tag" ]]; then
      echo "platforms=linux/amd64,linux/arm64" >> $GITHUB_OUTPUT
    else
      echo "platforms=linux/amd64" >> $GITHUB_OUTPUT
    fi

# Update the build step
- name: Build and push Docker image
  uses: docker/build-push-action@v5
  with:
    platforms: ${{ steps.platforms.outputs.platforms }}  # ← Use conditional platforms
    # ... rest stays the same
```

**Result**: Regular commits build single-arch only → **50% faster builds**

## Performance Comparison

| Scenario | Current | After Quick Wins | After Medium Wins |
|----------|---------|------------------|-------------------|
| **Cold build** (no cache) | 5-8 min | 4-6 min | 2-4 min |
| **Warm build** (cache hit) | 3-5 min | 2-3 min | 1-2 min |
| **Code-only change** | 4-6 min | 1-2 min | 30-60 sec |
| **Multi-arch overhead** | Always | Always | Only on releases |

## What Each Optimization Does

### 1. Dependency Layer Separation
**Problem**: Every code change forces dependency reinstall
**Solution**: Install dependencies in separate Docker layer before copying code
**Impact**: ⚡ **60-70% faster** on code changes

### 2. Remove Editable Install
**Problem**: `pip install -e .` is slower and unnecessary in containers
**Solution**: Use `pip install .` instead
**Impact**: ⚡ **10-15% faster** dependency installation

### 3. Conditional Multi-Arch
**Problem**: Building arm64 on every commit is slow and often unnecessary
**Solution**: Only build arm64 for tagged releases
**Impact**: ⚡ **50% faster** regular builds

### 4. Cache Mounts (Advanced)
**Problem**: pip downloads packages fresh every time
**Solution**: Use BuildKit cache mounts to persist pip cache
**Impact**: ⚡ **30-40% faster** dependency installation

### 5. Use uv Instead of pip (Advanced)
**Problem**: pip is relatively slow at resolving dependencies
**Solution**: Use `uv` (10-100x faster than pip)
**Impact**: ⚡ **5-10x faster** package installation

## Implementation Steps

### Step 1: Update Dockerfile (5 minutes)

```bash
# Backup current Dockerfile
cp docker/Dockerfile docker/Dockerfile.backup

# Edit docker/Dockerfile
nano docker/Dockerfile
```

Apply the changes from "Quick Wins" section above.

### Step 2: Test Locally (5 minutes)

```bash
cd docker
./build.sh --tag test-optimized

# Compare build times
time docker build -f Dockerfile.backup -t test-old .
time docker build -f Dockerfile -t test-new .
```

### Step 3: Update Workflow (5 minutes)

```bash
# Edit the workflow
nano .github/workflows/docker-build.yml
```

Apply changes from "Medium Wins" section above.

### Step 4: Commit and Test (5 minutes)

```bash
git add docker/Dockerfile .github/workflows/docker-build.yml
git commit -m "perf(ci): optimize Docker builds for faster iteration

- Separate dependency layer from code layer
- Use regular install instead of editable install  
- Conditional multi-arch (arm64 only on releases)

Expected improvement: 60-70% faster code-only builds"

git push origin dev
```

Watch the build in Actions: https://github.com/humlab-sead/sead_authority_service/actions

## Advanced: Use Optimized Files

We've created fully optimized versions you can use:

```bash
# Option 1: Replace current Dockerfile
cp docker/Dockerfile.optimized docker/Dockerfile

# Option 2: Replace current workflow
cp .github/workflows/docker-build.optimized.yml .github/workflows/docker-build.yml

# Commit
git add docker/Dockerfile .github/workflows/docker-build.yml
git commit -m "perf(ci): implement all build optimizations"
git push origin dev
```

## Expected Results

After implementing quick + medium wins:

```
Before:
✗ Code change → 4-6 minute build → 😴
✗ Multi-arch every time → slow → 😴
✗ Dependencies rebuild on code change → 😴

After:  
✓ Code change → 30-60 second build → 🚀
✓ Multi-arch only on releases → fast → 🚀
✓ Dependencies cached → 🚀
```

## Monitoring

After implementing, monitor build times in GitHub Actions:
- https://github.com/humlab-sead/sead_authority_service/actions/workflows/docker-build.yml
- Look for "Build and push Docker image" step duration
- Should see significant reduction in build times

## Questions?

See full analysis: [CI_CD_PERFORMANCE_ANALYSIS.md](CI_CD_PERFORMANCE_ANALYSIS.md)

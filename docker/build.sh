#!/bin/bash
# Build script for SEAD Authority Service Docker image
# Usage: ./build.sh [OPTIONS]
#
# Options:
#   -t, --tag TAG        Image tag (default: latest)
#   -p, --push           Push to registry after build
#   --no-cache           Build without cache
#   --use-uv             Use uv for faster package installation
#   --from-github TAG    Build from GitHub repository at specified tag/branch

set -e

# Default values
IMAGE_TAG="latest"
DOCKERFILE="Dockerfile"
PUSH=false
NO_CACHE=""
USE_UV=true
FROM_GITHUB=""
REGISTRY="ghcr.io/humlab-sead"
IMAGE_NAME="sead_authority_service"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --use-uv)
            USE_UV=true
            shift
            ;;
        --from-github)
            FROM_GITHUB="$2"
            shift 2
            ;;
        # Legacy support for old --github-tag option
        --github-tag)
            FROM_GITHUB="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -t, --tag TAG         Image tag (default: latest)"
            echo "  -p, --push            Push to registry after build"
            echo "  --no-cache            Build without cache"
            echo "  --use-uv              Use uv for faster package installation (5-10x faster)"
            echo "  --from-github TAG     Build from GitHub repository at tag/branch"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./build.sh                                    # Build from local context"
            echo "  ./build.sh --use-uv --tag v1.0.0             # Build locally with uv"
            echo "  ./build.sh --from-github v1.0.0              # Build from GitHub tag"
            echo "  ./build.sh --from-github main --use-uv       # Build from main with uv"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Build command
BUILD_CMD="docker build"
BUILD_CMD="$BUILD_CMD -f $DOCKERFILE"
BUILD_CMD="$BUILD_CMD -t $IMAGE_NAME:$IMAGE_TAG"
BUILD_CMD="$BUILD_CMD -t $REGISTRY/$IMAGE_NAME:$IMAGE_TAG"

# Add build args
if [ "$USE_UV" = true ]; then
    BUILD_CMD="$BUILD_CMD --build-arg USE_UV=true"
fi

if [ -n "$FROM_GITHUB" ]; then
    BUILD_CMD="$BUILD_CMD --build-arg FROM_GITHUB=true"
    BUILD_CMD="$BUILD_CMD --build-arg GIT_TAG=$FROM_GITHUB"
fi

# Add no-cache if specified
if [ -n "$NO_CACHE" ]; then
    BUILD_CMD="$BUILD_CMD $NO_CACHE"
fi

# Context is parent directory
BUILD_CMD="$BUILD_CMD .."

echo "Building Docker image..."
echo "Image: $IMAGE_NAME:$IMAGE_TAG"
echo "Dockerfile: $DOCKERFILE"
if [ -n "$FROM_GITHUB" ]; then
    echo "Source: GitHub @ $FROM_GITHUB"
else
    echo "Source: Local context"
fi
if [ "$USE_UV" = true ]; then
    echo "Package installer: uv (fast)"
else
    echo "Package installer: pip"
fi
echo ""

# Execute build
cd "$(dirname "$0")"
eval $BUILD_CMD

echo ""
echo "✓ Build completed successfully!"
echo "  Local image: $IMAGE_NAME:$IMAGE_TAG"
echo "  Registry image: $REGISTRY/$IMAGE_NAME:$IMAGE_TAG"

# Push if requested
if [ "$PUSH" = true ]; then
    echo ""
    echo "Pushing to registry..."
    docker push $REGISTRY/$IMAGE_NAME:$IMAGE_TAG
    echo "✓ Push completed successfully!"
fi

echo ""
echo "To run the container:"
echo "  docker run -d -p 8000:8000 \\"
echo "    -v \$(pwd)/config.yml:/app/config/config.yml:ro \\"
echo "    -v \$(pwd)/logs:/app/logs \\"
echo "    --env-file .env \\"
echo "    $IMAGE_NAME:$IMAGE_TAG"

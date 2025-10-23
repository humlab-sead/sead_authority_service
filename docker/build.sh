#!/bin/bash
# Build script for SEAD Authority Service Docker image
# Usage: ./build.sh [OPTIONS]
#
# Options:
#   -t, --tag TAG        Image tag (default: latest)
#   -p, --push           Push to registry after build
#   -f, --file FILE      Dockerfile to use (default: Dockerfile)
#   --no-cache           Build without cache
#   --github-tag TAG     Use Dockerfile.github and build from GitHub tag

set -e

# Default values
IMAGE_TAG="latest"
DOCKERFILE="Dockerfile"
PUSH=false
NO_CACHE=""
GITHUB_TAG=""
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
        -f|--file)
            DOCKERFILE="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --github-tag)
            GITHUB_TAG="$2"
            DOCKERFILE="Dockerfile.github"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -t, --tag TAG        Image tag (default: latest)"
            echo "  -p, --push           Push to registry after build"
            echo "  -f, --file FILE      Dockerfile to use (default: Dockerfile)"
            echo "  --no-cache           Build without cache"
            echo "  --github-tag TAG     Build from GitHub tag using Dockerfile.github"
            echo "  -h, --help           Show this help message"
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

# Add GitHub tag if specified
if [ -n "$GITHUB_TAG" ]; then
    BUILD_CMD="$BUILD_CMD --build-arg GIT_TAG=$GITHUB_TAG"
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
if [ -n "$GITHUB_TAG" ]; then
    echo "GitHub Tag: $GITHUB_TAG"
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

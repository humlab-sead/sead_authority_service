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

g_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
g_script_file="$(basename "${BASH_SOURCE[0]}")"
g_image_tag="latest"
g_dockerfile="Dockerfile"
g_push=false
g_no_cache=
g_use_uv=true
g_from_github=
g_registry="ghcr.io/humlab-sead"
g_image_name="sead_authority_service"

function print_usage() {
    if [ "$1" != "" ]; then
        echo "error: $1"
    fi
    cat << EOF
    Usage: $g_script_file [OPTIONS]
    
    Options:
      -t, --tag TAG         Image tag (default: latest)
      -p, --push            Push to registry after build
      --no-cache            Build without cache
      --use-uv              Use uv for faster package installation (5-10x faster)
      --from-github TAG     Build from GitHub repository at tag/branch
      -h, --help            Show this help message
    Examples:
      $g_script_file                                   # Build from local context
      $g_script_file --use-uv --tag v1.0.0            # Build locally with uv
      $g_script_file --from-github v1.0.0             # Build from GitHub tag
      $g_script_file --from-github main --use-uv      # Build from main with uv
EOF
    if [ "$1" != "" ]; then
        exit 64
    else
        exit 0
    fi
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag) g_image_tag="$2" ; shift 2 ;;
        -p|--push)
            g_push=true
            shift
            ;;
        --no-cache)
            g_no_cache="--no-cache"
            shift
            ;;
        --use-uv)
            g_use_uv=true
            shift
            ;;
        --from-github)
            g_from_github="$2"
            shift 2
            ;;
        # Legacy support for old --github-tag option
        --github-tag)
            g_from_github="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            ;;
        *)
            print_usage "unknown option $1"
            ;;
    esac
done

g_optional_args=""
if [ -n "$g_from_github" ]; then
    g_optional_args="$g_optional_args --build-arg FROM_GITHUB=true"
    g_optional_args="$g_optional_args --build-arg GIT_TAG=$g_from_github"
fi

if [ -n "$g_no_cache" ]; then
    g_optional_args="$g_optional_args $g_no_cache"
fi

g_cmd="docker build -f $g_dockerfile -t $g_image_name:$g_image_tag -t $g_registry/$g_image_name:$g_image_tag --build-arg USE_UV=$g_use_uv $g_optional_args .."

echo "info: building image $g_image_name:$g_image_tag using $g_dockerfile"

pushd "$g_script_dir" > /dev/null

eval $g_cmd

if [ "$g_push" = true ]; then
    echo "info: pushing image to registry $g_registry"
    docker push $g_registry/$g_image_name:$g_image_tag
    echo "info: ✓ push completed successfully!"
fi

echo ""
echo "info: to run the container:"
echo "  docker run -d -p 8000:8000 \\"
echo "    -v \$(pwd)/config.yml:/app/config/config.yml:ro \\"
echo "    -v \$(pwd)/logs:/app/logs \\"
echo "    $g_image_name:$g_image_tag"

popd
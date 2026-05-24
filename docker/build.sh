#!/bin/bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
script_name="$(basename "${BASH_SOURCE[0]}")"
image_ref="ghcr.io/humlab-sead/sead_authority_service"
git_repo="https://github.com/humlab-sead/sead_authority_service.git"
git_ref=""
target_env="${SEAD_AUTHORITY_ENVIRONMENT:-staging}"
image_tag=""
push_image=false
no_cache=false

print_usage() {
    if [[ -n "${1:-}" ]]; then
        echo "error: $1" >&2
    fi

    cat <<EOF
Usage: ${script_name} [OPTIONS]

Build the same image artifact previously produced by the disabled GitHub Actions workflow.
This script always builds from GitHub, not from the local worktree.

Options:
    --git-ref REF        Git branch or tag to build from
    --target-env ENV     Deployment target environment: dev, staging, production
    -t, --tag TAG        Override the derived image tag
    -p, --push           Push the image to GHCR after a successful build
    --no-cache           Build without using the Docker layer cache
    -h, --help           Show this help message

Examples:
    ${script_name} --git-ref dev
    ${script_name} --git-ref main --target-env staging
    ${script_name} --git-ref v1.2.0 --target-env production --push
EOF

    if [[ -n "${1:-}" ]]; then
        exit 64
    fi
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --git-ref)
            git_ref="$2"
            shift 2
            ;;
        --target-env)
            target_env="$2"
            shift 2
            ;;
        -t|--tag)
            image_tag="$2"
            shift 2
            ;;
        -p|--push)
            push_image=true
            shift
            ;;
        --no-cache)
            no_cache=true
            shift
            ;;
        -h|--help)
            print_usage
            ;;
        *)
            print_usage "unknown option $1"
            ;;
    esac
done

if [[ -z "${git_ref}" ]]; then
    print_usage "--git-ref is required"
fi

case "${target_env}" in
    dev|staging|production)
        ;;
    *)
        print_usage "unsupported target environment '${target_env}'"
        ;;
esac

if [[ -z "${image_tag}" ]]; then
    if [[ "${git_ref}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([-.].*)?$ ]]; then
        if [[ "${target_env}" == "production" ]]; then
            image_tag="${git_ref}"
        else
            image_tag="${target_env}"
        fi
    else
        case "${target_env}" in
            dev)
                image_tag="dev"
                ;;
            staging)
                image_tag="staging"
                ;;
            production)
                if [[ "${git_ref}" == "main" ]]; then
                    image_tag="latest"
                else
                    image_tag="$(echo "${git_ref}" | sed 's/[^a-zA-Z0-9._-]/-/g')"
                fi
                ;;
        esac
    fi
fi

user_uid="$(id -u sead 2>/dev/null || echo 1002)"
user_gid="$(getent group www-data | cut -d: -f3 || echo 33)"

build_cmd=(
    docker
    buildx
    build
    --platform linux/amd64
    --file docker/Dockerfile
    --tag "${image_ref}:${image_tag}"
    --build-arg USE_UV=true
    --build-arg FROM_GITHUB=true
    --build-arg "GIT_TAG=${git_ref}"
    --build-arg "GIT_REPO=${git_repo}"
    --build-arg "USER_UID=${user_uid}"
    --build-arg "USER_GID=${user_gid}"
)

if [[ "${no_cache}" == true ]]; then
    build_cmd+=(--no-cache)
fi

if [[ "${push_image}" == true ]]; then
    build_cmd+=(--push)
else
    build_cmd+=(--load)
fi

build_cmd+=(.)

echo "info: building ${image_ref}:${image_tag} from ${git_repo}@${git_ref} for ${target_env}"

cd "${script_dir}"
"${build_cmd[@]}"

if [[ "${push_image}" == true ]]; then
    echo "info: pushed ${image_ref}:${image_tag}"
else
    echo "info: loaded ${image_ref}:${image_tag} into the local Docker image store"
fi
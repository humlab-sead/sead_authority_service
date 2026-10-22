#!/bin/bash
# Podman image build/push helper for the SEAD Authority Service.
#
# Rootless Podman image build/push helper. Preserves the options, defaults,
# and GHCR tag mapping of the former Docker helper, and keeps the same
# source contract: the image is always built from the selected GitHub ref,
# never from the local worktree (see Containerfile).
#
# Publishing stays opt-in: the image is pushed only with --push, after
# "podman login ghcr.io". The GitHub Actions image workflow calls this helper
# for automated publication and repeats --tag for a version tag plus latest.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bundle_dir="$(cd "${script_dir}/.." && pwd)"
script_name="$(basename "${BASH_SOURCE[0]}")"
image_ref="ghcr.io/humlab-sead/sead_authority_service"
git_repo_default="https://github.com/humlab-sead/sead_authority_service.git"

# Read one KEY=VALUE line from an env file. The helper reads only the
# SEAD_AUTHORITY_* keys it uses instead of sourcing the whole file, because
# the tracked .env.example keeps placeholder secrets such as
# OPENAI_API_KEY=<your-openai-api-key>, which is not valid shell and would
# abort a plain "source". Compose reads the full file itself at runtime.
read_env_value() {
    local file="$1" key="$2" value=""
    if [[ -f "${file}" ]]; then
        value="$(sed -n "s/^[[:space:]]*${key}=\(.*\)/\1/p" "${file}" | tail -1)"
        # Strip surrounding single or double quotes if present.
        value="${value%\"}"; value="${value#\"}"
        value="${value%\'}"; value="${value#\'}"
    fi
    printf '%s' "${value}"
}

# Defaults resolve from: environment > caller-directory .env > bundle .env.
bundle_env_file="${bundle_dir}/.env"
caller_env_file="${PWD}/.env"

env_or() {
    # env_or KEY DEFAULT — environment first, then caller .env, then bundle .env.
    local key="$1" default="$2" value=""
    value="${!key:-}"
    if [[ -z "${value}" && -f "${caller_env_file}" && "${caller_env_file}" != "${bundle_env_file}" ]]; then
        value="$(read_env_value "${caller_env_file}" "${key}")"
    fi
    if [[ -z "${value}" ]]; then
        value="$(read_env_value "${bundle_env_file}" "${key}")"
    fi
    printf '%s' "${value:-${default}}"
}

git_repo="$(env_or SEAD_AUTHORITY_GIT_REPO "${git_repo_default}")"
git_ref="$(env_or SEAD_AUTHORITY_GIT_REF "")"
git_commit="$(env_or SEAD_AUTHORITY_GIT_COMMIT "")"
target_env="$(env_or SEAD_AUTHORITY_ENVIRONMENT "staging")"
image_tag="$(env_or SEAD_AUTHORITY_IMAGE_TAG "")"
image_tags=()
explicit_tags=false
push_image=false
no_cache=false

print_usage() {
    if [[ -n "${1:-}" ]]; then
        echo "error: $1" >&2
    fi

    cat <<EOF
Usage: ${script_name} [OPTIONS]

Build the image artifact used by the GitHub Actions image workflow and by manual deployments.
This script always builds from GitHub, not from the local worktree.
It reads SEAD_AUTHORITY_* settings from the environment, then the caller
folder's .env, then this bundle's .env (placeholder secrets are ignored).

Options:
    --git-ref REF        Git branch or tag to build from
    --git-commit SHA     Exact 40-character Git commit to build from
    --target-env ENV     Deployment target environment: dev, staging, production
    -t, --tag TAG        Image tag to build and push. Repeat the option to build
                         several tags from one build. Overrides the derived tag
                         and SEAD_AUTHORITY_IMAGE_TAG.
    -p, --push           Push the image to GHCR after a successful build
    --no-cache           Build without using the Podman layer cache
    -h, --help           Show this help message

Examples:
    ${script_name} --git-ref dev
    ${script_name} --git-ref dev --git-commit <commit> --tag phase2-<date>-<sha>
    ${script_name} --git-ref main --target-env staging
    ${script_name} --git-ref v1.2.0 --target-env production --push
    cd ~/container && ./scripts/build.sh
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
        --git-commit)
            git_commit="$2"
            shift 2
            ;;
        --target-env)
            target_env="$2"
            shift 2
            ;;
        -t|--tag)
            image_tags+=("$2")
            explicit_tags=true
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

if [[ -n "${git_commit}" && ! "${git_commit}" =~ ^[0-9a-fA-F]{40}$ ]]; then
    print_usage "--git-commit must be a 40-character hexadecimal commit ID"
fi

if [[ -z "${git_ref}" && -z "${git_commit}" ]]; then
    print_usage "--git-ref or --git-commit is required unless a source is set in the environment or local .env"
fi

if [[ -z "${git_ref}" ]]; then
    git_ref="commit-${git_commit:0:7}"
fi

case "${target_env}" in
    dev|staging|production)
        ;;
    *)
        print_usage "unsupported target environment '${target_env}'"
        ;;
esac

# Tag precedence: explicit --tag options, then SEAD_AUTHORITY_IMAGE_TAG from the
# environment or .env, then the tag derived from the target environment and ref.
if [[ "${explicit_tags}" == false && -n "${image_tag}" ]]; then
    image_tags+=("${image_tag}")
fi

if [[ ${#image_tags[@]} -eq 0 ]]; then
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
    image_tags+=("${image_tag}")
fi

# Drop empty and duplicate tags while preserving the given order.
declare -A seen_tags=()
unique_tags=()
for tag in "${image_tags[@]}"; do
    if [[ -z "${tag}" || -n "${seen_tags[${tag}]:-}" ]]; then
        continue
    fi
    seen_tags["${tag}"]=1
    unique_tags+=("${tag}")
done

if [[ ${#unique_tags[@]} -eq 0 ]]; then
    print_usage "at least one non-empty image tag is required"
fi
image_tags=("${unique_tags[@]}")

# Rootless Podman keeps the deployment user, so build with the current UID/GID.
# podman-compose.yml uses "userns_mode: keep-id", which maps this host user to
# the same UID/GID inside the container so it can write the mounted logs/.
user_uid="$(id -u)"
user_gid="$(id -g)"

build_cmd=(
    podman
    build
    --platform linux/amd64
    --format docker
    --file "${bundle_dir}/Containerfile"
    --build-arg "GIT_REF=${git_ref}"
    --build-arg "GIT_COMMIT=${git_commit}"
    --build-arg "GIT_REPO=${git_repo}"
    --build-arg "USER_UID=${user_uid}"
    --build-arg "USER_GID=${user_gid}"
)

for tag in "${image_tags[@]}"; do
    build_cmd+=(--tag "${image_ref}:${tag}")
done

if [[ "${no_cache}" == true ]]; then
    build_cmd+=(--no-cache)
fi

# The Containerfile clones the selected ref itself, so the build context only
# needs to be the bundle directory.
build_cmd+=("${bundle_dir}")

source_description="${git_repo}@${git_ref}"
if [[ -n "${git_commit}" ]]; then
    source_description+=" (commit ${git_commit})"
fi
tag_list="$(printf '%s,' "${image_tags[@]}")"
tag_list="${tag_list%,}"
echo "info: building ${image_ref} tags ${tag_list} from ${source_description} for ${target_env}"

"${build_cmd[@]}"

if [[ "${push_image}" == true ]]; then
    for tag in "${image_tags[@]}"; do
        echo "info: pushing ${image_ref}:${tag} (run 'podman login ghcr.io' first if not authenticated)"
        podman push "${image_ref}:${tag}"
    done
fi

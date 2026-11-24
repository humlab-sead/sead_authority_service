#!/usr/bin/env bash
set -euo pipefail

readonly repository="humlab-sead/sead_authority_service"
readonly source_branch="dev"
readonly target_branch="staging"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly script_dir
repository_root="$(cd -- "${script_dir}/../.." && pwd)"
readonly repository_root
readonly cli_path="${repository_root}/scripts/workflow/promote_dev_to_staging.sh"
readonly description_script="${repository_root}/scripts/workflow/update_pr_descriptions.py"
readonly provenance_script="${repository_root}/scripts/ci/verify_promotion_provenance.sh"
readonly python="${repository_root}/.venv/bin/python"
# Set by --quiet: progress text moves to stderr and stdout carries only the PR number.
quiet=0
# Temporary escape hatch for the provenance check. Set SKIP_PROMOTION_PROVENANCE=1
# or pass --skip-provenance to promote commits that reached dev without a pull
# request. The check stays available and unchanged; only this caller skips it.
skip_provenance="${SKIP_PROMOTION_PROVENANCE:-0}"
cd -- "$repository_root"

usage() {
  cat <<'EOF'
Prepare and publish a dev-to-staging promotion pull request.

Usage:
  scripts/workflow/promote_dev_to_staging.sh prepare
  scripts/workflow/promote_dev_to_staging.sh publish <pull-request-number>
  scripts/workflow/promote_dev_to_staging.sh merge <pull-request-number>

Commands:
  prepare             Fetch branches, verify provenance, create a draft promotion PR,
                      and write its description to the PR on GitHub (nothing is
                      stored on disk). Review or edit the description on GitHub.
  publish <number>    Verify provenance again and mark the PR ready for review.
                      Keeps the description as it is on GitHub.
  merge <number>      Merge the promotion PR into staging with a merge commit.
  -h, --help          Show this help.
  -q, --quiet         Print only the pull request number on stdout. Progress text moves
                      to stderr, so every command can be captured.
  --skip-provenance   Skip the pull request provenance check. Temporary: commits that
                      reached dev without a pull request are promoted unreported.

Environment:
  SKIP_PROMOTION_PROVENANCE   Same as --skip-provenance when set to 1, true, yes, or on.

Commands that fetch branches and verify provenance print a warning when the check
is skipped, so the bypass stays visible in the output.

The merge command runs 'gh pr merge --merge', so GitHub still enforces the
repository's branch protection rules: required reviews and checks must pass.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

validate_pull_request_number() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]] || die "Pull request number must be a positive integer."
}

# Accepts the values used for the provenance bypass, so 1, true, yes, and on all work.
is_enabled() {
  case "${1,,}" in
    1 | true | yes | on) return 0 ;;
    *) return 1 ;;
  esac
}

# Run a command, moving its stdout to stderr under --quiet so stdout stays clean.
run_quietly() {
  if (( quiet )); then
    "$@" >&2
  else
    "$@"
  fi
}

# Checks shared by every command: the GitHub CLI, authentication, and repository identity.
check_github_environment() {
  require_command gh

  gh auth status --hostname github.com >/dev/null 2>&1 || die "Authenticate with 'gh auth login' first."

  local actual_repository
  actual_repository="$(gh repo view --json nameWithOwner --jq .nameWithOwner)" \
    || die "Could not determine the current GitHub repository."
  [[ "$actual_repository" == "$repository" ]] \
    || die "Run this script from ${repository}; current repository is ${actual_repository}."
}

# Additional checks for prepare and publish, which regenerate descriptions and verify provenance.
check_environment() {
  require_command git
  check_github_environment

  [[ -x "$python" ]] || die "Python environment not found at ${python}; set up the repository .venv first."
  [[ -f "$description_script" ]] || die "Description script not found: ${description_script}"
  [[ -x "$provenance_script" ]] || die "Provenance script is not executable: ${provenance_script}"

  local origin_url
  origin_url="$(git remote get-url origin)" || die "Git remote 'origin' is required."
  [[ "$origin_url" =~ github\.com[:/]humlab-sead/sead_authority_service(\.git)?$ ]] \
    || die "Git remote 'origin' must point to ${repository}; found ${origin_url}."
}

fetch_branches() {
  if [[ "$(git rev-parse --is-shallow-repository)" == "true" ]]; then
    git fetch --unshallow origin
  else
    git fetch origin
  fi

  git show-ref --verify --quiet "refs/remotes/origin/${source_branch}" \
    || die "Remote branch origin/${source_branch} was not found."
  git show-ref --verify --quiet "refs/remotes/origin/${target_branch}" \
    || die "Remote branch origin/${target_branch} was not found."
}

verify_provenance() {
  if is_enabled "$skip_provenance"; then
    printf 'warning: skipping the promotion provenance check; commits without pull requests will not be reported.\n' >&2
    return 0
  fi

  local token
  token="$(gh auth token)" || die "Could not read the GitHub CLI authentication token."
  [[ -n "$token" ]] || die "GitHub CLI returned an empty authentication token."

  run_quietly env GH_TOKEN="$token" "$provenance_script" \
    --base "origin/${target_branch}" \
    --head "origin/${source_branch}"
}

prepare_promotion() {
  check_environment
  fetch_branches

  local existing_pr
  existing_pr="$(gh pr list \
    --repo "$repository" \
    --state open \
    --base "$target_branch" \
    --head "$source_branch" \
    --json number,url \
    --jq '.[0].url // empty')"
  [[ -z "$existing_pr" ]] || die "An open promotion PR already exists: ${existing_pr}"

  verify_provenance

  local pull_request_url
  pull_request_url="$(gh pr create \
    --repo "$repository" \
    --draft \
    --base "$target_branch" \
    --head "$source_branch" \
    --title "Promote dev to staging" \
    --body-file - <<'EOF'
<!-- promotion-pr -->
## Summary

Promotes `dev` into `staging`.

## Included PRs

Pending generation from the promotion branch history.

## User-facing release note

None - no user-visible change.

## Upgrade notes

None - no user action required.

## Validation

Not verified: validation results unavailable.
EOF
  )" || die "Could not create the draft promotion pull request."

  local pull_request_number
  pull_request_number="${pull_request_url##*/}"
  validate_pull_request_number "$pull_request_number"

  if ! run_quietly "$python" "$description_script" "$pull_request_number" --update-promotion; then
    die "Created ${pull_request_url}, but could not write its description. Run: ${python} ${description_script} ${pull_request_number} --update-promotion"
  fi

  if (( quiet )); then
    printf '%s\n' "$pull_request_number"
    return 0
  fi

  printf '\nCreated draft promotion PR: %s\n' "$pull_request_url"
  printf 'Review or edit its description on GitHub, then mark it ready with: %s publish %s\n' "$cli_path" "$pull_request_number"
}

publish_promotion() {
  local pull_request_number="$1"
  validate_pull_request_number "$pull_request_number"
  check_environment

  local metadata
  metadata="$(gh pr view "$pull_request_number" \
    --repo "$repository" \
    --json state,baseRefName,headRefName,isDraft \
    --jq '[.state, .baseRefName, .headRefName, (.isDraft | tostring)] | @tsv')" \
    || die "Could not read pull request #${pull_request_number}."

  local state base_branch head_branch is_draft
  IFS=$'\t' read -r state base_branch head_branch is_draft <<< "$metadata"
  [[ "$state" == "OPEN" ]] || die "Pull request #${pull_request_number} is not open."
  [[ "$base_branch" == "$target_branch" && "$head_branch" == "$source_branch" ]] \
    || die "Pull request #${pull_request_number} is not a ${source_branch}-to-${target_branch} promotion."
  [[ "$is_draft" == "true" ]] || die "Pull request #${pull_request_number} is not a draft."

  fetch_branches
  verify_provenance

  if ! run_quietly gh pr ready "$pull_request_number" --repo "$repository"; then
    die "Could not mark PR #${pull_request_number} ready for review. Run: gh pr ready ${pull_request_number}"
  fi

  if (( quiet )); then
    printf '%s\n' "$pull_request_number"
    return 0
  fi

  printf 'Marked PR #%s ready for review.\n' "$pull_request_number"
  printf 'After required reviews and checks pass, merge with: %s merge %s\n' "$cli_path" "$pull_request_number"
}

merge_promotion() {
  local pull_request_number="$1"
  validate_pull_request_number "$pull_request_number"
  check_github_environment

  local metadata
  metadata="$(gh pr view "$pull_request_number" \
    --repo "$repository" \
    --json state,baseRefName,headRefName,isDraft \
    --jq '[.state, .baseRefName, .headRefName, (.isDraft | tostring)] | @tsv')" \
    || die "Could not read pull request #${pull_request_number}."

  local state base_branch head_branch is_draft
  IFS=$'\t' read -r state base_branch head_branch is_draft <<< "$metadata"
  [[ "$state" == "OPEN" ]] || die "Pull request #${pull_request_number} is not open."
  [[ "$base_branch" == "$target_branch" && "$head_branch" == "$source_branch" ]] \
    || die "Pull request #${pull_request_number} is not a ${source_branch}-to-${target_branch} promotion."
  [[ "$is_draft" == "false" ]] \
    || die "Pull request #${pull_request_number} is still a draft. Run the publish command first."

  run_quietly gh pr merge "$pull_request_number" --repo "$repository" --merge \
    || die "Could not merge pull request #${pull_request_number}."

  if (( quiet )); then
    printf '%s\n' "$pull_request_number"
    return 0
  fi

  printf 'Merged PR #%s into %s with a merge commit.\n' "$pull_request_number" "$target_branch"
}

main() {
  local -a positional=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -q | --quiet)
        quiet=1
        shift
        ;;
      -h | --help)
        usage
        return 0
        ;;
      --skip-provenance)
        skip_provenance=1
        shift
        ;;
      --)
        shift
        positional+=("$@")
        break
        ;;
      -*)
        usage >&2
        die "Unknown option: $1"
        ;;
      *)
        positional+=("$1")
        shift
        ;;
    esac
  done

  if [[ ${#positional[@]} -eq 0 ]]; then
    usage
    return 0
  fi

  case "${positional[0]}" in
    prepare)
      [[ ${#positional[@]} -eq 1 ]] || die "The prepare command takes no arguments."
      prepare_promotion
      ;;
    publish)
      [[ ${#positional[@]} -eq 2 ]] || die "Usage: scripts/workflow/promote_dev_to_staging.sh publish <pull-request-number>"
      publish_promotion "${positional[1]}"
      ;;
    merge)
      [[ ${#positional[@]} -eq 2 ]] || die "Usage: scripts/workflow/promote_dev_to_staging.sh merge <pull-request-number>"
      merge_promotion "${positional[1]}"
      ;;
    *)
      usage >&2
      die "Unknown command: ${positional[0]}"
      ;;
  esac
}

main "$@"

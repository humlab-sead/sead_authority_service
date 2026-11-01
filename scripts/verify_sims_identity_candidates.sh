#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)"

BACKUP="${SIMS_VERIFY_BACKUP:-${XDG_CACHE_HOME:-$HOME/.cache}/sead-authority-service/sead_staging.dump}"
AUTHORITY_SCHEMA_DIR="${SIMS_AUTHORITY_SCHEMA_DIR:-$REPO_ROOT/schema}"
IDENTITY_SCHEMA_DIR="${SIMS_IDENTITY_SCHEMA_DIR:-$REPO_ROOT/schema/sql/identity}"
CONTAINER_NAME="${SIMS_VERIFY_CONTAINER:-sead-sims-candidate-verification}"
IMAGE="${SIMS_VERIFY_IMAGE:-docker.io/postgis/postgis:18-3.6}"
HOST_PORT="${SIMS_VERIFY_PORT:-55432}"
CONTAINER_LABEL="org.sead-shape-shifter.sims-candidate-verification"
BACKUP_FORMAT=""

SOURCE_HOST="${SIMS_VERIFY_SOURCE_HOST:-}"
SOURCE_PORT="${SIMS_VERIFY_SOURCE_PORT:-}"
SOURCE_DATABASE="${SIMS_VERIFY_SOURCE_DATABASE:-}"
SOURCE_USER="${SIMS_VERIFY_SOURCE_USER:-}"

SCHEMA_FILES=(
    000_schema.sql
    001_source_scopes.sql
    002_submissions.sql
    003_source_identities.sql
    003b_source_identity_keys.sql
    004_submission_source_identities.sql
    005_tracked_identities.sql
    006_binding_sets.sql
    007_bindings.sql
    008_seed_scopes.sql
    009_site_id_allocator.sql
    010_aggregate_identity_value.sql
    011_resolve_batch_idempotency.sql
)

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

temporary_files=()

cleanup_temporary_files() {
    local temporary_file
    for temporary_file in "${temporary_files[@]}"; do
        rm -f -- "$temporary_file"
    done
}

trap cleanup_temporary_files EXIT

usage() {
    cat <<'EOF'
Usage: scripts/verify_sims_identity_candidates.sh COMMAND [ARGS]

Commands:
  dump --yes [--env-file <ENV_FILE>]
                                Dump the configured SEAD database to a local archive.
  setup                         Restore the archive into a disposable database and
                                install the Authority and SIMS identity schemas.
  bootstrap [site|sample|dataset|analysis_entity|all]
                                Add missing materialized SIMS identities for existing
                                SEAD rows and initialize the SIMS allocator state.
  sql FILE                      Run a SQL file in sead_staging; use - to read stdin.
  psql                          Open an interactive psql session in sead_staging.
  credentials                   Print local connection settings, including password.
  status                        Show the disposable container state and port mapping.
  start                         Start the existing container without resetting data.
  stop                          Stop the existing container and preserve its data.
  destroy --yes                 Remove the container and its disposable database.

Environment overrides:
  SIMS_VERIFY_BACKUP          Local archive path (default: $XDG_CACHE_HOME/sead-authority-service/sead_staging.dump,
                              or ~/.cache/... when XDG_CACHE_HOME is unset)
  SIMS_VERIFY_SOURCE_HOST     Source SEAD PostgreSQL host for dump
  SIMS_VERIFY_SOURCE_PORT     Source SEAD PostgreSQL port for dump
  SIMS_VERIFY_SOURCE_DATABASE Source SEAD database name for dump
  SIMS_VERIFY_SOURCE_USER     Source SEAD PostgreSQL user for dump
  SIMS_AUTHORITY_SCHEMA_DIR   Authority Service schema directory
  SIMS_IDENTITY_SCHEMA_DIR    Authority Service schema/sql/identity directory
  SIMS_VERIFY_CONTAINER       Podman container name
  SIMS_VERIFY_IMAGE           PostGIS-enabled PostgreSQL image (default PG 18)
  SIMS_VERIFY_PORT            Host port bound on 127.0.0.1 (default 55432)

Source credentials use libpq authentication; use a local .pgpass file or
PGPASSFILE rather than putting passwords in command arguments. The dump
excludes the existing authority and sead_identity schemas so this script can
install their current definitions.

The archive may contain sensitive SEAD data. By default it is written outside
the repository with owner-only permissions. The Podman container is
loopback-only and has no host data volume. Destroying it deletes the restored
database but does not delete the archive. Bootstrap changes only SIMS rows in
this helper-owned disposable container; it does not modify the restored SEAD
rows.
EOF
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "$1 is required"
}

require_podman() {
    require_command podman
}

assert_owned_container() {
    podman container exists "$CONTAINER_NAME" || fail "container not found: $CONTAINER_NAME (run setup first)"
    local label_value
    label_value="$(podman inspect --format "{{ index .Config.Labels \"$CONTAINER_LABEL\" }}" "$CONTAINER_NAME")"
    [[ "$label_value" == true ]] || fail "refusing to use container not created by this script: $CONTAINER_NAME"
}

wait_for_postgres() {
    local attempt
    for ((attempt = 1; attempt <= 90; attempt++)); do
        local init_process
        init_process="$(podman exec "$CONTAINER_NAME" cat /proc/1/comm 2>/dev/null || true)"
        if [[ "$init_process" == postgres ]] \
            && podman exec "$CONTAINER_NAME" pg_isready -U postgres -d postgres >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    fail "PostgreSQL did not become ready in container $CONTAINER_NAME"
}

ensure_running() {
    assert_owned_container
    local running
    running="$(podman inspect --format '{{.State.Running}}' "$CONTAINER_NAME")"
    if [[ "$running" != true ]]; then
        podman start "$CONTAINER_NAME" >/dev/null
    fi
    wait_for_postgres
}

psql_exec() {
    podman exec "$CONTAINER_NAME" psql -X -v ON_ERROR_STOP=1 -U postgres -d sead_staging "$@"
}

dump_source_database() {

    local SOURCE_HOST="${SIMS_VERIFY_SOURCE_HOST:-}"
    local SOURCE_PORT="${SIMS_VERIFY_SOURCE_PORT:-}"
    local SOURCE_DATABASE="${SIMS_VERIFY_SOURCE_DATABASE:-}"
    local SOURCE_USER="${SIMS_VERIFY_SOURCE_USER:-}"

    require_command pg_dump
    require_command pg_restore

    [[ -n "$SOURCE_HOST" ]] || fail "set SIMS_VERIFY_SOURCE_HOST"
    [[ -n "$SOURCE_PORT" ]] || fail "set SIMS_VERIFY_SOURCE_PORT"
    [[ -n "$SOURCE_DATABASE" ]] || fail "set SIMS_VERIFY_SOURCE_DATABASE"
    [[ -n "$SOURCE_USER" ]] || fail "set SIMS_VERIFY_SOURCE_USER"
    [[ "$SOURCE_PORT" =~ ^[0-9]+$ ]] || fail "SIMS_VERIFY_SOURCE_PORT must be an integer between 1 and 65535"
    (( 10#$SOURCE_PORT >= 1 && 10#$SOURCE_PORT <= 65535 )) || fail "SIMS_VERIFY_SOURCE_PORT must be an integer between 1 and 65535"

    local backup_directory temporary_backup
    backup_directory="$(dirname -- "$BACKUP")"
    mkdir -p -- "$backup_directory"
    temporary_backup="$(mktemp "${BACKUP}.tmp.XXXXXX")"
    temporary_files+=("$temporary_backup")

    printf 'Dumping database %s to a local custom-format archive.\n' "$SOURCE_DATABASE"
    if ! pg_dump \
        --no-password \
        --format=custom \
        --no-owner \
        --no-acl \
        --exclude-schema=authority \
        --exclude-schema=sead_identity \
        --exclude-schema=audit \
        --exclude-schema=clearing_house \
        --exclude-schema=clearing_house_commit \
        --exclude-schema=postgrest_api \
        --exclude-schema=postgrest_default_api \
        --exclude-schema=bugs_import \
        --exclude-schema=facet \
        --host "$SOURCE_HOST" \
        --port "$SOURCE_PORT" \
        --username "$SOURCE_USER" \
        --dbname "$SOURCE_DATABASE" \
        --file "$temporary_backup"; then
        rm -f -- "$temporary_backup"
        fail "pg_dump failed; check the source connection and local password file"
    fi

    if ! pg_restore --list "$temporary_backup" >/dev/null; then
        rm -f -- "$temporary_backup"
        fail "pg_dump produced an invalid archive"
    fi

    chmod 600 "$temporary_backup"
    mv -f -- "$temporary_backup" "$BACKUP"
    printf 'Archive saved: %s\n' "$BACKUP"
}

check_setup_inputs() {
    [[ -f "$BACKUP" ]] || fail "database archive not found: $BACKUP"
    [[ -f "$AUTHORITY_SCHEMA_DIR/create_schema.sh" ]] || fail "Authority schema installer not found: $AUTHORITY_SCHEMA_DIR/create_schema.sh"
    [[ -f "$AUTHORITY_SCHEMA_DIR/__deploy__.sql" ]] || fail "generated Authority deployment SQL not found: $AUTHORITY_SCHEMA_DIR/__deploy__.sql (run create_schema.sh first)"

    if [[ "$(head -c 5 "$BACKUP")" == "PGDMP" ]]; then
        BACKUP_FORMAT="custom"
        require_command pg_restore
        pg_restore --list "$BACKUP" >/dev/null || fail "backup is not a valid PostgreSQL custom-format archive: $BACKUP"
    elif gzip -t "$BACKUP" 2>/dev/null; then
        BACKUP_FORMAT="sql-gzip"
    else
        fail "backup must be a PostgreSQL custom-format archive or a legacy gzip SQL dump: $BACKUP"
    fi

    local schema_file
    for schema_file in "${SCHEMA_FILES[@]}"; do
        [[ -f "$IDENTITY_SCHEMA_DIR/$schema_file" ]] || fail "SIMS schema file not found: $IDENTITY_SCHEMA_DIR/$schema_file"
    done

    [[ "$HOST_PORT" =~ ^[0-9]+$ ]] || fail "SIMS_VERIFY_PORT must be an integer between 1 and 65535"
    (( 10#$HOST_PORT >= 1 && 10#$HOST_PORT <= 65535 )) || fail "SIMS_VERIFY_PORT must be an integer between 1 and 65535"
}

setup() {
    require_podman
    require_command psql
    check_setup_inputs

    if podman container exists "$CONTAINER_NAME"; then
        fail "container already exists: $CONTAINER_NAME (use start, stop, or destroy --yes)"
    fi

    local database_password
    database_password="$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')"
    printf 'Starting %s from %s\n' "$IMAGE" "$CONTAINER_NAME"
    POSTGRES_PASSWORD="$database_password" podman run --detach \
        --name "$CONTAINER_NAME" \
        --label "$CONTAINER_LABEL=true" \
        --publish "127.0.0.1:${HOST_PORT}:5432" \
        --env POSTGRES_PASSWORD \
        "$IMAGE" >/dev/null
    unset database_password

    wait_for_postgres

    # Create the target database before restoring; legacy SQL dumps replace it.
    podman exec "$CONTAINER_NAME" createdb -U postgres sead_staging

    if [[ "$BACKUP_FORMAT" == custom ]]; then
        printf 'Restoring custom-format archive %s\n' "$BACKUP"
        podman exec --interactive "$CONTAINER_NAME" \
            pg_restore --exit-on-error --no-owner --no-acl --username=postgres --dbname=sead_staging < "$BACKUP"
    else
        printf 'Restoring legacy SQL archive %s\n' "$BACKUP"
        gzip -dc "$BACKUP" | podman exec --interactive "$CONTAINER_NAME" \
            psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres
    fi

    local database_password passfile
    database_password="$(
        podman inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$CONTAINER_NAME" \
            | sed -n 's/^POSTGRES_PASSWORD=//p'
    )"
    [[ -n "$database_password" ]] || fail "could not read generated database password"
    passfile="$(mktemp "${TMPDIR:-/tmp}/sead-sims-pgpass.XXXXXX")"
    temporary_files+=("$passfile")
    chmod 600 "$passfile"
    printf '127.0.0.1:%s:sead_staging:postgres:%s\n' "$HOST_PORT" "$database_password" > "$passfile"
    unset database_password

    if [[ "$(psql_exec -Atqc "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'humlab_admin');")" != t ]]; then
        printf 'Creating local NOLOGIN role humlab_admin for Authority schema ownership\n'
        psql_exec -c 'CREATE ROLE humlab_admin NOLOGIN;'
    fi

    printf 'Installing PostgreSQL extensions required by Authority schema\n'
    psql_exec -c 'CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public;'
    psql_exec -c 'CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;'

    printf 'Installing Authority schema with create_schema.sh\n'
    if ! (
        cd "$SCRIPT_DIR"
        PGPASSFILE="$passfile" "$AUTHORITY_SCHEMA_DIR/create_schema.sh" \
            --no-generate --deploy \
            --database sead_staging \
            --host 127.0.0.1 \
            --port "$HOST_PORT" \
            --user postgres
    ); then
        rm -f -- "$passfile"
        fail "Authority schema installation failed"
    fi
    rm -f -- "$passfile"

    local schema_file
    for schema_file in "${SCHEMA_FILES[@]}"; do
        printf 'Applying SIMS schema: %s\n' "$schema_file"
        podman exec --interactive "$CONTAINER_NAME" \
            psql -X -v ON_ERROR_STOP=1 -U postgres -d sead_staging \
            < "$IDENTITY_SCHEMA_DIR/$schema_file"
    done

    [[ "$(psql_exec -Atqc "SELECT to_regprocedure('authority.fuzzy_site(text,integer)') IS NOT NULL;")" == t ]] \
        || fail "Authority installation did not create authority.fuzzy_site(text,integer)"
    [[ "$(psql_exec -Atqc "SELECT
        to_regclass('sead_identity.tracked_identities') IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'sead_identity'
              AND table_name = 'tracked_identities'
              AND column_name = 'aggregate_id'
        )
        AND to_regclass('sead_identity.internal_id_allocators') IS NOT NULL
        AND to_regclass('sead_identity.resolve_batches') IS NOT NULL;")" == t ]] \
        || fail "SIMS installation is missing current identity schema migrations"

    printf '\nSIMS schema check:\n'
    psql_exec -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'sead_identity' ORDER BY table_name;"

    printf '\nDatabase is ready. Container: %s\n' "$CONTAINER_NAME"
    printf 'Local port: 127.0.0.1:%s\n' "$HOST_PORT"
    printf 'Use the sql or psql command for follow-up checks; credentials prints host connection settings.\n'
}

bootstrap_candidates() {
    local candidate="${1:-all}"
    local bootstrap_site=false bootstrap_sample=false bootstrap_dataset=false bootstrap_analysis_entity=false

    case "$candidate" in
        site) bootstrap_site=true ;;
        sample) bootstrap_sample=true ;;
        dataset) bootstrap_dataset=true ;;
        analysis_entity) bootstrap_analysis_entity=true ;;
        all)
            bootstrap_site=true
            bootstrap_sample=true
            bootstrap_dataset=true
            bootstrap_analysis_entity=true
            ;;
        *) fail "unknown candidate '$candidate' (expected site, sample, dataset, analysis_entity, or all)" ;;
    esac

    ensure_running
    printf 'Bootstrapping existing %s identities in the disposable database.\n' "$candidate"
    podman exec --interactive "$CONTAINER_NAME" \
        psql -X -v ON_ERROR_STOP=1 \
            -v "bootstrap_site=$bootstrap_site" \
            -v "bootstrap_sample=$bootstrap_sample" \
        -v "bootstrap_dataset=$bootstrap_dataset" \
        -v "bootstrap_analysis_entity=$bootstrap_analysis_entity" \
        -U postgres -d sead_staging <<'SQL'
BEGIN;
SET LOCAL lock_timeout = '5s';
LOCK TABLE sead_identity.internal_id_allocators IN SHARE ROW EXCLUSIVE MODE;
LOCK TABLE sead_identity.tracked_identities IN SHARE ROW EXCLUSIVE MODE;
\if :bootstrap_site
LOCK TABLE public.tbl_sites IN SHARE MODE;
\endif
\if :bootstrap_sample
LOCK TABLE public.tbl_physical_samples IN SHARE MODE;
\endif
\if :bootstrap_dataset
LOCK TABLE public.tbl_datasets IN SHARE MODE;
\endif
\if :bootstrap_analysis_entity
LOCK TABLE public.tbl_analysis_entities IN SHARE MODE;
\endif

CREATE TEMP TABLE bootstrap_requested (
    entity_type text NOT NULL,
    aggregate_id bigint NOT NULL,
    PRIMARY KEY (entity_type, aggregate_id)
) ON COMMIT DROP;

\if :bootstrap_site
INSERT INTO bootstrap_requested (entity_type, aggregate_id)
SELECT 'site', site_id FROM public.tbl_sites;
\endif
\if :bootstrap_sample
INSERT INTO bootstrap_requested (entity_type, aggregate_id)
SELECT 'sample', physical_sample_id FROM public.tbl_physical_samples;
\endif
\if :bootstrap_dataset
INSERT INTO bootstrap_requested (entity_type, aggregate_id)
SELECT 'dataset', dataset_id FROM public.tbl_datasets;
\endif
\if :bootstrap_analysis_entity
INSERT INTO bootstrap_requested (entity_type, aggregate_id)
SELECT 'analysis_entity', analysis_entity_id FROM public.tbl_analysis_entities;
\endif

DO $bootstrap_preflight$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM sead_identity.tracked_identities
        WHERE entity_type IN (SELECT DISTINCT entity_type FROM bootstrap_requested)
          AND aggregate_id IS NULL
    ) THEN
        RAISE EXCEPTION 'Bootstrap stopped: selected entity type has SIMS identities without a SEAD ID; review them before bootstrapping';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM sead_identity.tracked_identities
        WHERE entity_type IN (SELECT DISTINCT entity_type FROM bootstrap_requested)
          AND aggregate_id IS NOT NULL
        GROUP BY entity_type, aggregate_id
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Bootstrap stopped: selected entity type has duplicate SIMS mappings';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM sead_identity.tracked_identities AS identity
        WHERE identity.entity_type IN (SELECT DISTINCT entity_type FROM bootstrap_requested)
          AND identity.aggregate_id IS NOT NULL
                    AND identity.lifecycle_state NOT IN ('allocated', 'pending_materialization')
          AND NOT EXISTS (
              SELECT 1
              FROM bootstrap_requested AS source
              WHERE source.entity_type = identity.entity_type
                AND source.aggregate_id = identity.aggregate_id
          )
    ) THEN
        RAISE EXCEPTION 'Bootstrap stopped: selected entity type has SIMS IDs absent from SEAD';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM sead_identity.tracked_identities AS identity
        JOIN bootstrap_requested AS source
          ON source.entity_type = identity.entity_type
         AND source.aggregate_id = identity.aggregate_id
        WHERE identity.lifecycle_state IN ('allocated', 'pending_materialization')
    ) THEN
        RAISE EXCEPTION 'Bootstrap stopped: a SIMS ID reservation now overlaps a SEAD row; review the competing allocation before bootstrapping';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM sead_identity.tracked_identities AS identity
        JOIN bootstrap_requested AS source
          ON source.entity_type = identity.entity_type
         AND source.aggregate_id = identity.aggregate_id
        WHERE identity.lifecycle_state = 'invalidated'
    ) THEN
        RAISE EXCEPTION 'Bootstrap stopped: a matching SIMS identity is invalidated; review it before bootstrapping';
    END IF;
END
$bootstrap_preflight$;

UPDATE sead_identity.tracked_identities AS identity
SET lifecycle_state = 'materialized',
    materialized_at = COALESCE(identity.materialized_at, now())
FROM bootstrap_requested AS source
WHERE source.entity_type = identity.entity_type
  AND source.aggregate_id = identity.aggregate_id
    AND (identity.lifecycle_state <> 'materialized' OR identity.materialized_at IS NULL);

INSERT INTO sead_identity.tracked_identities (
    tracked_identity_uuid,
    entity_type,
    aggregate_id,
    lifecycle_state,
    created_by,
    materialized_at
)
SELECT gen_random_uuid(), source.entity_type, source.aggregate_id,
       'materialized', 'sims-existing-id-bootstrap', now()
FROM bootstrap_requested AS source
WHERE NOT EXISTS (
    SELECT 1
    FROM sead_identity.tracked_identities AS identity
    WHERE identity.entity_type = source.entity_type
      AND identity.aggregate_id = source.aggregate_id
);

\if :bootstrap_site
INSERT INTO sead_identity.internal_id_allocators (
    entity_type,
    next_internal_id,
    initialized_at,
    initialized_by
)
SELECT 'site',
       GREATEST(
           COALESCE((SELECT max(site_id) FROM public.tbl_sites), 0),
           COALESCE((
               SELECT max(aggregate_id)
               FROM sead_identity.tracked_identities
               WHERE entity_type = 'site'
           ), 0)
       ) + 1,
       now(),
       'sims-candidate-verification-bootstrap'
ON CONFLICT (entity_type) DO UPDATE
SET next_internal_id = GREATEST(
    sead_identity.internal_id_allocators.next_internal_id,
    EXCLUDED.next_internal_id
);
\endif
\if :bootstrap_sample
INSERT INTO sead_identity.internal_id_allocators (
    entity_type,
    next_internal_id,
    initialized_at,
    initialized_by
)
SELECT 'sample',
       GREATEST(
           COALESCE((SELECT max(physical_sample_id) FROM public.tbl_physical_samples), 0),
           COALESCE((
               SELECT max(aggregate_id)
               FROM sead_identity.tracked_identities
               WHERE entity_type = 'sample'
           ), 0)
       ) + 1,
       now(),
       'sims-candidate-verification-bootstrap'
ON CONFLICT (entity_type) DO UPDATE
SET next_internal_id = GREATEST(
    sead_identity.internal_id_allocators.next_internal_id,
    EXCLUDED.next_internal_id
);
\endif
\if :bootstrap_dataset
INSERT INTO sead_identity.internal_id_allocators (
    entity_type,
    next_internal_id,
    initialized_at,
    initialized_by
)
SELECT 'dataset',
       GREATEST(
           COALESCE((SELECT max(dataset_id) FROM public.tbl_datasets), 0),
           COALESCE((
               SELECT max(aggregate_id)
               FROM sead_identity.tracked_identities
               WHERE entity_type = 'dataset'
           ), 0)
       ) + 1,
       now(),
       'sims-candidate-verification-bootstrap'
ON CONFLICT (entity_type) DO UPDATE
SET next_internal_id = GREATEST(
    sead_identity.internal_id_allocators.next_internal_id,
    EXCLUDED.next_internal_id
);
\endif
\if :bootstrap_analysis_entity
INSERT INTO sead_identity.internal_id_allocators (
    entity_type,
    next_internal_id,
    initialized_at,
    initialized_by
)
SELECT 'analysis_entity',
       GREATEST(
           COALESCE((SELECT max(analysis_entity_id) FROM public.tbl_analysis_entities), 0),
           COALESCE((
               SELECT max(aggregate_id)
               FROM sead_identity.tracked_identities
               WHERE entity_type = 'analysis_entity'
           ), 0)
       ) + 1,
       now(),
       'sims-candidate-verification-bootstrap'
ON CONFLICT (entity_type) DO UPDATE
SET next_internal_id = GREATEST(
    sead_identity.internal_id_allocators.next_internal_id,
    EXCLUDED.next_internal_id
);
\endif

DO $bootstrap_postcheck$
BEGIN
    IF EXISTS (
        SELECT source.entity_type, source.aggregate_id
        FROM bootstrap_requested AS source
        LEFT JOIN sead_identity.tracked_identities AS identity
          ON identity.entity_type = source.entity_type
         AND identity.aggregate_id = source.aggregate_id
        GROUP BY source.entity_type, source.aggregate_id
        HAVING count(identity.tracked_identity_uuid) <> 1
            OR bool_or(identity.lifecycle_state <> 'materialized' OR identity.materialized_at IS NULL)
    ) THEN
        RAISE EXCEPTION 'Bootstrap post-check failed: each selected SEAD row must have exactly one materialized SIMS identity';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM sead_identity.tracked_identities AS identity
        WHERE identity.entity_type IN (SELECT DISTINCT entity_type FROM bootstrap_requested)
          AND identity.aggregate_id IS NOT NULL
                    AND identity.lifecycle_state NOT IN ('allocated', 'pending_materialization')
          AND NOT EXISTS (
              SELECT 1
              FROM bootstrap_requested AS source
              WHERE source.entity_type = identity.entity_type
                AND source.aggregate_id = identity.aggregate_id
          )
    ) THEN
        RAISE EXCEPTION 'Bootstrap post-check failed: selected entity type still has SIMS IDs absent from SEAD';
    END IF;
END
$bootstrap_postcheck$;

COMMIT;
SQL
}

show_credentials() {
    assert_owned_container
    local env_lines database_password host_port
    env_lines="$(podman inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$CONTAINER_NAME")"
    database_password="$(printf '%s\n' "$env_lines" | sed -n 's/^POSTGRES_PASSWORD=//p')"
    [[ -n "$database_password" ]] || fail "could not read generated database password"
    host_port="$(podman port "$CONTAINER_NAME" 5432/tcp | sed -n 's/.*://p' | head -n 1)"
    [[ -n "$host_port" ]] || fail "container has no published PostgreSQL port"

    printf 'PGHOST=127.0.0.1\nPGPORT=%s\nPGDATABASE=sead_staging\nPGUSER=postgres\nPGPASSWORD=%s\n' \
        "$host_port" "$database_password"
}

status() {
    require_podman
    assert_owned_container
    podman ps --all --filter "name=^${CONTAINER_NAME}$" \
        --format 'Container: {{.Names}} | State: {{.Status}} | Image: {{.Image}}'
    podman port "$CONTAINER_NAME" 5432/tcp || true
}

destroy() {
    [[ "${1:-}" == --yes ]] || fail "destroy removes the disposable database; confirm with: destroy --yes"
    assert_owned_container
    podman rm --force --volumes "$CONTAINER_NAME"
    printf 'Removed disposable container and database: %s\n' "$CONTAINER_NAME"
}

main() {
    local command="${1:-help}"
    shift || true

    case "$command" in
        dump)
            # [[ $# -eq 1 ]] || fail "dump requires --yes because it creates a local copy of SEAD data"
            local confirmed=false
            local env_file=""

            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --yes)
                        confirmed=true
                        shift
                        ;;
                    --env-file)
                        [[ $# -ge 2 && "$2" != --* ]] || fail "Missing value for --env-file"
                        env_file="$2"
                        shift 2
                        ;;
                    *)
                        fail "Unknown option: $1"
                        ;;
                esac
            done
            [[ "$confirmed" == true ]] || fail "Confirmation required: my-cmd --yes"

            if [[ -n "$env_file" ]]; then
                [[ -f "$env_file" ]] || fail "Environment file not found: $env_file"
                set -a
                # The caller selects the environment file at runtime.
                # shellcheck disable=SC1090
                source "$env_file"
                set +a
            fi
            dump_source_database
            ;;
        setup)
            [[ $# -eq 0 ]] || fail "setup does not accept arguments; use environment overrides (see --help)"
            setup
            ;;
        bootstrap)
            [[ $# -le 1 ]] || fail "bootstrap accepts at most one candidate"
            require_podman
            bootstrap_candidates "${1:-all}"
            ;;
        sql)
            [[ $# -eq 1 ]] || fail "sql requires a file path or - for stdin"
            require_podman
            ensure_running
            if [[ "$1" == - ]]; then
                podman exec --interactive "$CONTAINER_NAME" psql -X -v ON_ERROR_STOP=1 -U postgres -d sead_staging
            else
                [[ -f "$1" ]] || fail "SQL file not found: $1"
                podman exec --interactive "$CONTAINER_NAME" psql -X -v ON_ERROR_STOP=1 -U postgres -d sead_staging < "$1"
            fi
            ;;
        psql)
            [[ $# -eq 0 ]] || fail "psql does not accept arguments"
            require_podman
            ensure_running
            podman exec --interactive --tty "$CONTAINER_NAME" psql -X -U postgres -d sead_staging
            ;;
        credentials)
            [[ $# -eq 0 ]] || fail "credentials does not accept arguments"
            require_podman
            show_credentials
            ;;
        status)
            [[ $# -eq 0 ]] || fail "status does not accept arguments"
            status
            ;;
        start)
            [[ $# -eq 0 ]] || fail "start does not accept arguments"
            require_podman
            ensure_running
            printf 'Container is running: %s\n' "$CONTAINER_NAME"
            ;;
        stop)
            [[ $# -eq 0 ]] || fail "stop does not accept arguments"
            require_podman
            assert_owned_container
            podman stop "$CONTAINER_NAME"
            ;;
        destroy)
            [[ $# -eq 1 ]] || fail "destroy requires --yes"
            require_podman
            destroy "$1"
            ;;
        -h|--help|help)
            usage
            ;;
        *)
            usage >&2
            fail "unknown command: $command"
            ;;
    esac
}

main "$@"
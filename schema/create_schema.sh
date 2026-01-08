#!/bin/bash
# Install script for SEAD Authority Service database schema
#
# This script:
# 1. Generates entity-specific SQL files from templates
# 2. Creates a deployment SQL file combining all schemas
# 3. Optionally deploys the schema to a PostgreSQL database
#
# Usage: ./create_schema.sh [OPTIONS]
# Run with --help for detailed usage information

set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

g_user="${SEAD_AUTHORITY_OPTIONS_DATABASE_USER:-}"
g_host="${SEAD_AUTHORITY_OPTIONS_DATABASE_HOST:-}"
g_port="${SEAD_AUTHORITY_OPTIONS_DATABASE_PORT:-5432}"
g_db="${SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME:-}"

g_generate_deploy_sql="YES"
g_deploy="NO"
g_schema_folder="schema/generated"

if [[ -z "$g_host" ]] && [[ -f ~/vault/.default.sead.server ]]; then
    g_host=$(cat ~/vault/.default.sead.server)
    g_host=${g_host:-$(dnsdomainname -A)}
fi

if [[ -z "$g_user" ]] && [[ -f ~/vault/.default.sead.username ]]; then
    g_user=$(cat ~/vault/.default.sead.username)
fi

readonly g_deploy_sql_filename="schema/__deploy__.sql"
readonly g_script_dir="$(dirname "$(realpath "$0")")"
readonly g_root_dir="$(realpath "${g_script_dir}/..")"

log_info() {
    echo -e "${GREEN}$(date +"%H:%M:%S") | INFO     | ${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}$(date +"%H:%M:%S") | WARN    | ${NC} $*" >&2
}

log_error() {
    echo -e "${RED}$(date +"%H:%M:%S") | ERROR   | ${NC} $*" >&2
}

function print_usage {
    if [[ -n "${1:-}" ]]; then
        log_error "$1"
    fi
    cat <<EOF
Usage: $0 [OPTIONS]

This script generates and optionally deploys the complete database schema 
for the SEAD Authority Service.

Options:
  --database, -d DB_NAME   Target database name (overrides SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME)
  --port, -p PORT          Database port (default: 5432, overrides SEAD_AUTHORITY_OPTIONS_DATABASE_PORT)
  --user, -U USERNAME      Database user (overrides SEAD_AUTHORITY_OPTIONS_DATABASE_USER)
  --host, -h HOSTNAME      Database host (overrides SEAD_AUTHORITY_OPTIONS_DATABASE_HOST)
  --schema-folder FOLDER   Directory to store generated SQL files (default: ${g_schema_folder})
  --deploy, -D             Deploy the generated schema to the target database
  --no-generate            Skip schema generation, only deploy existing files
  --help                   Show this help message and exit

Environment Variables:
  SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME    Target database name
  SEAD_AUTHORITY_OPTIONS_DATABASE_HOST      Database host
  SEAD_AUTHORITY_OPTIONS_DATABASE_PORT      Database port (default: 5432)
  SEAD_AUTHORITY_OPTIONS_DATABASE_USER      Database user

Examples:
  # Generate schema files only (default)
  $0

  # Generate and deploy to local database
  $0 --deploy --database sead_staging --host localhost --user postgres

  # Deploy previously generated schema
  $0 --no-generate --deploy --database sead_production

EOF
    [[ -n "${1:-}" ]] && exit 1 || exit 0
}

# Change to project root directory
pushd "${g_root_dir}" > /dev/null || exit 1

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --database|-d)
            g_db="$2"
            shift 2
            ;;
        --port|-p)
            g_port="$2"
            shift 2
            ;;
        --user|-U)
            g_user="$2"
            shift 2
            ;;
        --host|-h)
            g_host="$2"
            shift 2
            ;;
        --schema-folder)
            g_schema_folder="$2"
            shift 2
            ;;
        --no-generate)
            g_generate_deploy_sql="NO"
            shift
            ;;
        --deploy|-D)
            g_deploy="YES"
            shift
            ;;
        --help)
            print_usage
            ;;
        *)
            print_usage "Unknown option: $1"
            ;;
    esac
done

if [[ "$g_deploy" == "YES" ]]; then
    if [[ -z "$g_db" ]] || [[ -z "$g_user" ]] || [[ -z "$g_host" ]]; then
        print_usage "Database connection parameters (--database, --user, --host) are required for deployment"
    fi
fi

cleanup() {
    log_info "Cleaning up generated schema files"
    rm -rf schema/generated
    rm -f "${g_deploy_sql_filename}"
}

generate_deploy_sql() {
    log_info "Generating entity schema files from templates"
    mkdir -p "${g_schema_folder}"
    
    # Generate entity-specific SQL files using Python script
    if ! PYTHONPATH=. uv run python src/scripts/generate_entity_schema.py --all --force \
        --config config/entities.yml \
        --template-dir schema/templates \
        --output-dir "${g_schema_folder}"; then
        log_error "Schema generation failed"
        return 1
    fi

    log_info "Schema generation completed (stored in ${g_schema_folder}/)"

    # Create combined deployment SQL file
    log_info "Creating deployment SQL file: ${g_deploy_sql_filename}"

    cat > "${g_deploy_sql_filename}" <<SQLEOF
-- SEAD Authority Service Schema Deployment
-- Generated automatically by create_schema.sh

\set quiet on
\set echo none
\set verbosity terse
SET client_min_messages = warning;

BEGIN;

-- Core authority schema
\i schema/sql/authority.sql
\i schema/sql/utility.sql

SQLEOF

    local file_count=0
    for sql_file in schema/generated/*.sql; do
        [[ -f "$sql_file" ]] || continue
        [[ "$sql_file" =~ semantic- ]] && continue
        echo "\\i $sql_file" >> "${g_deploy_sql_filename}"
        ((file_count++))
        # log_info "...added $sql_file"
    done

    # Add semantic entity schemas last
    log_info "Including semantic search schemas"
    for sql_file in schema/generated/semantic-*.sql; do
        [[ -f "$sql_file" ]] || continue
        echo "\\i $sql_file" >> "${g_deploy_sql_filename}"
        ((file_count++))
        # log_info "...added $sql_file"
    done

    echo "COMMIT;" >> "${g_deploy_sql_filename}"
    log_info "Deployment SQL file created with $file_count schema files"
    
    return 0
}

# Deploy schema to database
deploy_schema() {
    if [[ ! -f "${g_deploy_sql_filename}" ]]; then
        log_error "Deployment SQL file not found: ${g_deploy_sql_filename}"
        log_error "Run with --generate or without --no-generate to create it first"
        return 1
    fi

    log_info "Deploying schema to database: ${g_db}@${g_host}:${g_port}"
    log_warn "This will modify the database schema. Press Ctrl+C to cancel..."
    sleep 2

    if psql -h "$g_host" -p "$g_port" -U "$g_user" -d "$g_db" \
            -v ON_ERROR_STOP=1 -q -t -A -f "${g_deploy_sql_filename}"; then
        log_info "Schema deployment completed successfully!"
        return 0
    else
        log_error "Schema deployment failed!"
        return 1
    fi
}

main() {
    local exit_code=0

    if [[ "$g_generate_deploy_sql" == "YES" ]]; then
        cleanup
        if ! generate_deploy_sql; then
            log_error "Schema generation failed"
            exit_code=1
        fi
    fi

    if [[ "$g_deploy" == "YES" ]] && [[ $exit_code -eq 0 ]]; then
        if ! deploy_schema; then
            exit_code=1
        fi
    elif [[ "$g_deploy" == "NO" ]] && [[ $exit_code -eq 0 ]]; then
        log_info "Schema files generated successfully"
        log_info "To deploy the schema, re-run with the --deploy option"
        log_info "Example: $0 --deploy --database sead_staging --host localhost --user postgres"
    fi

    popd > /dev/null || true

    return $exit_code
}

main
exit $?

# Note: Embeddings are updated client-side via Python scripts
# See: src/scripts/update_embeddings.py (if implemented)
# Legacy command (deprecated):
# \i schema/sql/update_embeddings.sql
# ${HOME}/bin/sql -v ON_ERROR_STOP=1 -q -t -A -c "call authority.update_all_embeddings(true);"

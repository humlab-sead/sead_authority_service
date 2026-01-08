#!/bin/bash
# Install script for SEAD Authority Service database

set -euo pipefail

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

g_user="${SEAD_AUTHORITY_OPTIONS_DATABASE_USER}"
g_host="${SEAD_AUTHORITY_OPTIONS_DATABASE_HOST}"
g_port="${SEAD_AUTHORITY_OPTIONS_DATABASE_PORT:=5433}"
g_db="${SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME}"
g_generate_deploy_sql=YES
g_deploy=NO
g_schema_folder="schema/generated"

if [ "$g_host" == "" ] && [ -f ~/vault/.default.sead.server ]; then
    g_host=`cat ~/vault/.default.sead.server`
    g_host=${g_host:=$(dnsdomainname -A)}
fi

if [ "$g_user" == "" ] && [ -f ~/vault/.default.sead.username ]; then
    g_user=`cat  ~/vault/.default.sead.username`
fi

g_deploy_sql_filename="schema/__deploy__.sql"
g_script_dir="$(dirname "$(realpath "$0")")"
g_root_dir="$(realpath "${g_script_dir}/..")"

function print_usage {
    if [ "$1" != "" ]; then
        echo "error: $1"
    fi
    # Convert this to a here document for better readability
    cat <<EOF
Usage: $0 [--database DB_NAME] [--port PORT] [--user USERNAME] [--host HOSTNAME] [PSQL-OPTIONS ...] [--help]

This script generates and deploys the complete database schema for the SEAD Authority Service.

Options:
  --database, -d         Target database name (overrides SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME)
  --port, -p             Database port (overrides SEAD_AUTHORITY_OPTIONS_DATABASE_PORT)
  --user, -U             Database user (overrides SEAD_AUTHORITY_OPTIONS_DATABASE_USER)
  --host, -h             Database host (overrides SEAD_AUTHORITY_OPTIONS_DATABASE_HOST)
  --generate-deploy-sql  Generate the deploy SQL file only     
  --deploy, -D           Deploy the generated schema to the target database
  --schema-folder        Directory to store generated SQL files (default: ${g_schema_folder})
  --help                 Show this help message and exit

Additional options provided will be passed directly to the psql command.

EOF 
    if [ "$1" != "" ]; then
        exit 1
    else
        exit 0
    fi
}


pushd "${g_root_dir}" > /dev/null

PASSTHROUGHS=()
while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in
        --database|-d) g_db="$2"; shift 2;
        ;;
        --port|-p)
            g_port="$2"; shift 2;
        ;;
        --user|-U)
            g_user="$2"; shift 2;
        ;;
        --host|-h)
            g_host="$2"; shift 2;
        ;;
        --schema-folder)
            g_schema_folder="$2"; shift 2;
        ;;
        --generate-deploy-sql)
            g_generate_deploy_sql=YES
            shift
        ;;
        --deploy|-D)
            g_deploy=YES
            shift
        ;;
        --help)
            psql --help
            exit 0
        ;;
        --deploy|-D)
            g_deploy=YES
            shift
        ;;
        *)
        PASSTHROUGHS+=("$1")
        shift
        ;;
    esac
done

if [ "$g_db" == "" ] || [ "$g_user" == "" ] || [ "$g_host" == "" ]; then
    usage 'fatal: target database connection options not specified!'
fi

set -- "${PASSTHROUGHS[@]}"
function cleanup {
    echo "info: cleaning up generated schema files"
    rm -rf schema/generated
    rm -f ${g_deploy_sql_filename}
}

function generate_deploy_sql {
    echo "info: generating entity schema files"
    mkdir -p "${g_schema_folder}"
    
    @PYTHONPATH=. uv run python src/scripts/generate_entity_schema.py --all --force \
        --config config/entities.yml \
        --template-dir schema/templates \
        --output-dir schema/generated

    echo "info: schema generation completed and stored in schema/generated/"

    echo "info: generating deploy SQL file ${g_deploy_sql_filename}"

    cat <<EOF > ${g_deploy_sql_filename}
\set quiet on
\set echo none
\set verbosity terse
set client_min_messages = warning;
begin;
\i schema/sql/authority.sql
\i schema/sql/utility.sql
EOF

    for sql_file in $(ls schema/generated/*.sql | grep -v "semantic-" | sort); do
        echo "\i $sql_file" >> ${g_deploy_sql_filename}
    done
    for sql_file in $(ls schema/generated/*.sql | grep "semantic-" | sort); do
        echo "\i $sql_file" >> ${g_deploy_sql_filename}
    done
    echo "commit;" >> ${g_deploy_sql_filename}
}

function deploy_schema {
    echo "info: deploying schema to database"
    psql -h "$g_host" -p "$g_port" -U "$g_user" -d "$g_db" -v ON_ERROR_STOP=1 -q -t -A -f ${g_deploy_sql_filename}
    echo "info: installation completed!"
}

if [ "$g_generate_deploy_sql" == "YES" ]; then
    cleanup
    generate_deploy_sql
fi

if [ "$g_deploy" == "YES" ]; then

    deploy_schema
    echo "info: schema generation completed. To deploy the schema, re-run with the --deploy option."
fi


# embeddings are updated client-side now
# \i schema/sql/update_embeddings.sql
# ${HOME}/bin/sql -v ON_ERROR_STOP=1 -q -t -A -c "call authority.update_all_embeddings(true);"

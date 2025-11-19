#!/bin/bash
# Install script for SEAD Authority Service database

set -e

DEPLOY_SQL_FILE="schema/__deploy__.sql"

if [ -d "./schema" ]; then
    echo "info: changing to root directory"
    cd "$(dirname "$0")/.."
fi

rm -rf schema/generated && mkdir -p schema/generated

echo "info: generating entity SQL files"

uv run python src/scripts/generate_entity_schema.py --all --force \
    --config config/entities.yml \
    --template-dir schema/templates \
    --output-dir schema/generated

echo "info: generating deploy SQL file ${DEPLOY_SQL_FILE}"

cat <<EOF > ${DEPLOY_SQL_FILE}
\set quiet on
\set echo none
\set verbosity terse
set client_min_messages = warning;
begin;
\i schema/sql/authority.sql
\i schema/sql/utility.sql
\i schema/sql/update_embeddings.sql
EOF

for sql_file in $(ls schema/generated/*.sql | sort); do
    echo "\i $sql_file" >> ${DEPLOY_SQL_FILE}
done
echo "commit;" >> ${DEPLOY_SQL_FILE}

echo "info: running schema deploy SQL file ${DEPLOY_SQL_FILE}"

${HOME}/bin/sql -v ON_ERROR_STOP=1 -q -t -A -f ${DEPLOY_SQL_FILE}
echo "info: installation completed!"

${HOME}/bin/sql -v ON_ERROR_STOP=1 -q -t -A -c "call authority.update_all_embeddings(true);"

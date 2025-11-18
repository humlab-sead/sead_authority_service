#!/bin/bash
# Install script for SEAD Authority Service database

cat <<EOF > sql/temp_install_all.sql
\set quiet on
\set echo none
\set verbosity terse
set client_min_messages = warning;
begin;
EOF

for sql_file in $(ls sql/[0-5][0-9]_*.sql | sort); do
    echo "\i $sql_file" >> sql/temp_install_all.sql
done
echo "commit;" >> sql/temp_install_all.sql

echo "info: Installation script generated at sql/temp_install_all.sql"

/home/roger/bin/sql -q -t -A -f sql/temp_install_all.sql

echo "info: Installation complete."
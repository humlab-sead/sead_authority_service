create extension if not exists unaccent;
create extension if not exists pg_trgm;
create extension if not exists postgis;
create extension if not exists vector; -- apt install -y postgresql-16-pgvector

select version();

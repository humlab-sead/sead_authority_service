
create table if not exists bugs_trace
(
    bugs_trace_id serial not null primary key,
    bugs_table character varying(100),
    bugs_data character varying,
    bugs_identifier character varying,
    sead_table character varying(255),
    sead_reference_id integer not null,
    change_date timestamp with time zone default now(),
    manipulation_type character varying(50),
    translated_compressed_data character varying,
    constraint bugs_trace_pkey primary key (bugs_trace_id)
)

create index if not exists idx_bugs_trace_bugs_table_bugs_identifier
    on bugs_trace using btree (bugs_table, bugs_identifier);

create index if not exists idx_bugs_trace_bugs_table_sead_table_bugs_identifier
    on bugs_trace using btree (bugs_table, sead_table, bugs_identifier);

create index if not exists idx_bugs_trace_sead_table_sead_reference_id
    on bugs_trace using btree (sead_table, sead_reference_id asc nulls last);

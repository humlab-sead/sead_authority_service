### Introduction

This an example of an existing of an existing system that keeps and updates links between SEAD and a remote system.

The SEAD BugsCEP Import System integrates BugsCEP data into the SEAD platform. The import design allows both inserting new data and updating already imported data, which necessitates a mechanism for tracking association of BugsCEP data with SEAD data.

### Identity Links Table

The "bugs_trace" table stores the identity links. The keys on the BugsCEP side is table name in BugsCEP, the record's identity in BugsCEP and the record serialized as a string. The keys on the SEAD side is the tables name and the record's primary key (integer) in SEAD.

It will store the original data from the bugs table, the identifier of the bugs data, the corresponding SEAD table and reference ID, the type of manipulation (insert, update, delete), and a compressed version of the original data for easier retrieval. This will allow us to track changes and maintain a history of modifications for auditing and debugging purposes.

| Column Name | Data Type | Description |
| --- | --- | --- |
| bugs_trace_id | serial | Unique identifier for each trace entry. |
| bugs_table | character varying(100) | Name of the original BugsCEP table. |
| bugs_identifier | character varying | Unique identifier for the BugsCEP data, used to track changes. |
| bugs_data | character varying | Original data from the BugsCEP table, serialized as a string. |
| sead_table | character varying(255) | Name of the corresponding SEAD table where the data is stored. |
| sead_reference_id | integer | Reference ID in the SEAD table that corresponds to the BugsCEP data. |
| manipulation_type | character varying(50) | Type of manipulation performed (e.g., insert, update, delete). |
| change_date | timestamp with time zone | Timestamp of when the change was made, defaulting to the current time. |
| ~~translated_compressed_data~~ | character varying | Updated version of bugs_data (not part of identity system) |

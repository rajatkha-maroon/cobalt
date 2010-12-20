--Partition Tables
SET CURRENT SCHEMA COBALT_DB_DEV

CREATE TABLE PARTITION_STATE (
    ID INTEGER GENERATED BY DEFAULT AS IDENTITY (START WITH 1, INCREMENT BY 1, CACHE 10 ORDER) NOT NULL PRIMARY KEY,
    LOG_ENTRY_ID INTEGER NOT NULL REFERENCES "COBALT_LOG_ENTRY" ("ID") ON DELETE CASCADE,
    NAME VARCHAR(128) NOT NULL,
    QUEUE VARCHAR(128) NOT NULL,
    STATE VARCHAR(32) NOT NULL,
    BACKFILL_TIME TIMESTAMP NOT NULL,
    RESERVED_UNTIL TIMESTAMP NOT NULL,
    SIZE INTEGER NOT NULL,
    PARENTS CLOB NOT NULL,
    CHILDREN CLOB NOT NULL,
    RESERVED_BY CLOB NOT NULL,
    NODE_CARDS CLOB NOT NULL,
    SWITCHES CLOB NOT NULL,
    USED_BY CLOB NOT NULL,
    WIRING_CONFLICTS CLOB NOT NULL,
    CLEANUP_PENDING INTEGER NOT NULL,
    SCHEDULED INTEGER NOT NULL,
    FUNCTIONAL INTEGER NOT NULL,
    DRAINING INTEGER NOT NULL
)
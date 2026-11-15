"""SQLite storage for the outreach CRM. Stdlib only."""

import os
import sqlite3

DEFAULT_DB = os.path.join(os.path.expanduser("~"), ".outreach_crm.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    org TEXT,
    role TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id),
    sent_date TEXT NOT NULL,          -- ISO date, YYYY-MM-DD
    subject TEXT,
    kind TEXT NOT NULL DEFAULT 'initial',   -- initial | follow-up
    status TEXT NOT NULL DEFAULT 'sent',    -- sent | replied | dead
    followup_days INTEGER NOT NULL DEFAULT 5,
    notes TEXT
);
"""


def connect(db_path=DEFAULT_DB):
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)
    return db

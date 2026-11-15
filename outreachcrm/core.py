"""Core CRM logic: contacts, outreach entries, follow-up scheduling, stats."""

import datetime

VALID_KINDS = ("initial", "follow-up")
VALID_STATUSES = ("sent", "replied", "dead")


def _today():
    return datetime.date.today()


def _days_between(d1, d2):
    """Days from ISO date string d1 to date d2."""
    return (d2 - datetime.date.fromisoformat(d1)).days


def add_contact(db, name, email, org=None, role=None, notes=None):
    if not name or not name.strip():
        raise ValueError("contact name must not be empty")
    email = (email or "").strip()
    if "@" not in email:
        raise ValueError(f"not an email address: {email!r}")
    cur = db.execute(
        "INSERT INTO contacts (name, email, org, role, notes, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (name.strip(), email, org, role, notes, _today().isoformat()),
    )
    db.commit()
    return cur.lastrowid


def get_contact(db, contact_id):
    row = db.execute("SELECT * FROM contacts WHERE id = ?",
                     (contact_id,)).fetchone()
    if row is None:
        raise KeyError(f"no contact with id {contact_id}")
    return dict(row)


def find_contact(db, email):
    row = db.execute("SELECT * FROM contacts WHERE email = ?",
                     (email.strip(),)).fetchone()
    return dict(row) if row else None


def log_outreach(db, contact_id, subject=None, kind="initial",
                 sent_date=None, followup_days=5, notes=None):
    """Record a sent email. Returns the outreach id."""
    if kind not in VALID_KINDS:
        raise ValueError(f"kind must be one of {VALID_KINDS}")
    if followup_days < 1:
        raise ValueError("followup_days must be at least 1")
    get_contact(db, contact_id)  # raises if missing
    sent_date = sent_date or _today().isoformat()
    datetime.date.fromisoformat(sent_date)  # validate
    cur = db.execute(
        "INSERT INTO outreach (contact_id, sent_date, subject, kind,"
        " status, followup_days, notes) VALUES (?, ?, ?, ?, 'sent', ?, ?)",
        (contact_id, sent_date, subject, kind, followup_days, notes),
    )
    db.commit()
    return cur.lastrowid


def mark_status(db, contact_id, status):
    """Mark a contact's most recent outreach replied or dead."""
    if status not in ("replied", "dead"):
        raise ValueError("status must be 'replied' or 'dead'")
    row = db.execute(
        "SELECT id FROM outreach WHERE contact_id = ?"
        " ORDER BY sent_date DESC, id DESC LIMIT 1",
        (contact_id,),
    ).fetchone()
    if row is None:
        raise ValueError("contact has no outreach to update")
    db.execute("UPDATE outreach SET status = ? WHERE id = ?",
               (status, row["id"]))
    db.commit()


def followups_due(db, today=None):
    """Contacts whose follow-up window has opened.

    A contact is due when their latest outreach is still 'sent' (no reply)
    and at least followup_days have passed since it went out. A follow-up
    you already logged becomes the new latest outreach and resets the clock.
    """
    today = today or _today()
    due = []
    for contact in db.execute("SELECT * FROM contacts").fetchall():
        latest = db.execute(
            "SELECT * FROM outreach WHERE contact_id = ?"
            " ORDER BY sent_date DESC, id DESC LIMIT 1",
            (contact["id"],),
        ).fetchone()
        if latest is None or latest["status"] != "sent":
            continue
        waited = _days_between(latest["sent_date"], today)
        if waited >= latest["followup_days"]:
            due.append({
                "contact": dict(contact),
                "last_outreach": dict(latest),
                "days_waiting": waited,
                "overdue_by": waited - latest["followup_days"],
            })
    due.sort(key=lambda d: d["overdue_by"], reverse=True)
    return due


def pipeline(db):
    """Every contact with their latest status and outreach count."""
    rows = []
    for contact in db.execute("SELECT * FROM contacts ORDER BY name").fetchall():
        entries = db.execute(
            "SELECT * FROM outreach WHERE contact_id = ?"
            " ORDER BY sent_date DESC, id DESC",
            (contact["id"],),
        ).fetchall()
        rows.append({
            "contact": dict(contact),
            "outreach_count": len(entries),
            "latest": dict(entries[0]) if entries else None,
        })
    return rows


def stats(db):
    """Funnel numbers: emails sent, replies, reply rate, per-org breakdown."""
    total = db.execute("SELECT COUNT(*) c FROM outreach").fetchone()["c"]
    initials = db.execute(
        "SELECT COUNT(*) c FROM outreach WHERE kind = 'initial'"
    ).fetchone()["c"]
    replied_contacts = db.execute(
        "SELECT COUNT(DISTINCT contact_id) c FROM outreach"
        " WHERE status = 'replied'"
    ).fetchone()["c"]
    rate = (replied_contacts / initials) if initials else 0.0
    by_org = {}
    for row in db.execute(
        "SELECT c.org, COUNT(o.id) sent,"
        " SUM(CASE WHEN o.status = 'replied' THEN 1 ELSE 0 END) replies"
        " FROM outreach o JOIN contacts c ON c.id = o.contact_id"
        " GROUP BY c.org"
    ).fetchall():
        by_org[row["org"] or "(no org)"] = {
            "sent": row["sent"], "replies": row["replies"],
        }
    return {
        "emails_sent": total,
        "initial_emails": initials,
        "contacts_replied": replied_contacts,
        "reply_rate": rate,
        "by_org": by_org,
    }

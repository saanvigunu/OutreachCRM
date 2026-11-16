"""Command line interface for the outreach CRM."""

import argparse
import sys

from . import core
from .db import DEFAULT_DB, connect


def _db(args):
    return connect(args.db)


def cmd_add(args):
    db = _db(args)
    cid = core.add_contact(db, args.name, args.email,
                           org=args.org, role=args.role, notes=args.notes)
    print(f"added contact #{cid}: {args.name} <{args.email}>")
    return 0


def cmd_log(args):
    db = _db(args)
    contact = core.find_contact(db, args.email)
    if contact is None:
        print(f"no contact with email {args.email} - add them first",
              file=sys.stderr)
        return 1
    oid = core.log_outreach(
        db, contact["id"], subject=args.subject,
        kind=args.kind, sent_date=args.date,
        followup_days=args.followup_days, notes=args.notes,
    )
    print(f"logged {args.kind} outreach #{oid} to {contact['name']}"
          f" (follow up in {args.followup_days}d)")
    return 0


def cmd_due(args):
    db = _db(args)
    due = core.followups_due(db)
    if not due:
        print("nothing due - inbox zero on follow-ups")
        return 0
    print(f"{len(due)} follow-up(s) due:\n")
    for d in due:
        c, last = d["contact"], d["last_outreach"]
        org = f" @ {c['org']}" if c["org"] else ""
        print(f"  {c['name']}{org} <{c['email']}>")
        print(f"    last email: {last['sent_date']}"
              f" ({d['days_waiting']}d ago, {d['overdue_by']}d overdue)")
        if last["subject"]:
            print(f"    subject: {last['subject']}")
    return 0


def cmd_list(args):
    db = _db(args)
    rows = core.pipeline(db)
    if not rows:
        print("no contacts yet - 'add' one first")
        return 0
    for r in rows:
        c = r["contact"]
        org = f" @ {c['org']}" if c["org"] else ""
        if r["latest"]:
            state = f"{r['latest']['status']} ({r['outreach_count']} emails," \
                    f" last {r['latest']['sent_date']})"
        else:
            state = "not contacted yet"
        print(f"  #{c['id']} {c['name']}{org}: {state}")
    return 0


def cmd_mark(args):
    db = _db(args)
    contact = core.find_contact(db, args.email)
    if contact is None:
        print(f"no contact with email {args.email}", file=sys.stderr)
        return 1
    core.mark_status(db, contact["id"], args.status)
    print(f"marked {contact['name']} as {args.status}")
    return 0


def cmd_stats(args):
    db = _db(args)
    s = core.stats(db)
    print(f"emails sent:      {s['emails_sent']}"
          f" ({s['initial_emails']} initial)")
    print(f"contacts replied: {s['contacts_replied']}")
    print(f"reply rate:       {s['reply_rate']:.0%} of contacted")
    if s["by_org"]:
        print("\nby org:")
        for org, o in sorted(s["by_org"].items()):
            print(f"  {org}: {o['sent']} sent, {o['replies']} replies")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="outreach-crm",
        description="Track cold emails and never miss a follow-up.",
    )
    parser.add_argument("--db", default=DEFAULT_DB,
                        help="sqlite database path")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="add a contact")
    p.add_argument("name")
    p.add_argument("email")
    p.add_argument("--org")
    p.add_argument("--role")
    p.add_argument("--notes")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("log", help="log a sent email")
    p.add_argument("email", help="contact's email")
    p.add_argument("--subject")
    p.add_argument("--kind", choices=core.VALID_KINDS, default="initial")
    p.add_argument("--date", help="sent date, YYYY-MM-DD (default: today)")
    p.add_argument("--followup-days", type=int, default=5)
    p.add_argument("--notes")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("due", help="show follow-ups due now")
    p.set_defaults(func=cmd_due)

    p = sub.add_parser("list", help="show the whole pipeline")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("mark", help="mark a contact replied or dead")
    p.add_argument("email")
    p.add_argument("status", choices=("replied", "dead"))
    p.set_defaults(func=cmd_mark)

    p = sub.add_parser("stats", help="funnel stats and reply rates")
    p.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

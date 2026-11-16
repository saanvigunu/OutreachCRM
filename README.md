# Outreach CRM

A command-line CRM for cold-email outreach. Track who you've emailed, when,
and about what - and get a daily list of the follow-ups that are due, so a
good thread never dies because you forgot about it.

Built for running lots of cold outreach (internships, research labs,
sponsors): hundreds of threads, one terminal.

## how it works

Everything lives in one SQLite file (`~/.outreach_crm.db`). Two tables:
`contacts` (people) and `outreach` (every email you send, initial or
follow-up).

The follow-up engine: each email you log carries a `followup_days` window
(default 5). A contact shows up in `due` when their latest email is still
unanswered and the window has opened. Logging a follow-up resets the clock;
marking them `replied` or `dead` takes them off the board for good.

## quick start

No dependencies - Python 3.8+ stdlib only.

```bash
# add a contact
python3 -m outreachcrm.cli add "Alice Chen" alice@lab.berkeley.edu \
    --org BAIR --role "PhD student"

# log the cold email you just sent (default: 5-day follow-up window)
python3 -m outreachcrm.cli log alice@lab.berkeley.edu \
    --subject "undergrad interested in your robotics work"

# every morning: what's due?
python3 -m outreachcrm.cli due

# when you send the follow-up, log it - the clock resets
python3 -m outreachcrm.cli log alice@lab.berkeley.edu --kind follow-up

# when they reply (or don't, for good)
python3 -m outreachcrm.cli mark alice@lab.berkeley.edu replied
python3 -m outreachcrm.cli mark alice@lab.berkeley.edu dead

# the whole board, and the funnel numbers
python3 -m outreachcrm.cli list
python3 -m outreachcrm.cli stats
```

`due` output sorts by how overdue each thread is, worst first:

```
2 follow-up(s) due:

  Alice Chen @ BAIR <alice@lab.berkeley.edu>
    last email: 2026-11-08 (7d ago, 2d overdue)
    subject: undergrad interested in your robotics work
```

## stats

`stats` gives the funnel: total emails, initial emails, contacts who
replied, reply rate, and a per-org breakdown - so you can see which kinds
of places actually answer.

## tests

```bash
python3 -m unittest discover -s tests -v
```

Covers contact validation, every follow-up-due path (window boundaries,
clock resets, replied/dead contacts, overdue ordering), the funnel stats,
and the pipeline view.

## project structure

```
outreachcrm/
  __init__.py
  db.py      # SQLite schema and connection
  core.py    # contacts, outreach logging, follow-up engine, stats
  cli.py     # add / log / due / list / mark / stats
tests/
  test_crm.py
```
